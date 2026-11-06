"""ComicMaker backend — FastAPI.

Areas, one router each:

  projects  projects, the wizard's memory, episodes
  skills    the shipped originals and the user's editable copies
  derive    the views that are recomputed and never stored (preview, compile)
  stages    the stage runner — status and run
  providers the model endpoints the runner calls (this file)
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import bible, history, projects, providers, skills
from .derive.router import router as derive_router
from .stages.router import router as stages_router

app = FastAPI(title="ComicMaker", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(bible.router)
app.include_router(derive_router)
app.include_router(stages_router)


# ------------------------------------------------------------------- history
def _project_root(slug: str):
    root = projects.PROJECTS / slug
    if not (root / "project.json").is_file():
        raise HTTPException(404, f"no project {slug!r}")
    return root


@app.get("/api/projects/{slug}/history")
def list_history(slug: str, stage: str | None = None) -> list[dict]:
    return history.list_snapshots(_project_root(slug), stage)


@app.post("/api/projects/{slug}/history/{sid}/restore")
def restore_history(slug: str, sid: str) -> dict:
    try:
        return history.restore(_project_root(slug), sid)
    except FileNotFoundError:
        raise HTTPException(404, f"no snapshot {sid}")


@app.get("/api/info")
def info() -> dict:
    return {
        "ok": True,
        "version": app.version,
        "projects_dir": str(projects.PROJECTS),
        "skills_origin": str(skills.ORIGIN),
        "skills_edited": str(skills.EDITED),
    }


# --------------------------------------------------------------------- skills
@app.get("/api/skills")
def list_skills() -> list[dict]:
    return [a.__dict__ for a in skills.list_assets()]


@app.get("/api/skills/asset")
def get_skill(path: str) -> dict:
    try:
        return skills.read_asset(path)
    except FileNotFoundError:
        raise HTTPException(404, f"no asset {path}")


class SkillWrite(BaseModel):
    content: str


@app.put("/api/skills/asset")
def put_skill(path: str, body: SkillWrite) -> dict:
    try:
        return skills.edit_asset(path, body.content)
    except FileNotFoundError:
        raise HTTPException(404, f"no asset {path}")


@app.post("/api/skills/rollback")
def rollback(path: str) -> dict:
    return skills.rollback_asset(path)


@app.post("/api/skills/rollback-all")
def rollback_all() -> dict:
    return skills.rollback_all()


# ------------------------------------------------------------------ providers
@app.get("/api/providers")
def get_providers() -> dict:
    """Every slot (keys stripped) plus the model catalogue, favourites and active."""
    return {"providers": providers.public(), **providers.catalog()}


class ProviderIn(BaseModel):
    id: str
    kind: str = "openai-compatible"
    label: str | None = None
    base_url: str
    api_key: str | None = None
    models: dict | None = None
    supports_json_mode: bool | None = None


@app.put("/api/providers")
def put_provider(body: ProviderIn) -> dict:
    return providers.upsert(body.model_dump(exclude_none=True))


class ProviderTest(BaseModel):
    stage: str | None = None
    provider_id: str | None = None
    model: str | None = None


@app.post("/api/providers/test")
def test_provider(body: ProviderTest) -> dict:
    """One tiny round trip, so a bad key or url is found here, not mid-pipeline."""
    try:
        reply = providers.chat(
            [{"role": "user", "content": "Reply with the single word: ready"}],
            stage=body.stage,
            provider_id=body.provider_id,
            model=body.model,
            temperature=0,
        )
        return {"ok": True, "reply": reply.strip()[:120]}
    except providers.ProviderError as e:
        return {"ok": False, "error": str(e)}


class RefreshIn(BaseModel):
    provider_id: str | None = None


@app.post("/api/providers/models")
def refresh_models(body: RefreshIn | None = None) -> dict:
    """Re-read the model list from a provider (or from every configured one)."""
    providers.refresh(body.provider_id if body else None)
    return {"providers": providers.public(), **providers.catalog()}


@app.get("/api/models")
def get_models(provider: str | None = None) -> dict:
    return providers.catalog(provider)


class ModelFavorite(BaseModel):
    provider: str
    model: str
    on: bool | None = None


@app.post("/api/models/favorite")
def model_favorite(body: ModelFavorite) -> dict:
    providers.toggle_favorite(body.provider, body.model, body.on)
    return providers.catalog()


class ModelSelect(BaseModel):
    provider: str
    model: str


@app.post("/api/models/select")
def model_select(body: ModelSelect) -> dict:
    providers.select_model(body.provider, body.model)
    return providers.catalog()
