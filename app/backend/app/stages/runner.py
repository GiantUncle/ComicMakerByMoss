"""The stage runner — one invocation runs one stage, and a retake re-runs part.

Each model stage is a loop, not a single call:

    build prompt  ->  ask  ->  validate  ->  (errors?) hand them back  ->  repeat
                                          ->  clean  ->  write  ->  gate

A stage is not done until `validate.py` finds no error. That is the point: the
model does not get to stop with overlapping panels or a leaked `ref_id`.

`feedback`, `pages` and `ids` turn a run into a **retake** — the same path, but
scoped: rewrite only these pages, only these characters, with the user's note.

    model stages     1 source · 3 bible · 5 plan · 6 conti
    deterministic    4 refsheets · 7 sheets · 8 prompts   (no model; the tools decide)
    present          2 project                           (the wizard already wrote it)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

from .. import history, pageshape, projects, providers, skills
from . import build, registry, validate
from .registry import Stage

Caller = Callable[[str, str, str], str]      # (stage_id, system, user) -> reply text

SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_REPAIR = 8

SHEET_FRAMING = (
    "A character reference sheet: one figure, front and three-quarter bust, "
    "plain flat neutral background, even light, nothing cropped."
)


class StageError(RuntimeError):
    """A stage cannot run, or the model's reply fails the stage's checks."""


# ------------------------------------------------------------------- fs utils
def _root(slug: str) -> Path:
    root = projects.PROJECTS / slug
    if not (root / "project.json").is_file():
        raise StageError(f"no project {slug!r}")
    return root


_MISSING = object()


def _read_json(path: Path, default: Any = _MISSING) -> Any:
    if not path.is_file():
        if default is _MISSING:
            raise StageError(f"missing {path.name}")
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _source_text(root: Path, ep: str) -> str:
    """An episode's source text — the manga novel, or a comic's brief."""
    src = root / "episodes" / ep / "source"
    return _read_text(src / "novel.txt") or _read_text(src / "brief.md")


def _stage_files(root: Path, stage: Stage, ep: str | None) -> list[str]:
    """The stage's own files that already exist — what a run would overwrite."""
    out: list[str] = []
    for pattern in stage.produces:
        for path in registry.matches(root, registry.render(pattern, ep)):
            out.append(_rel(root, path))
    if stage.gate:
        gate = root / registry.render(stage.gate, ep)
        if gate.is_file():
            out.append(_rel(root, gate))
    return sorted(set(out))


def block_pages(page_total: int, block: int) -> list[int]:
    if block < 1:
        raise StageError("block starts at 1")
    first = (block - 1) * 4 + 1
    return [n for n in range(first, first + 4) if n <= page_total]


def block_of(page: int) -> int:
    return (page - 1) // 4 + 1


# ------------------------------------------------------------------- prompt
def _skill_doc(stage_id: str) -> str:
    return skills.read_asset(f"{stage_id}/SKILL.md")["content"]


def _craft_doc(name: str) -> str:
    return skills.read_asset(f"manga-craft/{name}")["content"]


def _system_prompt(stage: Stage) -> str:
    parts = [_skill_doc(stage.id)]
    for name in stage.craft:
        parts.append(_craft_doc(name))
    parts.append(
        "Reply with a single JSON object and nothing else — no prose, no code "
        "fence. Follow the stage document above; it is the contract. The build "
        "validates your JSON against the schema and the manga grammar, and will "
        "send it back until there is no error."
    )
    return "\n\n---\n\n".join(parts)


def _project_brief(project: dict, episode: dict | None) -> str:
    lines = [
        f"mode: {project.get('mode')}",
        f"reading_direction: {project.get('reading_direction')}",
        f"canvas_tier: {project.get('canvas', {}).get('tier')}",
        f"art_style: {project.get('art_style')}",
        f"panel_range: {project.get('panels', {}).get('min')}..{project.get('panels', {}).get('max')}",
        f"detail_panels: {project.get('detail_panels', False)}",
        f"story_focus: {project.get('story_focus', 'balanced')}",
        f"languages: {', '.join(project.get('languages', {}).get('all', []))}",
    ]
    if episode:
        lines.append(f"episode: {episode.get('id')} — {episode.get('title')}")
        lines.append(f"cast: {', '.join(episode.get('cast', [])) or '(not yet fixed)'}")
    return "\n".join(lines)


def _valid_templates(project: dict) -> list[str]:
    """Every layout id a project may use — both libraries, minus detailed cuts
    when the project has not opted in."""
    ids = [t["id"] for t in build.library()["templates"]]
    ids += [m["id"] for m in build.moss_layout_summary(project.get("detail_panels", False))]
    return ids


def _default_template(project: dict, panels: int, used: set[str] | None = None) -> str:
    """A layout with this many panels that no other page has taken."""
    taken = used or set()
    for m in pickable(project):
        if m["panels"] == panels and m["id"] not in taken:
            return m["id"]
    for m in pickable(project):
        if m["panels"] == panels:
            return m["id"]
    return "DAN3"


def _unrepeat_layouts(project: dict, pages: list[dict]) -> None:
    """One layout per page. A layout is never used twice in an episode."""
    used: set[str] = set()
    for page in pages:
        tpl = page.get("template_suggestion")
        if not tpl:
            continue
        if tpl in used:
            page["template_suggestion"] = _default_template(
                project, page["panel_target"], used
            )
        used.add(page["template_suggestion"])


def pickable(project: dict) -> list[dict]:
    detail = project.get("detail_panels", False)
    return [m for m in build.pickable_layouts(detail)]


def _used_layouts(prev: dict | None, pages: list[int]) -> set[str]:
    """Layouts already named on pages of the episode that are not being redone.

    The plan stage runs a block at a time, so `prev` holds the pages already
    written; `pages` are the ones being written now. A layout named on a kept
    page is removed from the menu — the episode must not repeat a drawing.
    """
    if not prev:
        return set()
    doing = {int(p) for p in (pages or [])}
    out: set[str] = set()
    for p in prev.get("pages", []):
        # nothing being redone means the whole episode is replanned: the new
        # plan chooses every layout itself, so nothing is held back
        if doing and int(p.get("page", 0)) in doing:
            continue
        tpl = p.get("template_suggestion")
        if isinstance(tpl, str) and tpl:
            out.add(tpl)
    return out


def _split_of(plan: dict, pages: list[int]) -> str:
    """The pages this block works on must all want the same kind of page.

    One block is four pages of one story movement, so the split is the block's.
    If the plan gives mixed splits the stronger (`single`) wins for the menu, and
    each page's own split is still what the validator judges it by.
    """
    wanted = {
        p.get("split") or "even"
        for p in plan.get("pages", [])
        if int(p.get("page", 0)) in set(pages)
    }
    if not wanted:
        return "even"
    if "single" in wanted:
        return "single"
    return wanted.pop()


def _layout_menu(
    project: dict,
    split: str | None = None,
    exclude: set[str] | None = None,
) -> str:
    """Pickable layouts for this page's split, with the facts that decided it.

    The split comes first — an even order, or a page carrying one subject — and
    only layouts whose own shape agrees are offered. Each entry carries what was
    measured: the panel count, whether one panel leads, and how it divides each
    row. `exclude` drops layouts already used elsewhere in the episode, so the
    same drawing does not repeat page after page.
    """
    detail = project.get("detail_panels", False)
    rows = build.pickable_layouts(detail)
    skip = exclude or set()

    def goes(m: dict) -> bool:
        if m["id"] in skip:
            return False
        kind = pageshape.page_type(pageshape.load(m["id"]) or {"panels": []})
        if split == "even":
            return kind == "even"
        if split == "single":
            return kind == "single"
        return True

    kept = [m for m in rows if goes(m)]
    out = []
    for m in kept:
        shapes = pageshape.shapes(pageshape.load(m["id"]) or {"panels": []})
        d = shapes["dominance"]
        split_desc = ", ".join(shapes["row_shapes"])
        leads = d["ratio"] >= 2.0 or d["share"] >= 0.50
        lead = f", 한 컷이 {d['share']:.0%}" if leads else ", 균등"
        out.append(f"{m['id']} (컷 {m['panels']} · {split_desc}{lead})")
    if not out:
        return "(이 split에 맞는 레이아웃이 없습니다)"
    label = "순서·절차 — 균등한 컷을 순서대로" if split == "even" else "강조 — 한 컷이 이끄는 페이지"
    return f"{label} [{len(out)}개]: " + "; ".join(out)


FOCUS_BRIEF = (
    "# Page split: default to a single emphasized beat (rarely a sequence)\n"
    "Most pages are `single`: ONE subject/moment/turn carries the page (a reveal, arrival, reaction, decision, key emotion, impact, place, or character shot). One dominant panel holds that beat; other panels are smaller follow-ups/reactions. This is the DEFAULT for normal story beats, including most conversations (anchor the page on the line/reaction/turn that matters most).\n"
    "\n"
    "Use `even` ONLY for a true sequence/procedure with near-equal weight across panels: an internal thought unfolding step by step, 고민/갈등이 단계적으로 이어지는 장면, 지루한 반복(청소/작업/훈련 등)이나 시간 경과를 순서대로 보여주는 장면, or a mechanical step-by-step process. Do NOT use `even` for ordinary dialogue, reactions, reveals, entrances, confrontations, or any page that has a clear key moment.\n"
    "\n"
    "`split` is `single` or `even`. `focus` names the one subject on a `single` page: `person`, `place`, or `moment`. On an `even` page set `focus` to null (no single dominant subject). If unsure, choose `single` and pick the most important moment/person/place as focus.\n"
    "\n"
    "Read the page's story_job: ask \"what is the ONE thing the reader must feel/understand here?\" If there is a clear answer, it is `single`. Only if the job is genuinely about showing steps/repetition/process in order, make it `even`.\n"
)


def _default_split(story_job: str) -> str:
    """Default to `single` (emphasis). Use `even` only for clear sequence/procedure."""
    job = (story_job or "").lower()
    sequence = any(
        w in job
        for w in (
            "sequence", "step by step", "step-by-step", "process", "procedure",
            "routine", "repeated", "repetition", "repeat", "cleaning", "chores",
            "training montage", "montage", "work through", "working through",
            "time passes", "over time", "gradually", "one by one", "in order",
            "thought process", "inner thoughts", "internal monologue", "deliberat",
            "ponder", "mull", "고민", "생각의 흐름", "반복", "청소", "작업", "순서대로", "절차", "과정", "단계적으로",
        )
    )
    return "even" if sequence else "single"


def _focus_brief(project: dict) -> str:
    """The page's dominant-panel strategy — offered as a strategy, not a rule."""
    focus = project.get("story_focus", "balanced")
    lead = {
        "character": "the protagonist — a beauty / character shot carries the page",
        "narrative": "the story — the decisive, shocking or turning moment carries the page",
        "balanced": "whichever single moment matters most on this page",
    }.get(focus, "whichever single moment matters most on this page")
    return (
        "# Story focus (a strategy to apply, not a rule)\n"
        f"Spend the page's dominant panel on {lead}. **One dominant panel per page.** "
        "A huge focus must stand alone — do not surround it with competing large "
        "panels; if a page wants two focuses, make both medium. Choose a layout whose "
        "largest panel ([big %]) sits where this page's focus belongs. Keep a "
        "beauty-shot panel clean of lettering; narration carries time and place "
        "while the art carries the emotion. Apply this per page as the story asks; "
        "it is a choice, not a fixed rule."
    )


