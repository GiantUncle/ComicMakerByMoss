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
    n: int                     # pipeline number, 1..7
    scope: str                 # project | episode
    mode: str                  # model | deterministic | present
    produces: tuple[str, ...]  # glob patterns, relative to the project root
    gate: str | None           # the gate file, or None for a gate-less stage
    requires: tuple[str, ...] = ()   # gate files that must already exist
    craft: tuple[str, ...] = ()      # craft docs to attach to the model prompt
    per_block: bool = False          # runs once per 4-page block


STAGES: tuple[Stage, ...] = (
    Stage(
        id="manga-1-source", n=1, scope="episode", mode="model",
        produces=("episodes/{ep}/episode.json", "episodes/{ep}/source/novel.txt"),
        gate="episodes/{ep}/source/APPROVED",
    ),
    Stage(
        id="manga-2-project", n=2, scope="project", mode="present",
        produces=("project.json",), gate=None,
    ),
    Stage(
        id="manga-3-bible", n=3, scope="project", mode="model",
        produces=("bible/characters.json",), gate="bible/APPROVED",
        requires=("episodes/{ep}/source/APPROVED",),
        craft=("character-consistency.md",),
    ),
    Stage(
        id="manga-4-refsheets", n=4, scope="project", mode="deterministic",
        produces=("bible/characters/*/sheet.prompt.txt",), gate="bible/SHEETS_APPROVED",
        requires=("bible/APPROVED",),
    ),
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
        id="manga-7-pages", n=7, scope="episode", mode="deterministic", per_block=True,
        produces=("episodes/{ep}/prompts/page-{block}*.prompt.txt",),
        gate=None,
        requires=("episodes/{ep}/plan/APPROVED",),
    ),
)

BY_ID = {s.id: s for s in STAGES}
BY_N = {s.n: s for s in STAGES}


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


@dataclass
class StageStatus:
    id: str
    n: int
    scope: str
    mode: str
    state: str                 # done | ready | waiting | not-for-this-project
    reason: str = ""
    gate: str | None = None
    outputs: list[str] = field(default_factory=list)


def status_for(root: Path, project: dict, ep: str | None, episode: dict | None) -> list[StageStatus]:
    """State of every stage for a project, and for one episode when given."""
    mode = project.get("mode", "manga")
    out: list[StageStatus] = []

    for stage in STAGES:
        # episode-scope stages need an episode
        if stage.scope == "episode" and not ep:
            out.append(StageStatus(stage.id, stage.n, stage.scope, stage.mode,
                                   "unavailable", "에피소드를 먼저 선택하세요", stage.gate))
            continue
        # illustration ends after stage 4; comic after stage 5
        if mode == "illustration" and stage.n > 4:
            out.append(StageStatus(stage.id, stage.n, stage.scope, stage.mode,
                                   "unavailable", "illustration 은 4단계에서 끝납니다", stage.gate))
            continue
        if mode == "comic" and stage.n == 7:
            out.append(StageStatus(stage.id, stage.n, stage.scope, stage.mode,
                                   "unavailable", "comic 은 한 장이라 7단계가 없습니다", stage.gate))
            continue

        done = is_done(root, stage, ep)
        missing = [r for r in stage.requires if not (root / render(r, ep)).exists()]
        outputs = [
            render(p, ep)
            for p in stage.produces
        ]
        if done:
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
