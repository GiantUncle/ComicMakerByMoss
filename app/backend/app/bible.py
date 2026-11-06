"""The cast pool — viewable and editable by hand.

A character is data, not a prompt: the card holds the anchors, the signature and
the appearance-only descriptor, and stage 7 copies the descriptor into the page.
Editing the card here is editing the data the pipeline reads. Each edit is
validated with the same rules the model is held to, and snapshotted first.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from . import history, projects
from .stages import validate

router = APIRouter(prefix="/api/projects/{slug}/bible", tags=["bible"])

EMPTY = {"characters": [], "objects": []}


def _root(slug: str) -> Path:
    root = projects.PROJECTS / slug
    if not (root / "project.json").is_file():
        raise HTTPException(404, f"no project {slug!r}")
    return root


def _read(root: Path) -> dict:
    path = root / "bible" / "characters.json"
    if not path.is_file():
        return dict(EMPTY)
    return json.loads(path.read_text(encoding="utf-8"))


def _write(root: Path, pool: dict) -> None:
    path = root / "bible" / "characters.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(pool, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@router.get("")
def get_bible(slug: str) -> dict:
    root = _root(slug)
    pool = _read(root)
    issues = validate.validate_bible(pool, None)
    return {
        "pool": pool,
        "issues": issues,
        "error_count": len(validate.errors(issues)),
        "warning_count": len(validate.warnings(issues)),
    }


class PoolIn(BaseModel):
    pool: dict


@router.put("")
def put_bible(slug: str, body: PoolIn) -> dict:
    root = _root(slug)
    issues = validate.validate_bible(body.pool, None)
    if validate.errors(issues):
        raise HTTPException(422, {"message": "카드에 오류가 있습니다", "issues": validate.errors(issues)})
    history.snapshot(root, ["bible/characters.json"], stage="manga-3-bible", note="cast edited by hand")
    _write(root, body.pool)
    return {"pool": body.pool, "saved": True, "issues": issues}


class CardIn(BaseModel):
    bucket: str = "characters"          # characters | objects
    card: dict


@router.put("/card")
def upsert_card(slug: str, body: CardIn) -> dict:
    root = _root(slug)
    if body.bucket not in ("characters", "objects"):
        raise HTTPException(400, "bucket must be characters or objects")
    cid = str(body.card.get("id", "")).strip()
    if not cid:
        raise HTTPException(400, "a card needs an id")

    pool = _read(root)
    other = "objects" if body.bucket == "characters" else "characters"
    pool.setdefault(body.bucket, [])
    pool.setdefault(other, [])
    cards = [c for c in pool[body.bucket] if c.get("id") != cid]
    cards.append(body.card)
    pool[body.bucket] = cards
    # a card lives in exactly one bucket
    pool[other] = [c for c in pool[other] if c.get("id") != cid]

    issues = validate.validate_bible(pool, None)
    if validate.errors(issues):
        raise HTTPException(422, {"message": "카드에 오류가 있습니다", "issues": validate.errors(issues)})
    history.snapshot(root, ["bible/characters.json"], stage="manga-3-bible", note=f"cast edited: {cid}")
    _write(root, pool)
    return {"pool": pool, "saved": True, "issues": issues}


@router.delete("/card/{cid}")
def delete_card(slug: str, cid: str) -> dict:
    root = _root(slug)
    pool = _read(root)
    history.snapshot(root, ["bible/characters.json"], stage="manga-3-bible", note=f"cast removed: {cid}")
    for bucket in ("characters", "objects"):
        pool[bucket] = [c for c in pool.get(bucket, []) if c.get("id") != cid]
    _write(root, pool)
    return {"pool": pool, "removed": cid}