def _ask(stage: Stage, system: str, user: str, caller, json_mode: bool = True) -> Any:
    if caller is not None:
        reply = caller(stage.id, system, user)
    else:
        reply = providers.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            stage=stage.id,
            json_mode=json_mode,
        )
    return providers.parse_json(reply) if json_mode else reply


def _repair_message(base: str, issues: list[dict], feedback: str | None) -> str:
    lines = [base, ""]
    if feedback:
        lines += ["# The user reviewed the last result and asks", feedback.strip(), ""]
    lines.append("# Fix every one of these and return the full corrected JSON")
    for e in validate.errors(issues):
        lines.append(f"- {e['where']}: {e['message']}")
    return "\n".join(lines)


def _ask_until_valid(stage: Stage, system: str, base_user: str, caller, check, feedback):
    """Ask, validate, hand the errors back, repeat. Returns (data, issues)."""
    user = _repair_message(base_user, [], feedback) if feedback else base_user
    data: Any = None
    issues: list[dict] = []
    for _ in range(MAX_REPAIR):
        data = _ask(stage, system, user, caller)
        issues = check(data)
        if not validate.errors(issues):
            return data, issues
        user = _repair_message(base_user, issues, feedback)
    return data, issues


# ============================================================ stage 1 source
def _run_source(root: Path, stage: Stage, ep: str, caller, dry, feedback, pages, ids, cuts, block, episode_pages=None) -> dict:
    eproot = root / "episodes" / ep
    episode = _read_json(eproot / "episode.json")
    gate = eproot / "source" / "APPROVED"
    if gate.is_file() and not feedback:
        return {"note": "source gate already stamped", "files": [], "issues": []}

    road = episode.get("source_origin", "provided")
    novel = eproot / "source" / "novel.txt"
    if road == "provided":
        if not novel.is_file() or not novel.read_text(encoding="utf-8").strip():
            raise StageError("스토리가 없습니다. 위저드 2단계에서 붙여넣으세요.")
        _write_text(gate, f"provided · {_today()}\n")
        return {"note": "pasted story kept verbatim", "files": [_rel(root, novel), _rel(root, gate)], "issues": []}

    brief = _read_text(eproot / "source" / "brief.md")
    if not brief.strip():
        raise StageError("전제/장르/개요가 없습니다. 위저드에서 입력하세요.")

    project = _read_json(root / "project.json")
    system = _system_prompt(stage)
    user = (
        f"# Project\n{_project_brief(project, episode)}\n\n"
        f"# Road\n{road}\n\n"
        f"# Brief\n{brief}\n\n"
        "Write the episode's prose now. Plain prose only: no title line, no JSON, "
        "no commentary. Keep scene breaks. Aim for a length that reads as one episode."
    )
    if feedback:
        user += f"\n\n# The user asks\n{feedback.strip()}"
    if dry:
        return {"dry": True, "system": system, "user": user}

    text = str(_ask(stage, system, user, caller, json_mode=False)).strip()
    if len(text) < 200:
        raise StageError("the authored story is too short to be usable")
    _write_text(novel, text + "\n")
    _write_text(gate, f"{road} · {_today()}\n")
    return {"note": f"authored from {road}", "files": [_rel(root, novel), _rel(root, gate)], "issues": []}


# ============================================================= stage 3 bible
def _merge_pool(existing: dict, incoming: dict, ep: str, replace_ids: set[str] | None) -> tuple[dict, list[str]]:
    pool = {
        "characters": list(existing.get("characters", [])),
        "objects": list(existing.get("objects", [])),
    }
    index = {c["id"]: (bucket, i) for bucket in ("characters", "objects")
             for i, c in enumerate(pool[bucket])}
    changed: list[str] = []
    for bucket in ("characters", "objects"):
        for card in incoming.get(bucket, []):
            cid = str(card.get("id", "")).strip()
            if not SLUG.match(cid):
                raise StageError(f"character id {cid!r} is not a kebab-case slug")
            if replace_ids is not None and cid not in replace_ids:
                continue
            card.setdefault("reference", {"sheet": None, "approved": False})
            if cid in index:
                b, i = index[cid]
                card["first_seen_episode"] = pool[b][i].get("first_seen_episode", ep)
                pool[b][i] = card
                changed.append(cid)
            else:
                card["first_seen_episode"] = ep
                pool[bucket].append(card)
                index[cid] = (bucket, len(pool[bucket]) - 1)
                changed.append(cid)
    return pool, changed


def _bible_check(project: dict, cast_hint: list[str]):
    def check(data: dict) -> list[dict]:
        pool = {"characters": data.get("characters", []), "objects": data.get("objects", [])}
        cast = data.get("cast") or cast_hint
        return validate.validate_bible(pool, cast)
    return check


def _run_bible(root: Path, stage: Stage, ep: str, caller, dry, feedback, pages, ids, cuts, block, episode_pages=None) -> dict:
    project = _read_json(root / "project.json")
    episode = _read_json(root / "episodes" / ep / "episode.json")
    source = _source_text(root, ep)
    existing = _read_json(root / "bible" / "characters.json", {"characters": [], "objects": []})

    replace_ids = set(ids) if ids else None
    scope = (
        f"Rewrite only these characters, keeping their ids: {', '.join(sorted(replace_ids))}. "
        "Return those cards again with the fix; do not resend the others."
        if replace_ids else
        "List every character who speaks or matters in this episode, plus recurring props. "
        "Existing ids keep their card; only add what is new."
    )

    system = _system_prompt(stage)
    base = (
        f"# Project\n{_project_brief(project, episode)}\n\n"
        f"# Existing pool\n{json.dumps(existing, ensure_ascii=False, indent=2)}\n\n"
        f"# Source\n{source}\n\n"
        "# Task\n" + scope + "\nReturn exactly:\n"
        '{"characters": [<card>...], "objects": [<card>...], "cast": ["<id>", ...]}\n'
        "A card is: {id (name slug), name {ko,en,ja}, role {ko,en,ja}, age_phrase, "
        "anchors [2-4 appearance terms], signature (exactly one), body, default_outfit, "
        "descriptor (appearance only, one paragraph, no art style or camera or lighting), "
        "identifier_label, consistency_risk}. `cast` is the ids appearing in THIS episode."
    )
    if dry:
        return {"dry": True, "system": system, "user": base}

    data, issues = _ask_until_valid(
        stage, system, base, caller, _bible_check(project, episode.get("cast", [])), feedback
    )
    if validate.errors(issues):
        raise StageError("the cast still fails validation: " + _first_error(issues))

    pool, changed = _merge_pool(existing, data, ep, replace_ids)
    _write_json(root / "bible" / "characters.json", pool)

    pool_ids = {c["id"] for c in pool["characters"]} | {c["id"] for c in pool["objects"]}
    cast = [c for c in data.get("cast", episode.get("cast", [])) if c in pool_ids]
    episode["cast"] = cast
    _write_json(root / "episodes" / ep / "episode.json", episode)

    _write_text(root / "bible" / "APPROVED", f"episode {ep} · {_today()}\n")
    return {
        "note": f"{len(pool['characters'])} characters · changed {', '.join(changed) or '—'}",
        "files": [_rel(root, root / "bible" / "characters.json"), _rel(root, root / "bible" / "APPROVED")],
        "issues": issues,
    }


# ========================================================= stage 4 refsheets
def _run_refsheets(root: Path, stage: Stage, ep: str, caller, dry, feedback, pages, ids, cuts, block, episode_pages=None) -> dict:
    bible = _read_json(root / "bible" / "characters.json", {"characters": [], "objects": []})
    wizard = _read_json(root / "wizard.json", {})
    branch = (wizard.get("answers") or {}).get("sheet_source", "prompt_only")
    only = set(ids) if ids else None
    files: list[str] = []

    if branch == "prompt_only":
        for card in list(bible.get("characters", [])) + list(bible.get("objects", [])):
            if only is not None and card["id"] not in only:
                continue
            descriptor = str(card.get("descriptor", "")).strip()
            if not descriptor:
                continue
            folder = root / "bible" / "characters" / card["id"]
            sheet = folder / "sheet.prompt.txt"
            if not sheet.is_file() or feedback or only is not None:
                _write_text(sheet, f"{SHEET_FRAMING}\n{descriptor}\n")
                files.append(_rel(root, sheet))
            card.setdefault("reference", {})["sheet"] = "sheet.prompt.txt"
            card["reference"].setdefault("approved", False)
        _write_json(root / "bible" / "characters.json", bible)

    gate = root / "bible" / "SHEETS_APPROVED"
    _write_text(gate, f"{branch} · {_today()}\n")
    files.append(_rel(root, gate))
    return {"note": f"branch: {branch}", "files": files, "issues": []}


# =============================================================== stage 5 plan
def _plan_check(project: dict):
    def check(data: dict) -> list[dict]:
        return validate.validate_plan(data, project)
    return check


