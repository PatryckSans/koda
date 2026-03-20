"""Manages project folders in ~/koda/Projects/"""
import os
import shutil
from pathlib import Path


class ProjectManager:
    def __init__(self):
        self.base_dir = Path.home() / "koda" / "Projects"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def list_projects(self) -> list[str]:
        return sorted(
            d.name for d in self.base_dir.iterdir() if d.is_dir()
        )

    def create_project(self, name: str) -> bool:
        path = self.base_dir / name
        if path.exists():
            return False
        path.mkdir(parents=True)
        return True

    def remove_project(self, name: str) -> bool:
        path = self.base_dir / name
        if not path.exists():
            return False
        shutil.rmtree(path)
        return True

    def get_project_path(self, name: str) -> Path:
        return self.base_dir / name
