#!/usr/bin/env python3
"""Instantiate a manga layout template into panel bboxes, and validate the page.

Turns a template id (templates/layouts.json) + a canvas size tier into concrete
panel boxes in absolute pixels, ordered by the reading direction, then checks the
page against the manga grammar rules (T-rule / gutters / 見せゴマ / panel count).

Usage
-----
    python instantiate_layout.py --list
    python instantiate_layout.py T3C --size M
    python instantiate_layout.py T3C --size M --reading ltr
    python instantiate_layout.py DAN4 --size M --json
    python instantiate_layout.py T3C --size M --center        # emit abs_centralized yxyx
    python instantiate_layout.py T3C --size M --emit-draft draft.json --canvas 992 1408

Exit codes: 0 ok, 1 grammar warnings, 2 error.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_LIB = HERE.parent / "templates" / "layouts.json"


def load_library(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def find_template(lib, template_id: str):
    for tpl in lib["templates"]:
        if tpl["id"].lower() == template_id.lower():
            return tpl
    raise ValueError(f"unknown template id {template_id!r}")


def size_of(lib, tier: str):
    sizes = lib["sizes"]
    if tier not in sizes:
        raise ValueError(f"unknown size tier {tier!r} (have {sorted(sizes)})")
    return sizes[tier]


# --------------------------------------------------------------------------- #
# instantiation
# --------------------------------------------------------------------------- #
def instantiate(template, size, reading: str):
    width, height = size["w"], size["h"]
    margin = size["margin"]
    gutter = int(round(size["gutter"] * template.get("gutter_scale", 1.0)))

    live_w = width - 2 * margin
    live_h = height - 2 * margin
    tiers = template["tiers"]
    tier_n = len(tiers)

    avail_h = live_h - gutter * (tier_n - 1)
    total_weight = sum(t["weight"] for t in tiers)
    heights = [int(round(avail_h * t["weight"] / total_weight)) for t in tiers]
    heights[-1] += avail_h - sum(heights)

    panels = []
    y = margin
    for tier_index, tier in enumerate(tiers):
        h = heights[tier_index]
        weights = tier["panels"]
        count = len(weights)
        avail_w = live_w - gutter * (count - 1)
        total_pw = sum(weights)
        widths = [int(round(avail_w * w / total_pw)) for w in weights]
        widths[-1] += avail_w - sum(widths)

        row = []
        x = margin
        for w in widths:
            row.append({"tier": tier_index, "bbox": [x, y, x + w, y + h]})
            x += w + int(round(gutter))

        if reading == "rtl":
            row.sort(key=lambda p: -p["bbox"][0])
        else:
            row.sort(key=lambda p: p["bbox"][0])
        panels.extend(row)
        y += h + int(round(gutter))

    for index, panel in enumerate(panels, start=1):
        panel["n"] = index
        x1, y1, x2, y2 = panel["bbox"]
        panel["size"] = [x2 - x1, y2 - y1]
        panel["area"] = (x2 - x1) * (y2 - y1)
    return panels


def centrify(panels, width, height):
    out = []
    for p in panels:
        x1, y1, x2, y2 = p["bbox"]
        out.append(
            {
                "n": p["n"],
                "tier": p["tier"],
                "bbox": [
                    y1 - height // 2,
                    x1 - width // 2,
                    y2 - height // 2,
                    x2 - width // 2,
                ],
            }
        )
    return out


# --------------------------------------------------------------------------- #
# validation
# --------------------------------------------------------------------------- #
def split_positions(panels, tier_index):
    xs = sorted({p["bbox"][0] for p in panels if p["tier"] == tier_index})
    return xs[1:]  # internal left edges only


def validate(panels, template, size, lib):
    rules = lib["rules"]
    width, height = size["w"], size["h"]
    issues = []
    notes = []

    # panel count
    n = len(panels)
    lo, hi = rules["panel_count"]["min"], rules["panel_count"]["max"]
    if not (lo <= n <= hi):
        issues.append(f"panel count {n} outside {lo}..{hi}")
    standard = rules["panel_count"]["standard"]
    if n > standard[1]:
        issues.append(f"panel count {n} above the standard band {standard} - consider two pages")

    # tier count
    tier_n = len(template["tiers"])
    if tier_n > rules["tier_count"]["max"]:
        issues.append(f"tier count {tier_n} above max {rules['tier_count']['max']}")

    # margin
    margin_min = width * rules["margin_min_fraction"]
    if size["margin"] < margin_min:
        issues.append(f"margin {size['margin']}px below the {margin_min:.0f}px floor")

    # T-rule: adjacent split tiers must not align their vertical cuts.
    # Templates whose whole point is a "+" intersection are exempt, but the
    # exemption is reported so the caller knows the page is order-exempt.
    stagger_min = width * rules["stagger_min_fraction"]
    exempt = template.get("t_rule_exempt")
    if exempt:
        notes.append(f"T-rule exempt: {exempt}")
    else:
        by_tier = {}
        for p in panels:
            by_tier.setdefault(p["tier"], []).append(p)
        tier_ids = sorted(by_tier)
        for a, b in zip(tier_ids, tier_ids[1:]):
            ca, cb = split_positions(panels, a), split_positions(panels, b)
            if not ca or not cb:
                continue
            for x in ca:
                for y_ in cb:
                    if abs(x - y_) < stagger_min:
                        issues.append(
                            f"T-rule: tiers {a}/{b} split at x={x} and x={y_} "
                            f"(< {stagger_min:.0f}px apart) - stagger them"
                        )

    # 見せゴマ - only checked when the template claims to have one.
    areas = sorted((p["area"] for p in panels), reverse=True)
    if template.get("expects_misegoma") and len(areas) >= 2:
        ratio = areas[0] / areas[1]
        need = rules["misegoma"]["min_area_vs_second"]
        if ratio < need:
            issues.append(
                f"no clear 見せゴマ: largest panel is only {ratio:.2f}x the second "
                f"(want >= {need}x) - raise the bottom tier weight"
            )
    if len(panels) > 1:
        share = areas[0] / (width * height)
        lo_s, hi_s = rules["misegoma"]["page_area_share"]
        notes.append(
            f"largest panel = {share * 100:.0f}% of the page "
            f"(guideline {lo_s * 100:.0f}-{hi_s * 100:.0f}% for a normal page)"
        )

    # bounds
    for p in panels:
        x1, y1, x2, y2 = p["bbox"]
        if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
            issues.append(f"panel {p['n']} out of bounds {p['bbox']}")

    return issues, notes


def ascii_page(panels, size, cols=64):
    width, height = size["w"], size["h"]
    rows = max(8, min(44, int(round(cols * height / width))))
    grid = [[" "] * cols for _ in range(rows)]
    for p in panels:
        x1, y1, x2, y2 = p["bbox"]
        digit = str(p["n"])[-1]
        cx1 = min(cols - 1, int(x1 / width * cols))
        cx2 = max(cx1 + 1, min(cols, int(round(x2 / width * cols))))
        ry1 = min(rows - 1, int(y1 / height * rows))
        ry2 = max(ry1 + 1, min(rows, int(round(y2 / height * rows))))
        for r in range(ry1, ry2):
            for c in range(cx1, cx2):
                on_border = r in (ry1, ry2 - 1) or c in (cx1, cx2 - 1)
                grid[r][c] = digit if on_border else "."
    return "\n".join("".join(row) for row in grid)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("template", nargs="?", help="template id, e.g. T3C")
    parser.add_argument("--library", type=Path, default=DEFAULT_LIB)
    parser.add_argument("--size", default="M", help="S | M | L | XL (default M)")
    parser.add_argument("--reading", choices=("rtl", "ltr"), default="rtl")
    parser.add_argument("--json", action="store_true", help="print panels as JSON")
    parser.add_argument("--center", action="store_true", help="emit abs_centralized yxyx")
    parser.add_argument("--emit-draft", type=Path, help="write a MOSS layout draft JSON")
    parser.add_argument("--canvas", nargs=2, type=int, metavar=("W", "H"),
                        help="canvas size for --emit-draft (overrides --size)")
    parser.add_argument("--list", action="store_true", help="list templates and exit")
    parser.add_argument("--no-ascii", action="store_true")
    args = parser.parse_args(argv)

    try:
        lib = load_library(args.library)
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    if args.list:
        for pfn, ids in lib.get("page_function_defaults", {}).items():
            print(f"{pfn:<10} -> {', '.join(ids)}")
        print()
        for tpl in lib["templates"]:
            count = sum(len(t["panels"]) for t in tpl["tiers"])
            print(
                f"{tpl['id']:<12} {count} panels  {tpl['name_ja']:<22} {tpl['name_en']}"
            )
        return 0

    if not args.template:
        parser.error("a template id is required (or use --list)")

    try:
        template = find_template(lib, args.template)
        size = size_of(lib, args.size)
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    panels = instantiate(template, size, args.reading)
    issues, notes = validate(panels, template, size, lib)

    width, height = size["w"], size["h"]
    print(f"template : {template['id']}  ({template['name_ja']} / {template['name_en']})")
    print(f"canvas   : {width} x {height}  (tier {args.size}, margin {size['margin']}, gutter {size['gutter']})")
    print(f"reading  : {args.reading}   panels: {len(panels)}  tiers: {len(template['tiers'])}")
    print()
    for p in panels:
        x1, y1, x2, y2 = p["bbox"]
        print(
            f"  {p['n']:>2}  tier {p['tier']}  xyxy [{x1},{y1},{x2},{y2}]  "
            f"size {p['size'][0]}x{p['size'][1]}  area {p['area'] / (width * height) * 100:.0f}%"
        )
    if not args.no_ascii:
        print()
        print(ascii_page(panels, size))
    print()
    for note in notes:
        print(f"  . {note}")
    if issues:
        print(f"GRAMMAR WARNINGS ({len(issues)})")
        for issue in issues:
            print(f"  ! {issue}")
    else:
        print("GRAMMAR WARNINGS: none")

    if args.json or args.center:
        payload = centrify(panels, width, height) if args.center else panels
        print()
        print(json.dumps(payload, ensure_ascii=False))

    if args.emit_draft:
        cw, ch = (args.canvas if args.canvas else (width, height))
        draft = {
            "width": cw,
            "height": ch,
            "bbox_coord_space": "abs",
            "bbox_format": "xyxy",
            "summary": {
                "meta": ["comic", "multi_panel"],
                "canvas": "multi_panel",
                "caption": "<style brief: medium, palette, light, rendering, zero rough sketch lines>",
            },
            "items": [
                {
                    "label": "object",
                    "caption": f"<panel {p['n']}: what happens here>",
                    "bbox": p["bbox"],
                }
                for p in panels
            ],
        }
        args.emit_draft.parent.mkdir(parents=True, exist_ok=True)
        args.emit_draft.write_text(
            json.dumps(draft, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"\nWrote draft {args.emit_draft}", file=sys.stderr)

    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
