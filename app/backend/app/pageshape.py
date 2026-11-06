"""What a layout actually does on the page — the facts a page is judged by.

A layout is not a name. It is a set of boxes, and three things about those boxes
decide whether a page works:

  **rows**      how many horizontal strips the page is cut into. Two rows bend the
                RTL S-path once; three bend it twice. One row is not a page, it is
                a column.
  **aspect**    how the panels sit in each row — wide and narrow, or even. A panel
                that is 1:3 or thinner cannot hold a drawing.
  **dominance** whether one panel leads. A scene needs a leader; a procedure page
                needs none; a character page wants an uneven but readable ratio.

Everything here is measured. `page_type` is the two-way split the story asks for
first — even order (`sequence`) or emphasis (`emphasis`) — and the two emphatic
shapes that follow it: `one-big` (one leading panel, the rest quiet) and `intimate`
(barely divided at all).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

STRIP_ASPECT = 0.34          # thinner than this and a panel cannot be drawn


# ------------------------------------------------------------------- geometry
def _box_area(box: list[float]) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def _aspect(box: list[float]) -> float:
    return (box[2] - box[0]) / max(1e-6, box[3] - box[1])


def dominant(layout: dict) -> dict:
    """The leading panel: its share of the page and how far ahead of the second."""
    panels = layout.get("panels", [])
    if not panels:
        return {"n": 0, "share": 0.0, "ratio": 0.0}
    areas = [_box_area(p["bbox"]) for p in panels]
    total = sum(areas) or 1.0
    srt = sorted(areas, reverse=True)
    second = srt[1] if len(srt) > 1 else 0.0
    lead = max(range(len(panels)), key=lambda i: areas[i])
    return {
        "n": panels[lead].get("n", lead + 1),
        "share": round(srt[0] / total, 3),
        "ratio": round(srt[0] / second, 2) if second > 0 else float(srt[0] and 0.0) or 0.0,
    }


def rows(layout: dict) -> int:
    """How many horizontal strips the page is cut into.

    Panels share a top edge when it is within 2% of the page. One strip means
    the page is cut into columns, not rows.
    """
    tops = sorted({round(p["bbox"][1], 3) for p in layout.get("panels", [])})
    if not tops:
        return 0
    count = 1
    for a, b in zip(tops, tops[1:]):
        if b - a >= 0.02:
            count += 1
    return count


def row_shapes(layout: dict) -> list[str]:
    """How each row is divided: `single` (one panel) or `divided`."""
    panels = layout.get("panels", [])
    if not panels:
        return []

    tops = sorted({round(p["bbox"][1], 3) for p in panels})
    rows_found: list[list[float]] = []
    for top in tops:
        boxes = [p["bbox"] for p in panels if round(p["bbox"][1], 3) == top]
        if not rows_found:
            rows_found.append(boxes)
            continue
        prev = rows_found[-1]
        same = abs(boxes[0][1] - prev[0][1]) < 0.02
        if same:
            rows_found[-1].extend(boxes)
        else:
            rows_found.append(boxes)

    out = []
    for boxes in rows_found:
        out.append("single" if len(boxes) == 1 else "divided")
    return out


def page_type(layout: dict) -> str:
    """How the page is cut, from the geometry alone.

    - `single`  one panel carries the page; the rest sit beside it
    - `even`    panels weigh close to the same; the page carries an order

    Dominance is the biggest panel against the second. If the two are near equal
    the page is even, however it is shaped.
    """
    panels = layout.get("panels", [])
    d = dominant(layout)
    if not panels:
        return "even"
    # one panel clearly outweighs the rest: the page has a single subject
    if d["ratio"] >= 1.8 and d["share"] >= 0.35:
        return "single"
    return "even"


def shapes(layout: dict) -> dict:
    panels = layout.get("panels", [])
    return {
        "rows": rows(layout),
        "row_shapes": row_shapes(layout),
        "dominance": dominant(layout),
        "thinnest": round(min(_aspect(p["bbox"]) for p in panels), 2) if panels else 1.0,
        "page_type": page_type(layout),
    }


# ------------------------------------------------------------------ validation
def problems(layout: dict, want: str | None = None) -> list[str]:
    """What is wrong with this layout for a page that wants `want`.

    `want` is the split the story asked for: `even` (an order, panels of
    near-equal weight) or `single` (one subject the page carries). A `single`
    layout on an even page reads as a random blow-up; an `even` layout on a
    single-subject page loses the subject.
    """
    out: list[str] = []
    panels = layout.get("panels", [])
    if len(panels) < 2:
        out.append("컷이 2개 미만입니다")
    if not panels:
        return out

    count = rows(layout)
    if count <= 1 and len(panels) > 1:
        out.append(
            f"가로줄이 1개이고 세로 기둥 {len(panels)}개 — 우측 상단에서 시작하는 "
            "S자 흐름이 없습니다. A4 세로에서 망가진 칸입니다"
        )
    thin = min(_aspect(p["bbox"]) for p in panels)
    if thin < STRIP_ASPECT:
        out.append(
            f"가장 가는 컷이 가로 1 : 세로 {round(1/thin,1)} (가로세로 {thin:.2f}) — "
            "그림이 들어갈 수 없는 줄형입니다"
        )
    for i, p in enumerate(panels, 1):
        bbox = p["bbox"]
        if not (0 <= bbox[0] < bbox[2] <= 1 and 0 <= bbox[1] < bbox[3] <= 1):
            out.append(f"컷 {i} 좌표가 캔버스를 벗어났습니다")

    got = page_type(layout)
    if want == "even" and got == "single":
        out.append(
            "순서·절차 페이지인데 한 컷이 페이지를 지배합니다 — 단조롭게 이어지는 "
            "칸이 필요한 페이지입니다"
        )
    if want == "single" and got == "even":
        out.append(
            "한 주제를 담는 페이지인데 모든 컷이 같은 무게입니다 — 주제를 담은 컷이 "
            "필요한 페이지입니다"
        )
    return out


# --------------------------------------------------------------------- loading
@lru_cache(maxsize=1)
def _catalog() -> dict[str, dict]:
    # the layout library lives with the skills, not the app
    from . import skills

    path = skills.ORIGIN / "manga-craft" / "templates" / "moss-layouts.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    return {l["id"]: l for l in doc["layouts"]}


def load(layout_id: str) -> dict | None:
    return _catalog().get(layout_id)


def judge(layout_id: str, want: str | None = None) -> dict:
    """A verdict on one layout for a page, ready to print or return."""
    layout = load(layout_id)
    if layout is None:
        return {"id": layout_id, "known": False, "problems": ["라이브러리에 없는 id"]}
    return {
        "id": layout_id,
        "known": True,
        "name": layout.get("name_en", ""),
        "want": want,
        "shapes": shapes(layout),
        "problems": problems(layout, want),
    }
