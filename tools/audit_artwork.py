#!/usr/bin/env python3
"""Audit the artist's pages (stage 8) with the same rules the app enforces.

    python tools/audit_artwork.py <project-slug> [--ep <episode>] [--json]

For every `page-NNN.art.json` it runs `validate.validate_artwork` against the
page's conti and reports what the artist got wrong:

  - a panel or a text with no caption
  - a caption that restates the lettering (the words live in the conti)
  - a caption that opens with a panel position, or carries coordinates
  - a caption that is the conti's beat verbatim

Exit code 0 when nothing is wrong, 1 when there is an error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "app" / "backend"))
sys.stdout.reconfigure(encoding="utf-8")

from app.stages import validate  # noqa: E402


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
    eps = sorted(p.name for p in (root / "episodes").iterdir() if p.is_dir())
    ep = args.ep or (eps[0] if eps else None)
    if not ep:
        print(f"project {args.slug!r} has no episodes")
        return 2
    pages = root / "episodes" / ep / "pages"
    pool = json.loads((root / "bible" / "characters.json").read_text(encoding="utf-8")) \
        if (root / "bible" / "characters.json").is_file() else {"characters": [], "objects": []}
    cards = {c["id"]: c for c in pool.get("characters", [])}
    cards |= {o["id"]: o for o in pool.get("objects", [])}

    rows: list[dict] = []
    issues: list[dict] = []
    for art_path in sorted(pages.glob("page-*.art.json")):
        art = json.loads(art_path.read_text(encoding="utf-8"))
        page = int(art.get("page", 0) or 0)
        conti_path = pages / f"page-{page:03d}.conti.json"
        if not conti_path.is_file():
            issues.append(validate.issue("error", "art.no-conti", art_path.name,
                                         "no conti for this artwork page"))
            continue
        conti = json.loads(conti_path.read_text(encoding="utf-8"))
        page_issues = validate.validate_artwork(art, conti, cards)
        issues += page_issues
        rows.append({
            "page": page,
            "errors": len(validate.errors(page_issues)),
            "warnings": len(validate.warnings(page_issues)),
            "codes": sorted({i["code"] for i in page_issues}),
        })

    if args.json:
        print(json.dumps({"pages": rows, "issues": issues}, ensure_ascii=False, indent=2))
    else:
        if not rows:
            print(f"{args.slug}/{ep}: no artwork yet")
        for r in rows:
            flag = f"  <-- {', '.join(r['codes'])}" if r["codes"] else ""
            print(f"page {r['page']:2}: {r['errors']} error {r['warnings']} warning{flag}")
        for i in issues:
            print(f"[{i['level']:7}] {i['code']:26} {i['where']}: {i['message']}")
        errs = validate.errors(issues)
        print(f"\n{len(errs)} error(s), {len(validate.warnings(issues))} warning(s)")
    return 1 if validate.errors(issues) else 0


if __name__ == "__main__":
    raise SystemExit(main())
