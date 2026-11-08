"""Projects, the wizard's memory, and episodes.

A project holds what outlives one story: settings, the cast pool, the art style.
An episode is one chapter: its source, its plan, its pages. The wizard records
its answers in `wizard.json` before anything is built, so a resumed session knows
both where it is and why each setting is what it is.
"""

from __future__ import annotations

import json
import os
import re
from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

REPO = Path(__file__).resolve().parents[3]
PROJECTS = Path(os.environ.get("CM_PROJECTS", REPO / "projects"))

SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
TIERS = ("S", "M", "L", "XL")
MODES = ("manga", "comic")   # illustration is a top-level tool, not a project (see docs/design-output-modes.md)

# The default drawing style, in one sentence for `summary.caption`. A project
# carries this so every page looks the same; the user may replace it.
DEFAULT_STYLE_PROMPT = (
    "2D digital painting comic, finely rendered luminous facial features and "
    "delicate hair strands against breathable painterly brushwork, selective focus"
)
ROUTES = ("provided", "premise", "genre", "outline")
# how the dominant panel of a page is spent — a strategy the agent applies, not a rule
FOCUS = ("character", "narrative", "balanced")

router = APIRouter(prefix="/api", tags=["projects"])


# ----------------------------------------------------------------- helpers
def _require_slug(slug: str) -> Path:
    if not SLUG.match(slug):
        raise HTTPException(400, "slug must be lowercase kebab-case")
    return PROJECTS / slug