def _run_plan(root: Path, stage: Stage, ep: str, caller, dry, feedback, pages, ids, cuts, block, episode_pages=None) -> dict:
    project = _read_json(root / "project.json")
    episode = _read_json(root / "episodes" / ep / "episode.json")
    source = _read_text(root / "episodes" / ep / "source" / "novel.txt")
    lo = project.get("panels", {}).get("min", 3)
    hi = project.get("panels", {}).get("max", 5)

    prev = _read_json(root / "episodes" / ep / "plan" / "page-story-plan.json", None)
    existing_block = ""
    scope = ""
    if prev and pages:
        existing_block = f"\n# Current plan\n{json.dumps(prev, ensure_ascii=False, indent=2)}\n"
        scope = (
            f"Rewrite ONLY pages {sorted(set(pages))}, keeping page_total at "
            f"{prev.get('page_total')}. Return those pages only:\n"
        )

    raw_target = episode_pages if episode_pages is not None else project.get("episode_pages")
    try:
        target_pages = int(raw_target) if raw_target is not None else 12
    except Exception:
        target_pages = 12
    if target_pages < 4:
        target_pages = 4
    target_pages = max(4, min(32, round(target_pages / 4) * 4))

    if prev and pages:
        total_instruction = f"Keep page_total at {prev.get('page_total')} (do not change it)."
    else:
        total_instruction = (
            f"Set page_total to {target_pages} (project setting: episode_pages, a multiple of 4). "
            "Plan the source to fit this page count; adjust pacing/beats so the story fills these pages."
        )

    system = _system_prompt(stage)
    base = (
        f"# Project\n{_project_brief(project, episode)}\n"
        f"{existing_block}\n"
        f"# Source\n{source}\n\n"
        f"# Task\n{total_instruction} Plan in spreads of two pages.\n" + scope +
        f'Return exactly {{"slug": "<slug>", "page_total": <multiple of 4>, '
        '"page_total_basis": "<why this count fits>", "pages": [<page>...]}.\n'
        f"Each page is {{page, block, page_function, story_job, source_span, "
        f"reader_state {{knows, learns, question}}, page_turn_hook, beats [..], "
        f"panel_target, template_suggestion, split, focus}}. "        f"`split`: default `single` (one emphasized moment/subject with a dominant panel + focus person/place/moment); use `even` ONLY for true step-by-step sequence, internal thought process, or repetitive/routine process (cleaning/work/training/time passing) with no single key beat. Most pages must be `single`. "
        f"panel_target must be inside {lo}..{hi}.\n"
        f"{FOCUS_BRIEF}\n"
        f"# Every page gets its own layout\n"
        f"A layout is used once. A layout already named on an earlier page is "
        f"left out of the list below; if the list is short, change the panel "
        f"count first. The same layout never appears on two pages of the "
        f"episode.\n"
        f"# Available layouts (template_suggestion must be one of these ids, and "
        f"its panel count must equal the number of panels on the page)\n"
        f"{_layout_menu(project, exclude=_used_layouts(prev, pages))}\n\n"
        f"{_focus_brief(project)}"
    )
    if dry:
        return {"dry": True, "system": system, "user": base}

    if prev and pages:
        # validate the merged result, not just the returned slice
        def check(data: dict) -> list[dict]:
            merged = {**prev, "pages": _merge_pages(prev.get("pages", []), data.get("pages", []))}
            merged["page_total"] = prev.get("page_total")
            return validate.validate_plan(merged, project)

        data, issues = _ask_until_valid(stage, system, base, caller, check, feedback)
        if validate.errors(issues):
            raise StageError("the plan still fails validation: " + _first_error(issues))
        plan = {**prev, "pages": _merge_pages(prev.get("pages", []), data.get("pages", []))}
        plan.setdefault("slug", prev.get("slug", root.name))
        plan.setdefault("page_total_basis", prev.get("page_total_basis", ""))
    else:
        data, issues = _ask_until_valid(stage, system, base, caller, _plan_check(project), feedback)
        if validate.errors(issues):
            raise StageError("the plan still fails validation: " + _first_error(issues))
        plan = data

    page_total = int(plan["page_total"])
    plan["page_total"] = page_total
    pages_out = sorted(plan.get("pages", []), key=lambda p: int(p.get("page", 0)))
    valid = set(_valid_templates(project))
    for i, page in enumerate(pages_out, start=1):
        page.setdefault("page", i)
        page["block"] = block_of(int(page["page"]))
        target = int(page.get("panel_target", lo))
        page["panel_target"] = min(max(target, lo), hi)
        if page.get("template_suggestion") not in valid:
            page["template_suggestion"] = _default_template(project, page["panel_target"])
        if page.get("split") not in ("even", "single"):
            page["split"] = _default_split(page.get("story_job", ""))
        # the split decides whether a focus exists at all: never both
        if page["split"] == "even":
            page["focus"] = None
        elif page.get("focus") not in ("person", "place", "moment"):
            page["focus"] = "moment"
        page.pop("background_panel", None)
    _unrepeat_layouts(project, pages_out)
    plan["pages"] = pages_out

    plan_path = root / "episodes" / ep / "plan" / "page-story-plan.json"
    _write_json(plan_path, plan)
    episode["page_total"] = page_total
    _write_json(root / "episodes" / ep / "episode.json", episode)
    gate = root / "episodes" / ep / "plan" / "APPROVED"
    _write_text(gate, f"{plan.get('page_total_basis', '')} · {_today()}\n")
    return {
        "note": f"{page_total} pages planned",
        "files": [_rel(root, plan_path), _rel(root, gate)],
        "issues": issues,
    }


def _merge_pages(existing: list[dict], incoming: list[dict]) -> list[dict]:
    by_page = {int(p.get("page", 0)): p for p in existing}
    for p in incoming:
        by_page[int(p.get("page", 0))] = p
    return [by_page[k] for k in sorted(by_page)]


# ============================================================== stage 6 conti
def _conti_check(project: dict):
    def check(data: dict) -> list[dict]:
        contis = data.get("pages") or (data if isinstance(data, list) else [])
        out: list[dict] = []
        for conti in contis:
            out += validate.validate_conti(conti, project)
        if not contis:
            out.append(validate.issue("error", "conti.none", "reply", "no pages in the reply"))
        return out
    return check


def _merge_cuts(existing: dict, incoming: dict, panel_numbers: set[int]) -> dict:
    """Replace only the named panels and their texts; keep everything else."""
    merged = json.loads(json.dumps(existing))
    inc_panels = {p.get("n"): p for p in incoming.get("panels", [])}
    merged["panels"] = [
        inc_panels.get(p.get("n"), p) if p.get("n") in panel_numbers else p
        for p in merged.get("panels", [])
    ]
    keep = [t for t in merged.get("texts", []) if t.get("panel_ref") not in panel_numbers]
    add = [t for t in incoming.get("texts", []) if t.get("panel_ref") in panel_numbers]
    merged["texts"] = keep + add
    for key in ("style", "story_job", "page_turn_hook", "cast_index", "validation"):
        if key in incoming:
            merged[key] = incoming[key]
    return merged


def _menu_exclude(plan: dict, selected: list[int]) -> set[str]:
    """Layouts the rest of the episode already uses — off the menu for this block.

    Only the pages being written now may reuse nothing; pages outside this block
    keep their layout and it is taken out of the list, so the same drawing never
    shows up twice in the episode.
    """
    doing = {int(p) for p in (selected or [])}
    out: set[str] = set()
    for p in plan.get("pages", []):
        if doing and int(p.get("page", 0)) in doing:
            continue
        tpl = p.get("template_suggestion")
        if isinstance(tpl, str) and tpl:
            out.add(tpl)
    return out


def _run_conti_cuts(root, stage, ep, project, episode, plan, cast, cuts, caller, dry, feedback) -> dict:
    by_page: dict[int, set[int]] = {}
    for c in cuts:
        by_page.setdefault(int(c["page"]), set()).add(int(c["n"]))

    existing: dict[int, dict] = {}
    for n in sorted(by_page):
        p = root / "episodes" / ep / "pages" / f"page-{n:03d}.conti.json"
        if not p.is_file():
            raise StageError(f"missing conti for page {n} — run stage 6 first")
        existing[n] = _read_json(p)

    targets = ", ".join(f"page {n} panel {sorted(v)}" for n, v in sorted(by_page.items()))
    tier = project.get("canvas", {}).get("tier", "M")
    width, height = build.tier_size(tier)

    system = _system_prompt(stage)
    base = (
        f"# Project\n{_project_brief(project, episode)}\n\n"
        f"# Canvas: {width} x {height} px — every text bbox stays inside it\n\n"
        f"# Cast cards (use identifiers, never names unless drawn)\n"
        f"{json.dumps(cast, ensure_ascii=False, indent=2)}\n\n"
        f"# Current conti — keep everything else identical\n"
        f"{json.dumps(list(existing.values()), ensure_ascii=False, indent=2)}\n\n"
        f"# Task\nRewrite ONLY these cuts: {targets}. Change the beat, shot, angle, "
        "characters, anchor_of, dialogue and sfx of the named panels, and their text "
        "entries. Return full contis for those pages with every OTHER panel and text "
        "left exactly as given. Return {\"pages\": [<conti>...]}. Exactly one "
        "anchor_of per character per page. Set `split` to match the page: even "
        "for an even progression, single when one panel carries the page. A `bg` "
        "belongs to a panel that establishes the place; the rest carry none."
    )
    if feedback:
        base += f"\n\n# The user asks\n{feedback.strip()}"
    if dry:
        return {"dry": True, "system": system, "user": base}

    def check(data: dict) -> list[dict]:
        contis = data.get("pages") or (data if isinstance(data, list) else [])
        out: list[dict] = []
        seen = 0
        for conti in contis:
            n = int(conti.get("page", 0))
            if n in existing:
                seen += 1
                out += validate.validate_conti(_merge_cuts(existing[n], conti, by_page[n]), project)
        if seen == 0:
            out.append(validate.issue("error", "conti.none", "reply", "no pages in the reply"))
        return out

    data, issues = _ask_until_valid(stage, system, base, caller, check, feedback)
    if validate.errors(issues):
        raise StageError("the cut still fails validation: " + _first_error(issues))

    contis = data.get("pages") or (data if isinstance(data, list) else [])
    files = []
    for conti in contis:
        n = int(conti.get("page", 0))
        if n not in existing:
            continue
        p = root / "episodes" / ep / "pages" / f"page-{n:03d}.conti.json"
        _write_json(p, _merge_cuts(existing[n], conti, by_page[n]))
        files.append(_rel(root, p))
    return {"note": f"cuts rewritten — {targets}", "files": files, "issues": issues}


def _run_conti(root: Path, stage: Stage, ep: str, caller, dry, feedback, pages, ids, cuts, block, episode_pages=None) -> dict:
    project = _read_json(root / "project.json")
    tier = project.get("canvas", {}).get("tier", "M")
    width, height = build.tier_size(tier)
    episode = _read_json(root / "episodes" / ep / "episode.json")
    plan = _read_json(root / "episodes" / ep / "plan" / "page-story-plan.json")
    bible = _read_json(root / "bible" / "characters.json", {"characters": [], "objects": []})
    source = _read_text(root / "episodes" / ep / "source" / "novel.txt")

    cards = {c["id"]: c for c in bible.get("characters", [])}
    cast = [cards[c] for c in episode.get("cast", []) if c in cards]

    if cuts:
        return _run_conti_cuts(root, stage, ep, project, episode, plan, cast, cuts, caller, dry, feedback)

    page_total = int(plan.get("page_total", len(plan.get("pages", []))))
    block = _block_from_pages(pages) if pages else block
    wanted = block_pages(page_total, block)
    selected = [p for p in (pages or wanted) if p in wanted] or wanted
    slice_ = [p for p in plan.get("pages", []) if int(p.get("page", 0)) in set(selected)]
    if not slice_:
        raise StageError(f"no plan pages for {selected}")

    existing = {}
    for n in wanted:
        p = root / "episodes" / ep / "pages" / f"page-{n:03d}.conti.json"
        if p.is_file() and n not in selected:
            existing[n] = _read_json(p)

    system = _system_prompt(stage)
    base = (
        f"# Project\n{_project_brief(project, episode)}\n\n"
        f"# Cast cards (use identifiers, never names unless drawn)\n"
        f"{json.dumps(cast, ensure_ascii=False, indent=2)}\n\n"
        f"# Plan slice (pages {selected[0]}..{selected[-1]})\n"
        f"{json.dumps(slice_, ensure_ascii=False, indent=2)}\n\n"
        + (f"# Pages already built, keep them consistent\n"
           f"{json.dumps(list(existing.values()), ensure_ascii=False, indent=2)}\n\n" if existing else "")
        + f"# Source\n{source}\n\n"
        f"# Task\nWrite one 字コンテ per page for pages {selected}. "
        "Return exactly {\"pages\": [<conti>...]} (only those pages). Each conti is: "
        "{page, spread, split, story_job, page_turn_hook, style, "
        "layout {template_id, size_tier, reading}, cast_index [{label, anchors}], "
        "panels [{n, tier, shot, angle, beat, anchor_of, characters, ref_ids, bg, "
        "eyeline {subject, dir}, transition, dialogue [ids], sfx [ids]}], "
        "texts [{id, kind, panel_ref, speaker, lines {ko:[..], en:[..], ja:[..]}, "
        "bubble, tail, bbox [x1,y1,x2,y2], vertical}], validation {passed, issues}}. "
        f"Every text bbox must sit INSIDE the canvas {width}x{height} px: 0 <= x1 < x2 <= {width} "
        f"and 0 <= y1 < y2 <= {height}. A box that leaves the canvas is clipped by the model. "
        "Set vertical true for a tall narrow box, false for a wide one. "
        "The number of panels must equal the layout's. Exactly one anchor_of per "
        "character per page. Author all three languages in parallel. Carry the page's "
        "`split` and `focus` from the plan. `focus` names the one subject a "
        "single page carries — person, place, or moment — and its panel is the "
        "leading one; an even page has no focus and no leading panel. `bg` "
        "belongs to the panels that establish the place; the rest carry none.\n\n"
        "# Available layouts — layout.template_id must be one of these ids, its panel "
        "count must equal the number of panels on the page, and its page type must "
        "match the page's `split` (even for an equal order, single when one panel "
        "leads)\n"
        f"{_layout_menu(project, _split_of(plan, selected), _menu_exclude(plan, selected))}\n\n"
        f"{_focus_brief(project)}"
    )
    if dry:
        return {"dry": True, "system": system, "user": base}

    data, issues = _ask_until_valid(stage, system, base, caller, _conti_check(project), feedback)
    errors = validate.errors(issues)
    if errors:
        raise StageError("the conti still fails validation: " + _first_error(issues))

    contis = data.get("pages") or (data if isinstance(data, list) else [])
    files = []
    for conti in contis:
        n = int(conti["page"])
        if n not in selected:
            continue
        p = root / "episodes" / ep / "pages" / f"page-{n:03d}.conti.json"
        _write_json(p, conti)
        files.append(_rel(root, p))
    return {"note": f"conti for pages {selected[0]}..{selected[-1]}", "files": files, "issues": issues}


