"""The shared favourites store — a saved prompt set that lives outside projects.

The illustration tool has no project, so a prompt made there would be lost when
the next one is made. This store is where a prompt is kept instead: star it and
it stays, load it any time. comic and manga prompts can be starred here too, so
one list holds every saved prompt regardless of the mode that made it.

    ~/.comicmaker/favorites/
      index.json          the catalogue (and the next id)
      fav-001/
        meta.json         title, kind, canvas, style, brief, tags, dates
        prompt.txt        the positive prompt
        negative.txt      the three-section negative
        draft.json        the structured source (recompile / preview)
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from . import providers

ROOT = providers.CONFIG / "favorites"
router = APIRouter(prefix="/api/favorites", tags=["favorites"])

KINDS = ("illustration", "comic", "manga")


# --------------------------------------------------------------------- fs
def _read_json(path: Path, default=None):
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _index() -> dict:
    return _read_json(ROOT / "index.json", {"next": 1, "favorites": []})


def _row(fid: str) -> dict:
    return next((row for row in _index().get("favorites", []) if row.get("id") == fid), {})


def _today() -> str:
    return date.today().isoformat()


def _slug_id(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")
    return s[:40] or "prompt"


# --------------------------------------------------------------------- ops
def list_favorites() -> list[dict]:
    return _index().get("favorites", [])


def get_favorite(fid: str) -> dict:
    if not re.fullmatch(r"[a-z0-9-]+", fid or ""):
        raise HTTPException(400, "bad favourite id")
    folder = ROOT / fid
    meta = _read_json(folder / "meta.json")
    if not meta:
        raise HTTPException(404, f"no favourite {fid}")
    return {
        **meta,
        "prompt": (folder / "prompt.txt").read_text(encoding="utf-8") if (folder / "prompt.txt").is_file() else "",
        "negative": (folder / "negative.txt").read_text(encoding="utf-8") if (folder / "negative.txt").is_file() else "",
        "draft": _read_json(folder / "draft.json", {}),
    }


def save_favorite(
    *,
    kind: str,
    title: str,
    draft: dict,
    prompt: str,
    negative: str,
    brief: str = "",
    source: str = "",
    canvas_tier: str = "M",
    art_style: str = "fkey_painterly",
    tags: list[str] | None = None,
) -> dict:
    if kind not in KINDS:
        raise HTTPException(400, f"kind must be one of {KINDS}")
    idx = _index()
    n = int(idx.get("next", 1))
    fid = f"fav-{n:03d}"
    while (ROOT / fid).exists():
        n += 1
        fid = f"fav-{n:03d}"
    idx["next"] = n + 1

    title = (title or "prompt").strip()[:120]
    meta = {
        "id": fid,
        "title": title,
        "kind": kind,
        "canvas_tier": canvas_tier,
        "art_style": art_style,
        "brief": brief[:2000],
        "source": source,
        "tags": tags or [],
        "created": _today(),
        "updated": _today(),
    }
    folder = ROOT / fid
    _write_json(folder / "meta.json", meta)
    (folder / "prompt.txt").parent.mkdir(parents=True, exist_ok=True)
    (folder / "prompt.txt").write_text(prompt + ("" if prompt.endswith("\n") else "\n"), encoding="utf-8")
    (folder / "negative.txt").write_text(negative + ("" if negative.endswith("\n") else "\n"), encoding="utf-8")
    _write_json(folder / "draft.json", draft or {})

    idx["favorites"] = [meta] + idx.get("favorites", [])
    _write_json(ROOT / "index.json", idx)
    return meta


def update_favorite(fid: str, *, title: str | None = None, tags: list[str] | None = None,
                    draft: dict | None = None, prompt: str | None = None,
                    negative: str | None = None) -> dict:
    folder = ROOT / fid
    meta = _read_json(folder / "meta.json")
    if not meta:
        raise HTTPException(404, f"no favourite {fid}")
    if title is not None:
        meta["title"] = title.strip()[:120]
    if tags is not None:
        meta["tags"] = tags
    if draft is not None:
        _write_json(folder / "draft.json", draft)
    if prompt is not None:
        (folder / "prompt.txt").write_text(prompt + ("" if prompt.endswith("\n") else "\n"), encoding="utf-8")
    if negative is not None:
        (folder / "negative.txt").write_text(negative + ("" if negative.endswith("\n") else "\n"), encoding="utf-8")
    meta["updated"] = _today()
    _write_json(folder / "meta.json", meta)

    idx = _index()
    idx["favorites"] = [meta if row.get("id") == fid else row for row in idx.get("favorites", [])]
    _write_json(ROOT / "index.json", idx)
    return meta


def delete_favorite(fid: str) -> dict:
    folder = ROOT / fid
    if not folder.is_dir():
        raise HTTPException(404, f"no favourite {fid}")
    for child in folder.iterdir():
        if child.is_file():
            child.unlink()
    folder.rmdir()
    idx = _index()
    idx["favorites"] = [row for row in idx.get("favorites", []) if row.get("id") != fid]
    _write_json(ROOT / "index.json", idx)
    return {"removed": fid}


# --------------------------------------------------------------------- api
class FavoriteIn(BaseModel):
    kind: str
    title: str = "prompt"
    draft: dict = {}
    prompt: str
    negative: str
    brief: str = ""
    source: str = ""
    canvas_tier: str = "M"
    art_style: str = "fkey_painterly"
    tags: list[str] | None = None


class FavoritePatch(BaseModel):
    title: str | None = None
    tags: list[str] | None = None
    draft: dict | None = None
    prompt: str | None = None
    negative: str | None = None


@router.get("")
def list_route() -> list[dict]:
    return list_favorites()


@router.post("")
def save_route(body: FavoriteIn) -> dict:
    return save_favorite(**body.model_dump())


@router.get("/{fid}")
def get_route(fid: str) -> dict:
    return get_favorite(fid)


@router.put("/{fid}")
def update_route(fid: str, body: FavoritePatch) -> dict:
    return update_favorite(fid, **body.model_dump(exclude_none=True))


@router.delete("/{fid}")
def delete_route(fid: str) -> dict:
    return delete_favorite(fid)
