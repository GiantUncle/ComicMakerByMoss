"""The stage table — one row per skill, and how to tell whether it is done.

This mirrors `manga-craft/pipeline.md` §1 exactly. A stage owns one artifact and
one gate; nothing outside its row is its business.
"""

from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]


@dataclass(frozen=True)
class Stage:
    id: str                    # the skill name, e.g. "manga-3-bible"
    n: int                     # pipeline number, 1..9
    scope: str                 # project | episode
    mode: str                  # model | deterministic | present
    produces: tuple[str, ...]  # glob patterns, relative to the project root
    gate: str | None           # the gate file, or None for a gate-less stage
    requires: tuple[str, ...] = ()   # gate files that must already exist
    craft: tuple[str, ...] = ()      # craft docs to attach to the model prompt
    per_block: bool = False          # runs once per 4-page block
    modes: tuple[str, ...] = ("manga",)   # which output modes the stage belongs to


# ------------------------------------------------------- shared (manga + comic)
# A project setting, a cast pool and a reference sheet are mode-independent, so
# these three stages are literally the same skill and artifact in both modes.
_STAGE_PROJECT = Stage(
    id="manga-2-project", n=2, scope="project", mode="present",
    produces=("project.json",), gate=None, modes=("manga", "comic"),
)
_STAGE_BIBLE = Stage(
    id="manga-3-bible", n=3, scope="project", mode="model",
    produces=("bible/characters.json",), gate="bible/APPROVED",
    requires=("episodes/{ep}/source/APPROVED",),
    craft=("character-consistency.md",), modes=("manga", "comic"),
)
_STAGE_SHEETS = Stage(
    id="manga-4-refsheets", n=4, scope="project", mode="deterministic",
    produces=("bible/characters/*/sheet.prompt.txt",), gate="bible/SHEETS_APPROVED",
    requires=("bible/APPROVED",), modes=("manga", "comic"),
)

# --------------------------------------------------------------- manga (Type A)
# Multi-panel manuscript pages. Stages 5/7/8/9 are the cut-splitting machinery.
MANGA_STAGES: tuple[Stage, ...] = (
    Stage(
        id="manga-1-source", n=1, scope="episode", mode="model",
        produces=("episodes/{ep}/episode.json", "episodes/{ep}/source/novel.txt"),
        gate="episodes/{ep}/source/APPROVED",
    ),
    _STAGE_PROJECT,
    _STAGE_BIBLE,
    _STAGE_SHEETS,
    Stage(
        id="manga-5-plan", n=5, scope="episode", mode="model",
        produces=("episodes/{ep}/plan/page-story-plan.json",),
        gate="episodes/{ep}/plan/APPROVED",
        requires=("episodes/{ep}/source/APPROVED", "bible/APPROVED"),
        craft=("comic-planning.md",),
    ),
    Stage(
        id="manga-6-conti", n=6, scope="episode", mode="model", per_block=True,
        produces=("episodes/{ep}/pages/page-{block}*.conti.json",),
        gate=None,
        requires=("episodes/{ep}/plan/APPROVED", "bible/APPROVED"),
        craft=("comic-planning.md", "character-consistency.md"),
    ),
    Stage(
        id="manga-7-sheets", n=7, scope="episode", mode="deterministic", per_block=True,
        produces=("episodes/{ep}/pages/page-{block}*.sheet.json",),
        gate=None,
        requires=("episodes/{ep}/plan/APPROVED",),
    ),
    Stage(
        id="manga-8-artwork", n=8, scope="episode", mode="model", per_block=True,
        produces=("episodes/{ep}/pages/page-{block}*.art.json",),
        gate=None,
        # the sheet is checked at run time (it is per page, not a gate file)
        requires=("episodes/{ep}/plan/APPROVED", "bible/APPROVED"),
        craft=(
            "comic-planning.md",
            "character-consistency.md",
            "authoring-spec.md",
            "verified-examples.md",
        ),
    ),
    Stage(
        id="manga-9-prompts", n=9, scope="episode", mode="deterministic", per_block=True,
        produces=("episodes/{ep}/prompts/page-{block}*.prompt.txt",),
        gate=None,
        requires=("episodes/{ep}/plan/APPROVED",),
    ),
)

