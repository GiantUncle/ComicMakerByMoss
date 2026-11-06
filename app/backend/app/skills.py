"""Skill assets: originals are read-only, edits happen on a copy (D12).

    origin  <repo>/.opencode/skills/...      read-only, shipped
    edited  ~/.comicmaker/skills/...         the user's working copy

    read(path)  -> edited if it exists, else origin
    edit(...)   -> copy origin -> edited, then write
    rollback    -> delete the edited copy, so the origin is used again

Nothing in the origin tree is ever written.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
ORIGIN = Path(os.environ.get("CM_SKILL_ORIGIN", REPO / ".opencode" / "skills"))
EDITED = Path(os.environ.get("CM_SKILL_EDITED", Path.home() / ".comicmaker" / "skills"))

TEXT_SUFFIXES = {".md", ".json", ".txt", ".py"}


@dataclass
class Asset:
    path: str          # relative to the skills root, posix
    kind: str          # markdown | json | text | script
    edited: bool
    bytes: int


def _safe(rel: str) -> Path:
    rel = rel.replace("\\", "/").lstrip("/")
    p = Path(rel)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError(f"unsafe path: {rel}")
    return p


def _kind(p: Path) -> str:
    if p.suffix == ".md":
        return "markdown"
    if p.suffix == ".json":
        return "json"
    if p.suffix == ".py":
        return "script"
    return "text"


def _origin_files() -> list[Path]:
    if not ORIGIN.exists():
        return []
    return sorted(
        p for p in ORIGIN.rglob("*")
        if p.is_file()
        and p.suffix in TEXT_SUFFIXES
        and "__pycache__" not in p.parts
    )


# ---------------------------------------------------------------- self-check
# What a fresh clone must have shipped with it. Without these the app cannot
# lay out a single panel or compile a single prompt, so the backend reports the
# gap at startup instead of failing on the first stage run.
REQUIRED = (
    "manga-craft/templates/moss-layouts.json",
    "manga-craft/templates/layouts.json",
    "manga-craft/scripts/compile_layout.py",
    "manga-craft/scripts/instantiate_layout.py",
    "manga-craft/scripts/build_negative.py",
)


def preflight() -> dict:
    """Is the shipped skill library complete? Say what is missing, if not."""
    missing = [rel for rel in REQUIRED if not (ORIGIN / rel).is_file()]
    return {
        "ok": not missing,
        "origin": str(ORIGIN),
        "missing": missing,
        "assets": len(_origin_files()),
        "hint": (
            "the skill library is shipped code — if it is missing the clone is "
            "incomplete (see .gitignore: .opencode/skills must NOT be ignored)"
            if missing else ""
        ),
    }


def list_assets() -> list[Asset]:
    out = []
    for p in _origin_files():
        rel = p.relative_to(ORIGIN).as_posix()
        edited_file = EDITED / rel
        out.append(Asset(
            path=rel,
            kind=_kind(p),
            edited=edited_file.exists(),
            bytes=(edited_file if edited_file.exists() else p).stat().st_size,
        ))
    return out


def read_asset(rel: str) -> dict:
    r = _safe(rel)
    origin = ORIGIN / r
    if not origin.exists():
        raise FileNotFoundError(rel)
    edited = EDITED / r
    source = edited if edited.exists() else origin
    return {
        "path": rel,
        "edited": edited.exists(),
        "origin": origin.read_text(encoding="utf-8"),
        "content": source.read_text(encoding="utf-8"),
    }


def edit_asset(rel: str, content: str) -> dict:
    r = _safe(rel)
    origin = ORIGIN / r
    if not origin.exists():
        raise FileNotFoundError(rel)
    edited = EDITED / r
    edited.parent.mkdir(parents=True, exist_ok=True)
    edited.write_text(content, encoding="utf-8")
    return {"path": rel, "edited": True}


def _prune_empty(path: Path) -> None:
    """Remove now-empty directories up to, but not including, the edited root."""
    while path != EDITED and path.is_dir() and not any(path.iterdir()):
        path.rmdir()
        path = path.parent


def rollback_asset(rel: str) -> dict:
    r = _safe(rel)
    edited = EDITED / r
    if edited.exists():
        edited.unlink()
        _prune_empty(edited.parent)
    return {"path": rel, "edited": False}


def rollback_all() -> dict:
    removed = 0
    if EDITED.exists():
        for p in sorted(EDITED.rglob("*"), reverse=True):
            if p.is_file():
                p.unlink()
                removed += 1
            elif p.is_dir():
                _prune_empty(p)
    return {"removed": removed}
