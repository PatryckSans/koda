from textual.app import App, ComposeResult, SystemCommand
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Header, Footer, ListView, ListItem, Input, Label, Button, Checkbox
from textual.screen import ModalScreen, Screen
from kiro_tui.components.sidebar import Sidebar, AgentsSection, ChatSection, AuthSection, ModelsSection, PromptsSection
from kiro_tui.components.chat import ChatArea, ActionPrompt, TrustPicker
from kiro_tui.components.status_bar import StatusBar
from kiro_tui.services.agent_manager import AgentManager
from kiro_tui.services.cli_executor import CLIExecutor
from kiro_tui.screens.project_selector import ProjectSelector
from kiro_tui.screens.login_screen import LoginScreen
from kiro_tui.i18n import t, load_lang_from_config
import json, os

CONFIG_PATH = os.path.expanduser("~/.config/koda/config.json")

def _load_config():
    try:
        with open(CONFIG_PATH, encoding="utf-8")as f:
            return json.load(f)
    except Exception:
        return {}

def _save_config(data):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8")as f:
        json.dump(data, f)


class InputModal(ModalScreen[str]):
    """Simple input modal that returns a string"""
    
    DEFAULT_CSS = """
    InputModal { align: center middle; }
    InputModal > Vertical {
        width: 60; height: auto; border: thick $primary;
        background: $surface; padding: 1 2;
    }
    """
    
    def __init__(self, title: str, placeholder: str = ""):
        super().__init__()
        self.title_text = title
        self.placeholder = placeholder
    
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self.title_text)
            yield Input(placeholder=self.placeholder, id="modal-input")
            with Horizontal():
                yield Button("OK", variant="primary", id="ok")
                yield Button("Cancel", id="cancel")
    
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "ok":
            self.dismiss(self.query_one("#modal-input", Input).value)
        else:
            self.dismiss("")
    
    def on_input_submitted(self, event: Input.Submitted):
        self.dismiss(event.value)


class ToolsModal(ModalScreen[dict]):
    """Modal to view and toggle tools"""
    
    DEFAULT_CSS = """
    ToolsModal { align: center middle; }
    ToolsModal > Vertical {
        width: 90%; height: 80%; border: thick $primary;
        background: $surface; padding: 1 2;
    }
    ToolsModal #tools-title { height: auto; margin-bottom: 1; }
    ToolsModal #tools-scroll { height: 1fr; border: solid $primary-darken-2; }
    ToolsModal #tools-scroll Checkbox { margin: 0; padding: 0 1; }
    ToolsModal #tools-buttons { height: auto; margin-top: 1; dock: bottom; }
    """
    
    def __init__(self, tools: list):
        super().__init__()
        self.tools = tools
        self.checkboxes = {}
    
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(t("tools_title"), id="tools-title")
            with VerticalScroll(id="tools-scroll"):
                for name, trusted in self.tools:
                    cb = Checkbox(name, value=trusted, id=f"tool-{name}")
                    self.checkboxes[name] = cb
                    yield cb
            with Horizontal(id="tools-buttons"):
                yield Button("Apply", variant="primary", id="apply")
                yield Button("Cancel", id="cancel")
    
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "apply":
            result = {name: cb.value for name, cb in self.checkboxes.items()}
            self.dismiss(result)
        else:
            self.dismiss({})


class SaveModal(ModalScreen[str]):
    """Save modal with input and existing files list"""
    
    DEFAULT_CSS = """
    SaveModal { align: center middle; }
    SaveModal > Vertical {
        width: 60; height: auto; max-height: 25; border: thick $primary;
        background: $surface; padding: 1 2;
    }
    #existing-label { margin-top: 1; }
    #existing-list { height: auto; max-height: 10; }
    """
    
    def __init__(self, title: str, placeholder: str, existing: list):
        super().__init__()
        self.title_text = title
        self.placeholder = placeholder
        self.existing = existing
    
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self.title_text)
            yield Input(placeholder=self.placeholder, id="modal-input")
            if self.existing:
                yield Label(t("or_overwrite"), id="existing-label")
                yield ListView(
                    *[ListItem(Label(f)) for f in self.existing],
                    id="existing-list"
                )
            with Horizontal():
                yield Button("OK", variant="primary", id="ok")
                yield Button("Cancel", id="cancel")
    
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "ok":
            self.dismiss(self.query_one("#modal-input", Input).value)
        else:
            self.dismiss("")
    
    def on_input_submitted(self, event: Input.Submitted):
        self.dismiss(event.value)
    
    def on_list_view_selected(self, event: ListView.Selected):
        idx = event.list_view.index
        if idx is not None and idx < len(self.existing):
            self.dismiss(self.existing[idx])


