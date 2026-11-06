"""Snapshots — every write leaves the previous version behind.

Before a stage overwrites its own files, the files it is about to touch are
copied into `projects/<slug>/history/<id>/files/`. A retake is then undoable: the
snapshot names the stage and the note that caused it, and restoring copies the
files back.

The snapshot lives under `history/`, which no stage ever reads, so it cannot
disturb the pipeline.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

HISTORY = "history"


def _history_root(project_root: Path) -> Path:
    return project_root / HISTORY


def snapshot(
    project_root: Path,
    rel_paths: list[str],
    *,
    stage: str,
    note: str = "",
    episode: str | None = None,
) -> dict | None:
    """Copy the given existing files into a new snapshot. Returns None if none exist."""
    existing = [p for p in rel_paths if (project_root / p).is_file()]
    if not existing:
        return None

    root = _history_root(project_root)
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    sid = stamp
    n = 1
    while (root / sid).exists():
        n += 1
        sid = f"{stamp}-{n}"

    base = root / sid
    files_dir = base / "files"
    for rel in existing:
        dest = files_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(project_root / rel, dest)

    meta = {
        "id": sid,
        "stage": stage,
        "note": note,
        "episode": episode,
        "time": datetime.now().isoformat(timespec="seconds"),
        "files": existing,
    }
    (base / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return meta


def list_snapshots(project_root: Path, stage: str | None = None) -> list[dict]:
    root = _history_root(project_root)
    if not root.is_dir():
        return []
    out = []
    for entry in sorted(root.iterdir(), reverse=True):
        meta_file = entry / "meta.json"
        if not meta_file.is_file():
            continue
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if stage and meta.get("stage") != stage:
            continue
        out.append(meta)
    return out


def restore(project_root: Path, sid: str) -> dict:
    """Put an old snapshot back — after keeping what is there now.

    A restore is itself an edit, so the state being replaced is snapshotted
    first. Otherwise the work you are undoing would be gone with no way back.
    """
    base = _history_root(project_root) / sid
    meta_file = base / "meta.json"
    if not meta_file.is_file():
        raise FileNotFoundError(sid)
    meta = json.loads(meta_file.read_text(encoding="utf-8"))

    # what currently occupies those files, kept before it is replaced
    current = [rel for rel in meta.get("files", []) if (project_root / rel).is_file()]
    guard = None
    if current:
        guard = snapshot(
            project_root, current,
            stage=meta.get("stage", "history"),
            note=f"restoring {sid}",
        )
        if guard:
            guard["restored_from"] = sid
            (base.parent / guard["id"] / "meta.json").write_text(
                json.dumps(guard, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )

    restored = []
    for rel in meta.get("files", []):
        src = base / "files" / rel
        if not src.is_file():
            continue
        dest = project_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        restored.append(rel)
    return {
        "id": sid,
        "restored": restored,
        "stage": meta.get("stage"),
        "current_kept_as": guard["id"] if guard else None,
    }
