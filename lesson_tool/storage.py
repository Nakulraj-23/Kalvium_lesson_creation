"""File-based persistence.

Design goals (from the brief: "preserve previously saved work and instructor edits"):
* every write is atomic (temp file + os.replace) so a crash never leaves a half-written project;
* every change to lesson content creates a new immutable version snapshot under versions/;
* pipeline failures only ever update step status - they never overwrite existing content.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from .models import Lesson, LessonProject, VersionInfo, now_iso


def slugify(text: str, max_len: int = 40) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return s[:max_len] or "lesson"


def _atomic_write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


class Store:
    def __init__(self, data_dir: Path):
        self.root = Path(data_dir) / "lessons"
        self.root.mkdir(parents=True, exist_ok=True)

    # ---------- projects ----------
    def _dir(self, project_id: str) -> Path:
        return self.root / project_id

    def new_project(self, title: str, objective: str, audience: str = "") -> LessonProject:
        pid = f"{slugify(title)}-{uuid.uuid4().hex[:6]}"
        project = LessonProject(id=pid, title=title.strip(), objective=objective.strip(), audience=audience.strip())
        self.save(project)
        return project

    def save(self, project: LessonProject) -> None:
        project.updated_at = now_iso()
        _atomic_write(self._dir(project.id) / "project.json", project.model_dump_json(indent=2))

    def load(self, project_id: str) -> LessonProject:
        path = self._dir(project_id) / "project.json"
        return LessonProject.model_validate_json(path.read_text(encoding="utf-8"))

    def list_projects(self) -> list[dict]:
        out = []
        for p in sorted(self.root.glob("*/project.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                out.append({"id": d["id"], "title": d["title"], "updated_at": d.get("updated_at", "")})
            except Exception:
                continue  # a corrupt file must not break the sidebar
        return out

    # ---------- versions ----------
    def commit_lesson(self, project: LessonProject, lesson: Lesson, note: str) -> int:
        """Store `lesson` as a new version and make it current. Returns version number."""
        version = project.lesson_version + 1
        _atomic_write(self._dir(project.id) / "versions" / f"v{version:03d}.json", lesson.model_dump_json(indent=2))
        project.lesson = lesson
        project.lesson_version = version
        project.versions.append(VersionInfo(version=version, note=note))
        self.save(project)
        return version

    def load_version(self, project_id: str, version: int) -> Optional[Lesson]:
        path = self._dir(project_id) / "versions" / f"v{version:03d}.json"
        if not path.exists():
            return None
        return Lesson.model_validate_json(path.read_text(encoding="utf-8"))

    def export_dir(self, project_id: str) -> Path:
        d = self._dir(project_id) / "exports"
        d.mkdir(parents=True, exist_ok=True)
        return d