# --------------------------------------------------------------- comic (Type C)
# A sequence of pages, each a single still frame with dialogue. There is no cut
# splitting: no plan-layout, no cut sheet, no panel artwork, no multi-panel
# compile. So comic shares only the project/cast/sheets steps with manga.
_COMIC_BRIEF = Stage(
    id="comic-1-brief", n=1, scope="episode", mode="model",
    produces=("episodes/{ep}/episode.json", "episodes/{ep}/source/brief.md"),
    gate="episodes/{ep}/source/APPROVED", modes=("comic",),
)
_COMIC_PLAN = Stage(
    id="comic-5-plan", n=5, scope="episode", mode="model",
    produces=("episodes/{ep}/plan/comic-plan.json",),
    gate="episodes/{ep}/plan/APPROVED",
    requires=("episodes/{ep}/source/APPROVED", "bible/APPROVED"),
    craft=("twitter-comic.md",), modes=("comic",),
)
_COMIC_SCENE = Stage(
    id="comic-6-scene", n=6, scope="episode", mode="model", per_block=True,
    produces=("episodes/{ep}/pages/page-{block}*.scene.json",),
    gate=None,
    requires=("episodes/{ep}/plan/APPROVED", "bible/APPROVED"),
    craft=("twitter-comic.md", "character-consistency.md", "authoring-spec.md"),
    modes=("comic",),
)
_COMIC_PROMPTS = Stage(
    id="comic-7-prompts", n=7, scope="episode", mode="deterministic", per_block=True,
    produces=("episodes/{ep}/prompts/page-{block}*.prompt.txt",),
    gate=None,
    requires=("episodes/{ep}/plan/APPROVED",), modes=("comic",),
)

COMIC_STAGES: tuple[Stage, ...] = (
    _COMIC_BRIEF,
    _STAGE_PROJECT,
    _STAGE_BIBLE,
    _STAGE_SHEETS,
    _COMIC_PLAN,
    _COMIC_SCENE,
    _COMIC_PROMPTS,
)

STAGES_BY_MODE: dict[str, tuple[Stage, ...]] = {
    "manga": MANGA_STAGES,
    "comic": COMIC_STAGES,
}

# Every stage, for id lookup (STAGES_BY_MODE is what a mode actually runs).
STAGES: tuple[Stage, ...] = MANGA_STAGES + (_COMIC_BRIEF, _COMIC_PLAN, _COMIC_SCENE, _COMIC_PROMPTS)
BY_ID = {s.id: s for s in STAGES}
BY_N = {s.n: s for s in MANGA_STAGES}


def render(pattern: str, ep: str | None, block: int | None = None) -> str:
    out = pattern.replace("{ep}", ep or "")
    if block is None:
        out = out.replace("page-{block}*", "page-*")
    else:
        # block 1 -> pages 001-004, block 2 -> 005-008
        first = (block - 1) * 4 + 1
        last = first + 3
        out = out.replace("page-{block}*", f"page-{first:03d}")  # one representative
        # a representative match is enough for "done" detection below
        _ = last
    return out


def _glob_matches(root: Path, pattern: str) -> list[Path]:
    """Match a pattern that may contain '*' across path segments, from the root."""
    if "*" not in pattern:
        p = root / pattern
        return [p] if p.exists() else []
    # fnmatch on the posix relative path
    out = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if fnmatch.fnmatch(rel, pattern):
            out.append(p)
    return out


def matches(root: Path, pattern: str) -> list[Path]:
    return _glob_matches(root, pattern)


def is_done(root: Path, stage: Stage, ep: str | None) -> bool:
    if stage.gate:
        return (root / render(stage.gate, ep)).exists()
    for pattern in stage.produces:
        if not _glob_matches(root, render(pattern, ep)):
            return False
    return True


def _mtime(p: Path) -> float | None:
    try:
        return p.stat().st_mtime if p.is_file() else None
    except OSError:
        return None


def _page_no(p: Path) -> int | None:
    """page-007.sheet.json -> 7."""
    try:
        return int(p.name.split("-")[1].split(".")[0])
    except (IndexError, ValueError):
        return None


def _episode_page_files(root: Path, ep: str, kind: str) -> dict[int, Path]:
    """Map page -> file for one kind (conti|sheet|art|prompt) of an episode."""
    if kind == "prompt":
        d = root / "episodes" / ep / "prompts"
        if not d.is_dir():
            return {}
        return {n: p for p in d.glob("page-*.prompt.txt")
                if (n := _page_no(p)) is not None}
    d = root / "episodes" / ep / "pages"
    if not d.is_dir():
        return {}
    ext = {"conti": "conti.json", "sheet": "sheet.json", "art": "art.json",
           "scene": "scene.json"}[kind]
    return {n: p for p in d.glob(f"page-*.{ext}")
            if (n := _page_no(p)) is not None}