def _read(path: Path) -> dict:
    if not path.is_file():
        raise HTTPException(404, f"missing {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _today() -> str:
    return date.today().isoformat()


def _norm_episode_pages(n: object) -> int:
    try:
        v = int(n)  # type: ignore[arg-type]
    except Exception:
        v = 12
    v = max(1, min(32, v))
    if v < 4:
        return 4
    return max(4, min(32, round(v / 4) * 4))


# ------------------------------------------------------------------- models
class Title(BaseModel):
    ko: str = ""
    en: str = ""
    ja: str = ""


class Languages(BaseModel):
    default: str = "ko"
    all: list[str] = Field(default_factory=lambda: ["ko", "en", "ja"])


class Canvas(BaseModel):
    tier: str = "M"
    ratio: str = "a4_portrait"


class Panels(BaseModel):
    min: int = 2
    max: int = 4          # 5+ panels means small, detailed cuts — opt-in only


class NewProject(BaseModel):
    slug: str
    title: Title = Title()
    mode: str = "manga"
    languages: Languages = Languages()
    reading_direction: str = "rtl"
    canvas: Canvas = Canvas()
    art_style: str = "fkey_painterly"
    art_style_prompt: str = DEFAULT_STYLE_PROMPT   # the project-wide drawing style
    panels: Panels = Panels()
    cut_mode: str = "balanced"
    detail_panels: bool = False   # allow small/detailed cuts (5+ panels, insets)
    story_focus: str = "balanced"  # character | narrative | balanced
    episode_pages: int = 12        # pages per episode (multiples of 4 recommended)


class ProjectPatch(BaseModel):
    title: Title | None = None
    canvas: Canvas | None = None
    reading_direction: str | None = None
    languages: Languages | None = None
    art_style: str | None = None
    art_style_prompt: str | None = None
    panels: Panels | None = None
    detail_panels: bool | None = None
    story_focus: str | None = None
    episode_pages: int | None = None


class WizardPatch(BaseModel):
    story_route: str | None = None
    answers: dict | None = None
    project_settled: list[str] | None = None
    open_episode: str | None = None


class NewEpisode(BaseModel):
    id: str
    title: Title = Title()
    source_origin: str = "provided"
    story: str | None = None      # the pasted text, if the user has it
    cast: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------- endpoints
@router.get("/projects")
def list_projects() -> list[dict]:
    out = []
    if PROJECTS.exists():
        for d in sorted(PROJECTS.iterdir()):
            pj = d / "project.json"
            if not pj.is_file():
                continue
            try:
                p = json.loads(pj.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            eps = []
            for e in sorted((d / "episodes").glob("*")) if (d / "episodes").exists() else []:
                if not e.is_dir():
                    continue
                meta = {}
                if (e / "episode.json").is_file():
                    meta = json.loads((e / "episode.json").read_text(encoding="utf-8"))
                eps.append({
                    "id": e.name,
                    "title": meta.get("title", {}),
                    "page_total": meta.get("page_total"),
                    "source": (e / "source" / "APPROVED").exists(),
                    "plan": (e / "plan" / "APPROVED").exists(),
                    "pages": len(list((e / "pages").glob("*.conti.json")))
                    if (e / "pages").exists() else 0,
                })
            out.append({**p, "episodes": eps})
    return out


@router.post("/projects")
def create_project(body: NewProject) -> dict:
    if body.mode not in MODES:
        raise HTTPException(400, f"mode must be one of {MODES}")
    if body.canvas.tier not in TIERS:
        raise HTTPException(400, f"tier must be one of {TIERS}")
    if body.story_focus not in FOCUS:
        raise HTTPException(400, f"story_focus must be one of {FOCUS}")
    if not (1 <= body.panels.min <= body.panels.max <= 8):
        raise HTTPException(400, "panels must satisfy 1 <= min <= max <= 8")

    root = _require_slug(body.slug)
    if (root / "project.json").exists():
        raise HTTPException(409, f"{body.slug} already exists")
    root.mkdir(parents=True, exist_ok=True)

    panels = body.panels.model_dump()
    if body.mode == "comic":
        # a comic page is one still frame — no cut range at all
        panels = {"min": 1, "max": 1}
    elif not body.detail_panels:
        # a page of five or more panels means small, detailed cuts the model
        # handles poorly, so the default keeps every page at four or fewer
        panels["max"] = min(panels["max"], 4)
        panels["min"] = min(panels["min"], panels["max"])

    raw_pages = getattr(body, "episode_pages", 12)
    if body.mode == "comic" and raw_pages in (None, 12):
        raw_pages = 4   # a short twitter comic defaults to four frames
    episode_pages = _norm_episode_pages(raw_pages)
    project = {
        "slug": body.slug,
        "mode": body.mode,
        "canvas": body.canvas.model_dump(),
        "reading_direction": body.reading_direction,
        "languages": body.languages.model_dump(),
        "art_style": body.art_style,
        "art_style_prompt": body.art_style_prompt,
        "panels": panels,
        "detail_panels": body.detail_panels,
        "story_focus": body.story_focus,
        "episode_pages": episode_pages,
        "page_unit": 4,
        "cut_mode": body.cut_mode,
        "title": body.title.model_dump(),
        "episodes": [],
    }
    _write(root / "project.json", project)
    _write(root / "wizard.json", {
        "slug": body.slug,
        "mode": body.mode,
        "story_route": None,
        "answers": {
            "languages": body.languages.model_dump(),
            "reading_direction": body.reading_direction,
            "canvas_tier": body.canvas.tier,
            "art_style": body.art_style,
            "panels": panels,
            "cut_mode": body.cut_mode,
            "detail_panels": body.detail_panels,
            "story_focus": body.story_focus,
            "episode_pages": episode_pages,
        },
        "project_settled": [],
        "episodes": [],
        "updated": _today(),
    })
    return project


@router.get("/projects/{slug}")
def get_project(slug: str) -> dict:
    return _read(_require_slug(slug) / "project.json")


@router.patch("/projects/{slug}")
def patch_project(slug: str, patch: ProjectPatch) -> dict:
    root = _require_slug(slug)
    data = _read(root / "project.json")
    for key, value in patch.model_dump(exclude_none=True).items():
        if key == "episode_pages":
            value = _norm_episode_pages(value)
        data[key] = value
    if not data.get("detail_panels", False):
        panels = data.get("panels", {})
        panels["max"] = min(panels.get("max", 4), 4)
        panels["min"] = min(panels.get("min", 3), panels["max"])
        data["panels"] = panels
    _write(root / "project.json", data)
    return data


@router.get("/projects/{slug}/wizard")
def get_wizard(slug: str) -> dict:
    return _read(_require_slug(slug) / "wizard.json")


@router.patch("/projects/{slug}/wizard")
def patch_wizard(slug: str, patch: WizardPatch) -> dict:
    root = _require_slug(slug)
    data = _read(root / "wizard.json")
    if patch.story_route is not None:
        if patch.story_route not in ROUTES:
            raise HTTPException(400, f"story_route must be one of {ROUTES}")
        data["story_route"] = patch.story_route
    if patch.answers is not None:
        data.setdefault("answers", {}).update(patch.answers)
    if patch.project_settled is not None:
        data["project_settled"] = patch.project_settled
    if patch.open_episode is not None:
        data["open_episode"] = patch.open_episode
    data["updated"] = _today()
    _write(root / "wizard.json", data)
    return data


@router.post("/projects/{slug}/episodes")
def create_episode(slug: str, body: NewEpisode) -> dict:
    if body.source_origin not in ROUTES:
        raise HTTPException(400, f"source_origin must be one of {ROUTES}")
    root = _require_slug(slug)
    project = _read(root / "project.json")
    if not SLUG.match(body.id):
        raise HTTPException(400, "episode id must be lowercase kebab-case")

    ep_root = root / "episodes" / body.id
    if (ep_root / "episode.json").exists():
        raise HTTPException(409, f"episode {body.id} already exists")

    episode = {
        "id": body.id,
        "title": body.title.model_dump(),
        "source_origin": body.source_origin,
        "cast": body.cast,
        "page_budget": "estimate",
        "page_total": None,
    }
    _write(ep_root / "episode.json", episode)

    if body.story and body.story.strip():
        src = ep_root / "source"
        src.mkdir(parents=True, exist_ok=True)
        if body.source_origin == "provided":
            # the user's own text is the source, verbatim — prose for manga, a
            # short brief for a comic
            name = "brief.md" if project.get("mode") == "comic" else "novel.txt"
            (src / name).write_text(body.story, encoding="utf-8")
            (src / "APPROVED").write_text(
                f"provided · {_today()}\n", encoding="utf-8"
            )
        else:
            # premise / genre / outline: stage 1 authors the prose from this brief
            (src / "brief.md").write_text(body.story, encoding="utf-8")

    if body.id not in project.get("episodes", []):
        project.setdefault("episodes", []).append(body.id)
        _write(root / "project.json", project)

    wizard = _read(root / "wizard.json")
    wizard.setdefault("episodes", [])
    if not any(e.get("id") == body.id for e in wizard["episodes"]):
        wizard["episodes"].append({"id": body.id, "phase": 2, "settled": []})
    wizard["open_episode"] = body.id
    wizard["updated"] = _today()
    _write(root / "wizard.json", wizard)

    return {"episode": episode, "source": bool(body.story)}


@router.get("/projects/{slug}/episodes/{ep}")
def get_episode(slug: str, ep: str) -> dict:
    return _read(_require_slug(slug) / "episodes" / ep / "episode.json")


@router.get("/projects/{slug}/episodes/{ep}/source")
def get_source(slug: str, ep: str) -> dict:
    root = _require_slug(slug) / "episodes" / ep
    src = root / "source"
    novel = src / "novel.txt"
    brief = src / "brief.md"
    if novel.is_file():
        return {
            "exists": True,
            "text": novel.read_text(encoding="utf-8"),
            "approved": (src / "APPROVED").exists(),
            "origin": _read(root / "episode.json").get("source_origin", "provided"),
            "kind": "novel",
        }
    if brief.is_file():
        return {
            "exists": True,
            "text": brief.read_text(encoding="utf-8"),
            "approved": False,
            "origin": _read(root / "episode.json").get("source_origin", "premise"),
            "kind": "brief",
        }
    return {"exists": False, "text": "", "approved": False, "origin": None, "kind": None}


class SourceIn(BaseModel):
    text: str
    # "provided" = save as final novel.txt + APPROVED. "brief" = save as brief.md for AI authoring (clears approval).
    mode: str = "provided"
    origin: str | None = None


@router.put("/projects/{slug}/episodes/{ep}/source")
def put_source(slug: str, ep: str, body: SourceIn) -> dict:
    root = _require_slug(slug) / "episodes" / ep
    ej = root / "episode.json"
    if not ej.is_file():
        raise HTTPException(404, f"episode {ep} not found")
    text = (body.text or "").strip()
    if not text:
        raise HTTPException(400, "source text is required")
    src = root / "source"
    src.mkdir(parents=True, exist_ok=True)
    approved = src / "APPROVED"
    novel = src / "novel.txt"
    brief = src / "brief.md"

    if body.mode == "brief":
        origin = body.origin if body.origin in ROUTES and body.origin != "provided" else "premise"
        episode = _read(ej)
        episode["source_origin"] = origin
        _write(ej, episode)
        brief.write_text(text, encoding="utf-8")
        if approved.exists():
            approved.unlink()
        # keep prior novel.txt? stage 1 will overwrite it; removing avoids confusion
        if novel.exists():
            novel.unlink()
        return {"ok": True, "mode": "brief", "origin": origin}
    else:
        origin = body.origin if body.origin in ROUTES else "provided"
        episode = _read(ej)
        episode["source_origin"] = origin
        _write(ej, episode)
        mode = _read(_require_slug(slug) / "project.json").get("mode", "manga")
        target, other = (brief, novel) if mode == "comic" else (novel, brief)
        target.write_text(text, encoding="utf-8")
        approved.write_text(f"{origin} · {_today()}\n", encoding="utf-8")
        if other.exists():
            other.unlink()
        return {"ok": True, "mode": "provided", "origin": origin}
