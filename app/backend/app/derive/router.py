"""Derive endpoints: the things that are recomputed, never stored.

Compiling a prompt and drawing its preview are both pure functions of the stored
artifacts plus the current view state (language, canvas tier). Nothing here
writes to disk.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import projects
from ..stages import build
from . import preview

router = APIRouter(prefix="/api/derive", tags=["derive"])

# Canvas tiers, mirrored from manga-craft/templates/layouts.json so the preview
# can resolve a tier without reading the library for every request.
TIERS: dict[str, tuple[int, int]] = {
    "S": (704, 992),
    "M": (992, 1408),
    "L": (1248, 1760),
    "XL": (1408, 1984),
}


def tier_size(tier: str) -> tuple[int, int]:
    if tier not in TIERS:
        raise HTTPException(400, f"unknown canvas tier {tier!r}")
    return TIERS[tier]


class PreviewIn(BaseModel):
    prompt: str            # the compiled prompt, as text
    width: int | None = None
    height: int | None = None
    tier: str | None = "M"


@router.post("/preview")
def post_preview(body: PreviewIn) -> dict[str, Any]:
    """Draw a compiled prompt.

    The prompt text may be a bare JSON object or the pasted form that carries the
    trigger line on the first line, so strip anything before the first brace.
    """
    raw = body.prompt.strip()
    brace = raw.find("{")
    if brace < 0:
        raise HTTPException(400, "no JSON object found in the prompt")
    try:
        prompt = json.loads(raw[brace:])
    except json.JSONDecodeError as e:
        raise HTTPException(400, f"prompt is not valid JSON: {e}")

    if "items" not in prompt:
        raise HTTPException(400, "the prompt has no items")

    if body.width and body.height:
        width, height = body.width, body.height
    else:
        width, height = tier_size(body.tier or "M")

    return preview.build(prompt, width, height)


@router.get("/tiers")
def get_tiers() -> dict[str, list[int]]:
    return {k: list(v) for k, v in TIERS.items()}


@router.get("/templates")
def get_templates(slug: str | None = None) -> list[dict[str, Any]]:
    """Every layout a project may pick: the 13 tier templates and the 196 dataset
    layouts. When `slug` is given, detailed cuts are filtered by the project's
    `detail_panels` setting."""
    detail: bool | None = None
    if slug:
        path = projects.PROJECTS / slug / "project.json"
        if path.is_file():
            detail = json.loads(path.read_text(encoding="utf-8")).get("detail_panels", False)

    out: list[dict[str, Any]] = list(build.tier_layout_summary())
    for m in build.moss_layout_summary(detail):
        out.append({
            "id": m["id"], "name_en": m["name_en"], "name_ja": m["name"],
            "panels": m["panels"], "tiers": 0, "source": "moss",
            "detail": m["detail"], "inset": m["inset"], "category": m["category"],
            "focus": m["focus"],
        })
    return out


class ComicPageIn(BaseModel):
    slug: str
    episode: str
    page: int
    lang: str | None = None       # ko | en | ja — recompiles the lettering


@router.post("/comic-page")
def post_comic_page(body: ComicPageIn) -> dict[str, Any]:
    """Recompile one comic page for a chosen language.

    A comic scene already holds every line in ko/en/ja, so the language button is
    a recompile, never a translation (design D6): the same frame, the same drawing,
    only the lettering swapped to the chosen language.
    """
    root = projects.PROJECTS / body.slug
    if not (root / "project.json").is_file():
        raise HTTPException(404, f"no project {body.slug!r}")
    scene_path = root / "episodes" / body.episode / "pages" / f"page-{body.page:03d}.scene.json"
    if not scene_path.is_file():
        raise HTTPException(404, f"no comic scene for {body.episode} page {body.page}")

    project = json.loads((root / "project.json").read_text(encoding="utf-8"))
    bible_path = root / "bible" / "characters.json"
    bible = json.loads(bible_path.read_text(encoding="utf-8")) if bible_path.is_file() else {"characters": []}
    scene = json.loads(scene_path.read_text(encoding="utf-8"))

    lang = body.lang or project.get("languages", {}).get("default", "ko")
    if lang not in ("ko", "en", "ja"):
        raise HTTPException(400, f"unknown language {lang!r}")

    characters = {c["id"]: c for c in bible.get("characters", [])}
    draft = build.compile_single_frame(scene, project, characters, lang)
    prompt = build.compile_draft(draft)
    data = json.loads(prompt[prompt.index("{"):])
    return {
        "lang": lang,
        "tier": project.get("canvas", {}).get("tier", "M"),
        "prompt": prompt,
        "negative": build.negative(build.negative_style(project)),
        "preview": preview.build(data, draft["width"], draft["height"]),
        "characters": scene.get("characters", []),
    }


class PageIn(BaseModel):
    slug: str
    episode: str
    page: int
    lang: str | None = None       # defaults to the project's language
    tier: str | None = None       # redraw at another canvas size


@router.post("/page")
def post_page(body: PageIn) -> dict[str, Any]:
    """Rebuild one stored page for a language and a canvas tier.

    This is why the language button is free: the conti already holds all three
    languages, so the page is recompiled, never retranslated. Nothing is written.
    """
    root = projects.PROJECTS / body.slug
    if not (root / "project.json").is_file():
        raise HTTPException(404, f"no project {body.slug!r}")

    conti_path = root / "episodes" / body.episode / "pages" / f"page-{body.page:03d}.conti.json"
    if not conti_path.is_file():
        raise HTTPException(404, f"no conti for {body.episode} page {body.page}")

    project = json.loads((root / "project.json").read_text(encoding="utf-8"))
    bible_path = root / "bible" / "characters.json"
    bible = json.loads(bible_path.read_text(encoding="utf-8")) if bible_path.is_file() else {"characters": []}
    conti = json.loads(conti_path.read_text(encoding="utf-8"))

    lang = body.lang or project.get("languages", {}).get("default", "ko")
    if lang not in ("ko", "en", "ja"):
        raise HTTPException(400, f"unknown language {lang!r}")
    tier = body.tier or project.get("canvas", {}).get("tier", "M")
    if tier not in TIERS:
        raise HTTPException(400, f"unknown canvas tier {tier!r}")

    characters = {c["id"]: c for c in bible.get("characters", [])}
    try:
        draft = build.build_page(conti, project, characters, lang, tier_override=tier)
        prompt = build.compile_draft(draft)
    except ValueError as e:
        raise HTTPException(422, f"the page does not compile: {e}")

    data = json.loads(prompt[prompt.index("{"):])
    width, height = tier_size(tier)
    return {
        "lang": lang,
        "tier": tier,
        "prompt": prompt,
        "preview": preview.build(data, width, height),
        "layout": conti.get("layout", {}),
        "split": conti.get("split", "sequence"),
        "panel_count": len(conti.get("panels", [])),
    }