def _block_from_pages(pages: list[int]) -> int:
    return block_of(min(pages))


# ============================================================ stage 7 sheets
def _run_sheets(root: Path, stage: Stage, ep: str, caller, dry, feedback, pages, ids, cuts, block, episode_pages=None) -> dict:
    project = _read_json(root / "project.json")
    bible = _read_json(root / "bible" / "characters.json", {"characters": [], "objects": []})
    plan = _read_json(root / "episodes" / ep / "plan" / "page-story-plan.json")
    page_total = int(plan.get("page_total", len(plan.get("pages", []))))
    block = _block_from_pages(pages) if pages else block
    wanted = list(pages) if pages else block_pages(page_total, block)
    characters = {c["id"]: c for c in bible.get("characters", [])}
    lang = project.get("languages", {}).get("default", "ko")

    pages_dir = root / "episodes" / ep / "pages"
    files: list[str] = []
    issues: list[dict] = []

    for n in wanted:
        conti_path = pages_dir / f"page-{n:03d}.conti.json"
        if not conti_path.is_file():
            raise StageError(f"missing conti for page {n} — run stage 6 (콘티) first")
        conti = _read_json(conti_path)
        issues += validate.validate_conti(conti, project)
        draft = build.build_page(conti, project, characters, lang)
        draft_issues = validate.validate_draft(draft, project)
        issues += [i for i in draft_issues if i["code"] not in ("page.panel-count",)]
        sheet = pages_dir / f"page-{n:03d}.sheet.json"
        if not dry:
            _write_json(sheet, draft)
        files.append(_rel(root, sheet))

    every = []
    for conti_path in sorted(pages_dir.glob("page-*.conti.json")):
        try:
            every.append(_read_json(conti_path))
        except Exception:
            pass
    issues += validate.validate_episode(every, project)

    errs = validate.errors(issues)
    res = {
        "note": f"cut sheets {'(dry run) ' if dry else ''}for pages {wanted[0]}..{wanted[-1]}"
                + ("" if not errs else f" · {len(errs)} error(s)"),
        "warnings": [i["message"] for i in validate.warnings(issues)],
        "files": files,
        "issues": issues,
    }
    if dry:
        res["system"] = "결정적 단계(코드 실행)입니다. AI 프롬프트가 없습니다."
        res["user"] = f"콘티 → 컷 시트 생성\n대상 페이지: {wanted}\n언어 기준: {lang}\n출력: page-NNN.sheet.json"
    return res


# ========================================================== stage 8 artwork
def _pos_hint(bbox: list[float], width: int, height: int) -> str:
    """Where a box sits on the page, in words — context for the artist."""
    x1, y1, x2, y2 = bbox
    cx = ((x1 + x2) / 2) / max(1, width)
    cy = ((y1 + y2) / 2) / max(1, height)
    band = "left" if cx < 0.34 else "right" if cx > 0.66 else "center"
    row = "top" if cy < 0.34 else "bottom" if cy > 0.66 else "middle"
    w, h = x2 - x1, y2 - y1
    aspect = w / h if h else 1
    shape = "wide horizontal" if aspect > 1.3 else "tall vertical" if aspect < 0.77 else "squarish"
    return f"{row}-{band}, {shape}"


_STYLE_FILLER = r"(?:textured|painterly|loose|breathable|expressive|violent|gentle|soft|cool|warm)?\s*"
_STYLE_TAIL = r"(?:\s+(?:bleed|bleeds|wash|washes|stroke|strokes|shading|texture|rendering|lines))?"


def _strip_style_words(text: str) -> str:
    """Remove medium/technique words from a caption.

    Style belongs to the summary; a panel says what it draws. Models keep
    slipping 'textured brushwork' into captions, so the words are removed
    mechanically rather than argued with.
    """
    out = text
    for word in validate.STYLE_WORDS:
        out = re.sub(_STYLE_FILLER + re.escape(word) + _STYLE_TAIL, " ", out, flags=re.IGNORECASE)
    out = re.sub(r"\s*,\s*(?=[,.])", "", out)     # ", ," and ", ."
    out = re.sub(r"\s{2,}", " ", out)
    out = re.sub(r"\s+([.,;:])", r"\1", out)
    out = re.sub(r"\.\s*\.", ".", out)
    return out.strip()


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p.strip()]


def _sanitize_artwork(data: dict, conti: dict, characters: dict | None = None) -> dict:
    """Mechanical fixes the model keeps missing, applied before validation.

    - style words are removed from captions (they belong to the summary)
    - the anchor panel carries the cast descriptor word for word: the card's
      text is placed first and the model's own sentences that merely restate
      it are dropped, so the drawing keeps its pose and framing and gains the
      canonical face
    """
    if not isinstance(data, dict):
        return data
    if isinstance(data.get("summary_caption"), str):
        cap = re.sub(r"\s{2,}", " ", data["summary_caption"]).strip()
        # the summary states the figures' skin tone (Type A) — take it from the
        # card when the drawing's own brief left it out
        if cap and not re.search(r"\b(?:skin|complexion|flesh)\b", cap, re.I):
            for card in (characters or {}).values():
                m = re.search(r"\b([a-z]+)\s+skin\b", card.get("descriptor", ""), re.I)
                if m:
                    # after the style sentence, so it stays inside the brief and
                    # out of the render-tag run that closes the summary
                    parts = _sentences(cap)
                    if parts:
                        parts.insert(1, f"Their skin is {m.group(1).lower()}.")
                        cap = " ".join(parts)
                    else:
                        cap = f"{cap} Their skin is {m.group(1).lower()}."
                    break
        data["summary_caption"] = cap

    anchor_of = {int(p.get("n", 0)): str(p.get("anchor_of"))
                 for p in conti.get("panels", []) if p.get("anchor_of")}
    cards = characters or {}

    for p in data.get("panels", []) or []:
        if not isinstance(p, dict) or not isinstance(p.get("caption"), str):
            continue
        cap = _strip_style_words(p["caption"])
        cid = anchor_of.get(int(p.get("n", 0)))
        if not cid:
            # a non-anchor frame never re-describes: drop the sentences that
            # merely restate a card (it keeps the label and one anchor)
            for card in (characters or {}).values():
                d_tokens = set(re.findall(r"[a-z]+", card.get("descriptor", "").lower()))
                if len(d_tokens) < 6:
                    continue
                keep = [s for s in _sentences(cap)
                        if len(set(re.findall(r"[a-z]+", s.lower())) & d_tokens)
                        / max(1, len(set(re.findall(r"[a-z]+", s.lower())))) < 0.6]
                cap = " ".join(keep).strip() or cap
        card = (cards.get(cid) or {}) if cid else {}
        desc = card.get("descriptor", "")
        if desc:
            desc_tokens = set(re.findall(r"[a-z]+", desc.lower()))
            keep = []
            for s in _sentences(cap):
                toks = set(re.findall(r"[a-z]+", s.lower()))
                overlap = len(toks & desc_tokens) / max(1, len(toks))
                if overlap < 0.6:
                    keep.append(s.strip())
            head = desc.strip()
            # the anti-drift device Type A writes into the drawing
            if card.get("age_phrase") and not re.search(r"neither\b.{0,120}?\bnor\b", cap, re.I):
                low = desc.lower()
                noun = "woman" if "woman" in low else "man" if " man" in low else "figure"
                head += f" Neither a big-headed child nor a mature older {noun}."
            cap = (head + " " + " ".join(keep)).strip()
        p["caption"] = re.sub(r"\s{2,}", " ", cap).strip()

    lines: list[str] = []
    for t in conti.get("texts", []):
        body = t.get("lines") or {}
        for lang in ("ko", "en", "ja"):
            for v in (body.get(lang) or []):
                if str(v).strip():
                    lines.append(str(v).strip())
    for t in data.get("texts", []) or []:
        if isinstance(t, dict) and isinstance(t.get("caption"), str):
            cap = _strip_style_words(t["caption"])
            cap = re.sub(r"\bmultilingual\b\s*", "", cap, flags=re.IGNORECASE)
            for line in lines:               # the caption describes the box; the
                if len(line) < 4:            # words stay in the conti (short glyphs
                    for quoted in (f'"{line}"', f"'{line}'", f"“{line}”"):
                        cap = cap.replace(quoted, " ")
                    continue
                cap = cap.replace(line, " ")
            # a stripped word must not leave a dangling clause behind
            cap = re.sub(r"\s*\b(?:of|at|from|near|beside|on|to)\s+the\s*,", ",", cap)
            cap = re.sub(r"\s*\b(?:of|at|from|near|beside)\s*,", ",", cap)
            t["caption"] = re.sub(r"\s{2,}", " ", re.sub(r"\s+([.,;:])", r"\1", cap)).strip()
    return data


def _artwork_check(conti: dict, characters: dict | None = None):
    def check(data: dict) -> list[dict]:
        return validate.validate_artwork(data, conti, characters)
    return check


