"""CLI Executor - Executes kiro-cli commands via subprocess"""
import subprocess
import json
import os
import sys
import threading
import time
from typing import Dict, Any, Optional, Tuple, Callable

IS_WINDOWS = sys.platform == "win32"


class CLIExecutor:
    """Executes kiro-cli commands and parses outputs"""
    
    def __init__(self, cli_command: str = "kiro-cli"):
        self.cli_command = cli_command
        self.chat_process = None
        self.chat_output_callback = None
        self.chat_reader_thread = None
    
    def _build_cmd(self, args: list[str]) -> list[str]:
        """Build command list, prefixing with 'wsl' on Windows."""
        if IS_WINDOWS:
            return ["wsl", self.cli_command] + args
        return [self.cli_command] + args
    
    def start_chat_session(self, output_callback: Callable[[str], None], agent: str = None, cwd: str = None) -> bool:
        """Start a persistent kiro-cli chat session"""
        self.stop_chat_session()
        
        try:
            cmd = self._build_cmd(["chat"])
            if agent:
                cmd += ["--agent", agent]
            
            self.chat_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                text=True,
                bufsize=1,
                cwd=cwd
            )
            
            self.chat_output_callback = output_callback
            
            # Start thread to read output
            self.chat_reader_thread = threading.Thread(
                target=self._read_chat_output,
                daemon=True
            )
            self.chat_reader_thread.start()
            
            return True
            
        except Exception as e:
            output_callback(f"Error starting chat: {str(e)}")
            return False
    
    def _read_chat_output(self):
        """Read chat output in background thread"""
        import re
        ansi_escape = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')
        
        try:
            buffer = ""
            
            while self.chat_process.poll() is None:
                char = self.chat_process.stdout.read(1)
                if not char:
                    break
                
                if char == '\r':
                    buffer = ""
                    continue
                
                if char == '\n':
                    line = ansi_escape.sub('', buffer).strip()
                    buffer = ""
                    
                    if not line:
                        continue
                    
                    # Check if context output line (always filter, no flag needed)
                    if ("% used" in line or "Context window" in line or
                        "Pro Tips" in line or "% (estimated)" in line or
                        "/compact" in line or "/context show" in line or
                        "Run /clear" in line or
                        (line and "%" in line and ("█" in line or "░" in line))):
                        import re as _re
                        m = _re.search(r'([\d.]+)%\s*used', line)
                        if m and getattr(self, '_context_callback', None):
                            self._context_callback(float(m.group(1)))
                            self._context_callback = None
                        continue
                    
                    # Skip spinner/thinking lines
                    if "Thinking" in line:
                        if "> " in line:
                            resp = line.split("> ", 1)[1].strip()
                            if resp and self.chat_output_callback:
                                self.chat_output_callback(resp)
                        continue
                    
                    # Skip banner, box drawing, metadata
                    if (line and line[0] in "⠀⠁⠂⠃⠄⠅⠆⠇⠈⠉⠊⠋⠌⠍⠎⠏⠐⠑⠒⠓⠔⠕⠖⠗⠘⠙⠚⠛⠜⠝⠞⠟⠠⠡⠢⠣⠤⠥⠦⠧⠨⠩⠪⠫⠬⠭⠮⠯⠰⠱⠲⠳⠴⠵⠶⠷⠸⠹⠺⠻⠼⠽⠾⠿⡀⡁⢀⢁⣀⣁⣠⣡⣤⣥⣦⣧⣨⣩⣴⣵⣶⣷⣸⣹⣼⣽⣾⣿╭╰│╮╯─▔" or
                        "Did you know" in line or
                        "Model:" in line or
                        "▸" in line or
                        line.startswith(">")):
                        continue
                    
                    # Strip invisible chars
                    line = line.replace('\x1b[?25h', '').replace('\x1b[?25l', '').strip()
                    if not line:
                        continue
                    
                    if self.chat_output_callback and not getattr(self, '_capturing_tools', False):
                        self.chat_output_callback(line)
                else:
                    buffer += char
                        
        except Exception as e:
            if self.chat_output_callback:
                self.chat_output_callback(f"Error: {str(e)}")
    
    def send_chat_message(self, message: str) -> bool:
        """Send a message to the active chat session"""
        if not self.chat_process or self.chat_process.poll() is not None:
            return False
        
        try:
            self.chat_process.stdin.write(message + "\n")
            self.chat_process.stdin.flush()
            return True
        except Exception:
            return False
    
    def stop_chat_session(self):
        """Stop the chat session"""
        if self.chat_process:
            try:
                self.chat_process.stdin.close()
                self.chat_process.terminate()
                self.chat_process.wait(timeout=2)
            except Exception:
                self.chat_process.kill()
            finally:
                self.chat_process = None
    
    def execute(self, args: list[str], parse_json: bool = False) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Execute a kiro-cli command
        
        Returns:
            Tuple of (success, output_text, parsed_json)
        """
        try:
            result = subprocess.run(
                self._build_cmd(args),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = result.stdout.strip()
            success = result.returncode == 0
            
            parsed = None
            if parse_json and output:
                try:
                    parsed = json.loads(output)
                except json.JSONDecodeError:
                    pass
            
            return success, output, parsed
            
        except subprocess.TimeoutExpired:
            return False, "Command timed out", None
        except FileNotFoundError:
            return False, f"Command '{self.cli_command}' not found", None
        except Exception as e:
            return False, f"Error: {str(e)}", None
    
    def execute_interactive(self, args: list[str], output_callback: Callable[[str], None]):
        """Execute an interactive command and stream output, filtering spinners"""
        import re
        ansi_re = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]|\x1b\[\?[0-9]*[hl]')
        try:
            process = subprocess.Popen(
                self._build_cmd(args),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                text=True,
                bufsize=0
            )
            
            buffer = ""
            while True:
                char = process.stdout.read(1)
                if not char:
                    break
                if char == '\r':
                    buffer = ""
                    continue
                if char == '\n':
                    line = ansi_re.sub('', buffer).strip()
                    if line and "Logging in" not in line and "Opening browser" not in line and "▰" not in line and "▱" not in line:
                        output_callback(line)
                    buffer = ""
                else:
                    buffer += char
            
            # Flush remaining buffer
            if buffer:
                line = ansi_re.sub('', buffer).strip()
                if line and "Logging in" not in line and "Opening browser" not in line and "▰" not in line and "▱" not in line:
                    output_callback(line)
            
            process.wait()
            return process.returncode == 0
            
        except Exception as e:
            output_callback(f"Error: {str(e)}")
            return False
    
    def agent_list(self) -> Tuple[bool, str, Optional[list]]:
        """List available agents. Returns list of (name, is_active) tuples."""
        import re
        
        try:
            if IS_WINDOWS:
                # On Windows, use wsl which provides a TTY
                result = subprocess.run(
                    ["wsl", self.cli_command, "agent", "list"],
                    capture_output=True, text=True, timeout=10
                )
                output = result.stdout
            else:
                import pty, select
                master, slave = pty.openpty()
                process = subprocess.Popen(
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
                process.wait(timeout=5)
            
            # Strip ANSI codes
            ansi_escape = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')
            clean = ansi_escape.sub('', output)
            
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
        """Swap to a different agent"""
        success, output, _ = self.execute(["agent", "swap", agent_name])
        return success, output
    
    def model_list(self) -> Tuple[bool, list]:
        """List available models by triggering error with invalid model"""
        import re
        try:
            result = subprocess.run(
                self._build_cmd(["chat", "--model", "___invalid___"]),
                capture_output=True, text=True, timeout=10
            )
            output = result.stdout + result.stderr
            m = re.search(r'Available models: (.+)', output)
            if m:
                models = [x.strip() for x in m.group(1).split(',')]
                return True, models
            return False, []
        except Exception:
            return False, []
    
    def chat_save(self, name: str) -> Tuple[bool, str]:
        """Save current chat by sending /save command"""
        return self.send_chat_message(f"/save {name}"), name
    
    def chat_list_sessions(self) -> list:
        """List saved sessions. Returns list of (session_id, preview)."""
        import re
        try:
            if IS_WINDOWS:
                result = subprocess.run(
                    ["wsl", self.cli_command, "chat", "--list-sessions"],
                    capture_output=True, text=True, timeout=15
                )
                output = result.stdout
            else:
                import pty, select
                master, slave = pty.openpty()
                process = subprocess.Popen(
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
                process.wait(timeout=5)
            
            ansi = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')
            clean = ansi.sub('', output)
            
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
        """Send /context and capture usage percentage."""
        if not self.chat_process or self.chat_process.poll() is not None:
            return
        self._context_callback = callback
        try:
            self.chat_process.stdin.write("/context\n")
            self.chat_process.stdin.flush()
        except Exception:
            pass
    
    def prompt_list(self, project_path: str = None) -> list:
        """List prompts from local and global dirs. Returns [(name, source)]."""
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

    def prompt_create(self, name: str, content: str, project_path: str = None, is_global: bool = False) -> bool:
        """Create a prompt .md file."""
        base = os.path.expanduser("~/.kiro/prompts") if is_global else os.path.join(project_path or ".", ".kiro", "prompts")
        os.makedirs(base, exist_ok=True)
        with open(os.path.join(base, f"{name}.md"), "w") as f:
            f.write(content)
        return True

    def prompt_remove(self, name: str, project_path: str = None, is_global: bool = False) -> bool:
        """Remove a prompt .md file."""
        base = os.path.expanduser("~/.kiro/prompts") if is_global else os.path.join(project_path or ".", ".kiro", "prompts")
        path = os.path.join(base, f"{name}.md")
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def prompt_read(self, name: str, project_path: str = None) -> tuple:
        """Read prompt content. Returns (content, is_global)."""
        if project_path:
            local = os.path.join(project_path, ".kiro", "prompts", f"{name}.md")
            if os.path.exists(local):
                return open(local).read(), False
        glob = os.path.join(os.path.expanduser("~/.kiro/prompts"), f"{name}.md")
        if os.path.exists(glob):
            return open(glob).read(), True
        return "", False

    def login_interactive(self, output_callback: Callable[[str], None], license: str = None, identity_provider: str = None, region: str = None) -> bool:
        """Login using interactive flow with device flow"""
        args = ["login", "--use-device-flow"]
        if identity_provider:
            args += ["--identity-provider", identity_provider]
        if region:
            args += ["--region", region]
        return self.execute_interactive(args, output_callback)
    
    def logout(self) -> Tuple[bool, str]:
        """Logout from Kiro CLI"""
        success, output, _ = self.execute(["logout"])
        return success, output
    
    def whoami(self) -> Tuple[bool, str]:
        """Check current login status"""
        success, output, _ = self.execute(["whoami"])
        return success, output