class PickerModal(ModalScreen[str]):
    """Modal to pick from a list of options"""
    
    DEFAULT_CSS = """
    PickerModal { align: center middle; }
    PickerModal > Vertical {
        width: 60; height: auto; max-height: 20; border: thick $primary;
        background: $surface; padding: 1 2;
    }
    """
    
    def __init__(self, title: str, options: list):
        super().__init__()
        self.title_text = title
        self.options = options
    
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self.title_text)
            yield ListView(
                *[ListItem(Label(opt)) for opt in self.options],
                id="picker-list"
            )
            yield Button("Cancel", id="cancel")
    
    def on_list_view_selected(self, event: ListView.Selected):
        idx = event.list_view.index
        if idx is not None and idx < len(self.options):
            self.dismiss(self.options[idx])
    
    def on_button_pressed(self, event: Button.Pressed):
        self.dismiss("")


class PromptsManagerModal(ModalScreen[str]):
    """Modal to manage prompts: create, edit, delete"""

    DEFAULT_CSS = """
    PromptsManagerModal { align: center middle; }
    PromptsManagerModal > Vertical {
        width: 70; height: auto; max-height: 30; border: thick $primary;
        background: $surface; padding: 1 2;
    }
    #pm-list { height: auto; max-height: 18; }
    """

    def __init__(self, prompts: list):
        super().__init__()
        self.prompts = prompts  # [(name, source)]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(t("prompt_manage"))
            yield ListView(
                *[ListItem(Label(f"{'[L]' if s == 'local' else '[G]'} {n}")) for n, s in self.prompts],
                id="pm-list"
            )
            with Horizontal():
                yield Button(t("prompt_create_action"), variant="primary", id="pm-create")
                yield Button(t("cancel"), id="pm-close")

    def on_list_view_selected(self, event: ListView.Selected):
        idx = event.list_view.index
        if idx is not None and idx < len(self.prompts):
            name, source = self.prompts[idx]
            self.dismiss(f"select:{name}:{'global' if source == 'global' else 'local'}")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "pm-create":
            self.dismiss("create")
        else:
            self.dismiss("")


class ConfirmModal(ModalScreen[bool]):
    DEFAULT_CSS = """
    ConfirmModal { align: center middle; }
    ConfirmModal > Vertical { width: 50; height: auto; border: thick $primary; background: $surface; padding: 1 2; }
    """
    BINDINGS = [("escape", "cancel", "Close")]

    def __init__(self, message: str, confirm_label: str = None, cancel_label: str = None):
        super().__init__()
        self._message = message
        self._confirm = confirm_label or t("yes")
        self._cancel = cancel_label or t("cancel")

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self._message)
            with Horizontal():
                yield Button(self._confirm, variant="error", id="confirm-yes")
                yield Button(self._cancel, id="confirm-no")

    def on_button_pressed(self, event: Button.Pressed):
        self.dismiss(event.button.id == "confirm-yes")

    def action_cancel(self):
        self.dismiss(False)


class ConfirmQuitModal(ModalScreen[bool]):
    DEFAULT_CSS = """
    ConfirmQuitModal { align: center middle; }
    ConfirmQuitModal > Vertical { width: 50; height: auto; border: thick $primary; background: $surface; padding: 1 2; }
    """
    BINDINGS = [("escape", "dismiss_quit", "Close")]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(t("confirm_quit"))
            with Horizontal():
                yield Button(t("yes"), variant="error", id="quit-yes")
                yield Button(t("no"), id="quit-no")

    def on_button_pressed(self, event: Button.Pressed):
        self.dismiss(event.button.id == "quit-yes")

    def action_dismiss_quit(self):
        self.dismiss(True)