def _run_artwork(root: Path, stage: Stage, ep: str, caller, dry, feedback, pages, ids, cuts, block, episode_pages=None) -> dict:
    """The artist: one finished page per model call, captions only (no geometry)."""
    project = _read_json(root / "project.json")
    plan = _read_json(root / "episodes" / ep / "plan" / "page-story-plan.json")
    episode = _read_json(root / "episodes" / ep / "episode.json")
    bible = _read_json(root / "bible" / "characters.json", {"characters": [], "objects": []})
    page_total = int(plan.get("page_total", len(plan.get("pages", []))))
    block = _block_from_pages(pages) if pages else block
    wanted = list(pages) if pages else block_pages(page_total, block)

    cards = {c["id"]: c for c in bible.get("characters", [])}
    objects = {o["id"]: o for o in bible.get("objects", [])}
    cast = [cards[c] for c in episode.get("cast", []) if c in cards]
    art_style = str(project.get("art_style", ""))
    size_w, size_h = build.tier_size(project.get("canvas", {}).get("tier", "M"))

    system = _system_prompt(stage)
    pages_dir = root / "episodes" / ep / "pages"
    files: list[str] = []
    issues: list[dict] = []

    for n in wanted:
        conti_path = pages_dir / f"page-{n:03d}.conti.json"
        sheet_path = pages_dir / f"page-{n:03d}.sheet.json"
        if not conti_path.is_file():
            raise StageError(f"missing conti for page {n} — run stage 6 (콘티) first")
        if not sheet_path.is_file():
            raise StageError(f"missing cut sheet for page {n} — run stage 7 (컷 시트) first")
        conti = _read_json(conti_path)
        sheet = _read_json(sheet_path)

        boxes = []
        drawn_i = 0
        for it in sheet.get("items", []):
            if it.get("label") == "text":
                boxes.append({"kind": "text", "id": it.get("ref_id"), "box": it.get("bbox")})
            else:
                drawn_i += 1
                boxes.append({"kind": "panel", "n": drawn_i, "box": it.get("bbox")})

        box_lines = "\n".join(
            f"- {'panel ' + str(b['n']) if b['kind'] == 'panel' else 'text ' + str(b.get('id'))}: "
            f"{_pos_hint(b['box'], size_w, size_h)}"
            for b in boxes if isinstance(b.get("box"), list)
        )

        text_ids = [t.get("id") for t in conti.get("texts", [])]
        user = (
            f"# Project\n{_project_brief(project, episode)}\n\n"
            f"# Cast cards — describe from these; never write a name\n"
            f"{json.dumps(cast, ensure_ascii=False, indent=2)}\n\n"
            f"# Objects that may be drawn\n"
            f"{json.dumps(list(objects.values()), ensure_ascii=False, indent=2)}\n\n"
            f"# This page's conti (the plan — your notes, not the page)\n"
            f"{json.dumps(conti, ensure_ascii=False, indent=2)}\n\n"
            f"# The page's boxes on a {size_w}x{size_h} canvas, in reading order\n"
            f"{box_lines}\n\n"
            f"# Page style hint\n{conti.get('style', '')}\n"
            f"adapter/art style: {art_style}\n\n"
            f"# Task\nYou are the manga artist. Draw page {n} in words.\n"
            f"Write the whole page again — do not copy the conti's beats.\n"
            f"Return exactly one object:\n"
            "{\"page\": %d, \"summary_caption\": \"...\", "
            "\"panels\": [{\"n\": <panel number>, \"caption\": \"...\"}], "
            "\"texts\": [{\"id\": \"<text id>\", \"caption\": \"...\"}]}\n"
            "Rules: one panels entry per panel (n must be 1..%d), one texts entry for "
            "every text id %s. For a panel decide whether it carries the place or drops "
            "it for the figure — only the panels that establish the place describe a "
            "background. Say where inside the panel each figure stands and how two "
            "people relate, in words. Fold light and texture into the sentence. Use the "
            "cast card's descriptor for the panel that anchors a character and its "
            "identifier_label elsewhere; never write a character's name. No coordinates, "
            "no panel-position prefix like 'Top-left panel:', no instructions to the "
            "model." % (n, drawn_i, json.dumps(text_ids, ensure_ascii=False))
        )
        if feedback:
            user += f"\n\n# The user asks\n{feedback.strip()}"

        if dry:
            return {"dry": True, "system": system, "user": user,
                    "note": f"artwork prompt for page {n}"}

        data, page_issues = _ask_until_valid(stage, system, user, caller,
                                             _artwork_check(conti, cards), feedback)
        # the mechanical fixes run whether or not the model's reply was clean
        data = _sanitize_artwork(data, conti, cards)
        page_issues = validate.validate_artwork(data, conti, cards)
        errs = validate.errors(page_issues)
        issues += page_issues
        if errs:
            raise StageError(f"page {n} artwork still fails validation: " + _first_error(page_issues))
        if isinstance(data, dict):
            # the boxes this page was drawn against; stage 9 compares it
            data.setdefault("geometry", build.panel_geometry_key(sheet))
        art_path = pages_dir / f"page-{n:03d}.art.json"
        _write_json(art_path, data)
        files.append(_rel(root, art_path))

    return {"note": f"artwork for pages {wanted[0]}..{wanted[-1]}", "files": files, "issues": issues}


LANG_NAME = {"ko": "Korean", "en": "English", "ja": "Japanese"}


def _apply_artwork(sheet: dict, art: dict, lang: str = "ko") -> dict:
    """Put the artist's captions onto the sheet's boxes. Boxes never move."""
    out = json.loads(json.dumps(sheet))
    summary = out.setdefault("summary", {})
    if str(art.get("summary_caption", "")).strip():
        # the summary's lettering clause is normalised the same way the text
        # captions are — it must promise exactly the language the page renders
        cap = str(art["summary_caption"]).strip()
        cap = re.sub(
            r"\b(?:Korean|English|Japanese)\b"
            r"(?:\s*(?:,\s*(?:and\s*)?|/\s*|\band\s+)\b(?:Korean|English|Japanese)\b)*",
            LANG_NAME.get(lang, "Korean"),
            cap,
            flags=re.IGNORECASE,
        )
        summary["caption"] = cap

    panels = {int(p.get("n", 0)): str(p.get("caption", "")).strip() for p in art.get("panels", [])}
    texts = {str(t.get("id")): str(t.get("caption", "")).strip() for t in art.get("texts", [])}
    # fallbacks, used only for sheets written before the wiring keys existed:
    # build sorts text boxes by id, and drawn boxes by panel number.
    panel_order = [panels[n] for n in sorted(panels)]
    text_order = [texts[k] for k in sorted(texts)]

    drawn_i = 0
    text_i = 0
    for item in out.get("items", []):
        if item.get("label") == "text":
            cap = texts.get(str(item.get("ref_id")))
            if cap is None:
                cap = text_order[text_i] if text_i < len(text_order) else None
            text_i += 1
        else:
            n = None
            note = str(item.get("note", ""))
            if note.startswith("panel-"):
                try:
                    n = int(note.split("-", 1)[1])
                except ValueError:
                    n = None
            cap = panels.get(n) if n is not None else None
            if cap is None:
                cap = panel_order[drawn_i] if drawn_i < len(panel_order) else None
            drawn_i += 1
        if cap:
            if item.get("label") == "text":
                # the caption names the language the lettering renders in; the
                # artist writes it before the compile language is known, so the
                # whole language run ("Korean, English and Japanese") collapses
                # to this sheet's one language here.
                cap = re.sub(
                    r"\b(?:Korean|English|Japanese)\b"
                    r"(?:\s*(?:,\s*(?:and\s*)?|/\s*|\band\s+)\b(?:Korean|English|Japanese)\b)*",
                    LANG_NAME.get(lang, "Korean"),
                    cap,
                    flags=re.IGNORECASE,
                )
            item["caption"] = cap
    return out


# =========================================================== stage 9 prompts
def _run_prompts(root: Path, stage: Stage, ep: str, caller, dry, feedback, pages, ids, cuts, block, episode_pages=None) -> dict:
    project = _read_json(root / "project.json")
    plan = _read_json(root / "episodes" / ep / "plan" / "page-story-plan.json")
    page_total = int(plan.get("page_total", len(plan.get("pages", []))))
    block = _block_from_pages(pages) if pages else block
    wanted = list(pages) if pages else block_pages(page_total, block)
    style = build.negative_style(project)

    pages_dir = root / "episodes" / ep / "pages"
    prompts_dir = root / "episodes" / ep / "prompts"
    files: list[str] = []
    issues: list[dict] = []

    for n in wanted:
        sheet_path = pages_dir / f"page-{n:03d}.sheet.json"
        art_path = pages_dir / f"page-{n:03d}.art.json"
        if not sheet_path.is_file():
            raise StageError(f"missing cut sheet for page {n} — run stage 7 (컷 시트) first")
        if not art_path.is_file():
            raise StageError(f"missing artwork for page {n} — run stage 8 (만화가) first")
        sheet = _read_json(sheet_path)
        art = _read_json(art_path)
        key = art.get("geometry")
        if key:
            # the drawing is bound to the panel boxes, not to the lettering boxes
            if key != build.panel_geometry_key(sheet):
                raise StageError(
                    f"page {n} panels moved since it was drawn — "
                    "draw the page again (stage 8)"
                )
        elif art_path.stat().st_mtime < sheet_path.stat().st_mtime:
            raise StageError(
                f"artwork for page {n} is older than its panel boxes — "
                "the page was re-boxed, so draw it again (stage 8)"
            )
        lang = project.get("languages", {}).get("default", "ko")
        draft = _apply_artwork(sheet, art, lang)
        draft_issues = validate.validate_draft(draft, project)
        issues += [i for i in draft_issues if i["code"] not in ("page.panel-count",)]
        prompt_text = build.compile_draft(draft)
        prompt_obj = json.loads(prompt_text[prompt_text.index("{"):])
        width, height = draft["width"], draft["height"]
        issues += [i for i in validate.validate_prompt(prompt_obj, width, height, project)
                   if i["code"] not in ("page.panel-count",)]
        if not dry:
            _write_text(prompts_dir / f"page-{n:03d}.prompt.txt", prompt_text + "\n")
            _write_text(prompts_dir / f"page-{n:03d}.negative.txt", build.negative(style) + "\n")
        files += [
            _rel(root, prompts_dir / f"page-{n:03d}.prompt.txt"),
            _rel(root, prompts_dir / f"page-{n:03d}.negative.txt"),
        ]

    errs = validate.errors(issues)
    res = {
        "note": f"prompts {'(dry run) ' if dry else ''}compiled for pages {wanted[0]}..{wanted[-1]}"
                + ("" if not errs else f" · {len(errs)} error(s)"),
        "warnings": [i["message"] for i in validate.warnings(issues)],
        "files": files,
        "issues": issues,
    }
    if dry:
        res["system"] = "결정적 단계(코드 실행)입니다. AI 프롬프트가 없습니다."
        res["user"] = f"만화가 원고 → 프롬프트 컴파일\n대상 페이지: {wanted}\n스타일: {style}\n출력: page-NNN.prompt.txt, page-NNN.negative.txt"
    return res


# ================================================================ comic stages
def _comic_brief_text(root: Path, ep: str) -> str:
    """The comic brief — brief.md, else the wizard's novel.txt (comic saves either)."""
    src = root / "episodes" / ep / "source"
    return _read_text(src / "brief.md") or _read_text(src / "novel.txt")


def _run_comic_brief(root: Path, stage: Stage, ep: str, caller, dry, feedback, pages, ids, cuts, block, episode_pages=None) -> dict:
    """Stage comic-1: accept the moment-sequence brief. No novel, just a brief."""
    eproot = root / "episodes" / ep
    episode = _read_json(eproot / "episode.json")
    gate = eproot / "source" / "APPROVED"
    if gate.is_file() and not feedback:
        return {"note": "source gate already stamped", "files": [], "issues": []}

    brief = eproot / "source" / "brief.md"
    novel = eproot / "source" / "novel.txt"
    road = episode.get("source_origin", "provided")

    if road == "provided":
        text = _read_text(brief).strip() or _read_text(novel).strip()
        if not text:
            raise StageError("브리프가 없습니다. 위저드에서 짧은 이야기를 입력하세요.")
        _write_text(brief, text if text.endswith("\n") else text + "\n")
        _write_text(gate, f"provided · {_today()}\n")
        return {"note": "brief kept verbatim",
                "files": [_rel(root, brief), _rel(root, gate)], "issues": []}

    raw = _read_text(brief).strip() or _read_text(novel).strip()
    if not raw:
        raise StageError("전제/장르/개요가 없습니다. 위저드에서 입력하세요.")
    project = _read_json(root / "project.json")
    system = _system_prompt(stage)
    user = (
        f"# Project\n{_project_brief(project, episode)}\n\n"
        f"# Road\n{road}\n\n"
        f"# Input\n{raw}\n\n"
        f"# Task\nWrite this comic's brief now, exactly as this stage's document "
        "defines. Plain prose only — no title, no JSON, no commentary."
    )
    if feedback:
        user += f"\n\n# The user asks\n{feedback.strip()}"
    if dry:
        return {"dry": True, "system": system, "user": user}

    text = str(_ask(stage, system, user, caller, json_mode=False)).strip()
    if len(text) < 80:
        raise StageError("the authored brief is too short to be usable")
    _write_text(brief, text + "\n")
    _write_text(gate, f"{road} · {_today()}\n")
    return {"note": f"authored from {road}",
            "files": [_rel(root, brief), _rel(root, gate)], "issues": []}


