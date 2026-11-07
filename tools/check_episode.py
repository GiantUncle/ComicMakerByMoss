#!/usr/bin/env python3
"""Check one episode's manuscripts with the same rules the app enforces.

    python tools/check_episode.py <project-slug> [--ep <episode>] [--json]

It reads what stage 5 and stage 6/7 actually wrote and reports every problem:

  - a layout used on two pages of the episode (a layout belongs to one page)
  - a page whose layout disagrees with the panels written for it
  - a layout whose shape disagrees with the page's split (even / single)
  - an artwork page that misses a panel or a text, or names a panel position
  - a prompt that is not parseable, or is missing a required field
  - a text box or panel box that leaves the canvas

Exit code is 0 when nothing is wrong, 1 when there is an error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "app" / "backend"))
sys.stdout.reconfigure(encoding="utf-8")

from app.pageshape import load as load_layout, problems as shape_problems  # noqa: E402
from app.stages import build, validate  # noqa: E402


def check(slug: str, ep: str) -> list[dict]:
    root = REPO / "projects" / slug
    project = json.loads((root / "project.json").read_text(encoding="utf-8"))
    pages_dir = root / "episodes" / ep / "pages"

    issues: list[dict] = []

    # ---- plan: split, layout, panel count, and no layout twice
    plan_path = root / "episodes" / ep / "plan" / "page-story-plan.json"
    if plan_path.is_file():
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        issues += validate.validate_plan(plan, project)
    else:
        issues.append(validate.issue("error", "episode.no-plan", "plan",
                                      "page-story-plan.json is missing"))

    # ---- contis: layout agreement, canvas, and no layout twice
    contis = []
    for conti_path in sorted(pages_dir.glob("page-*.conti.json")):
        conti = json.loads(conti_path.read_text(encoding="utf-8"))
        contis.append(conti)
        issues += validate.validate_conti(conti, project)

    issues += validate.validate_episode(contis, project)

    # ---- artwork: the artist's page must cover every panel and text
    conti_by_page = {int(c.get("page", 0)): c for c in contis}
    for art_path in sorted(pages_dir.glob("page-*.art.json")):
        try:
            art = json.loads(art_path.read_text(encoding="utf-8"))
        except Exception as exc:
            issues.append(validate.issue("error", "art.bad-json", art_path.name,
                                         f"artwork is not parseable: {exc}"))
            continue
        conti = conti_by_page.get(int(art.get("page", 0) or 0))
        if conti is None:
            issues.append(validate.issue("warning", "art.no-conti", art_path.name,
                                         "artwork has no matching conti page"))
            continue
        issues += validate.validate_artwork(art, conti)

    # ---- the same check, straight off the layout boxes
    seen: dict[str, int] = {}
    for conti in contis:
        tpl = (conti.get("layout") or {}).get("template_id")
        where = f"page {conti.get('page', '?')}"
        if not tpl:
            issues.append(validate.issue("error", "episode.no-layout", where,
                                         "no layout.template_id"))
            continue
        if tpl in seen:
            issues.append(validate.issue(
                "error", "episode.repeat-layout", where,
                f"layout {tpl} is also on page {seen[tpl]}"))
        else:
            seen[tpl] = int(conti.get("page", 0))

        layout = load_layout(tpl)
        if layout is not None:
            for p in shape_problems(layout, conti.get("split")):
                issues.append(validate.issue("error", "layout.wrong-shape", where, p))

    # ---- prompts: parse, required fields, canvas
    prompts_dir = root / "episodes" / ep / "prompts"
    for prompt_path in sorted(prompts_dir.glob("page-*.prompt.txt")):
        text = prompt_path.read_text(encoding="utf-8")
        sheet_path = pages_dir / prompt_path.name.replace("prompt.txt", "sheet.json")
        width, height = None, None
        if sheet_path.is_file():
            sheet = json.loads(sheet_path.read_text(encoding="utf-8"))
            width, height = sheet.get("width"), sheet.get("height")
        try:
            obj = json.loads(text[text.index("{"):])
        except Exception as exc:
            issues.append(validate.issue("error", "prompt.bad-json", prompt_path.name,
                                         f"prompt is not parseable: {exc}"))
            continue
        issues += validate.validate_prompt(obj, width or 0, height or 0, project)

    return issues


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--ep", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    root = REPO / "projects" / args.slug
    if not root.is_dir():
        print(f"no project {args.slug!r} under projects/")
        return 2

    ep = args.ep
    if ep is None:
        eps = sorted(p.name for p in (root / "episodes").iterdir() if p.is_dir())
        if not eps:
            print(f"project {args.slug!r} has no episodes")
            return 2
        ep = eps[0]

    issues = check(args.slug, ep)
    if args.json:
        print(json.dumps(issues, ensure_ascii=False, indent=2))
    else:
        if not issues:
            print(f"{args.slug}/{ep}: everything checks out")
        for i in issues:
            print(f"[{i['level']:7}] {i['where']}: {i['message']}")
        errs = validate.errors(issues)
        print(f"\n{len(errs)} error(s), {len(validate.warnings(issues))} warning(s)")
    return 1 if validate.errors(issues) else 0


if __name__ == "__main__":
    raise SystemExit(main())
