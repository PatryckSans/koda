"""Chat component with message display and input"""
import re
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.widgets import Static, Input, Button
from textual.message import Message
from ..i18n import t
from rich.text import Text


class ActionPrompt(Container):
    """Action prompt with y/n/t buttons"""

    DEFAULT_CSS = """
    ActionPrompt {
        width: 100%;
        height: auto;
        background: $surface;
        padding: 1;
        border: heavy $primary;
    }
    ActionPrompt .action-text {
        color: $text;
        text-style: bold;
        width: 100%;
        margin-bottom: 1;
    }
    ActionPrompt .action-buttons {
        height: auto;
        width: 100%;
    }
    ActionPrompt Button {
        margin: 0 1 0 0;
        min-width: 12;
    }
    ActionPrompt Button:hover {
        text-style: bold reverse;
    }
    """

    class ActionResponse(Message):
        def __init__(self, response: str):
            super().__init__()
            self.response = response

    def __init__(self, text: str):
        super().__init__()
        self.text = text

    def compose(self) -> ComposeResult:
        yield Static(self.text, classes="action-text", markup=False)
        with Horizontal(classes="action-buttons"):
            yield Button(t("action_yes"), variant="success", id="action-y")
            yield Button(t("action_no"), variant="error", id="action-n")
            yield Button(t("action_trust"), variant="warning", id="action-t")

    def on_button_pressed(self, event: Button.Pressed):
        response = event.button.id.split("-")[1]  # y, n, or t
        self.post_message(self.ActionResponse(response))
        # Disable buttons after click
        for btn in self.query(Button):
            btn.disabled = True


class TrustPicker(Container):
    """Trust scope picker - shows options from kiro-cli granular trust"""

    DEFAULT_CSS = """
    TrustPicker {
        width: 100%;
        height: auto;
        background: #4a3800;
        padding: 1;
        border: heavy $warning;
    }
    TrustPicker .picker-title {
        color: #ffffff;
        text-style: bold;
        width: 100%;
        margin-bottom: 1;
    }
    TrustPicker Button {
        width: 100%;
        margin: 0 0 1 0;
    }
    TrustPicker Button:hover {
        text-style: bold reverse;
    }
    """

    class TrustSelected(Message):
        def __init__(self, index: int):
            super().__init__()
            self.index = index

    def __init__(self, options: list):
        super().__init__()
        self.options = options  # list of (label, detail) tuples

    def compose(self) -> ComposeResult:
        yield Static("Select trust scope:", classes="picker-title")
        for i, (label, detail) in enumerate(self.options):
            text = f"{label} -> {detail}" if detail else label
            yield Button(text, variant="warning", id=f"trust-{i}")

    def on_button_pressed(self, event: Button.Pressed):
        idx = int(event.button.id.split("-")[1])
        self.post_message(self.TrustSelected(idx))
        for btn in self.query(Button):
            btn.disabled = True


class ChatMessage(Static):
    """Single chat message"""
    
    DEFAULT_CSS = """
    ChatMessage {
        width: 100%;
        height: auto;
        padding: 0 1;
        margin: 0;
    }
    
    ChatMessage.user {
        border-left: thick $primary;
        padding: 0 1;
    }
    
    ChatMessage.assistant {
        background: $surface-darken-1;
    }
    
    ChatMessage.system {
        background: $warning-darken-2;
        color: $warning-lighten-3;
    }
    
    ChatMessage.log {
        background: $accent-darken-2;
        color: $accent-lighten-2;
        text-style: italic;
    }
    
    ChatMessage.action {
        background: $surface;
        color: $text;
        text-style: bold;
        padding: 1;
        border: heavy $primary;
    }
    """
    
    def __init__(self, content: str, role: str = "user"):
        if role == "assistant":
            content = re.sub(r'\*\*(.+?)\*\*', lambda m: f'\x1b[1m{m.group(1)}\x1b[22m', content)
            super().__init__(Text.from_ansi(content), markup=False)
        else:
            super().__init__(content, markup=False)
        self.add_class(role)

    def update_content(self, content: str):
        """Update assistant message with new accumulated content."""
        content = re.sub(r'\*\*(.+?)\*\*', lambda m: f'\x1b[1m{m.group(1)}\x1b[22m', content)
        self.update(Text.from_ansi(content))


class ChatArea(Container):
    """Chat area with messages and input"""
    
    DEFAULT_CSS = """
    ChatArea {
        width: 1fr;
        height: 100%;
    }
    
    #messages {
        height: 1fr;
        border: solid $primary;
    }
    
    #input-container {
        height: auto;
        padding: 1;
    }
    
    #chat-input {
        width: 100%;
    }
    """
    
    class MessageSubmitted(Message):
        """Message sent when user submits input"""
        def __init__(self, text: str):
            super().__init__()
            self.text = text
    
    def compose(self) -> ComposeResult:
        with VerticalScroll(id="messages"):
            yield ChatMessage(t("welcome"), "system")
        with Vertical(id="input-container"):
            yield Input(placeholder=t("type_message"), id="chat-input")
    
    def on_input_submitted(self, event: Input.Submitted):
        """Handle input submission"""
        if event.value.strip():
            self.add_message(event.value, "user")
            self.post_message(self.MessageSubmitted(event.value))
            event.input.value = ""
    
    def add_message(self, content: str, role: str = "user"):
        """Add a message to the chat"""
        messages = self.query_one("#messages", VerticalScroll)
        if role == "action":
            messages.mount(ActionPrompt(content))
        elif role == "assistant":
            widget = ChatMessage(content, role)
            self._current_response = widget
            messages.mount(widget)
        else:
            messages.mount(ChatMessage(content, role))
        messages.scroll_end(animate=False)

    def update_response(self, content: str):
        """Update the current assistant response widget."""
        if hasattr(self, '_current_response') and self._current_response:
            self._current_response.update_content(content)
            self.query_one("#messages", VerticalScroll).scroll_end(animate=False)

    def end_response(self):
        """Finalize current response."""
        self._current_response = None
    
    def add_log(self, content: str):
        """Add a log message"""
        self.add_message(f"[LOG] {content}", "log")
