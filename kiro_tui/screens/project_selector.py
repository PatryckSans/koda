"""Project selection screen - shown at startup"""
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Label, ListView, ListItem, Button, Input
from textual.containers import Vertical, Horizontal

from ..services.project_manager import ProjectManager
from ..i18n import t, set_lang, get_lang, save_lang_to_config, load_lang_from_config, LANGUAGES


class ProjectSelector(Screen[str]):
    """Initial screen to select a project folder"""

    DEFAULT_CSS = """
    ProjectSelector {
        align: center middle;
    }

    #project-box {
        width: 60;
        height: auto;
        max-height: 30;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #project-title {
        text-align: center;
        text-style: bold;
        padding: 1;
    }

    #project-list {
        height: auto;
        max-height: 18;
        margin: 1 0;
    }

    #project-actions {
        height: auto;
        margin-top: 1;
    }

    #project-actions Button {
        margin: 0 1;
    }

    #lang-btn {
        dock: right;
        margin: 0 1;
    }
    """

    def __init__(self):
        super().__init__()
        self.pm = ProjectManager()
        load_lang_from_config()

    def compose(self) -> ComposeResult:
        with Vertical(id="project-box"):
            with Horizontal(id="project-actions"):
                yield Label(t("select_project"), id="project-title")
                yield Button(t("language"), id="lang-btn")
            yield ListView(id="project-list")
            with Horizontal():
                yield Button(t("add"), id="add-folder", variant="success")
                yield Button(t("remove"), id="remove-folder", variant="error")

    def on_mount(self):
        self._refresh_list()

    def _refresh_list(self):
        lv = self.query_one("#project-list", ListView)
        lv.clear()
        for name in self.pm.list_projects():
            lv.append(ListItem(Label(f"{name}")))

    def on_list_view_selected(self, event: ListView.Selected):
        if event.list_view.id != "project-list":
            return
        name = str(event.item.query_one(Label).render()).strip()
        path = str(self.pm.get_project_path(name))
        self.dismiss(path)

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "lang-btn":
            langs = list(LANGUAGES.keys())
            idx = (langs.index(get_lang()) + 1) % len(langs)
            set_lang(langs[idx])
            save_lang_to_config(langs[idx])
            self._refresh_ui()
        elif event.button.id == "add-folder":
            self.app.push_screen(AddFolderModal(), self._on_add_result)
        elif event.button.id == "remove-folder":
            projects = self.pm.list_projects()
            if projects:
                self.app.push_screen(RemoveFolderModal(projects), self._on_remove_result)

    def _refresh_ui(self):
        self.query_one("#project-title", Label).update(t("select_project"))
        self.query_one("#lang-btn", Button).label = t("language")
        self.query_one("#add-folder", Button).label = t("add")
        self.query_one("#remove-folder", Button).label = t("remove")

    def _on_add_result(self, name: str):
        if name:
            self.pm.create_project(name)
            self._refresh_list()

    def _on_remove_result(self, name: str):
        if name:
            self.pm.remove_project(name)
            self._refresh_list()


class AddFolderModal(Screen[str]):
    DEFAULT_CSS = """
    AddFolderModal { align: center middle; }
    #add-box { width: 50; height: auto; border: thick $primary; background: $surface; padding: 1 2; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="add-box"):
            yield Label(t("new_folder_name"))
            yield Input(placeholder=t("folder_placeholder"), id="folder-name")
            with Horizontal():
                yield Button(t("create"), id="create", variant="success")
                yield Button(t("cancel"), id="cancel")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "create":
            name = self.query_one("#folder-name", Input).value.strip()
            self.dismiss(name)
        else:
            self.dismiss("")

    def on_input_submitted(self, event: Input.Submitted):
        self.dismiss(event.value.strip())


class RemoveFolderModal(Screen[str]):
    DEFAULT_CSS = """
    RemoveFolderModal { align: center middle; }
    #remove-box { width: 50; height: auto; border: thick $error; background: $surface; padding: 1 2; }
    #confirm-box { width: 50; height: auto; border: thick $error; background: $surface; padding: 1 2; }
    .hidden { display: none; }
    """

    def __init__(self, projects: list[str]):
        super().__init__()
        self.projects = projects
        self.selected = ""

    def compose(self) -> ComposeResult:
        with Vertical(id="remove-box"):
            yield Label(t("select_remove"))
            yield ListView(
                *[ListItem(Label(f"{p}")) for p in self.projects],
                id="remove-list"
            )
            yield Button(t("cancel"), id="cancel")
        with Vertical(id="confirm-box", classes="hidden"):
            yield Label("", id="confirm-label")
            with Horizontal():
                yield Button(t("yes_delete"), id="confirm-yes", variant="error")
                yield Button(t("no"), id="confirm-no")

    def on_list_view_selected(self, event: ListView.Selected):
        idx = event.list_view.index
        if idx is not None and idx < len(self.projects):
            self.selected = self.projects[idx]
            self.query_one("#remove-box").add_class("hidden")
            self.query_one("#confirm-box").remove_class("hidden")
            self.query_one("#confirm-label", Label).update(
                t("confirm_delete", name=self.selected)
            )

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "confirm-yes":
            self.dismiss(self.selected)
        else:
            self.dismiss("")
