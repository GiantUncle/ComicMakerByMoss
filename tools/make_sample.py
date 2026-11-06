#!/usr/bin/env python3
"""Build the three sample manuscript prompts the preview screen ships with.

One page, three languages. Each output is a real compiled prompt produced by the
skill's own compile_layout.py, so the preview is drawn from exactly what the
pipeline emits.

    python tools/make_sample.py
    -> app/frontend/public/sample/{ko,en,ja}.json
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / ".opencode" / "skills" / "manga-craft" / "scripts"
OUT = REPO / "app" / "frontend" / "public" / "sample"

spec = importlib.util.spec_from_file_location("compile_layout", SCRIPTS / "compile_layout.py")
compile_layout = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(compile_layout)

W, H = 992, 1408

# One page, four panels, six text items. Korean, English and Japanese are
# authored side by side — the language button picks a column, it does not
# translate.
LINES = {
    "p1": {
        "ko": "두 번째 밤",
        "en": "The Second Night",
        "ja": "二夜目",
    },
    "p2": {
        "ko": "관객석이 갑자기 가득 찼다.\n모두 퇴근 복장이었다.",
        "en": "The seats filled in an instant.\nEvery one of them in office wear.",
        "ja": "客席が突然埋まった。\n誰もが出勤の身なりだった。",
    },
    "d1": {
        "ko": "어, 뭐지…?",
        "en": "Huh — what is this…?",
        "ja": "え、何だこれ…？",
    },
    "d2": {
        "ko": "반갑습니다, 직장인 여러분.",
        "en": "Welcome, office workers, one and all.",
        "ja": "ようこそ、勤め人の皆さん。",
    },
    "s1": {"ko": "달칵", "en": "clack", "ja": "カチッ"},
    "n1": {"ko": "브라운", "en": "Brown", "ja": "ブラウン"},
}

ITEMS = [
    # ---- panel 1 (T3C tier 0, right, read first in RTL) ----
    {
        "kind": "panel",
        "bbox": [503, 40, 952, 365],
        "caption": (
            "A wide panel of a brightly lit talk-show set: a warm cream and crimson "
            "stage seen from the audience side, empty of people."
        ),
    },
    {
        "kind": "text",
        "bbox": [560, 60, 900, 150],
        "caption": "Clean horizontal narration text in a plain white rectangular box.",
        "key": "p1",
    },
    # ---- panel 2 (tier 0, left) ----
    {
        "kind": "panel",
        "bbox": [40, 40, 489, 365],
        "caption": (
            "A medium panel of the audience seen from the stage: rows of tired "
            "commuters in grey and navy office clothes, lit by a warm stage wash."
        ),
    },
    {
        "kind": "text",
        "bbox": [70, 200, 420, 330],
        "caption": "Clean horizontal narration text in a plain white rectangular box.",
        "key": "p2",
    },
    # ---- panel 3 (tier 1, full width) ----
    {
        "kind": "panel",
        "bbox": [40, 379, 952, 704],
        "caption": (
            "A medium panel on the young woman at the edge of the glow: she is a "
            "woman in her mid-twenties with a soft oval face, calm dark eyes, and "
            "sleek dark hair pulled into a low ponytail. She stands turned three "
            "quarters toward the audience, one hand half raised in surprise."
        ),
    },
    {
        "kind": "text",
        "bbox": [620, 420, 900, 530],
        "caption": "Clean horizontal dialogue text in a rounded speech balloon, the tail pointing left.",
        "key": "d1",
    },
    # ---- panel 4 (tier 2, full width, tall) ----
    {
        "kind": "panel",
        "bbox": [40, 718, 952, 1368],
        "caption": (
            "A tall panel of the TV-headed host at the centre of the stage: an "
            "ageless showman with a boxy old CRT television for a head, a glowing "
            "screen face, and an immaculate ebony tuxedo with a deep crimson bow "
            "tie. He spreads both arms wide toward the room."
        ),
    },
    {
        "kind": "text",
        "bbox": [120, 780, 460, 900],
        "caption": "Clean horizontal dialogue text in a rounded speech balloon, the tail pointing right.",
        "key": "d2",
    },
    {
        "kind": "text",
        "bbox": [700, 1000, 900, 1120],
        "caption": "Bold comic sound effect lettering.",
        "key": "s1",
    },
    {
        "kind": "text",
        "bbox": [380, 1180, 620, 1260],
        "caption": "Clean horizontal character name tag.",
        "key": "n1",
    },
]


def build(lang: str) -> dict:
    items = []
    for item in ITEMS:
        if item["kind"] == "panel":
            items.append({
                "label": "character" if "young woman" in item["caption"] else "object",
                "caption": item["caption"],
                "bbox": item["bbox"],
            })
        else:
            items.append({
                "label": "text",
                "caption": item["caption"],
                "text": LINES[item["key"]][lang],
                "bbox": item["bbox"],
            })
    return {
        "width": W,
        "height": H,
        "bbox_coord_space": "abs",
        "bbox_format": "xyxy",
        "prefix": "<|artist|>fkey<|/artist|>",
        "summary": {
            "meta": ["comic", "multi_panel", "digital_painting"],
            "canvas": "multi_panel",
            "caption": (
                "High-taste, fully colored 2D digital painting comic with selective "
                "focus: finely rendered layers contrasted against expressive "
                "painterly brushwork. Muted warm peach skin and deep navy palette "
                "under soft bright stage light, zero rough sketch lines."
            ),
        },
        "items": items,
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for lang in ("ko", "en", "ja"):
        # compile_layout reads a draft from disk, so go through a temp file.
        tmp = OUT / f".{lang}.tmp.json"
        tmp.write_text(json.dumps(build(lang), ensure_ascii=False), encoding="utf-8")
        draft = compile_layout.load_draft(tmp)
        tmp.unlink()
        result = compile_layout.compile_layout(draft)
        (OUT / f"{lang}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"  {lang}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