def _comic_plan_check(project: dict):
    def check(data: dict) -> list[dict]:
        return validate.validate_comic_plan(data, project)
    return check


def _run_comic_plan(root: Path, stage: Stage, ep: str, caller, dry, feedback, pages, ids, cuts, block, episode_pages=None) -> dict:
    """Stage comic-5: plan the pages as a sequence of still moments (no cuts)."""
    project = _read_json(root / "project.json")
    episode = _read_json(root / "episodes" / ep / "episode.json")
    brief = _comic_brief_text(root, ep)

    prev = _read_json(root / "episodes" / ep / "plan" / "comic-plan.json", None)
    existing_block = ""
    scope = ""
    if prev and pages:
        existing_block = f"\n# Current plan\n{json.dumps(prev, ensure_ascii=False, indent=2)}\n"
        scope = (
            f"Rewrite ONLY pages {sorted(set(pages))}, keeping page_total at "
            f"{prev.get('page_total')}. Return those pages only:\n"
        )

    raw_target = episode_pages if episode_pages is not None else project.get("episode_pages")
    try:
        target_pages = int(raw_target) if raw_target is not None else 4
    except Exception:
        target_pages = 4
    target_pages = max(4, min(32, round(target_pages / 4) * 4))

    system = _system_prompt(stage)
    base = (
        f"# Project\n{_project_brief(project, episode)}\n"
        f"{existing_block}\n"
        f"# Brief\n{brief}\n\n"
        f"# Task\nPlan this comic as exactly {target_pages} still frames "
        f"(page_total = {target_pages}), exactly as this stage's document defines.\n"
        + scope + "Return the plan object it defines."
    )
    if dry:
        return {"dry": True, "system": system, "user": base}

    if prev and pages:
        def check(data: dict) -> list[dict]:
            merged = {**prev, "pages": _merge_pages(prev.get("pages", []), data.get("pages", []))}
            merged["page_total"] = prev.get("page_total")
            return validate.validate_comic_plan(merged, project)

        data, issues = _ask_until_valid(stage, system, base, caller, check, feedback)
        if validate.errors(issues):
            raise StageError("the comic plan still fails validation: " + _first_error(issues))
        plan = {**prev, "pages": _merge_pages(prev.get("pages", []), data.get("pages", []))}
        plan.setdefault("slug", prev.get("slug", root.name))
        plan.setdefault("moment_basis", prev.get("moment_basis", ""))
    else:
        data, issues = _ask_until_valid(stage, system, base, caller, _comic_plan_check(project), feedback)
        if validate.errors(issues):
            raise StageError("the comic plan still fails validation: " + _first_error(issues))
        plan = data

    page_total = int(plan["page_total"])
    plan["page_total"] = page_total
    pages_out = sorted(plan.get("pages", []), key=lambda p: int(p.get("page", 0)))
    for i, page in enumerate(pages_out, start=1):
        page.setdefault("page", i)
        page["block"] = block_of(int(page["page"]))
    plan["pages"] = pages_out

    plan_path = root / "episodes" / ep / "plan" / "comic-plan.json"
    _write_json(plan_path, plan)
    episode["page_total"] = page_total
    _write_json(root / "episodes" / ep / "episode.json", episode)
    gate = root / "episodes" / ep / "plan" / "APPROVED"
    _write_text(gate, f"{plan.get('moment_basis', '')} · {_today()}\n")
    return {"note": f"{page_total} frames planned",
            "files": [_rel(root, plan_path), _rel(root, gate)], "issues": issues}


def _run_comic_scene(root: Path, stage: Stage, ep: str, caller, dry, feedback, pages, ids, cuts, block, episode_pages=None) -> dict:
    """Stage comic-6: one still frame + lettering per page (no panels)."""
    project = _read_json(root / "project.json")
    tier = project.get("canvas", {}).get("tier", "M")
    width, height = build.tier_size(tier)
    episode = _read_json(root / "episodes" / ep / "episode.json")
    plan = _read_json(root / "episodes" / ep / "plan" / "comic-plan.json")
    bible = _read_json(root / "bible" / "characters.json", {"characters": [], "objects": []})
    brief = _comic_brief_text(root, ep)

    cards = {c["id"]: c for c in bible.get("characters", [])}
    cast = [cards[c] for c in episode.get("cast", []) if c in cards]

    page_total = int(plan.get("page_total", len(plan.get("pages", []))))
    block = _block_from_pages(pages) if pages else block
    wanted = block_pages(page_total, block)
    selected = [p for p in (pages or wanted) if p in wanted] or wanted
    slice_ = [p for p in plan.get("pages", []) if int(p.get("page", 0)) in set(selected)]
    if not slice_:
        raise StageError(f"no comic-plan pages for {selected}")

    system = _system_prompt(stage)
    base = (
        f"# Project\n{_project_brief(project, episode)}\n\n"
        f"# Canvas\n{width} x {height} px\n\n"
        f"# Cast cards\n{json.dumps(cast, ensure_ascii=False, indent=2)}\n\n"
        f"# Plan (pages {selected[0]}..{selected[-1]})\n"
        f"{json.dumps(slice_, ensure_ascii=False, indent=2)}\n\n"
        f"# Brief\n{brief}\n\n"
        f"# Task\nDraw the scene for each of pages {selected} now, exactly as this "
        f"stage's document defines. Return {{\"pages\": [<scene>...]}} for those pages only."
    )
    if feedback:
        base += f"\n\n# The user asks\n{feedback.strip()}"
    if dry:
        return {"dry": True, "system": system, "user": base}

    def check(data: dict) -> list[dict]:
        scenes = data.get("pages") or (data if isinstance(data, list) else [])
        out: list[dict] = []
        if not scenes:
            out.append(validate.issue("error", "comic-scene.none", "reply", "no pages in the reply"))
        for sc in scenes:
            out += validate.validate_comic_scene(sc, project)
        return out

    data, issues = _ask_until_valid(stage, system, base, caller, check, feedback)
    if validate.errors(issues):
        raise StageError("the scene still fails validation: " + _first_error(issues))

    scenes = data.get("pages") or (data if isinstance(data, list) else [])
    files = []
    for sc in scenes:
        n = int(sc.get("page", 0))
        if n not in selected:
            continue
        p = root / "episodes" / ep / "pages" / f"page-{n:03d}.scene.json"
        _write_json(p, sc)
        files.append(_rel(root, p))
    return {"note": f"comic scenes for pages {selected[0]}..{selected[-1]}", "files": files, "issues": issues}


def _run_comic_prompts(root: Path, stage: Stage, ep: str, caller, dry, feedback, pages, ids, cuts, block, episode_pages=None) -> dict:
    """Stage comic-7: compile each still frame into a Type C prompt (deterministic)."""
    project = _read_json(root / "project.json")
    plan = _read_json(root / "episodes" / ep / "plan" / "comic-plan.json")
    bible = _read_json(root / "bible" / "characters.json", {"characters": [], "objects": []})
    page_total = int(plan.get("page_total", len(plan.get("pages", []))))
    block = _block_from_pages(pages) if pages else block
    wanted = list(pages) if pages else block_pages(page_total, block)
    style = build.negative_style(project)
    lang = project.get("languages", {}).get("default", "ko")
    characters = {c["id"]: c for c in bible.get("characters", [])}

    pages_dir = root / "episodes" / ep / "pages"
    prompts_dir = root / "episodes" / ep / "prompts"
    files: list[str] = []
    issues: list[dict] = []
    plan_pages = {int(p.get("page", 0)): p for p in plan.get("pages", [])}

    for n in wanted:
        scene_path = pages_dir / f"page-{n:03d}.scene.json"
        if not scene_path.is_file():
            raise StageError(f"missing comic scene for page {n} — run comic-6 (장면) first")
        scene = _read_json(scene_path)
        issues += validate.validate_comic_scene(scene, project)
        # a page is the next frame of one running moment, not a fresh picture —
        # tell the page what it continues and the single thing that changes
        pp = plan_pages.get(n, {})
        prev = plan_pages.get(n - 1, {})
        bits: list[str] = []
        if page_total > 1:
            bits.append(f"This is frame {n} of {page_total} — one continuous moment in one place, read in order.")
        if prev.get("moment"):
            bits.append(f"It continues directly from the previous frame: {str(prev['moment']).strip().rstrip('.')}.")
        if pp.get("state_in"):
            bits.append(f"It opens in the state carried in: {str(pp['state_in']).strip().rstrip('.')}.")
        if pp.get("change"):
            bits.append(f"The only thing that changes here: {str(pp['change']).strip().rstrip('.')}.")
        continuity = " ".join(bits) or None
        draft = build.compile_single_frame(scene, project, characters, lang, continuity=continuity)
        issues += validate.validate_draft(draft, project)
        prompt_text = build.compile_draft(draft)
        prompt_obj = json.loads(prompt_text[prompt_text.index("{"):])
        width, height = draft["width"], draft["height"]
        issues += validate.validate_prompt(prompt_obj, width, height, project)
        if not dry:
            _write_text(prompts_dir / f"page-{n:03d}.prompt.txt", prompt_text + "\n")
            _write_text(prompts_dir / f"page-{n:03d}.negative.txt", build.negative(style) + "\n")
        files += [
            _rel(root, prompts_dir / f"page-{n:03d}.prompt.txt"),
            _rel(root, prompts_dir / f"page-{n:03d}.negative.txt"),
        ]

    errs = validate.errors(issues)
    res = {
        "note": f"comic prompts {'(dry run) ' if dry else ''}compiled for pages {wanted[0]}..{wanted[-1]}"
                + ("" if not errs else f" · {len(errs)} error(s)"),
        "warnings": [i["message"] for i in validate.warnings(issues)],
        "files": files,
        "issues": issues,
    }
    if dry:
        res["system"] = "결정적 단계(코드 실행)입니다. AI 프롬프트가 없습니다."
        res["user"] = f"장면 → 단일 프레임 프롬프트 컴파일\n대상 페이지: {wanted}\n언어: {lang}\n스타일: {style}\n출력: page-NNN.prompt.txt, page-NNN.negative.txt"
    return res


# ================================================================== dispatch
_RUNNERS = {
    "manga-1-source": _run_source,
    "manga-3-bible": _run_bible,
    "manga-4-refsheets": _run_refsheets,
    "manga-5-plan": _run_plan,
    "manga-6-conti": _run_conti,
    "manga-7-sheets": _run_sheets,
    "manga-8-artwork": _run_artwork,
    "manga-9-prompts": _run_prompts,
    # comic (Type C): a sequence of still frames, no cut splitting
    "comic-1-brief": _run_comic_brief,
    "comic-5-plan": _run_comic_plan,
    "comic-6-scene": _run_comic_scene,
    "comic-7-prompts": _run_comic_prompts,
}


