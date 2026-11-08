"""The illustration tool — a project-free prompt maker (Type B).

There is no project here. A command goes in, a finished sectioned prompt comes
out, and it can be starred into the shared favourites store or dropped. The
prompt is Type B (`docs/reference-prompts/B-*`): a sectioned `<|...|>` prompt
with no JSON and no boxes.

    POST /api/illustration/generate   { brief, canvas_tier, art_style }
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from . import providers, skills
from .stages import build, validate

router = APIRouter(prefix="/api/illustration", tags=["illustration"])

MAX_REPAIR = 3
NEGATIVE = {"fkey_clean": "clean"}   # everything else is painterly


def _system() -> str:
    parts = [skills.read_asset("illustration-prompt/SKILL.md")["content"]]
    for name in ("authoring-spec.md", "templates/type-b-sections.md"):
        parts.append(skills.read_asset(f"manga-craft/{name}")["content"])
    parts.append(
        "Reply with a single JSON object and nothing else — no prose, no code "
        "fence. The tool validates it against the Type B rules and will send it "
        "back until there is no error."
    )
    return "\n\n---\n\n".join(parts)


def _negative_style(art_style: str) -> str:
    return NEGATIVE.get(art_style, "painterly")


def generate(brief: str, *, canvas_tier: str = "M", art_style: str = "fkey_painterly",
             caller=None) -> dict:
    brief = (brief or "").strip()
    if not brief:
        raise HTTPException(400, "a command is required")
    try:
        width, height = build.tier_size(canvas_tier)
    except KeyError:
        raise HTTPException(400, f"unknown canvas tier {canvas_tier!r}")

    system = _system()
    user = (
        f"# Command\n{brief}\n\n"
        f"# Canvas\n{width} x {height} px (the prompt carries no boxes)\n\n"
        f"# Style adapter\n{art_style}\n\n"
        "# Task\nWrite one Type B sectioned prompt for the command above, exactly "
        "as this skill defines."
    )

    issue_list: list[dict] = []
    draft: dict = {}
    prompt_user = user
    for _ in range(MAX_REPAIR):
        if caller is not None:
            reply = caller("illustration-prompt", system, prompt_user)
        else:
            reply = providers.chat(
                [{"role": "system", "content": system}, {"role": "user", "content": prompt_user}],
                stage="illustration-prompt",
                json_mode=True,
            )
        draft = providers.parse_json(reply)
        issue_list = validate.validate_sections(draft)
        if not validate.errors(issue_list):
            break
        lines = [f"- {e['where']}: {e['message']}" for e in validate.errors(issue_list)]
        prompt_user = user + "\n\n# Fix every one of these and return the full corrected JSON\n" + "\n".join(lines)

    draft.setdefault("artist", "fkey" if str(art_style).startswith("fkey") else "")
    prompt = build.compile_sections(draft)
    negative = build.negative(_negative_style(art_style))
    return {
        "draft": draft,
        "prompt": prompt,
        "negative": negative,
        "issues": issue_list,
        "ok": not validate.errors(issue_list),
        "canvas_tier": canvas_tier,
        "art_style": art_style,
    }


class GenerateIn(BaseModel):
    brief: str
    canvas_tier: str = "M"
    art_style: str = "fkey_painterly"


@router.post("/generate")
def generate_route(body: GenerateIn) -> dict:
    try:
        return generate(body.brief, canvas_tier=body.canvas_tier, art_style=body.art_style)
    except providers.ProviderError as e:
        raise HTTPException(503, str(e))
