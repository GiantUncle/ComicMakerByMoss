#!/usr/bin/env python3
"""Compile a MOSS-Image comic/layout draft into a ready-to-paste prompt.

Drafts are written in the *human* coordinate system: pixels from the canvas
top-left, `bbox` as [x_min, y_min, x_max, y_max].  Compiled prompts use the
*model* coordinate system: `abs_centralized` / `yxyx`, i.e.
[y_min, x_min, y_max, x_max] with the canvas centre as the origin.

This tool does the arithmetic so the model never has to.  It also accepts an
already-compiled prompt and round-trips it, which is how an existing layout
gets edited.

Targets
-------
  layout  (default) : {summary:{caption,meta,canvas}, items:[...]}          MOSS Layout JSON
  scene             : {scene_type, gen_brief, elements:[...], must_not, palette}
                      MOSS Scene JSON (official multi-panel variant)

Usage
-----
    python compile_layout.py draft.json                  # compiled prompt -> stdout
    python compile_layout.py draft.json -o prompt.txt    # ... -> file
    python compile_layout.py draft.json --compact        # one physical line
    python compile_layout.py draft.json --check          # validate only
    python compile_layout.py draft.json --target scene   # emit Scene JSON
    python compile_layout.py draft.json --width 1024 --height 1536  # canvas for a compiled input
    python compile_layout.py --fit "你好！\n今天请多关照" --vertical --font-size 24

Exit codes: 0 ok, 2 validation error, 3 usage error.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

LABELS = ("object", "character", "text", "panel", "subject")
DRAFT_ROOT_FIELDS = {
    "width",
    "height",
    "bbox_coord_space",
    "bbox_format",
    "summary",
    "items",
    "prefix",
    "scene_type",
    "must_not",
    "palette",
}
SUMMARY_FIELDS = {"caption", "meta", "canvas", "palette"}
ITEM_FIELDS = {
    "label",
    "caption",
    "bbox",
    "text",
    "tags",
    "palette",
    "note",
    "identity",
    "salience",
    "colors",
    # Reference wiring: consumed by the render step, dropped from the prompt.
    "ref_id",
}
COMPILED_ROOT_FIELDS = {
    "summary",
    "items",
    "bbox_coord_space",
    "bbox_format",
    "width",
    "height",
    "prefix",
}
CANVAS_VALUES = ("single", "multi_panel", "collage")
TYPE_CHAR = {"text": "T", "character": "C", "object": "O", "panel": "P", "subject": "S"}


# --------------------------------------------------------------------------- #
# validation helpers
# --------------------------------------------------------------------------- #
def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def check_fields(value, allowed, required, location: str) -> None:
    require(isinstance(value, dict), f"{location} must be an object")
    unknown = set(value) - allowed
    missing = set(required) - set(value)
    require(not unknown, f"{location}: unknown fields {sorted(unknown)}")
    require(not missing, f"{location}: missing fields {sorted(missing)}")


def check_text(value, location: str) -> None:
    require(
        isinstance(value, str) and bool(value.strip()),
        f"{location} must be nonempty text",
    )


def check_string_list(value, location: str) -> None:
    require(isinstance(value, list), f"{location} must be an array")
    for index, item in enumerate(value):
        check_text(item, f"{location}[{index}]")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError(f"Invalid JSON number: {value}")


# --------------------------------------------------------------------------- #
# text metrics
# --------------------------------------------------------------------------- #
def visual_len(line: str) -> float:
    """Approximate rendered width of one line in 'em' units."""
    total = 0.0
    for char in line:
        code = ord(char)
        if (
            0x2E80 <= code <= 0x9FFF
            or 0xFF00 <= code <= 0xFFEF
            or 0x3000 <= code <= 0x303F
            or 0xAC00 <= code <= 0xD7AF
        ):
            total += 1.0
        elif char == " ":
            total += 0.3
        else:
            total += 0.55
    return total


def implied_font_size(box_w: float, box_h: float, text: str, vertical: bool) -> float:
    """Font size (px) that would just fill the box."""
    lines = text.split("\n")
    if vertical:
        columns = max(1, len(lines))
        longest = max(1, max(len(line) for line in lines))
        by_width = box_w / (columns * 1.5)
        by_height = box_h / (longest * 1.1)
    else:
        longest = max(1.0, max(visual_len(line) for line in lines))
        by_width = box_w / longest
        by_height = box_h / (max(1, len(lines)) * 1.4)
    return min(by_width, by_height)


def required_box(text: str, vertical: bool, font: float) -> tuple:
    lines = text.split("\n")
    if vertical:
        width = max(1, len(lines)) * font * 1.5
        height = max(1, max(len(line) for line in lines)) * font * 1.1
    else:
        width = max(1.0, max(visual_len(line) for line in lines)) * font
        height = max(1, len(lines)) * font * 1.4
    return width, height


# --------------------------------------------------------------------------- #
# geometry
# --------------------------------------------------------------------------- #
def to_absolute_xyxy(box, width: int, height: int, location: str):
    require(
        isinstance(box, list) and len(box) == 4,
        f"{location} must be [x_min, y_min, x_max, y_max]",
    )
    require(
        all(
            isinstance(v, (int, float))
            and not isinstance(v, bool)
            and math.isfinite(v)
            for v in box
        ),
        f"{location} must contain four finite numbers",
    )
    x1, y1, x2, y2 = box
    require(x1 < x2 and y1 < y2, f"{location} must have positive width and height")
    require(
        0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height,
        f"{location} exceeds the {width}x{height} canvas "
        f"(got x {x1}..{x2}, y {y1}..{y2})",
    )
    return x1, y1, x2, y2


def to_centered_yxyx(box, width: int, height: int, location: str):
    """[x1,y1,x2,y2] absolute pixels -> [y1,x1,y2,x2] centred on the canvas."""
    x1, y1, x2, y2 = to_absolute_xyxy(box, width, height, location)
    return [
        math.floor(round(y1, 9)) - height // 2,
        math.floor(round(x1, 9)) - width // 2,
        math.ceil(round(y2, 9)) - height // 2,
        math.ceil(round(x2, 9)) - width // 2,
    ]


def from_centered_yxyx(box, width: int, height: int, location: str):
    """[y1,x1,y2,x2] centred -> [x1,y1,x2,y2] absolute pixels."""
    require(
        isinstance(box, list) and len(box) == 4,
        f"{location} must be [y_min, x_min, y_max, x_max]",
    )
    require(
        all(
            isinstance(v, (int, float))
            and not isinstance(v, bool)
            and math.isfinite(v)
            for v in box
        ),
        f"{location} must contain four finite numbers",
    )
    y1, x1, y2, x2 = box
    require(y1 < y2 and x1 < x2, f"{location} must have positive width and height")
    abs_y1 = y1 + height // 2
    abs_x1 = x1 + width // 2
    abs_y2 = y2 + height // 2
    abs_x2 = x2 + width // 2
    require(
        0 <= abs_x1 < abs_x2 <= width and 0 <= abs_y1 < abs_y2 <= height,
        f"{location} exceeds the {width}x{height} canvas",
    )
    return abs_x1, abs_y1, abs_x2, abs_y2


# --------------------------------------------------------------------------- #
# loading
# --------------------------------------------------------------------------- #
def load_draft(path: Path, width_override=None, height_override=None):
    raw = path.read_text(encoding="utf-8-sig")
    data = json.loads(
        raw,
        object_pairs_hook=unique_object,
        parse_constant=reject_constant,
    )
    require(isinstance(data, dict), "Draft must be a JSON object")

    prefix = data.get("prefix", "")
    if prefix:
        check_text(prefix, "prefix")

    coord = data.get("bbox_coord_space")
    fmt = data.get("bbox_format")

    if coord == "abs" and fmt == "xyxy":
        check_fields(
            data,
            DRAFT_ROOT_FIELDS,
            {"width", "height", "bbox_coord_space", "bbox_format", "summary", "items"},
            "Layout draft",
        )
        width, height = data["width"], data["height"]
    elif coord == "abs_centralized" and fmt == "yxyx":
        check_fields(
            data,
            COMPILED_ROOT_FIELDS,
            {"summary", "items", "bbox_coord_space", "bbox_format"},
            "Compiled layout",
        )
        width = data.get("width", width_override)
        height = data.get("height", height_override)
        require(
            width is not None and height is not None,
            "A compiled layout has no canvas size: pass --width and --height",
        )
    else:
        raise ValueError(
            "bbox_coord_space/bbox_format must be "
            '"abs"/"xyxy" (draft) or "abs_centralized"/"yxyx" (compiled), '
            f"got {coord!r}/{fmt!r}"
        )

    for name, value in (("width", width), ("height", height)):
        require(
            type(value) is int and value > 0 and value % 16 == 0,
            f"{name} must be a positive integer multiple of 16 (got {value!r})",
        )

    summary = data.get("summary", {})
    if summary:
        check_fields(summary, SUMMARY_FIELDS, {"caption"}, "summary")
        check_text(summary["caption"], "summary.caption")
        if "canvas" in summary:
            require(
                summary["canvas"] in CANVAS_VALUES,
                f"summary.canvas must be one of {CANVAS_VALUES}",
            )
        for key in ("meta", "palette"):
            if key in summary:
                check_string_list(summary[key], f"summary.{key}")

    items = data["items"]
    require(
        isinstance(items, list) and bool(items),
        "items must be a nonempty flat array",
    )

    normalized = []
    for index, item in enumerate(items):
        location = f"items[{index}]"
        check_fields(item, ITEM_FIELDS, {"label", "caption", "bbox"}, location)
        require(item["label"] in LABELS, f"{location}.label must be one of {LABELS}")
        check_text(item["caption"], f"{location}.caption")
        if item["label"] == "text":
            require("text" in item, f"{location}: text items require a literal 'text'")
        if "text" in item:
            check_text(item["text"], f"{location}.text")
        for key in ("tags", "palette"):
            if key in item:
                check_string_list(item[key], f"{location}.{key}")
        if "colors" in item:
            colors = item["colors"]
            require(isinstance(colors, list), f"{location}.colors must be an array")
            for color_index, color in enumerate(colors):
                require(
                    isinstance(color, dict) and "color" in color and "hex" in color,
                    f"{location}.colors[{color_index}] needs 'color' and 'hex'",
                )

        if coord == "abs" and fmt == "xyxy":
            box = to_absolute_xyxy(item["bbox"], width, height, f"{location}.bbox")
        else:
            box = from_centered_yxyx(item["bbox"], width, height, f"{location}.bbox")
        normalized.append({**item, "bbox": list(box)})

    must_not = data.get("must_not", [])
    check_string_list(must_not, "must_not")
    palette = data.get("palette", [])
    check_string_list(palette, "palette")
    scene_type = data.get("scene_type", "")
    if scene_type:
        check_text(scene_type, "scene_type")

    return {
        "width": width,
        "height": height,
        "summary": summary,
        "items": normalized,
        "prefix": prefix,
        "scene_type": scene_type,
        "must_not": must_not,
        "palette": palette,
    }


# --------------------------------------------------------------------------- #
# compiling
# --------------------------------------------------------------------------- #
def compile_layout(draft) -> dict:
    width, height = draft["width"], draft["height"]
    compiled_items = []
    for index, item in enumerate(draft["items"]):
        location = f"items[{index}]"
        entry = {
            key: value
            for key, value in item.items()
            if key in ("label", "caption", "text", "tags", "palette")
        }
        entry["bbox"] = to_centered_yxyx(item["bbox"], width, height, f"{location}.bbox")
        compiled_items.append(entry)
    return {
        "summary": draft["summary"],
        "items": compiled_items,
        "bbox_coord_space": "abs_centralized",
        "bbox_format": "yxyx",
    }


def first_clause(caption: str) -> str:
    for separator in (": ", " - ", ", "):
        if separator in caption:
            return caption.split(separator)[0].strip()
    sentence = caption.split(". ")[0].strip()
    return sentence.rstrip(".") or caption[:60]


def compile_scene(draft) -> dict:
    width, height = draft["width"], draft["height"]
    summary = draft["summary"]
    gen_brief = summary.get("caption", "")
    meta = summary.get("meta", [])
    scene_type = draft.get("scene_type") or " / ".join(meta[:3]) or "MOSS-Image scene"

    elements = []
    for index, item in enumerate(draft["items"]):
        location = f"elements[{index}]"
        caption = item["caption"]
        entry = {
            "type": "text" if item["label"] == "text" else "obj",
            "bbox": to_centered_yxyx(item["bbox"], width, height, f"{location}.bbox"),
        }
        if entry["type"] == "text":
            entry["text"] = item.get("text", "")
            entry["shape"] = item.get("identity") or caption
            entry["is_watermark"] = False
        else:
            entry["salience"] = item.get(
                "salience", "primary" if item["label"] == "character" else "secondary"
            )
            entry["identity"] = item.get("identity") or first_clause(caption)
            if item.get("note"):
                entry["note"] = item["note"]
            entry["shape"] = caption
        if item.get("colors"):
            entry["colors"] = item["colors"]
        elements.append(entry)

    result = {
        "scene_type": scene_type,
        "gen_brief": gen_brief,
        "elements": elements,
    }
    if draft["must_not"]:
        result["must_not"] = draft["must_not"]
    if draft["palette"]:
        result["palette"] = draft["palette"]
    result["bbox_coord_space"] = "abs_centralized"
    return result


# --------------------------------------------------------------------------- #
# reporting
# --------------------------------------------------------------------------- #
def ascii_map(items, width: int, height: int, cols: int = 72) -> str:
    rows = max(8, min(46, int(round(cols * height / width))))
    grid = [[" "] * cols for _ in range(rows)]
    for item in items:
        x1, y1, x2, y2 = item["bbox"]
        char = TYPE_CHAR.get(item["label"], "O")
        cx1 = min(cols - 1, int(x1 / width * cols))
        cx2 = max(cx1 + 1, min(cols, int(round(x2 / width * cols))))
        ry1 = min(rows - 1, int(y1 / height * rows))
        ry2 = max(ry1 + 1, min(rows, int(round(y2 / height * rows))))
        for row in range(ry1, ry2):
            for col in range(cx1, cx2):
                if grid[row][col] == " ":
                    grid[row][col] = char
                elif grid[row][col] != char:
                    grid[row][col] = "#"
    return "\n".join("".join(row) for row in grid)


def build_report(draft, target: str) -> str:
    width, height = draft["width"], draft["height"]
    items = draft["items"]
    lines = []
    megapixels = width * height / 1_000_000
    lines.append(f"canvas      : {width} x {height} px ({megapixels:.2f} MP)")
    lines.append(f"target      : {target}")
    lines.append("coordinates : draft abs/xyxy -> compiled abs_centralized/yxyx")
    counts = {}
    for item in items:
        counts[item["label"]] = counts.get(item["label"], 0) + 1
    lines.append(
        "items       : "
        + ", ".join(f"{label}={counts[label]}" for label in LABELS if counts.get(label))
        + f" (total {len(items)})"
    )

    canvas_kind = draft["summary"].get("canvas", "?")
    if canvas_kind == "multi_panel" and len(items) < 4:
        lines.append("note        : multi_panel canvas with few items - is a panel grid planned?")
    if canvas_kind == "single" and len(items) > 12:
        lines.append("note        : single canvas with many items - consider Type A (multi_panel)")

    margin_x = width * 0.02
    margin_y = height * 0.02
    min_font = max(9.0, 11.0 * height / 1536)

    lines.append("")
    lines.append(
        f"{'#':>3}  {'label':<9} {'draft bbox xyxy (px)':<28} {'compiled bbox yxyx':<26} notes"
    )
    lines.append("-" * 104)
    warnings = []
    seen_text = {}
    for index, item in enumerate(items):
        x1, y1, x2, y2 = item["bbox"]
        centered = to_centered_yxyx(item["bbox"], width, height, f"items[{index}].bbox")
        notes = []
        box_w, box_h = x2 - x1, y2 - y1

        if item["label"] == "text":
            body = item.get("text", "")
            vertical = box_h > box_w * 1.15
            font = implied_font_size(box_w, box_h, body, vertical)
            orientation = "vert" if vertical else "horiz"
            notes.append(f"{orientation} ~{font:.0f}px font")
            if font < min_font:
                notes.append("TEXT TOO SMALL")
                warnings.append(
                    f"items[{index}] text renders at about {font:.0f}px "
                    f"(need >= {min_font:.0f}px on this canvas) - enlarge the box"
                )
            key = body.strip()
            if key in seen_text:
                notes.append(f"DUPLICATE of items[{seen_text[key]}]")
                warnings.append(
                    f"items[{index}] repeats the same 'text' as items[{seen_text[key]}]"
                )
            else:
                seen_text[key] = index

        if item["label"] == "text" and (
            x1 < margin_x or y1 < margin_y or x2 > width - margin_x or y2 > height - margin_y
        ):
            notes.append("near edge")
            warnings.append(
                f"items[{index}] text is within {margin_x:.0f}px of the canvas edge - "
                "MOSS may clip the lettering"
            )
        if item["label"] in ("character", "text") and box_w < 24 and box_h < 24:
            notes.append("tiny box")

        lines.append(
            f"{index:>3}  {item['label']:<9} "
            + f"[{x1:.0f},{y1:.0f},{x2:.0f},{y2:.0f}]".ljust(29)
            + f"[{centered[0]},{centered[1]},{centered[2]},{centered[3]}]".ljust(27)
            + "; ".join(notes)
        )

    coverage = sum(
        (i["bbox"][2] - i["bbox"][0]) * (i["bbox"][3] - i["bbox"][1]) for i in items
    )
    lines.append("")
    lines.append(
        f"sum of box areas: {coverage / (width * height) * 100:.0f}% of the canvas "
        "(overlaps counted twice - 100%+ means boxes overlap)"
    )
    lines.append("")
    lines.append(ascii_map(items, width, height))
    lines.append("")
    lines.append("legend: T=text  C=character  O=object  P=panel  S=subject  #=overlap")

    if warnings:
        lines.append("")
        lines.append("WARNINGS")
        for warning in warnings:
            lines.append(f"  ! {warning}")
    else:
        lines.append("")
        lines.append("WARNINGS: none")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def command_fit(args) -> int:
    body = args.fit.replace("\\n", "\n")
    vertical = args.vertical
    font = args.font_size
    width, height = required_box(body, vertical, font)
    lines = body.split("\n")
    print(f"text      : {len(lines)} line(s), longest {max(len(l) for l in lines)} chars")
    print(
        "direction : "
        + (
            "vertical (one column per line, right to left)"
            if vertical
            else "horizontal"
        )
    )
    print(f"font      : {font:.0f}px")
    print(f"box needs : width {width:.0f}px, height {height:.0f}px")
    print(
        "suggested : bbox = [x_min, y_min, x_max, y_max] with "
        f"x_max-x_min >= {width:.0f}, y_max-y_min >= {height:.0f}"
    )
    print("           (add ~10% padding, then run compile_layout.py)")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Compile a MOSS-Image layout draft into a layout prompt."
    )
    parser.add_argument("draft", nargs="?", type=Path, help="UTF-8 layout draft JSON")
    parser.add_argument("-o", "--output", type=Path, help="write the prompt to a file")
    parser.add_argument(
        "--target",
        choices=("layout", "scene"),
        default="layout",
        help="output schema: MOSS Layout JSON (default) or MOSS Scene JSON",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="emit one physical line of JSON (official compiler form)",
    )
    parser.add_argument(
        "--check", action="store_true", help="validate only; do not emit a prompt"
    )
    parser.add_argument("--width", type=int, help="canvas width for a compiled input")
    parser.add_argument("--height", type=int, help="canvas height for a compiled input")
    parser.add_argument(
        "--no-report", action="store_true", help="suppress the stderr layout report"
    )
    parser.add_argument(
        "--real-newline",
        action="store_true",
        help="separate the trigger prefix with a real newline instead of a literal \\n",
    )
    parser.add_argument("--fit", help="estimate the box a text string needs")
    parser.add_argument("--vertical", action="store_true", help="text is vertical")
    parser.add_argument("--font-size", type=float, default=24.0, help="font size in px")
    args = parser.parse_args(argv)

    if args.fit:
        return command_fit(args)

    if not args.draft:
        parser.error("a draft file is required (or use --fit)")
    if args.output and args.output.resolve() == args.draft.resolve():
        print("Error: --output must differ from the draft file", file=sys.stderr)
        return 3

    try:
        draft = load_draft(args.draft, args.width, args.height)
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    if not args.no_report:
        print(build_report(draft, args.target), file=sys.stderr)

    if args.check:
        return 0

    result = compile_scene(draft) if args.target == "scene" else compile_layout(draft)
    payload = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    if not args.compact:
        payload = json.dumps(result, ensure_ascii=False, indent=2)

    if draft["prefix"]:
        separator = "\n" if args.real_newline else "\\n"
        payload = draft["prefix"] + separator + payload

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
