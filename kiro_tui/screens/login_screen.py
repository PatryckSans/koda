"""Login screen - shown when user is not authenticated"""
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Label, Button, Input, RadioButton, RadioSet
from textual.containers import Vertical, Horizontal
import json, os

from ..i18n import t

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


class LoginScreen(Screen[dict]):
    """Login screen with license type selection"""

    DEFAULT_CSS = """
    LoginScreen { align: center middle; }
    #login-box {
        width: 60; height: auto; border: thick $primary;
        background: $surface; padding: 1 2;
    }
    #login-title { text-align: center; text-style: bold; padding: 1; }
    #pro-fields { margin: 1 0; }
    #pro-fields.hidden { display: none; }
    #login-actions { margin-top: 1; }
    #login-actions Button { margin: 0 1; }
    """

    def __init__(self):
        super().__init__()
        cfg = _load_config()
        self._saved_url = cfg.get("identity_provider", "")
        self._saved_region = cfg.get("region", "")

    def compose(self) -> ComposeResult:
        with Vertical(id="login-box"):
            yield Label(t("login_title"), id="login-title")
            yield Label(t("license_type"))
            yield RadioSet(
                RadioButton(t("free_label"), id="radio-free", value=True),
                RadioButton(t("pro_label"), id="radio-pro"),
                id="license-set"
            )
            with Vertical(id="pro-fields", classes="hidden"):
                yield Label(t("identity_provider_url"))
                yield Input(value=self._saved_url, placeholder="https://example.awsapps.com/start", id="idp-url")
                yield Label(t("region_label"))
                yield Input(value=self._saved_region, placeholder="us-east-1", id="region")
            with Horizontal(id="login-actions"):
                yield Button(t("login_btn"), id="login-btn", variant="success")
                yield Button(t("skip_login"), id="skip-btn")

    def on_radio_set_changed(self, event: RadioSet.Changed):
        pro_fields = self.query_one("#pro-fields")
        if event.pressed.id == "radio-pro":
            pro_fields.remove_class("hidden")
        else:
            pro_fields.add_class("hidden")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "skip-btn":
            self.dismiss({})
        elif event.button.id == "login-btn":
            is_pro = self.query_one("#radio-pro", RadioButton).value
            result = {"license": "pro" if is_pro else "free"}
            if is_pro:
                url = self.query_one("#idp-url", Input).value.strip()
                region = self.query_one("#region", Input).value.strip()
                result["identity_provider"] = url
                result["region"] = region
                # Persist for next time
                cfg = _load_config()
                if url:
                    cfg["identity_provider"] = url
                if region:
                    cfg["region"] = region
                _save_config(cfg)
            self.dismiss(result)