def run(
    slug: str,
    stage_id: str,
    *,
    ep: str | None = None,
    block: int = 1,
    caller: Caller | None = None,
    dry: bool = False,
    feedback: str | None = None,
    pages: list[int] | None = None,
    ids: list[str] | None = None,
    cuts: list[dict] | None = None,
    episode_pages: int | None = None,
) -> dict:
    stage = registry.BY_ID.get(stage_id)
    if stage is None:
        raise StageError(f"unknown stage {stage_id!r}")
    root = _root(slug)

    if stage.scope == "episode" and not ep:
        raise StageError(f"{stage_id} is an episode stage — an episode is required")

    missing = [
        registry.render(req, ep)
        for req in stage.requires
        if not (root / registry.render(req, ep)).exists()
    ]
    if missing:
        raise StageError("run these first: " + ", ".join(missing))

    if stage.mode == "present":
        return {"stage": stage_id, "note": "project.json already holds the settings", "files": [], "issues": []}

    if not dry:
        existing = _stage_files(root, stage, ep)
        if existing:
            history.snapshot(root, existing, stage=stage_id, note=feedback or "", episode=ep)

    runner = _RUNNERS[stage_id]
    result = runner(root, stage, ep, caller, dry, feedback, pages, ids, cuts, block, episode_pages)
    result.setdefault("stage", stage_id)
    result["dry"] = bool(dry)
    return result


# -------------------------------------------------------------- retemplate
def _template_panel_count(template_id: str) -> int | None:
    """Panel count of a layout from either library, or None when unknown."""
    moss = build.moss_layout(template_id)
    if moss is not None:
        return len(moss.get("panels", []))
    tpl = next((t for t in build.library().get("templates", []) if t.get("id") == template_id), None)
    tiers = (tpl or {}).get("tiers") or []
    if not tiers:
        return None
    return max(len(tier.get("panels", [])) for tier in tiers)


def retemplate_plan(slug: str, ep: str, page: int, template_id: str) -> dict:
    """Set a plan page's layout template (stage 5). Validates uniqueness and panel count fit."""
    root = _root(slug)
    project = _read_json(root / "project.json")
    plan_path = root / "episodes" / ep / "plan" / "page-story-plan.json"
    if not plan_path.is_file():
        raise StageError("no page plan yet — run stage 5 first")
    plan = _read_json(plan_path)
    pages = plan.get("pages", [])
    target = next((p for p in pages if int(p.get("page", 0)) == int(page)), None)
    if not target:
        raise StageError(f"page {page} not found in plan")

    # uniqueness in episode
    for p in pages:
        if int(p.get("page", 0)) == int(page):
            continue
        if p.get("template_suggestion") == template_id:
            raise StageError(f"layout {template_id} is already used on page {p.get('page')} — one layout per page per episode")

    # template must exist for this project, and match the page's panel target
    if template_id not in set(_valid_templates(project)):
        raise StageError(f"unknown or unavailable layout {template_id!r} for this project")
    n = _template_panel_count(template_id)
    pt = int(target.get("panel_target", 0) or 0)
    if n and pt and n != pt:
        raise StageError(f"layout {template_id} has {n} panels but page {page} targets {pt} panels")
    split = target.get("split")
    ptype = next(
        (m.get("page_type") for m in build.pickable_layouts(project.get("detail_panels", False))
         if m.get("id") == template_id),
        None,
    )
    if ptype and split and ptype != split:
        raise StageError(
            f"layout {template_id} is a {ptype} page layout but page {page} is a {split} page"
        )

    before = target.get("template_suggestion")
    target["template_suggestion"] = template_id
    plan["pages"] = sorted(pages, key=lambda p: int(p.get("page", 0)))
    issues = validate.validate_plan(plan, project)
    if validate.errors(issues):
        target["template_suggestion"] = before
        raise StageError("plan validation failed after template change: " + _first_error(issues))

    history.snapshot(root, [_rel(root, plan_path)], stage="manga-5-plan",
                     note=f"template page {page} -> {template_id}", episode=ep)
    _write_json(plan_path, plan)
    return {"ok": True, "page": page, "template_id": template_id, "issues": issues}


def retemplate(slug: str, ep: str, page: int, layout: dict) -> dict:
    """Swap a page's layout template, re-validate, and rebuild that page.

    The conti is the source of truth, so the change is made there first; the
    build then re-derives the boxes from the new template. A template with the
    wrong panel count is refused — the conti and the template must agree. So is
    a template another page of the episode already uses.
    """
    root = _root(slug)
    project = _read_json(root / "project.json")
    path = root / "episodes" / ep / "pages" / f"page-{page:03d}.conti.json"
    if not path.is_file():
        raise StageError(f"no conti for page {page}")

    new_id = layout.get("template_id")
    if new_id:
        pages_dir = root / "episodes" / ep / "pages"
        for other in sorted(pages_dir.glob("page-*.conti.json")):
            n = int(other.stem.split("-")[1].split(".")[0])
            if n == page:
                continue
            try:
                c = _read_json(other)
            except Exception:
                continue
            if (c.get("layout") or {}).get("template_id") == new_id:
                raise StageError(
                    f"layout {new_id} is already on page {n} — "
                    "a layout is used on one page of the episode only"
                )

    conti = _read_json(path)
    history.snapshot(root, [_rel(root, path)], stage="manga-6-conti",
                     note=f"retemplate page {page}", episode=ep)
    conti.setdefault("layout", {}).update(layout)

    # a template has its own tier sizes, so re-seat the panels into it in
    # reading order — otherwise two panels can land on the same box
    tpl = next((t for t in build.library()["templates"]
                if t["id"] == conti["layout"].get("template_id")), None)
    if tpl:
        index = 0
        for tier_index, tier in enumerate(tpl["tiers"]):
            for _ in range(len(tier["panels"])):
                if index < len(conti.get("panels", [])):
                    conti["panels"][index]["tier"] = tier_index
                    index += 1

    issues = validate.validate_conti(conti, project)
    if validate.errors(issues):
        raise StageError("that template does not fit this page: " + _first_error(issues))

    _write_json(path, conti)
    # boxes are deterministic, so rebuild them here. The artist's captions were
    # written for the old boxes, so they are left alone and go stale — the prompt
    # stage refuses until the page is drawn again (a model call the user starts).
    sheet_result = run(slug, "manga-7-sheets", ep=ep, pages=[page])
    return {
        "conti": {"stage": "manga-6-conti", "note": f"page {page} · template {conti['layout'].get('template_id')}",
                  "files": [_rel(root, path)], "issues": issues},
        "sheet": sheet_result,
        "needs_redraw": True,
    }


