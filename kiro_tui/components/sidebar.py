"""Sidebar component with collapsible sections"""
from textual.app import ComposeResult
from textual.containers import Container, Vertical, VerticalScroll
from textual.widgets import Static, Label, ListView, ListItem
from textual.binding import Binding
from textual.message import Message
from ..i18n import t


class Section(Container):
    """Collapsible section in sidebar"""
    
    DEFAULT_CSS = """
    Section {
        height: auto;
        border: solid $primary;
        margin: 1 1 0 1;
    }
    
    Section .section-header {
        background: $primary;
        color: $text;
        padding: 0 1;
        text-style: bold;
        link-style: none;
    }
    
    Section .section-header:hover {
        background: $primary-lighten-1;
    }
    
    Section .section-content {
        padding: 0;
        height: auto;
    }
    
    Section ListView {
        height: auto;
        padding: 0;
        margin: 0;
    }
    
    Section ListItem {
        padding: 0 1;
    }
    
    Section ListItem Label {
        padding: 0;
    }
    
    Section.collapsed .section-content {
        display: none;
    }
    """
    
    def __init__(self, title: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = title
        self.collapsed = False
    
    def compose(self) -> ComposeResult:
        yield Label(f"v {self.title}", classes="section-header", id=f"header-{id(self)}")
        with Vertical(classes="section-content"):
            yield from self.compose_content()
    
    def on_click(self, event):
        """Toggle collapse when header is clicked"""
        if "section-header" in event.widget.classes:
            self.toggle_collapse()
    
    def compose_content(self) -> ComposeResult:
        """Override in subclasses"""
        yield Label("Empty section")
    
    def toggle_collapse(self):
        """Toggle section collapsed state"""
        self.collapsed = not self.collapsed
        if self.collapsed:
            self.add_class("collapsed")
            self.query_one(".section-header", Label).update(f"> {self.title}")
        else:
            self.remove_class("collapsed")
            self.query_one(".section-header", Label).update(f"v {self.title}")


class AgentsSection(Section):
    """Agents section with list of agents"""
    
    class AgentSelected(Message):
        """Message sent when agent is selected"""
        def __init__(self, agent_name: str):
            super().__init__()
            self.agent_name = agent_name
    
    def __init__(self):
        super().__init__(t("agents"))
        self.agents = []
    
    def compose_content(self) -> ComposeResult:
        list_view = ListView(
            ListItem(Label(t("loading_agents"))),
            id="agents-list"
        )
        list_view.can_focus = True
        yield list_view
    
    def update_agents(self, agents: list):
        """Update the agents list"""
        self.agents = agents
        list_view = self.query_one("#agents-list", ListView)
        list_view.clear()
        
        for agent in agents:
            list_view.append(ListItem(Label(agent.display_name())))


class ModelsSection(Section):
    """Models section"""
    
    def __init__(self):
        super().__init__(t("models"))
    
    def compose_content(self) -> ComposeResult:
        list_view = ListView(id="models-list")
        list_view.can_focus = True
        yield list_view
    
    def update_models(self, models: list, active: str = "auto"):
        list_view = self.query_one("#models-list", ListView)
        list_view.clear()
        for model in models:
            prefix = "● " if model == active else ""
            list_view.append(ListItem(Label(f"{prefix}{model}")))


class PromptsSection(Section):
    """Prompts management section"""

    def __init__(self):
        super().__init__(t("prompts"))
        self.prompts = []

    def compose_content(self) -> ComposeResult:
        list_view = ListView(id="prompts-list")
        list_view.can_focus = True
        yield list_view

    def update_prompts(self, prompts: list):
        """Update prompts list. prompts = [(name, source)]"""
        self.prompts = prompts
        lv = self.query_one("#prompts-list", ListView)
        lv.clear()
        lv.append(ListItem(Label(t("prompt_manage"))))
        for name, source in prompts:
            tag = "L" if source == "local" else "G"
            lv.append(ListItem(Label(f"[{tag}] {name}")))


class ChatSection(Section):
    """Chat management section"""
    
    class ChatAction(Message):
        """Message sent when chat action is triggered"""
        def __init__(self, action: str):
            super().__init__()
            self.action = action
    
    def __init__(self):
        super().__init__(t("chat"))
    
    def compose_content(self) -> ComposeResult:
        list_view = ListView(
            ListItem(Label(t("save"))),
            ListItem(Label(t("load"))),
            ListItem(Label(t("list_sessions"))),
            ListItem(Label(t("clear"))),
            ListItem(Label(t("compact"))),
            id="chat-actions"
        )
        list_view.can_focus = True
        yield list_view


class AuthSection(Section):
    """Authentication section"""
    
    class AuthAction(Message):
        """Message sent when auth action is triggered"""
        def __init__(self, action: str):
            super().__init__()
            self.action = action
    
    def __init__(self):
        super().__init__(t("auth"))
    
    def compose_content(self) -> ComposeResult:
        yield Label("--", id="auth-status")
        list_view = ListView(
            ListItem(Label(t("login"))),
            ListItem(Label(t("logout"))),
            ListItem(Label(t("whoami"))),
            id="auth-actions"
        )
        list_view.can_focus = True
        yield list_view

    def set_auth_status(self, logged_in: bool):
        label = self.query_one("#auth-status", Label)
        if logged_in:
            label.update(f"[green]{t('auth_logged_as')}[/]")
        else:
            label.update(f"[red]{t('auth_not_logged')}[/]")


class Sidebar(Container):
    """Main sidebar with all sections"""
    
    DEFAULT_CSS = """
    Sidebar {
        width: 30;
        background: $surface;
        border-right: solid $primary;
    }
    
    #logo-box {
        background: $primary;
        padding: 1;
        width: 100%;
        height: auto;
        align: center middle;
    }
    #sidebar-title {
        color: $text;
        text-align: center;
        text-style: bold;
        width: 100%;
    }
    #sidebar-subtitle {
        color: $text-muted;
        text-align: center;
        width: 100%;
    }
    
    #sidebar-scroll {
        height: 1fr;
    }
    
    ListView {
        height: auto;
    }
    
    ListView > ListItem {
        padding: 0 1;
    }
    
    ListView > ListItem:hover {
        background: $accent;
        color: $text;
        text-style: bold;
    }
    
    ListView:focus > ListItem.-selected {
        background: $accent;
    }
    """
    
    BINDINGS = [
        Binding("up", "focus_previous", "Up", show=False),
        Binding("down", "focus_next", "Down", show=False),
    ]
    
    def compose(self) -> ComposeResult:
        with Container(id="logo-box"):
            yield Static(" █▄▀  █▀█  █▀▄  ▄▀█\n █░█  █▄█  █▄▀  █▀█", id="sidebar-title")
            yield Static("Kiro Operator\nDashboard Application", id="sidebar-subtitle")
        with VerticalScroll(id="sidebar-scroll"):
            yield AuthSection()
            yield AgentsSection()
            yield ModelsSection()
            yield PromptsSection()
            yield ChatSection()