def stale_pages(root: Path, ep: str, stage_id: str, block: int | None = None) -> list[int]:
    """Pages whose output is older than an upstream artifact.

    Chains (conservative — any upstream newer marks the page stale):
      manga-6-conti    : plan        > conti
      manga-7-sheets   : plan|conti  > sheet
      manga-8-artwork  : plan|conti|sheet > art
      manga-9-prompts  : plan|conti|sheet|art > prompt
    Empty when the stage has no such dependency or the page has no output yet.
    """
    if stage_id in ("comic-6-scene", "comic-7-prompts"):
        # comic chain: comic-plan > scene > prompt
        plan_m = _mtime(root / "episodes" / ep / "plan" / "comic-plan.json")
        scenes = _episode_page_files(root, ep, "scene")
        prompts = _episode_page_files(root, ep, "prompt")

        def c_in_block(n: int) -> bool:
            return block is None or ((n - 1) // 4 + 1) == block

        def c_older(out_m: float | None, ups: list[float | None]) -> bool:
            if out_m is None:
                return False
            return any(u is not None and u > out_m for u in ups)

        out: list[int] = []
        if stage_id == "comic-6-scene":
            for n, p in sorted(scenes.items()):
                if c_in_block(n) and c_older(_mtime(p), [plan_m]):
                    out.append(n)
        else:
            for n, p in sorted(prompts.items()):
                if not c_in_block(n):
                    continue
                up = [plan_m, _mtime(scenes[n]) if n in scenes else None]
                if c_older(_mtime(p), up):
                    out.append(n)
        return out

    if stage_id not in ("manga-6-conti", "manga-7-sheets", "manga-8-artwork", "manga-9-prompts"):
        return []
    plan_m = _mtime(root / "episodes" / ep / "plan" / "page-story-plan.json")
    contis = _episode_page_files(root, ep, "conti")
    sheets = _episode_page_files(root, ep, "sheet")
    arts = _episode_page_files(root, ep, "art")
    prompts = _episode_page_files(root, ep, "prompt")

    def in_block(n: int) -> bool:
        return block is None or ((n - 1) // 4 + 1) == block

    def older(out_m: float | None, up_ms: list[float | None]) -> bool:
        if out_m is None:
            return False
        return any(u is not None and u > out_m for u in up_ms)

    # transitive: a page whose upstream page is stale stays stale even if it
    # was rebuilt from a stale upstream after the plan change.
    def conti_stale_for(n: int) -> bool:
        p = contis.get(n)
        return p is not None and older(_mtime(p), [plan_m])

    def sheet_stale_for(n: int) -> bool:
        p = sheets.get(n)
        if p is None:
            return False
        up = [plan_m, _mtime(contis[n]) if n in contis else None]
        return older(_mtime(p), up) or conti_stale_for(n)

    def art_stale_for(n: int) -> bool:
        p = arts.get(n)
        if p is None:
            return False
        return older(_mtime(p), [plan_m]) or conti_stale_for(n) or sheet_stale_for(n)

    out: list[int] = []
    if stage_id == "manga-6-conti":
        for n, p in sorted(contis.items()):
            if in_block(n) and older(_mtime(p), [plan_m]):
                out.append(n)
    elif stage_id == "manga-7-sheets":
        for n in sorted(sheets):
            if in_block(n) and sheet_stale_for(n):
                out.append(n)
    elif stage_id == "manga-8-artwork":
        for n in sorted(arts):
            if in_block(n) and art_stale_for(n):
                out.append(n)
    else:  # manga-9-prompts
        for n, p in sorted(prompts.items()):
            if not in_block(n):
                continue
            up = [plan_m,
                  _mtime(contis[n]) if n in contis else None,
                  _mtime(sheets[n]) if n in sheets else None,
                  _mtime(arts[n]) if n in arts else None]
            if (older(_mtime(p), up) or conti_stale_for(n) or sheet_stale_for(n)
                    or art_stale_for(n)):
                out.append(n)
    return out


@dataclass
class StageStatus:
    id: str
    n: int
    scope: str
    mode: str
    state: str                 # done | stale | ready | waiting | not-for-this-project
    reason: str = ""
    gate: str | None = None
    outputs: list[str] = field(default_factory=list)


def status_for(root: Path, project: dict, ep: str | None, episode: dict | None) -> list[StageStatus]:
    """State of every stage for a project, and for one episode when given."""
    mode = project.get("mode", "manga")
    stages = STAGES_BY_MODE.get(mode, MANGA_STAGES)
    out: list[StageStatus] = []

    for stage in stages:
        # episode-scope stages need an episode
        if stage.scope == "episode" and not ep:
            out.append(StageStatus(stage.id, stage.n, stage.scope, stage.mode,
                                   "unavailable", "에피소드를 먼저 선택하세요", stage.gate))
            continue

        done = is_done(root, stage, ep)
        missing = [r for r in stage.requires if not (root / render(r, ep)).exists()]
        outputs = [
            render(p, ep)
            for p in stage.produces
        ]
        if done:
            stale = stale_pages(root, ep, stage.id) if ep else []
            if stale:
                state, reason = "stale", (
                    f"이전 단계가 변경됨 — 재작업 필요 "
                    f"({', '.join(str(p) for p in stale)}p)"
                )
            else:
                state, reason = "done", ""
        elif missing:
            names = ", ".join(_skill_for_path(m) for m in missing)
            state, reason = "waiting", f"먼저 필요: {names}"
        elif stage.mode == "present":
            state, reason = "done", ""
        else:
            state, reason = "ready", ""
        out.append(StageStatus(stage.id, stage.n, stage.scope, stage.mode,
                               state, reason, stage.gate, outputs))
    return out


def _skill_for_path(path: str) -> str:
    """Name the stage that owns a gate path, for a readable 'run this first'."""
    for stage in STAGES:
        if stage.gate and _same_gate(stage.gate, path):
            return f"{stage.id} ({stage.n}단계)"
    return path


def _same_gate(a: str, b: str) -> bool:
    return a.replace("{ep}", "X") == b.replace("{ep}", "X")
