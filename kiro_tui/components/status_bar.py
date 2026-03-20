"""Status bar component"""
from textual.widgets import Static
from ..i18n import t


class StatusBar(Static):
    """Status bar showing current state"""
    
    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        background: $primary;
        color: $text;
        padding: 0 1;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.agent = "default"
        self.model = "unknown"
        self.status = t("ready")
        self.context_pct = 0.0
        self._spinner_frames = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        self._spinner_idx = 0
        self._spinner_timer = None
        self.update_display()
    
    def update_display(self):
        filled = int(self.context_pct / 10)
        bar = "█" * filled + "░" * (10 - filled)
        text = t("status_bar", agent=self.agent, model=self.model, status=self.status, bar=bar, pct=f"{self.context_pct:.0f}")
        self.update(text)
    
    def _animate_spinner(self):
        self._spinner_idx = (self._spinner_idx + 1) % len(self._spinner_frames)
        spinner = self._spinner_frames[self._spinner_idx]
        self.status = f"{spinner} {self._loading_text}"
        self.update_display()
    
    def set_agent(self, agent: str):
        self.agent = agent
        self.update_display()
    
    def set_model(self, model: str):
        self.model = model
        self.update_display()
    
    def set_status(self, status: str):
        # Stop any existing spinner
        if self._spinner_timer:
            self._spinner_timer.stop()
            self._spinner_timer = None
        
        # Animate if status ends with "..."
        if status.endswith("..."):
            self._loading_text = status
            self._spinner_idx = 0
            self.status = f"⠋ {status}"
            self.update_display()
            self._spinner_timer = self.set_interval(0.1, self._animate_spinner)
        else:
            self.status = status
            self.update_display()
    
    def set_context(self, pct: float):
        self.context_pct = pct
        self.update_display()
