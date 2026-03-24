"""CLI Executor - Executes kiro-cli commands via subprocess with PTY support"""
import subprocess
import json
import os
import sys
import re
import threading
import time
from typing import Dict, Any, Optional, Tuple, Callable, List

IS_WINDOWS = sys.platform == "win32"

ANSI_RE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]|\x1b\[\?[0-9]*[hl]|\x1b\[[\d;]*m|\x1b\][^\x1b]*\x1b\\')
# Control-only ANSI: cursor movement, erase, mode switches, OSC — NOT SGR (formatting)
ANSI_CTRL_RE = re.compile(
    r'\x1b\[\?[0-9]*[hl]'        # mode set/reset (?25h, ?2004l)
    r'|\x1b\[\d*[ABCDEFGHJKST]'  # cursor movement, erase line/screen
    r'|\x1b\][^\x1b]*\x1b\\'     # OSC sequences
)


class CLIExecutor:
    """Executes kiro-cli commands via PTY for full interactive support"""

    def __init__(self, cli_command: str = "kiro-cli"):
        self.cli_command = cli_command
        self.chat_process = None
        self.chat_output_callback = None
        self.chat_reader_thread = None
        self._pty_master = None
        self._last_sent = None  # for echo filtering
        self._context_callback = None
        self._cached_tools = []  # (name, permission, server) tuples from /tools
        self._collecting_tools = False
        self._tools_ready_callback = None
        self._tools_current_server = None
        self._in_response = False
        self._awaiting_trust_options = False

    def _build_cmd(self, args: list) -> list:
        if IS_WINDOWS:
            return ["wsl", self.cli_command] + args
        return [self.cli_command] + args

    @staticmethod
    def _setup_pty_child():
        """Set up child with PTY as controlling terminal for proper Ctrl+C."""
        import fcntl, termios
        os.setsid()
        fcntl.ioctl(0, termios.TIOCSCTTY, 0)

    def _build_chat_cmd(self, agent=None, model=None, trusted_tools=None) -> list:
        """Build chat command with standard flags."""
        args = ["chat", "--legacy-ui", "--wrap", "never"]
        if agent:
            args += ["--agent", agent]
        if model and model != "auto":
            args += ["--model", model]
        if trusted_tools is not None:
            args += ["--trust-tools", ",".join(trusted_tools)]
        return args

    @staticmethod
    def _clean(text: str) -> str:
        return ANSI_RE.sub('', text).strip()

    @staticmethod
    def _clean_display(text: str) -> str:
        """Strip control ANSI but keep SGR formatting (bold, color)."""
        return ANSI_CTRL_RE.sub('', text).strip()

    @staticmethod
    def _is_noise(line: str) -> bool:
        """Filter spinner, banner, box drawing, metadata lines."""
        if not line:
            return True
        c = line[0]
        # Braille spinner chars
        if '\u2800' <= c <= '\u28ff' or '\u2840' <= c <= '\u28ff':
            return True
        # Box drawing, decorations
        if c in "╭╰│╮╯─▔▸":
            return True
        noise_kw = ("Logging in", "Logging out", "Opening browser", "▰", "▱",
                     "Did you know", "Model:", "Pro Tips", "/compact",
                     "/context show", "Run /clear")
        return any(kw in line for kw in noise_kw)

    # ── Chat session (PTY) ──────────────────────────────────────────

    def start_chat_session(self, output_callback: Callable[[str], None],
                           agent=None, model=None, trusted_tools=None, cwd=None) -> bool:
        """Start chat session using PTY for full interactive support."""
        self.stop_chat_session()
        try:
            args = self._build_chat_cmd(agent, model, trusted_tools)
            self.chat_output_callback = output_callback

            if IS_WINDOWS:
                # Use wsl script to allocate PTY inside WSL
                inner = f"export LANG=C.UTF-8 LC_ALL=C.UTF-8; {self.cli_command} {' '.join(args)}"
                cmd = ["wsl", "script", "-qc", inner, "/dev/null"]
                self.chat_process = subprocess.Popen(
                    cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, encoding='utf-8', errors='replace'
                )
                self.chat_reader_thread = threading.Thread(
                    target=self._read_chat_pipe, daemon=True)
            else:
                import pty, struct, fcntl, termios
                master, slave = pty.openpty()
                # Set PTY to wide terminal so kiro-cli doesn't wrap/break lines
                fcntl.ioctl(slave, termios.TIOCSWINSZ,
                            struct.pack('HHHH', 50, 500, 0, 0))
                self._pty_master = master
                self.chat_process = subprocess.Popen(
                    [self.cli_command] + args,
                    stdin=slave, stdout=slave, stderr=slave,
                    close_fds=True, cwd=cwd,
                    preexec_fn=self._setup_pty_child
                )
                os.close(slave)
                self.chat_reader_thread = threading.Thread(
                    target=self._read_chat_pty, daemon=True)

            self.chat_reader_thread.start()
            return True
        except Exception as e:
            output_callback(f"Error starting chat: {e}")
            return False

    def _read_chat_pty(self):
        """Read from PTY master fd (Linux)."""
        import select
        buf = ""
        try:
            while True:
                r, _, _ = select.select([self._pty_master], [], [], 0.5)
                if not r:
                    if self.chat_process and self.chat_process.poll() is not None:
                        break
                    # Check if tools collection timed out (1s after last Total)
                    if self._collecting_tools and hasattr(self, '_tools_last_total_time'):
                        if time.time() - self._tools_last_total_time > 1.0:
                            self._collecting_tools = False
                            if self._tools_ready_callback:
                                self._tools_ready_callback()
                                self._tools_ready_callback = None
                    # Flush buffer if it contains a prompt line (no trailing \n)
                    if buf:
                        clean = self._clean(buf)
                        if self._PROMPT_RE.search(clean) and len(clean) < 60:
                            try:
                                self._process_line(buf)
                            except Exception:
                                pass
                            buf = ""
                    continue
                try:
                    data = os.read(self._pty_master, 4096).decode('utf-8', errors='replace')
                except OSError:
                    break
                if not data:
                    break
                buf += data
                # First, extract all complete lines (before \n)
                while '\n' in buf:
                    line, buf = buf.split('\n', 1)
                    # Strip trailing \r from \r\n line endings first
                    line = line.rstrip('\r')
                    # Handle \x1b[2K within this line (erase line = discard before it)
                    if '\x1b[2K' in line:
                        line = line.rsplit('\x1b[2K', 1)[-1]
                    # Handle internal \r (prompt/spinner redraws)
                    if '\r' in line:
                        line = line.rsplit('\r', 1)[-1]
                    try:
                        self._process_line(line)
                    except Exception:
                        pass
                # Handle \x1b[2K in remaining buffer (current incomplete line only)
                if '\x1b[2K' in buf:
                    buf = buf.rsplit('\x1b[2K', 1)[-1]
                # Check for trust picker prompt (no trailing \n)
                clean = self._clean(buf)
                if 'navigate' in clean.lower() and 'select' in clean.lower():
                    try:
                        self._process_line(buf)
                    except Exception:
                        pass
                    buf = ""
                # Check for prompt in buffer (no trailing \n) to capture context %
                elif self._PROMPT_RE.search(clean) and len(clean) < 60:
                    try:
                        self._process_line(buf)
                    except Exception:
                        pass
                    buf = ""
        except OSError:
            pass

    def _read_chat_pipe(self):
        """Read from pipe stdout (Windows/WSL script)."""
        try:
            buf = ""
            while self.chat_process.poll() is None:
                ch = self.chat_process.stdout.read(1)
                if not ch:
                    break
                if ch == '\r':
                    buf = ""
                    continue
                if ch == '\n':
                    self._process_line(buf)
                    buf = ""
                else:
                    buf += ch
        except Exception as e:
            if self.chat_output_callback:
                self.chat_output_callback(f"Error: {e}")

    # Prompt line pattern: "6% > ..." or "agent-name 12% > ..."
    _PROMPT_RE = re.compile(r'\d+%\s*>')
    _TOOL_LINE_RE = re.compile(r'^-\s+(\w+)\s+')

    def _process_line(self, raw: str):
        """Process a single line of chat output."""
        line = self._clean(raw)
        display = self._clean_display(raw)
        if not line:
            if self._in_response:
                if self.chat_output_callback:
                    self.chat_output_callback("")
            return

        # Filter prompt lines — always check (ends response)
        if self._PROMPT_RE.search(line) and len(line) < 60:
            self._in_response = False
            if self._collecting_tools:
                self._collecting_tools = False
                if self._tools_ready_callback:
                    self._tools_ready_callback()
                    self._tools_ready_callback = None
            m = re.search(r'(\d+)%', line)
            if m:
                self._last_context_pct = float(m.group(1))
                if self._context_callback:
                    self._context_callback(self._last_context_pct)
                    self._context_callback = None
                elif self.chat_output_callback:
                    self.chat_output_callback(f"__CONTEXT__:{self._last_context_pct}")
            return

        # If already in response, pass through with minimal filtering
        if self._in_response:
            if "Allow this action" in line or "[y/n" in line:
                self._in_response = False
                if self.chat_output_callback:
                    self.chat_output_callback(display)
                return
            if "navigate" in line.lower() and "select" in line.lower():
                self._in_response = False
                self._awaiting_trust_options = True
                if self.chat_output_callback:
                    self.chat_output_callback(f"__TRUST_PICKER__:{raw}")
                return
            if line.startswith("Tool") and "Permission" in line:
                self._in_response = False
                self._collecting_tools = True
                self._cached_tools = []
                self._tools_current_server = None
                return
            if line.startswith("▸ ") and re.match(r'^▸\s+(Time|Cost|Tokens)', line):
                return
            if "Thinking" in line:
                # Windows: response may be concatenated after spinner
                idx = line.find("Thinking...")
                if idx >= 0:
                    after = line[idx + len("Thinking..."):].strip()
                    if after:
                        if after.startswith("> "):
                            after = after[2:]
                        display = after
                        if self.chat_output_callback:
                            self.chat_output_callback(display)
                        return
                return
            if self.chat_output_callback:
                self.chat_output_callback(display)
            return

        # === Below: filters only apply OUTSIDE response ===

        # Filter echo of sent messages
        if self._last_sent:
            sent_lines = set(l.rstrip() for l in self._last_sent.split('\n') if l.strip())
            if line.rstrip() in sent_lines:
                return
        if self._last_sent and '>' in line:
            for sl in self._last_sent.split('\n'):
                if sl.strip() and sl.strip() in line:
                    after = line.split(sl.strip(), 1)[-1].strip()
                    if not after:
                        return
                    break

        # Context usage capture
        if "% used" in line or "Context window" in line:
            m = re.search(r'([\d.]+)%\s*used', line)
            if m and self._context_callback:
                self._context_callback(float(m.group(1)))
                self._context_callback = None
            return
        if any(kw in line for kw in ("% (estimated)", "Run /clear")):
            return
        if '█' in line or ('|' in line and '%' in line and '█' in raw):
            m = re.search(r'([\d.]+)%', line)
            if m and self._context_callback:
                self._context_callback(float(m.group(1)))
                self._context_callback = None
            return

        # Response metadata
        if line.startswith("▸ "):
            return

        # Spinner/thinking
        if "Thinking" in line:
            # Windows: response may be concatenated after spinner
            idx = line.find("Thinking...")
            if idx >= 0:
                after = line[idx + len("Thinking..."):].strip()
                if after:
                    if after.startswith("> "):
                        after = after[2:]
                    line = after
                    display = after
                    # Fall through to process as response
                else:
                    return
            else:
                return

        # Noise filter
        if self._is_noise(line):
            return

        # /tools trust/untrust confirmation and echo
        if "is now trusted" in line or "is set to per-request" in line or "All tools are now trusted" in line or "are set to per-request" in line:
            return
        if line.startswith("/tools") or (self._last_sent and self._last_sent.startswith("/tools") and all(w.replace("@","").replace("/","").replace("-","").replace("_","").isalnum() for w in line.split())):
            return

        # /tools output
        if line.startswith("Tool") and "Permission" in line:
            self._collecting_tools = True
            self._cached_tools = []
            self._tools_current_server = None
            return
        if self._collecting_tools:
            if line.startswith("Total"):
                self._tools_last_total_time = time.time()
                return
            m_tool = self._TOOL_LINE_RE.match(line)
            if m_tool:
                name = m_tool.group(1)
                # Parse permission: check negatives first ("not trusted" contains "trusted")
                ll = line.lower()
                if "not trusted" in ll or "per-request" in ll or "ask" in ll:
                    perm = "ask"
                elif "allowed" in ll:
                    perm = "allowed"
                else:
                    perm = "trusted"
                self._cached_tools.append((name, perm, self._tools_current_server))
                return
            if "(MCP)" in line:
                self._tools_current_server = "@" + line.split("(MCP)")[0].strip()
                return
            if line in ("Built-in", "Native"):
                self._tools_current_server = None
                return

        # Trust picker detection
        if "navigate" in line.lower() and "select" in line.lower():
            self._awaiting_trust_options = True
            if self.chat_output_callback:
                self.chat_output_callback(f"__TRUST_PICKER__:{raw}")
            return

        # Trust option lines — only when actively awaiting after picker
        if self._awaiting_trust_options and "→" in line:
            if self.chat_output_callback:
                self.chat_output_callback(f"__TRUST_OPTION__:{line}")
            return

        # Strip leading "> " from response first line
        if line.startswith("> "):
            line = line[2:]
            display = re.sub(r'^(?:\x1b\[\d*(?:;\d+)*m)*>\s', '', display)

        if self.chat_output_callback:
            self._in_response = True
            self.chat_output_callback(display)

    def send_chat_message(self, message: str) -> bool:
        """Send message to chat session."""
        self._last_sent = message
        try:
            if self._pty_master is not None:
                os.write(self._pty_master, (message + "\r").encode('utf-8'))
                return True
            elif self.chat_process and self.chat_process.poll() is None:
                self.chat_process.stdin.write(message + "\n")
                self.chat_process.stdin.flush()
                return True
        except Exception:
            pass
        return False

    def send_interrupt(self):
        """Send Ctrl+C through PTY (like terminal Ctrl+C)."""
        try:
            if self._pty_master is not None:
                os.write(self._pty_master, b'\x03')
                return True
        except Exception:
            pass
        # Windows/pipe fallback
        import signal
        try:
            if self.chat_process and self.chat_process.poll() is None:
                if IS_WINDOWS:
                    self.chat_process.send_signal(signal.CTRL_C_EVENT)
                else:
                    os.killpg(os.getpgid(self.chat_process.pid), signal.SIGINT)
                return True
        except Exception:
            pass
        return False

    def send_raw(self, data: bytes) -> bool:
        """Send raw bytes (escape sequences for trust picker)."""
        try:
            if self._pty_master is not None:
                os.write(self._pty_master, data)
                return True
            elif self.chat_process and self.chat_process.poll() is None:
                self.chat_process.stdin.buffer.write(data)
                self.chat_process.stdin.flush()
                return True
        except Exception:
            pass
        return False

    def stop_chat_session(self):
        if self._pty_master is not None:
            try:
                os.close(self._pty_master)
            except OSError:
                pass
            self._pty_master = None
        if self.chat_process:
            try:
                if self.chat_process.stdin and not self.chat_process.stdin.closed:
                    self.chat_process.stdin.close()
                self.chat_process.terminate()
                self.chat_process.wait(timeout=2)
            except Exception:
                try:
                    self.chat_process.kill()
                except Exception:
                    pass
            finally:
                self.chat_process = None

    # ── Non-chat commands ───────────────────────────────────────────

    def execute(self, args: list, parse_json=False) -> Tuple[bool, str, Optional[Dict]]:
        try:
            result = subprocess.run(
                self._build_cmd(args), capture_output=True, text=True,
                timeout=30, encoding='utf-8', errors='replace'
            )
            output = result.stdout.strip()
            parsed = None
            if parse_json and output:
                try:
                    parsed = json.loads(output)
                except json.JSONDecodeError:
                    pass
            return result.returncode == 0, output, parsed
        except subprocess.TimeoutExpired:
            return False, "Command timed out", None
        except FileNotFoundError:
            return False, f"Command '{self.cli_command}' not found", None
        except Exception as e:
            return False, f"Error: {e}", None

    def execute_interactive(self, args: list, output_callback: Callable[[str], None]):
        try:
            process = subprocess.Popen(
                self._build_cmd(args), stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, stdin=subprocess.PIPE,
                text=True, bufsize=0, encoding='utf-8', errors='replace'
            )
            buf = ""
            while True:
                ch = process.stdout.read(1)
                if not ch:
                    break
                if ch == '\r':
                    buf = ""
                    continue
                if ch == '\n':
                    line = self._clean(buf)
                    if line and not self._is_noise(line):
                        output_callback(line)
                    buf = ""
                else:
                    buf += ch
            if buf:
                line = self._clean(buf)
                if line and not self._is_noise(line):
                    output_callback(line)
            process.wait()
            return process.returncode == 0
        except Exception as e:
            output_callback(f"Error: {e}")
            return False

    # ── Agent management ────────────────────────────────────────────

    def agent_list(self) -> Tuple[bool, str, Optional[list]]:
        try:
            if IS_WINDOWS:
                result = subprocess.run(
                    ["wsl", "bash", "-lic", f"{self.cli_command} agent list"],
                    capture_output=True, text=True, timeout=10,
                    encoding='utf-8', errors='replace'
                )
                output = result.stdout + result.stderr
            else:
                import pty, select
                master, slave = pty.openpty()
                proc = subprocess.Popen(
                    [self.cli_command, "agent", "list"],
                    stdout=slave, stderr=slave, stdin=slave, close_fds=True
                )
                os.close(slave)
                output = ""
                while True:
                    r, _, _ = select.select([master], [], [], 5)
                    if r:
                        try:
                            data = os.read(master, 4096).decode('utf-8', errors='ignore')
                            if data:
                                output += data
                            else:
                                break
                        except OSError:
                            break
                    else:
                        break
                os.close(master)
                proc.wait(timeout=5)

            clean = ANSI_RE.sub('', output)
            agents = []
            for line in clean.split('\n'):
                m = re.match(r'^([* ]) (.+?)  {2,}', line)
                if m:
                    is_active = m.group(1) == '*'
                    name = m.group(2).strip()
                    if name:
                        agents.append((name, is_active))
            return True, clean, agents
        except Exception as e:
            return False, str(e), None

    def agent_swap(self, agent_name: str) -> Tuple[bool, str]:
        success, output, _ = self.execute(["agent", "swap", agent_name])
        return success, output

    # ── Model management ────────────────────────────────────────────

    def model_list(self) -> Tuple[bool, list]:
        """List models using --list-models --format json."""
        try:
            result = subprocess.run(
                self._build_cmd(["chat", "--list-models", "--format", "json"]),
                capture_output=True, text=True, timeout=10,
                encoding='utf-8', errors='replace'
            )
            data = json.loads(result.stdout)
            models = [m.get("model_name", m.get("name", ""))
                      for m in data.get("models", [])]
            if models:
                return True, models
        except Exception:
            pass
        return self._model_list_fallback()

    def _model_list_fallback(self) -> Tuple[bool, list]:
        """Fallback: parse error message from invalid model."""
        try:
            result = subprocess.run(
                self._build_cmd(["chat", "--model", "___invalid___"]),
                capture_output=True, text=True, timeout=10,
                encoding='utf-8', errors='replace'
            )
            m = re.search(r'Available models: (.+)', result.stdout + result.stderr)
            if m:
                return True, [x.strip() for x in m.group(1).split(',')]
        except Exception:
            pass
        return False, []

    # ── Chat management ─────────────────────────────────────────────

    def chat_save(self, name: str) -> Tuple[bool, str]:
        return self.send_chat_message(f"/save {name}"), name

    def chat_list_sessions(self) -> list:
        try:
            if IS_WINDOWS:
                result = subprocess.run(
                    ["wsl", "bash", "-lic", f"{self.cli_command} chat --list-sessions"],
                    capture_output=True, text=True, timeout=15,
                    encoding='utf-8', errors='replace'
                )
                output = result.stdout + result.stderr
            else:
                import pty, select
                master, slave = pty.openpty()
                proc = subprocess.Popen(
                    [self.cli_command, "chat", "--list-sessions"],
                    stdout=slave, stderr=slave, stdin=slave, close_fds=True
                )
                os.close(slave)
                output = ""
                while True:
                    r, _, _ = select.select([master], [], [], 10)
                    if r:
                        try:
                            data = os.read(master, 4096).decode('utf-8', errors='ignore')
                            if data:
                                output += data
                            else:
                                break
                        except OSError:
                            break
                    else:
                        break
                os.close(master)
                proc.wait(timeout=5)

            clean = ANSI_RE.sub('', output)
            sessions = []
            current_id = None
            for line in clean.split('\n'):
                m = re.search(r'SessionId:\s*(\S+)', line)
                if m:
                    current_id = m.group(1).strip()
                elif current_id and '|' in line:
                    parts = line.split('|')
                    preview = parts[1].strip() if len(parts) > 1 else ""
                    sessions.append((current_id, preview))
                    current_id = None
            return sessions
        except Exception:
            return []

    def poll_context(self, callback: Callable[[float], None]):
        """Return cached context percentage from prompt lines."""
        pct = getattr(self, '_last_context_pct', None)
        if pct is not None:
            callback(pct)
        else:
            self._context_callback = callback

    def refresh_tools(self, callback=None):
        """Send /tools to populate cached tool list. Optional callback when done."""
        self._collecting_tools = False
        self._tools_ready_callback = callback
        self.send_chat_message("/tools")

    def get_tools(self) -> list:
        """Return cached (name, permission, server) tuples."""
        return list(self._cached_tools)

    # ── Prompts ─────────────────────────────────────────────────────

    def prompt_list(self, project_path=None) -> list:
        prompts = {}
        global_dir = os.path.expanduser("~/.kiro/prompts")
        if os.path.isdir(global_dir):
            for f in os.listdir(global_dir):
                if f.endswith(".md"):
                    prompts[f[:-3]] = "global"
        if project_path:
            local_dir = os.path.join(project_path, ".kiro", "prompts")
            if os.path.isdir(local_dir):
                for f in os.listdir(local_dir):
                    if f.endswith(".md"):
                        prompts[f[:-3]] = "local"
        return sorted(prompts.items())

    def prompt_create(self, name, content, project_path=None, is_global=False):
        base = os.path.expanduser("~/.kiro/prompts") if is_global else os.path.join(project_path or ".", ".kiro", "prompts")
        os.makedirs(base, exist_ok=True)
        with open(os.path.join(base, f"{name}.md"), "w", encoding="utf-8") as f:
            f.write(content)
        return True

    def prompt_remove(self, name, project_path=None, is_global=False):
        base = os.path.expanduser("~/.kiro/prompts") if is_global else os.path.join(project_path or ".", ".kiro", "prompts")
        path = os.path.join(base, f"{name}.md")
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    @staticmethod
    def _read_file(path):
        try:
            return open(path, encoding="utf-8").read()
        except UnicodeDecodeError:
            return open(path, encoding="latin-1").read()

    def prompt_read(self, name, project_path=None):
        if project_path:
            local = os.path.join(project_path, ".kiro", "prompts", f"{name}.md")
            if os.path.exists(local):
                return self._read_file(local), False
        g = os.path.join(os.path.expanduser("~/.kiro/prompts"), f"{name}.md")
        if os.path.exists(g):
            return self._read_file(g), True
        return "", False

    # ── Auth ────────────────────────────────────────────────────────

    def login_interactive(self, output_callback, license=None, identity_provider=None, region=None):
        args = ["login", "--use-device-flow"]
        if identity_provider:
            args += ["--identity-provider", identity_provider]
        if region:
            args += ["--region", region]
        return self.execute_interactive(args, output_callback)

    def logout(self):
        success, output, _ = self.execute(["logout"])
        return success, output

    def whoami(self):
        success, output, _ = self.execute(["whoami"])
        return success, output