class KodaApp(App):
    """KODA | Kiro Operator Dashboard Application"""

    TITLE = "KODA"
    SUB_TITLE = "Kiro Operator Dashboard Application"
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    #main-container {
        height: 1fr;
    }
    
    Button:hover {
        text-style: bold reverse;
    }
    
    PickerModal ListItem:hover, SaveModal ListItem:hover, PromptsManagerModal ListItem:hover {
        background: $accent;
        text-style: bold;
    }
    """
    
    BINDINGS = [
        ("escape", "handle_escape", "Quit"),
        ("ctrl+c", "handle_escape", "Quit"),
        ("ctrl+t", "toggle_tools", "Tools"),
        ("ctrl+s", "save_chat", "Save Chat"),
        ("ctrl+l", "clear_chat", "Clear Chat"),
        ("ctrl+k", "compact_chat", "Compact"),
        ("ctrl+r", "manage_prompts", "Manage Prompts"),
    ]
    
    def __init__(self):
        super().__init__()
        load_lang_from_config()
        self.agent_manager = AgentManager()
        self.cli_executor = CLIExecutor()
        self.project_path = None
        cfg = _load_config()
        if "theme" in cfg:
            self.theme = cfg["theme"]
    
    def watch_theme(self, old_value: str, new_value: str):
        cfg = _load_config()
        cfg["theme"] = new_value
        _save_config(cfg)

    def get_system_commands(self, screen: Screen):
        yield from super().get_system_commands(screen)
        yield SystemCommand("Save Chat", t("save_chat"), self.action_save_chat)
        yield SystemCommand("Clear Chat", t("chat_cleared"), self.action_clear_chat)
        yield SystemCommand("Compact", t("compact_sent"), self.action_compact_chat)
        yield SystemCommand("Tools", t("tools_title"), self.action_toggle_tools)
        yield SystemCommand("Manage Prompts", t("prompt_manage"), self.action_manage_prompts)
    
    def compose(self) -> ComposeResult:
        with Horizontal(id="main-container"):
            yield Sidebar()
            yield ChatArea()
        yield StatusBar()
        yield Footer()
    
    def on_mount(self):
        """Check auth, then show project selector"""
        self.is_authenticated = False
        self.run_worker(self._check_auth_and_start())

    async def _check_auth_and_start(self):
        success, _ = await self.run_in_thread(self.cli_executor.whoami)
        if success:
            self.is_authenticated = True
            self.push_screen(ProjectSelector(), callback=self._on_project_selected)
        else:
            self.push_screen(LoginScreen(), callback=self._on_login_config)

    def _on_login_config(self, result: dict):
        """After login screen, execute login then go to project selector"""
        if not result:
            # Skipped login
            self.push_screen(ProjectSelector(), callback=self._on_project_selected)
            return
        self.run_worker(self._do_login(result))

    async def _do_login(self, config: dict):
        self.cli_executor.stop_chat_session()
        chat = self.query_one(ChatArea)
        status = self.query_one(StatusBar)
        status.set_status(t("logging_in"))
        chat.add_log(t("auth_device_flow"))

        def output_handler(line: str):
            # Whitelist: only show lines with useful login info
            low = line.lower()
            if any(kw in low for kw in ("http", "code", "browser", "success", "error", "fail", "logged", "token", "device", "authorize")):
                self.call_from_thread(chat.add_message, line, "system")

        def run_login():
            return self.cli_executor.login_interactive(
                output_handler,
                license=config.get("license"),
                identity_provider=config.get("identity_provider"),
                region=config.get("region"),
            )

        success = await self.run_in_thread(run_login)
        if success:
            self.is_authenticated = True
            status.set_status(t("login_success"))
            self._update_auth_indicator(True)
        else:
            status.set_status(t("login_failed"))
            self._update_auth_indicator(False)

        self.push_screen(ProjectSelector(), callback=self._on_project_selected)

    def _update_auth_indicator(self, logged_in: bool):
        self.is_authenticated = logged_in
        try:
            self.query_one(AuthSection).set_auth_status(logged_in)
        except Exception:
            pass

    def _on_project_selected(self, path: str):
        """After project is selected, initialize everything"""
        if not path:
            self.exit()
            return
        
        self.project_path = path
        self.notify(t("loading_project", name=os.path.basename(path)), timeout=5)
        self.run_worker(lambda: self._init_project(path), thread=True)

    def _init_project(self, path: str):
        """Initialize project in background thread."""
        import time
        
        # Update auth indicator
        self.call_from_thread(self._update_auth_indicator, self.is_authenticated)
        
        # Load agents
        agents = self.agent_manager.list_agents()
        agents_section = self.query_one(AgentsSection)
        self.call_from_thread(agents_section.update_agents, agents)
        
        # Set active agent in status bar
        status = self.query_one(StatusBar)
        if self.agent_manager.active_agent:
            self.call_from_thread(status.set_agent, self.agent_manager.active_agent)
        
        # Load models
        self.active_model = "auto"
        success, models = self.cli_executor.model_list()
        if success:
            self.call_from_thread(self.query_one(ModelsSection).update_models, models, self.active_model)
            self.call_from_thread(status.set_model, self.active_model)
        
        # Load prompts
        self.call_from_thread(self._refresh_prompts)
        
        chat = self.query_one(ChatArea)
        self.call_from_thread(status.set_status, f"Project: {os.path.basename(path)}")
        self.call_from_thread(chat.add_log, t("project_label", path=path))
        self.call_from_thread(chat.add_log, t("starting_chat"))
        
        success = self._start_chat()
        time.sleep(1)
        
        if success and self.cli_executor.chat_process and self.cli_executor.chat_process.poll() is None:
            self.call_from_thread(status.set_status, t("ready"))
            self.call_from_thread(chat.add_log, t("chat_active"))
            self._poll_context()
        else:
            self.call_from_thread(status.set_status, t("chat_failed"))
            self.call_from_thread(chat.add_log, t("chat_failed_msg"))
    
    def _chat_output_handler(self, line: str):
        """Handle chat output: accumulate response into single Markdown widget."""
        # Deduplicate consecutive identical lines
        if line == getattr(self, '_last_chat_line', None):
            return
        self._last_chat_line = line

        chat = self.query_one(ChatArea)
        status = self.query_one(StatusBar)

        # Context percentage update
        if line.startswith("__CONTEXT__:"):
            pct = float(line.split(":", 1)[1])
            self.call_from_thread(status.set_context, pct)
            # Only stop ghost/status when response was received (not echo prompt)
            if getattr(self, '_response_lines', None):
                self._end_response()
                self.call_from_thread(status.set_status, t("ready"))
            return

        # Trust picker detection
        if line.startswith("__TRUST_PICKER__:"):
            self._trust_options = []
            return
        if line.startswith("__TRUST_OPTION__:"):
            opt = line[len("__TRUST_OPTION__:"):]
            # Parse "  Full command → git pull --rebase" or "> Full command → ..."
            opt = opt.lstrip("> ").strip()
            if "→" in opt:
                label, detail = opt.split("→", 1)
                self._trust_options.append((label.strip(), detail.strip()))
            else:
                self._trust_options.append((opt, ""))
            # Show picker after collecting options (small delay via timer)
            def _schedule_picker():
                if hasattr(self, '_trust_timer'):
                    self._trust_timer.stop()
                self._trust_timer = self.set_timer(0.5, self._show_trust_picker)
            self.call_from_thread(_schedule_picker)
            return

        # Action prompt — finalize current response first
        if "Allow this action" in line or "[y/n" in line:
            self._end_response()
            self.call_from_thread(chat.add_message, line, "action")
            self.call_from_thread(status.set_status, t("ready"))
            return

        # Accumulate response lines into single widget
        if not hasattr(self, '_response_lines'):
            self._response_lines = []

        self._response_lines.append(line)
        full = '\n'.join(self._response_lines)

        if len(self._response_lines) == 1:
            self.call_from_thread(chat.add_message, full, "assistant")
        else:
            self.call_from_thread(chat.update_response, full)

    def _end_response(self):
        """Finalize current response accumulation."""
        self._response_lines = []
        self._last_chat_line = None
        try:
            chat = self.query_one(ChatArea)
            chat.stop_ghost()
            try:
                self.call_from_thread(chat.end_response)
            except RuntimeError:
                chat.end_response()
        except Exception:
            pass

    def _poll_context(self):
        """Silently poll /context to update status bar percentage."""
        def on_context(pct):
            self.call_from_thread(self.query_one(StatusBar).set_context, pct)
        self.cli_executor.poll_context(on_context)
    
    # Fallback tools if /tools hasn't been parsed yet
    BUILTIN_TOOLS = [
        "read", "write", "shell", "aws", "report",
        "code", "delegate", "glob", "grep", "introspect",
        "knowledge", "session", "thinking", "todo",
        "subagent", "web_fetch", "web_search",
    ]

    def _is_processing(self) -> bool:
        """Check if kiro is currently processing (thinking or streaming)."""
        try:
            from kiro_tui.components.chat import GhostMascot
            if self.query_one("#ghost", GhostMascot)._animating:
                return True
        except Exception:
            pass
        return bool(getattr(self, '_response_lines', None))

    def action_handle_escape(self):
        # DEBUG
        _dl = __import__("os").path.expanduser("~/koda_debug.log")
        processing = self._is_processing()
        ghost_anim = False
        try:
            from kiro_tui.components.chat import GhostMascot
            ghost_anim = self.query_one("#ghost", GhostMascot)._animating
        except Exception:
            pass
        resp_lines = len(getattr(self, '_response_lines', []))
        with open(_dl, "a", encoding="utf-8") as f:
            f.write(f"ESC pressed: processing={processing} ghost={ghost_anim} resp_lines={resp_lines}\n")

        if processing:
            result = self.cli_executor.send_interrupt()
            with open(_dl, "a", encoding="utf-8") as f:
                f.write(f"  -> interrupt sent, result={result}\n")
            self._end_response()
            chat = self.query_one(ChatArea)
            chat.end_response()
            chat.stop_ghost()
            self.query_one(StatusBar).set_status(t("ready"))
        else:
            def on_quit(result: bool) -> None:
                if result:
                    self.exit()
            self.push_screen(ConfirmQuitModal(), on_quit)

    def action_toggle_tools(self):
        """Show tools modal — fetches current tools from agent first"""
        def on_tools_ready():
            tools = self.cli_executor.get_tools()
            if not tools:
                tools = [(n, False) for n in self.BUILTIN_TOOLS]
            self.call_from_thread(self.push_screen,
                ToolsModal(tools), self._on_tools_result)
        self.cli_executor.refresh_tools(callback=on_tools_ready)

    def action_save_chat(self):
        """Save current chat session"""
        existing = []
        if self.project_path:
            import os
            for f in os.listdir(self.project_path):
                fpath = os.path.join(self.project_path, f)
                if os.path.isfile(fpath) and not f.startswith("."):
                    try:
                        with open(fpath, "r", encoding="utf-8")as fh:
                            if "conversation_id" in fh.read(200):
                                existing.append(f)
                    except Exception:
                        pass
        self._existing_chats = sorted(existing)
        self.push_screen(SaveModal(t("save_chat"), "my-chat-name", self._existing_chats), callback=self._on_save_result)

    def action_clear_chat(self):
        """Clear chat history"""
        def on_confirm(confirmed: bool):
            if confirmed:
                self.cli_executor.send_chat_message("/clear")
                # Auto-confirm kiro-cli's built-in [y/n] prompt
                import threading
                def auto_confirm():
                    import time; time.sleep(1)
                    self.cli_executor.send_chat_message("y")
                threading.Thread(target=auto_confirm, daemon=True).start()
                chat = self.query_one(ChatArea)
                chat.query_one("#messages").remove_children()
                chat.add_log(t("chat_cleared"))
        self.push_screen(ConfirmModal(t("confirm_clear"), t("clear_action"), t("cancel")), on_confirm)

    def action_compact_chat(self):
        """Compact chat"""
        self.cli_executor.send_chat_message("/compact")
        self.query_one(ChatArea).add_log(t("compact_sent"))

    def action_manage_prompts(self):
        """Open prompts manager"""
        prompts = self.cli_executor.prompt_list(self.project_path)
        self.push_screen(PromptsManagerModal(prompts), callback=self._on_manager_result)
    
    def _on_tools_result(self, result: dict):
        if not result:
            return
        new_trusted = {name for name, on in result.items() if on}
        old_trusted = getattr(self, '_trusted_tools', set())
        to_trust = new_trusted - old_trusted
        to_untrust = old_trusted - new_trusted
        if not to_trust and not to_untrust:
            return
        self._trusted_tools = new_trusted
        if to_trust:
            self.cli_executor.send_chat_message(f"/tools trust {' '.join(to_trust)}")
        if to_untrust:
            self.cli_executor.send_chat_message(f"/tools untrust {' '.join(to_untrust)}")
        self.query_one(ChatArea).add_log(t("tools_updated"))

    def _start_chat(self):
        """Centralized chat startup using cli_executor PTY method."""
        agent = self.agent_manager.active_agent
        model = getattr(self, 'active_model', 'auto')
        trusted = list(getattr(self, '_trusted_tools', []))
        return self.cli_executor.start_chat_session(
            self._chat_output_handler,
            agent=agent, model=model,
            trusted_tools=trusted or None,
            cwd=self.project_path
        )

    def on_unmount(self):
        """Clean up chat session when app closes"""
        self.cli_executor.stop_chat_session()
    
    def on_action_prompt_action_response(self, event: ActionPrompt.ActionResponse):
        """Handle y/n/t button click on action prompts"""
        self.cli_executor.send_chat_message(event.response)
        chat = self.query_one(ChatArea)
        if event.response != "n":
            self.query_one(StatusBar).set_status(t("thinking"))
            chat.start_ghost()
        else:
            self.query_one(StatusBar).set_status(t("ready"))

    def _show_trust_picker(self):
        """Show trust picker options as buttons in chat."""
        options = getattr(self, '_trust_options', [])
        if options:
            chat = self.query_one(ChatArea)
            messages = chat.query_one("#messages")
            messages.mount(TrustPicker(options))
            messages.scroll_end(animate=False)

    def on_trust_picker_trust_selected(self, event: TrustPicker.TrustSelected):
        """Handle trust scope selection - send arrow downs + Enter."""
        self.cli_executor._awaiting_trust_options = False
        for _ in range(event.index):
            self.cli_executor.send_raw(b'\x1b[B')  # arrow down
        self.cli_executor.send_raw(b'\r')  # Enter
        self.query_one(StatusBar).set_status(t("thinking"))
        self.query_one(ChatArea).start_ghost()

    def on_chat_area_message_submitted(self, event: ChatArea.MessageSubmitted):
        """Handle chat message submission"""
        chat = self.query_one(ChatArea)
        chat.end_response()  # Finalize previous response (direct call, main thread)
        self._response_lines = []
        self._last_chat_line = None
        status = self.query_one(StatusBar)
        
        # Check if chat session is active
        if not self.cli_executor.chat_process or self.cli_executor.chat_process.poll() is not None:
            status.set_status("Chat not active")
            chat.add_log("✗ Chat session not active. Restart the app.")
            self.notify("Chat session not active - restart app", severity="error")
            return
        
        # Send message to active chat session
        success = self.cli_executor.send_chat_message(event.text)
        
        if success:
            status.set_status(t("thinking"))
            chat.start_ghost()
            # Poll context after a delay to let response complete
            import threading
            def delayed_poll():
                import time; time.sleep(8)
                self._poll_context()
            threading.Thread(target=delayed_poll, daemon=True).start()
        else:
            status.set_status("Failed to send")
            chat.add_log("✗ Failed to send message")
            self.notify("Failed to send message", severity="error")
    
    async def on_list_view_selected(self, event: ListView.Selected):
        """Handle list item selection"""
        list_id = event.list_view.id
        
        # Ignore events from modal screens
        if list_id not in ("agents-list", "models-list", "chat-actions", "auth-actions", "prompts-list"):
            return
        
        # Get the label text from the list item
        try:
            label = event.item.children[0]
        except (IndexError, AttributeError):
            return
        
        # Try different ways to get the text
        if hasattr(label, 'renderable'):
            label_text = str(label.renderable)
        elif hasattr(label, '_text'):
            label_text = str(label._text)
        else:
            # Get the actual text content
            try:
                label_text = label.render().plain
            except:
                label_text = str(label)
        
        # Debug log
        chat = self.query_one(ChatArea)
        chat.add_log(f"[DEBUG] Selected: {label_text} from {event.list_view.id}")
        
        # Check if it's from agents list
        if event.list_view.id == "agents-list":
            await self.handle_agent_selection(label_text)
        # Check if it's from models list
        elif event.list_view.id == "models-list":
            await self.handle_model_selection(label_text)
        # Check if it's from chat actions
        elif event.list_view.id == "chat-actions":
            await self.handle_chat_action(label_text)
        # Check if it's from auth actions
        elif event.list_view.id == "auth-actions":
            await self.handle_auth_action(label_text)
        # Check if it's from prompts list
        elif event.list_view.id == "prompts-list":
            await self.handle_prompt_selection(label_text)
    
    async def handle_agent_selection(self, label_text: str):
        """Handle agent selection from sidebar"""
        agent_name = label_text.replace("● ", "").strip()
        
        chat = self.query_one(ChatArea)
        status = self.query_one(StatusBar)
        
        status.set_status(t("switching_agent", name=agent_name))
        chat.add_log(t("switching_agent", name=agent_name))
        
        self._end_response()
        self.agent_manager.active_agent = agent_name
        
        # Switch agent within existing session to preserve context
        self.cli_executor.send_chat_message(f"/agent swap {agent_name}")
        
        status.set_agent(agent_name)
        status.set_status(t("ready"))
        chat.add_log(t("now_chatting", name=agent_name))
        self.notify(t("now_chatting", name=agent_name), severity="information")
        
        # Refresh agent list
        agents = self.agent_manager.list_agents()
        self.query_one(AgentsSection).update_agents(agents)
    
    async def handle_model_selection(self, label_text: str):
        """Handle model selection - restart chat with new model"""
        model_name = label_text.replace("● ", "").strip()
        chat = self.query_one(ChatArea)
        status = self.query_one(StatusBar)
        
        status.set_status(t("switching_model", name=model_name))
        chat.add_log(t("switching_model", name=model_name))
        
        self._end_response()
        self.active_model = model_name
        
        # Switch model within existing session to preserve context
        self.cli_executor.send_chat_message(f"/model {model_name}")
        
        status.set_model(model_name)
        status.set_status(t("ready"))
        chat.add_log(t("now_model", name=model_name))
        self.notify(t("now_model", name=model_name), severity="information")
        
        # Refresh model list to update indicator
        success, models = self.cli_executor.model_list()
        if success:
            self.query_one(ModelsSection).update_models(models, model_name)
    
    async def handle_chat_action(self, label_text: str):
        """Handle chat action from sidebar"""
        chat = self.query_one(ChatArea)
        status = self.query_one(StatusBar)
        
        if t("save") in label_text:
            import os
            # Find existing chat files in project directory
            existing = []
            for f in os.listdir(self.project_path):
                fpath = os.path.join(self.project_path, f)
                if os.path.isfile(fpath) and not f.startswith("."):
                    try:
                        with open(fpath, "r", encoding="utf-8")as fh:
                            if "conversation_id" in fh.read(200):
                                existing.append(f)
                    except Exception:
                        pass
            
            self._existing_chats = sorted(existing)
            self.push_screen(
                SaveModal(t("save_chat"), "my-chat-name", self._existing_chats),
                callback=self._on_save_result
            )
            
        elif t("load") in label_text:
            import os
            chat_files = []
            for f in os.listdir(self.project_path):
                fpath = os.path.join(self.project_path, f)
                if os.path.isfile(fpath) and not f.startswith("."):
                    try:
                        with open(fpath, "r", encoding="utf-8")as fh:
                            if "conversation_id" in fh.read(200):
                                chat_files.append(f)
                    except Exception:
                        pass
            
            if not chat_files:
                chat.add_log(t("no_saved_chats"))
            self.push_screen(
                PickerModal(t("load_chat"), sorted(chat_files)),
                callback=self._on_load_result
            )
        
        elif t("list_sessions") in label_text:
            status.set_status(t("listing_sessions"))
            self.run_worker(self._list_sessions())
        
        elif t("clear") in label_text:
            self.action_clear_chat()
        
        elif t("compact") in label_text:
            self.cli_executor.send_chat_message("/compact")
            chat.add_log(t("compact_sent"))
    
    def _on_save_result(self, name: str):
        if name:
            chat = self.query_one(ChatArea)
            force = "-f " if name in getattr(self, '_existing_chats', []) else ""
            self.cli_executor.send_chat_message(f"/chat save {force}{name}")
            chat.add_log(t("saved_as", name=name))
    
    def _on_load_result(self, name: str):
        if name:
            self._end_response()
            chat = self.query_one(ChatArea)
            self.cli_executor.send_chat_message(f"/chat load {name}")
            chat.add_log(t("loading_chat", name=name))
    
    async def _list_sessions(self):
        chat = self.query_one(ChatArea)
        status = self.query_one(StatusBar)
        sessions = await self.run_in_thread(self.cli_executor.chat_list_sessions)
        if sessions:
            chat.add_log(t("sessions_found", n=len(sessions)))
            for sid, preview in sessions[:10]:
                chat.add_message(f"  {sid[:8]}… | {preview[:70]}", "system")
        else:
            chat.add_log(t("no_sessions"))
        status.set_status(t("ready"))
    
    async def handle_auth_action(self, label_text: str):
        """Handle auth action from sidebar"""
        chat = self.query_one(ChatArea)
        status = self.query_one(StatusBar)
        
        if t("login") in label_text:
            self.push_screen(LoginScreen(), callback=self._on_sidebar_login)
        
        elif t("logout") in label_text:
            status.set_status(t("logging_out"))
            success, output = await self.run_in_thread(self.cli_executor.logout)
            
            if success:
                status.set_status(t("logout_success"))
                chat.add_message(output, "system")
                self._update_auth_indicator(False)
            else:
                status.set_status(t("logout_failed"))
                chat.add_message(output, "system")
        
        elif t("whoami") in label_text:
            success, output = await self.run_in_thread(self.cli_executor.whoami)
            if success:
                status.set_status(t("ready"))
                chat.add_message(output, "system")
                self._update_auth_indicator(True)
            else:
                status.set_status(t("error"))
                chat.add_message(output, "system")
                self._update_auth_indicator(False)

    def _on_sidebar_login(self, result: dict):
        if not result:
            return
        self.run_worker(self._do_sidebar_login(result))

    async def _do_sidebar_login(self, config: dict):
        self.cli_executor.stop_chat_session()
        chat = self.query_one(ChatArea)
        status = self.query_one(StatusBar)
        status.set_status(t("logging_in"))
        chat.add_log(t("auth_device_flow"))

        def output_handler(line: str):
            low = line.lower()
            if any(kw in low for kw in ("http", "code", "browser", "success", "error", "fail", "logged", "token", "device", "authorize")):
                self.call_from_thread(chat.add_message, line, "system")

        def run_login():
            return self.cli_executor.login_interactive(
                output_handler,
                license=config.get("license"),
                identity_provider=config.get("identity_provider"),
                region=config.get("region"),
            )

        success = await self.run_in_thread(run_login)
        if success:
            status.set_status(t("login_success"))
            self._update_auth_indicator(True)
            self._ensure_experiments()
        else:
            status.set_status(t("login_failed"))
            self._update_auth_indicator(False)

    def _ensure_experiments(self):
        """Enable required experimental features in cli.json."""
        import json
        cfg_path = os.path.expanduser("~/.kiro/settings/cli.json")
        try:
            data = {}
            if os.path.exists(cfg_path):
                with open(cfg_path, encoding="utf-8")as f:
                    data = json.load(f)
            required = {
                "chat.enableKnowledge": True,
                "chat.enableThinking": True,
                "chat.enableTangentMode": True,
                "chat.enableTodoList": True,
                "chat.enableDelegate": True,
            }
            if all(data.get(k) == v for k, v in required.items()):
                return
            data.update(required)
            os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
            with open(cfg_path, "w", encoding="utf-8")as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _refresh_prompts(self):
        """Refresh prompts list in sidebar"""
        prompts = self.cli_executor.prompt_list(self.project_path)
        self.query_one(PromptsSection).update_prompts(prompts)

    async def handle_prompt_selection(self, label_text: str):
        """Handle prompt list item click"""
        if t("prompt_manage") in label_text:
            prompts = self.cli_executor.prompt_list(self.project_path)
            self.push_screen(PromptsManagerModal(prompts), callback=self._on_manager_result)
        else:
            # Direct send — read content ourselves to avoid kiro-cli UTF-8 issues
            self._end_response()
            name = label_text.split("] ", 1)[-1].strip()
            content, _ = self.cli_executor.prompt_read(name, self.project_path)
            if content:
                chat = self.query_one(ChatArea)
                chat.add_message(content, "user")
                self.cli_executor.send_chat_message(content)
                chat.add_log(t("prompt_sent", name=name))
                self.query_one(StatusBar).set_status(t("thinking"))
                chat.start_ghost()

    def _on_manager_result(self, result: str):
        if not result:
            return
        if result == "create":
            self.push_screen(InputModal(t("prompt_name"), "my-prompt"), callback=self._on_prompt_name)
        elif result.startswith("select:"):
            _, name, scope = result.split(":", 2)
            is_global = scope == "global"
            self.push_screen(
                PickerModal(f"'{name}':", [t("prompt_edit"), t("prompt_delete")]),
                callback=lambda action: self._on_prompt_manage_action(action, name, is_global)
            )

    def _on_prompt_manage_action(self, action: str, name: str, is_global: bool):
        if not action:
            return
        if t("prompt_edit") in action:
            content, _ = self.cli_executor.prompt_read(name, self.project_path)
            self._pending_prompt_name = name
            self._pending_prompt_global = is_global
            self.push_screen(InputModal(t("prompt_content"), content or ""), callback=self._on_prompt_edit_content)
        elif t("prompt_delete") in action:
            self.cli_executor.prompt_remove(name, self.project_path, is_global)
            self.query_one(ChatArea).add_log(t("prompt_removed", name=name))
            self._refresh_prompts()

    def _on_prompt_edit_content(self, content: str):
        if not content:
            return
        name = self._pending_prompt_name
        is_global = self._pending_prompt_global
        self.cli_executor.prompt_create(name, content, self.project_path, is_global)
        self.query_one(ChatArea).add_log(t("prompt_created", name=name))
        self._refresh_prompts()

    def _on_prompt_name(self, name: str):
        if not name:
            return
        self._pending_prompt_name = name
        self.push_screen(
            PickerModal(t("prompt_scope"), [t("prompt_local"), t("prompt_global")]),
            callback=self._on_prompt_scope
        )

    def _on_prompt_scope(self, scope: str):
        if not scope:
            return
        self._pending_prompt_global = t("prompt_global") in scope
        self.push_screen(
            InputModal(t("prompt_content"), "Write your prompt here..."),
            callback=self._on_prompt_content
        )

    def _on_prompt_content(self, content: str):
        if not content:
            return
        name = self._pending_prompt_name
        is_global = self._pending_prompt_global
        self.cli_executor.prompt_create(name, content, self.project_path, is_global)
        self.query_one(ChatArea).add_log(t("prompt_created", name=name))
        self._refresh_prompts()

    def run_in_thread(self, func, *args):
        """Run blocking function in thread"""
        import asyncio
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(None, func, *args)
