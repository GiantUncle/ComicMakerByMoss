"""Stage endpoints — status, review, run and retake."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..providers import ProviderError
from . import runner

router = APIRouter(prefix="/api/stages", tags=["stages"])


@router.get("")
def list_stages(slug: str, episode: str | None = None) -> list[dict]:
    try:
        return runner.status(slug, episode)
    except runner.StageError as e:
        raise HTTPException(404, str(e))


@router.get("/review")
def review_stage(slug: str, stage: str, episode: str | None = None, block: int = 1) -> dict:
    """The stage's current output and its validation — the screen to decide a retake."""
    if not stage or stage == "undefined":
        raise HTTPException(400, "stage is required")
    try:
        return runner.review(slug, stage, ep=episode, block=block)
    except runner.StageError as e:
        raise HTTPException(404, str(e))


class RunIn(BaseModel):
    slug: str
    stage: str
    episode: str | None = None
    block: int = 1
    dry: bool = False
    # a retake: a note, and the scope to redo
    feedback: str | None = None
    pages: list[int] | None = None
    ids: list[str] | None = None
    cuts: list[dict] | None = None     # [{"page": 2, "n": 3}, ...]
    episode_pages: int | None = None


class RetakeIn(BaseModel):
    slug: str
    stage: str
    episode: str | None = None
    block: int = 1
    feedback: str = Field(default="", description="what to change")
    pages: list[int] | None = None      # stage 5/6/7: which pages
    ids: list[str] | None = None        # stage 3/4: which characters
    cuts: list[dict] | None = None      # stage 6/7: which panels — [{"page", "n"}]
    episode_pages: int | None = None


@router.post("/run")
def run_stage(body: RunIn) -> dict:
    try:
        return runner.run(
            body.slug, body.stage, ep=body.episode, block=body.block, dry=body.dry,
            feedback=body.feedback, pages=body.pages, ids=body.ids, cuts=body.cuts,
            episode_pages=body.episode_pages,
        )
    except runner.StageError as e:
        raise HTTPException(409, str(e))
    except ProviderError as e:
        raise HTTPException(503, str(e))


@router.post("/retake")
def retake_stage(body: RetakeIn) -> dict:
    """Re-run a stage, scoped. Same path as a run, with a note and a target."""
    if not (body.feedback.strip() or body.pages or body.ids or body.cuts):
        raise HTTPException(400, "a retake needs a note, pages, ids or cuts to act on")
    try:
        return runner.run(
            body.slug, body.stage, ep=body.episode, block=body.block,
            feedback=body.feedback or None, pages=body.pages, ids=body.ids, cuts=body.cuts,
            episode_pages=body.episode_pages,
        )
    except runner.StageError as e:
        raise HTTPException(409, str(e))
    except ProviderError as e:
        raise HTTPException(503, str(e))


class RetakeCutIn(BaseModel):
    slug: str
    episode: str
    page: int
    panel: int
    feedback: str = ""


@router.post("/retake-cut")
def retake_cut(body: RetakeCutIn) -> dict:
    """Retake one cut: rewrite that panel's conti, then rebuild sheet+prompt for that page."""
    try:
        conti = runner.run(
            body.slug, "manga-6-conti", ep=body.episode,
            cuts=[{"page": body.page, "n": body.panel}], feedback=body.feedback or None,
        )
        sheet = runner.run(body.slug, "manga-7-sheets", ep=body.episode, pages=[body.page])
        art = runner.run(body.slug, "manga-8-artwork", ep=body.episode, pages=[body.page])
        pages = runner.run(body.slug, "manga-9-prompts", ep=body.episode, pages=[body.page])
        return {"conti": conti, "sheet": sheet, "art": art, "page": pages}
    except runner.StageError as e:
        raise HTTPException(409, str(e))
    except ProviderError as e:
        raise HTTPException(503, str(e))


class RetemplateIn(BaseModel):
    slug: str
    episode: str
    page: int
    layout: dict


@router.post("/retemplate")
def retemplate(body: RetemplateIn) -> dict:
    """Swap a page's layout template and rebuild it (the conti is the source)."""
    try:
        return runner.retemplate(body.slug, body.episode, body.page, body.layout)
    except runner.StageError as e:
        raise HTTPException(409, str(e))
    except ProviderError as e:
        raise HTTPException(503, str(e))


class PlanTemplateIn(BaseModel):
    slug: str
    episode: str
    page: int
    template_id: str


@router.post("/plan-template")
def plan_template(body: PlanTemplateIn) -> dict:
    """Set a page's layout template in the episode plan (stage 5)."""
    try:
        return runner.retemplate_plan(body.slug, body.episode, body.page, body.template_id)
    except runner.StageError as e:
        raise HTTPException(409, str(e))


class OrchestrateIn(BaseModel):
    slug: str
    episode: str | None = None
    from_n: int = 1
    to_n: int = 9


@router.post("/orchestrate")
def orchestrate(body: OrchestrateIn) -> dict:
    """Run the whole table in order for one episode, stopping where a human must."""
    try:
        return runner.orchestrate(
            body.slug, body.episode, from_n=body.from_n, to_n=body.to_n
        )
    except runner.StageError as e:
        raise HTTPException(409, str(e))
    except ProviderError as e:
        raise HTTPException(503, str(e))
