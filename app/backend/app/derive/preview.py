"""Turn a compiled prompt into a manuscript preview.

The prompt already knows everything: every item has a box, every text item has
its words, and the canvas size is the one it was compiled for. So the preview is
a straight read — no guessing, no model.

    prompt (abs_centralized / yxyx)  ->  shapes in pixel coordinates

The frontend draws the shapes. Keeping this a data transform rather than an SVG
string is what lets a cut be hovered, clicked and retaken.
"""

from __future__ import annotations

from typing import Any

TAG = {"object": "OBJ", "character": "CH", "panel": "PNL", "subject": "SUB"}


def _to_abs(box: list[float], width: int, height: int) -> tuple[float, float, float, float]:
    y1, x1, y2, x2 = box
    return x1 + width / 2, y1 + height / 2, x2 + width / 2, y2 + height / 2


def _text_style(caption: str) -> str:
    c = caption.lower()
    if "balloon" in c or "bubble" in c:
        return "balloon"
    if "box" in c or "rect" in c:
        return "rect"
    return "plain"          # sound effect, floating line, inscription


def build(prompt: dict[str, Any], width: int, height: int) -> dict[str, Any]:
    """Return the drawable model for one page."""
    shapes: list[dict[str, Any]] = []
    panels = 0

    for index, item in enumerate(prompt.get("items", [])):
        x1, y1, x2, y2 = _to_abs(item["bbox"], width, height)
        base = {
            "id": index,
            "x": round(x1, 2),
            "y": round(y1, 2),
            "w": round(x2 - x1, 2),
            "h": round(y2 - y1, 2),
            "caption": item.get("caption", ""),
        }

        if item.get("label") == "text":
            shapes.append({
                **base,
                "kind": "text",
                "style": _text_style(item.get("caption", "")),
                "text": item.get("text", ""),
                "lines": _wrap(item.get("text", "")),
            })
        else:
            panels += 1
            shapes.append({
                **base,
                "kind": "panel",
                "tag": TAG.get(item.get("label", "object"), "OBJ"),
                "n": panels,
            })

    return {
        "width": width,
        "height": height,
        "shape_count": len(shapes),
        "panel_count": panels,
        "text_count": len(shapes) - panels,
        "shapes": shapes,
    }


def _wrap(text: str, per_line: int = 14) -> list[str]:
    """Split on real newlines; leave long lines to the renderer to shrink."""
    return [line for line in text.split("\n")] if text else []
