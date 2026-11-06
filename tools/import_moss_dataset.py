#!/usr/bin/env python3
"""Import the MOSS panel-layout dataset into the skill's template library.

Source: sepiablue-ai/ComfyUI-MossPanelDataset (MIT). It ships two catalogues we
use directly:

    data/layouts.json        196 panel layouts (2-6 panels, 1024x1536, RTL)
    data/compositions.json   120 camera compositions (1, 2 or 3 people)

Both are stored as normalised fractions, so they scale to any canvas tier. The
box data is kept; the preview images are not copied — a layout can be drawn from
its boxes, so the app renders a schematic instead of shipping ~50 MB of webp.

    python tools/import_moss_dataset.py --src <comfyui custom_nodes dir>
    python tools/import_moss_dataset.py            # uses the known clone path

The output goes to `.opencode/skills/manga-craft/templates/`:
    moss-layouts.json
    moss-compositions.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / ".opencode" / "skills" / "manga-craft" / "templates"
DEFAULT_SRC = Path(r"C:\Users\gayai\AppData\Local\Temp\opencode\moss-ref")

SOURCE = "sepiablue-ai/ComfyUI-MossPanelDataset"
LICENSE = "MIT"


def find_src(arg: str | None) -> Path:
    for candidate in ([Path(arg)] if arg else []) + [
        DEFAULT_SRC,
        DEFAULT_SRC / "ComfyUI-MossPanelDataset",
    ]:
        if (candidate / "data" / "layouts.json").is_file():
            return candidate
    raise SystemExit(
        "layouts.json not found — pass --src pointing at the cloned "
        "ComfyUI-MossPanelDataset folder"
    )


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def clean_layout(entry: dict) -> dict:
    spec = entry["specification"]
    panels = []
    for panel in spec["panels"]:
        out = {
            "n": panel["id"],
            "bbox": [round(float(v), 6) for v in panel["bbox"]],
            "polygon": [[round(float(x), 6), round(float(y), 6)] for x, y in panel.get("polygon", [])],
            "content_bbox": [round(float(v), 6) for v in panel.get("content_bbox", panel["bbox"])],
            "position": panel.get("position", ""),
            "shape": panel.get("shape_description", "rectangular"),
        }
        if panel.get("parent"):
            out["parent"] = panel["parent"]
        if panel.get("allow_insets"):
            out["allow_insets"] = True
        panels.append(out)
    return {
        "id": entry["id"],
        "name": entry.get("name", ""),
        "name_en": entry.get("name_en", entry.get("name", "")),
        "category": spec.get("category", ""),
        "description": spec.get("description", ""),
        "blank_description": spec.get("blank_description", ""),
        "direction": spec.get("direction", "右から左"),
        "width": spec.get("width", 1024),
        "height": spec.get("height", 1536),
        "panels": panels,
    }


def clean_composition(entry: dict) -> dict:
    return {
        "id": entry["id"],
        "name": entry.get("name", ""),
        "name_en": entry.get("name_en", entry.get("name", "")),
        "category": entry.get("category", ""),
        "prompt": entry.get("prompt", ""),
        "boxes": [[round(float(v), 6) for v in box] for box in entry.get("boxes", [])],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", help="path to the cloned ComfyUI-MossPanelDataset")
    args = ap.parse_args()

    src = find_src(args.src)
    layouts = load(src / "data" / "layouts.json")
    compositions = load(src / "data" / "compositions.json")

    OUT.mkdir(parents=True, exist_ok=True)

    layout_doc = {
        "version": 1,
        "source": SOURCE,
        "license": LICENSE,
        "note": (
            "Imported from ComfyUI-MossPanelDataset. Coordinates are normalised "
            "fractions of the source canvas (1024x1536). A panel may carry "
            "'parent'/'allow_insets' — an inset panel sits inside its parent, "
            "which is the one case where panel boxes may overlap."
        ),
        "canvas": {"w": 1024, "h": 1536},
        "layouts": [clean_layout(e) for e in layouts["layouts"]],
    }
    (OUT / "moss-layouts.json").write_text(
        json.dumps(layout_doc, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    composition_doc = {
        "version": 1,
        "source": SOURCE,
        "license": LICENSE,
        "note": (
            "Camera compositions: the prompt names camera, framing, placement, "
            "body/face direction, pose and furniture only — never expression, "
            "emotion, props or light. 'boxes' are the person regions (normalised)."
        ),
        "categories": sorted({c["category"] for c in compositions["compositions"]}),
        "compositions": [clean_composition(c) for c in compositions["compositions"]],
    }
    (OUT / "moss-compositions.json").write_text(
        json.dumps(composition_doc, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    by_count: dict[int, int] = {}
    for layer in layout_doc["layouts"]:
        by_count[len(layer["panels"])] = by_count.get(len(layer["panels"]), 0) + 1
    print(f"source      : {src}")
    print(f"layouts     : {len(layout_doc['layouts'])}  {dict(sorted(by_count.items()))}")
    print(f"compositions: {len(composition_doc['compositions'])}  {composition_doc['categories']}")
    print(f"written     : {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