# -------------------------------------------------------------- orchestrate
def _blocks_of(root: Path, ep: str) -> int:
    plan = _read_json(root / "episodes" / ep / "plan" / "page-story-plan.json", None)
    if not plan:
        return 0
    total = int(plan.get("page_total", len(plan.get("pages", []))))
    return max(1, (total + 3) // 4)


def _block_done(root: Path, ep: str, stage_id: str, block: int, page_total: int) -> bool:
    pages = block_pages(page_total, block)
    if stage_id == "manga-6-conti":
        return all((root / "episodes" / ep / "pages" / f"page-{n:03d}.conti.json").is_file() for n in pages)
    if stage_id == "manga-7-sheets":
        return all((root / "episodes" / ep / "pages" / f"page-{n:03d}.sheet.json").is_file() for n in pages)
    if stage_id == "manga-8-artwork":
        return all((root / "episodes" / ep / "pages" / f"page-{n:03d}.art.json").is_file() for n in pages)
    if stage_id == "manga-9-prompts":
        return all((root / "episodes" / ep / "prompts" / f"page-{n:03d}.prompt.txt").is_file() for n in pages)
    if stage_id == "comic-6-scene":
        return all((root / "episodes" / ep / "pages" / f"page-{n:03d}.scene.json").is_file() for n in pages)
    if stage_id == "comic-7-prompts":
        return all((root / "episodes" / ep / "prompts" / f"page-{n:03d}.prompt.txt").is_file() for n in pages)
    return False


def orchestrate(
    slug: str,
    episode: str | None = None,
    *,
    caller: Caller | None = None,
    from_n: int = 1,
    to_n: int = 9,
) -> dict:
    """Run the table in order for one episode, stopping where a human must decide.

    Stages whose gate exists are skipped; the block stages build only the blocks
    that are not done. A failure stops the run and says where, so nothing is
    silently skipped.
    """
    root = _root(slug)
    project = _read_json(root / "project.json")
    log: list[dict] = []

    if not episode:
        eps = project.get("episodes", [])
        episode = eps[-1] if eps else None
    if not episode:
        raise StageError("no episode to run — add one in the wizard")

    mode = project.get("mode", "manga")
    for stage in registry.STAGES_BY_MODE.get(mode, registry.MANGA_STAGES):
        if not (from_n <= stage.n <= to_n):
            continue

        statuses = registry.status_for(root, project, episode, None)
        row = next((r for r in statuses if r.id == stage.id), None)
        if row is None or row.state == "unavailable":
            log.append({"stage": stage.id, "n": stage.n, "status": "skipped",
                        "note": row.reason if row else ""})
            continue
        if row.state == "blocked":
            log.append({"stage": stage.id, "n": stage.n, "status": "blocked", "note": row.reason})
            return {"ok": False, "stopped_at": stage.id, "episode": episode, "log": log}

        if stage.per_block:
            nblocks = _blocks_of(root, episode)
            if nblocks == 0:
                log.append({"stage": stage.id, "n": stage.n, "status": "blocked",
                            "note": "no page plan yet"})
                return {"ok": False, "stopped_at": stage.id, "episode": episode, "log": log}
            plan = _read_json(root / "episodes" / episode / "plan" / "page-story-plan.json", {})
            page_total = int(plan.get("page_total", nblocks * 4))
            ran = 0
            for b in range(1, nblocks + 1):
                if _block_done(root, episode, stage.id, b, page_total):
                    log.append({"stage": stage.id, "n": stage.n, "block": b, "status": "done-skip"})
                    continue
                try:
                    res = run(slug, stage.id, ep=episode, block=b, caller=caller)
                except StageError as e:
                    log.append({"stage": stage.id, "n": stage.n, "block": b,
                                "status": "error", "note": str(e)})
                    return {"ok": False, "stopped_at": f"{stage.id} block {b}",
                            "episode": episode, "log": log}
                ran += 1
                log.append({"stage": stage.id, "n": stage.n, "block": b, "status": "ok",
                            "note": res.get("note"),
                            "errors": len(validate.errors(res.get("issues", [])))})
            if ran == 0:
                log.append({"stage": stage.id, "n": stage.n, "status": "done-skip"})
            continue

        if row.state == "done":
            log.append({"stage": stage.id, "n": stage.n, "status": "done-skip"})
            continue

        try:
            res = run(slug, stage.id, ep=episode, caller=caller)
        except StageError as e:
            log.append({"stage": stage.id, "n": stage.n, "status": "error", "note": str(e)})
            return {"ok": False, "stopped_at": stage.id, "episode": episode, "log": log}
        log.append({"stage": stage.id, "n": stage.n, "status": "ok", "note": res.get("note"),
                    "errors": len(validate.errors(res.get("issues", [])))})

    return {"ok": True, "episode": episode, "log": log}


# --------------------------------------------------------------------- review
def review(slug: str, stage_id: str, *, ep: str | None = None, block: int = 1) -> dict:
    """What a stage produced, and whether it still validates — without running."""
    stage = registry.BY_ID.get(stage_id)
    if stage is None:
        raise StageError(f"unknown stage {stage_id!r}")
    root = _root(slug)
    project = _read_json(root / "project.json")

    files: list[str] = []
    if stage.per_block and ep:
        # scope review files/updated_at to the current 4-page block
        plan = _read_json(root / "episodes" / ep / "plan" / "page-story-plan.json", {"page_total": 0})
        page_total = int(plan.get("page_total", 0))
        wanted = block_pages(page_total, block)
        if stage_id == "manga-6-conti":
            for n in wanted:
                p = root / "episodes" / ep / "pages" / f"page-{n:03d}.conti.json"
                if p.is_file():
                    files.append(_rel(root, p))
        elif stage_id == "manga-7-sheets":
            for n in wanted:
                p = root / "episodes" / ep / "pages" / f"page-{n:03d}.sheet.json"
                if p.is_file():
                    files.append(_rel(root, p))
        elif stage_id == "manga-8-artwork":
            for n in wanted:
                p = root / "episodes" / ep / "pages" / f"page-{n:03d}.art.json"
                if p.is_file():
                    files.append(_rel(root, p))
        elif stage_id == "manga-9-prompts":
            for n in wanted:
                for p in sorted((root / "episodes" / ep / "prompts").glob(f"page-{n:03d}*.prompt.txt")) if (root / "episodes" / ep / "prompts").is_dir() else []:
                    files.append(_rel(root, p))
                neg = root / "episodes" / ep / "prompts" / f"page-{n:03d}.negative.txt"
                if neg.is_file():
                    files.append(_rel(root, neg))
        else:
            for pattern in stage.produces:
                for path in registry.matches(root, registry.render(pattern, ep, block)):
                    files.append(_rel(root, path))
    else:
        for pattern in stage.produces:
            for path in registry.matches(root, registry.render(pattern, ep)):
                files.append(_rel(root, path))

    issues: list[dict] = []
    summary: dict[str, Any] = {}

    if stage_id == "manga-1-source" and ep:
        episode = _read_json(root / "episodes" / ep / "episode.json", {})
        novel = root / "episodes" / ep / "source" / "novel.txt"
        brief = root / "episodes" / ep / "source" / "brief.md"
        summary["road"] = episode.get("source_origin")
        summary["approved"] = (root / "episodes" / ep / "source" / "APPROVED").is_file()
        summary["chars"] = len(_read_text(novel)) if novel.is_file() else len(_read_text(brief))
        summary["excerpt"] = _read_text(novel)[:600] if novel.is_file() else _read_text(brief)[:600]
    elif stage_id == "manga-4-refsheets":
        pool = _read_json(root / "bible" / "characters.json", {"characters": [], "objects": []})
        summary["cast"] = [
            {"id": c["id"], "identifier_label": c.get("identifier_label"),
             "sheet": (c.get("reference") or {}).get("sheet"),
             "approved": (c.get("reference") or {}).get("approved")}
            for c in pool.get("characters", [])
        ]
    elif stage_id == "manga-3-bible":
        pool = _read_json(root / "bible" / "characters.json", {"characters": [], "objects": []})
        episode = _read_json(root / "episodes" / ep / "episode.json", {}) if ep else {}
        issues = validate.validate_bible(pool, episode.get("cast"))
        summary["cast"] = [
            {"id": c["id"], "name": c.get("name"), "identifier_label": c.get("identifier_label"),
             "descriptor": c.get("descriptor"), "anchors": c.get("anchors"),
             "reference": c.get("reference")}
            for c in pool.get("characters", [])
        ]
    elif stage_id == "manga-5-plan" and ep:
        plan = _read_json(root / "episodes" / ep / "plan" / "page-story-plan.json", None)
        if plan:
            issues = validate.validate_plan(plan, project)
            summary["page_total"] = plan.get("page_total")
            summary["pages"] = [
                {"page": p.get("page"), "page_function": p.get("page_function"),
                 "story_job": p.get("story_job"), "panel_target": p.get("panel_target"),
                 "template_suggestion": p.get("template_suggestion"),
                 "split": p.get("split"), "focus": p.get("focus")}
                for p in plan.get("pages", [])
            ]
    elif stage_id == "manga-6-conti" and ep:
        plan = _read_json(root / "episodes" / ep / "plan" / "page-story-plan.json", {"page_total": 0})
        page_total = int(plan.get("page_total", 0))
        contis = []
        for n in block_pages(page_total, block):
            p = root / "episodes" / ep / "pages" / f"page-{n:03d}.conti.json"
            if not p.is_file():
                continue
            conti = _read_json(p)
            issues += validate.validate_conti(conti, project)
            layout = conti.get("layout") or {}
            contis.append({"page": n, "panels": len(conti.get("panels", [])),
                           "texts": len(conti.get("texts", [])),
                           "template_suggestion": layout.get("template_id"),
                           "split": conti.get("split"),
                           "story_job": conti.get("story_job"),
                           "conti": conti})
        summary["pages"] = contis
    elif stage_id == "manga-7-sheets" and ep:
        plan = _read_json(root / "episodes" / ep / "plan" / "page-story-plan.json", {"page_total": 0})
        page_total = int(plan.get("page_total", 0))
        pages = []
        for n in block_pages(page_total, block):
            sheet = root / "episodes" / ep / "pages" / f"page-{n:03d}.sheet.json"
            if not sheet.is_file():
                continue
            draft = _read_json(sheet)
            issues += validate.validate_draft(draft, project)
            conti_path = root / "episodes" / ep / "pages" / f"page-{n:03d}.conti.json"
            conti = _read_json(conti_path, {}) if conti_path.is_file() else {}
            layout = conti.get("layout") or {}
            pages.append({"page": n, "panels": sum(1 for it in draft.get("items", []) if it.get("label") != "text"),
                          "texts": sum(1 for it in draft.get("items", []) if it.get("label") == "text"),
                          "width": draft.get("width"), "height": draft.get("height"),
                          "template_suggestion": layout.get("template_id"),
                          "split": conti.get("split")})
        summary["pages"] = pages
    elif stage_id == "manga-8-artwork" and ep:
        plan = _read_json(root / "episodes" / ep / "plan" / "page-story-plan.json", {"page_total": 0})
        page_total = int(plan.get("page_total", 0))
        pages = []
        for n in block_pages(page_total, block):
            art_path = root / "episodes" / ep / "pages" / f"page-{n:03d}.art.json"
            if not art_path.is_file():
                continue
            art = _read_json(art_path)
            conti_path = root / "episodes" / ep / "pages" / f"page-{n:03d}.conti.json"
            conti = _read_json(conti_path, {}) if conti_path.is_file() else {}
            if conti:
                pool = _read_json(root / "bible" / "characters.json", {"characters": [], "objects": []})
                cards = {c["id"]: c for c in pool.get("characters", [])} | {
                    o["id"]: o for o in pool.get("objects", [])
                }
                issues += validate.validate_artwork(art, conti, cards)
            layout = conti.get("layout") or {}
            pages.append({
                "page": n,
                "panels": len(art.get("panels", [])),
                "texts": len(art.get("texts", [])),
                "summary_caption": art.get("summary_caption"),
                "panel_captions": art.get("panels", []),
                "text_captions": art.get("texts", []),
                "template_suggestion": layout.get("template_id"),
                "split": conti.get("split"),
            })
        summary["pages"] = pages
    elif stage_id == "manga-9-prompts" and ep:
        plan = _read_json(root / "episodes" / ep / "plan" / "page-story-plan.json", {"page_total": 0})
        page_total = int(plan.get("page_total", 0))
        pages = []
        for n in block_pages(page_total, block):
            prompt_path = root / "episodes" / ep / "prompts" / f"page-{n:03d}.prompt.txt"
            sheet_path = root / "episodes" / ep / "pages" / f"page-{n:03d}.sheet.json"
            if not prompt_path.is_file():
                continue
            draft = _read_json(sheet_path, {}) if sheet_path.is_file() else {}
            conti_path = root / "episodes" / ep / "pages" / f"page-{n:03d}.conti.json"
            conti = _read_json(conti_path, {}) if conti_path.is_file() else {}
            layout = conti.get("layout") or {}
            row = {"page": n,
                   "panels": sum(1 for it in draft.get("items", []) if it.get("label") != "text") if draft else None,
                   "texts": sum(1 for it in draft.get("items", []) if it.get("label") == "text") if draft else None,
                   "width": draft.get("width"), "height": draft.get("height"),
                   "template_suggestion": layout.get("template_id"),
                   "split": conti.get("split")}
            pages.append(row)
        summary["pages"] = pages
    elif stage_id == "comic-1-brief" and ep:
        episode = _read_json(root / "episodes" / ep / "episode.json", {})
        brief = root / "episodes" / ep / "source" / "brief.md"
        summary["road"] = episode.get("source_origin")
        summary["approved"] = (root / "episodes" / ep / "source" / "APPROVED").is_file()
        summary["chars"] = len(_read_text(brief))
        summary["excerpt"] = _read_text(brief)[:600]
    elif stage_id == "comic-5-plan" and ep:
        plan = _read_json(root / "episodes" / ep / "plan" / "comic-plan.json", None)
        if plan:
            issues = validate.validate_comic_plan(plan, project)
            summary["page_total"] = plan.get("page_total")
            summary["pages"] = plan.get("pages", [])
    elif stage_id in ("comic-6-scene", "comic-7-prompts") and ep:
        plan = _read_json(root / "episodes" / ep / "plan" / "comic-plan.json", {"page_total": 0})
        page_total = int(plan.get("page_total", 0))
        rows = []
        for n in block_pages(page_total, block):
            scene_path = root / "episodes" / ep / "pages" / f"page-{n:03d}.scene.json"
            if stage_id == "comic-7-prompts" and not (root / "episodes" / ep / "prompts" / f"page-{n:03d}.prompt.txt").is_file():
                continue
            if not scene_path.is_file():
                continue
            scene = _read_json(scene_path)
            if stage_id == "comic-6-scene":
                issues += validate.validate_comic_scene(scene, project)
            rows.append({"page": n, "texts": len(scene.get("texts", [])), "scene": scene})
        summary["pages"] = rows

    updated_at = None
    if files:
        try:
            mtimes = []
            for f in files:
                fp = root / f
                if fp.is_file():
                    mtimes.append(fp.stat().st_mtime)
            if mtimes:
                from datetime import datetime
                updated_at = datetime.fromtimestamp(max(mtimes)).isoformat(timespec="seconds")
        except Exception:
            updated_at = None

    stale: list[int] = []
    if ep and stage.per_block:
        try:
            stale = registry.stale_pages(root, ep, stage_id, block)
        except Exception:
            stale = []
    return {
        "stage": stage_id,
        "exists": bool(files),
        "files": files,
        "issues": issues,
        "error_count": len(validate.errors(issues)),
        "warning_count": len(validate.warnings(issues)),
        "summary": summary,
        "history": history.list_snapshots(root, stage_id)[:20],
        "updated_at": updated_at,
        "stale": bool(stale),
        "stale_pages": stale,
        "stale_reason": (
            f"이전 단계가 변경됨 — 아래 결과는 낡았습니다 "
            f"({', '.join(str(p) for p in stale)}p). 다시 실행하세요."
            if stale else None
        ),
    }


# --------------------------------------------------------------------- misc
def _first_error(issues: list[dict]) -> str:
    e = validate.errors(issues)
    return f"{e[0]['where']}: {e[0]['message']}" if e else "unknown"


def _today() -> str:
    from datetime import date

    return date.today().isoformat()


def status(slug: str, ep: str | None = None) -> list[dict]:
    root = _root(slug)
    project = _read_json(root / "project.json")
    episode = _read_json(root / "episodes" / ep / "episode.json", {}) if ep else None
    return [s.__dict__ for s in registry.status_for(root, project, ep, episode)]
