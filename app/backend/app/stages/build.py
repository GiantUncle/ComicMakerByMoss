"""Stage 7's build — the deterministic half of the pipeline.

A model writes the conti (stage 6); the geometry is never the model's job. Here
the conti meets the layout library, the panel boxes come from
`instantiate_layout.py`, the prompt comes from `compile_layout.py` and the
negative from `build_negative.py`. Re-running gives identical output.

Nothing here writes files; the runner does. This module is pure enough that the
derive endpoint can call `build_page` for any language and canvas tier.
"""

from __future__ import annotations

import importlib.util
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .. import skills

FKEY_PREFIX = "<|artist|>fkey<|/artist|>"


def _res(rel: str) -> Path:
    """A skill resource, edited copy first, else the shipped original."""
    edited = skills.EDITED / rel
    return edited if edited.is_file() else skills.ORIGIN / rel


@lru_cache(maxsize=None)
def script(name: str):
    """The skill's own tool, edited copy first, else the shipped original."""
    path = _res(f"manga-craft/scripts/{name}")
    spec = importlib.util.spec_from_file_location(f"mcs_{name.replace('.', '_')}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=1)
def library() -> dict:
    return json.loads(_res("manga-craft/templates/layouts.json").read_text(encoding="utf-8"))


def is_ltr(project: dict[str, Any]) -> bool:
    return project.get("reading_direction") == "ltr"


def tier_size(tier: str) -> tuple[int, int]:
    size = library()["sizes"][tier]
    return size["w"], size["h"]


def instantiate(template_id: str, tier: str, reading: str) -> list[dict]:
    inst = script("instantiate_layout.py")
    lib = library()
    template = inst.find_template(lib, template_id)
    size = inst.size_of(lib, tier)
    return inst.instantiate(template, size, reading)


# ------------------------------------------------- the MOSS layout library
@lru_cache(maxsize=1)
def moss_library() -> dict:
    return json.loads(
        _res("manga-craft/templates/moss-layouts.json").read_text(encoding="utf-8")
    )


def moss_layouts() -> list[dict]:
    return moss_library()["layouts"]


def moss_layout(layout_id: str) -> dict | None:
    return next((x for x in moss_layouts() if x["id"] == layout_id), None)


def is_detail(layout: dict) -> bool:
    """A layout that needs small, detailed cuts — five or more panels, or an inset."""
    return len(layout["panels"]) >= 5 or any(p.get("parent") for p in layout["panels"])


def _aspect(box: list[float]) -> float:
    return (box[2] - box[0]) / max(1e-6, box[3] - box[1])


def min_aspect(layout: dict) -> float:
    """The skinniest panel in a layout, width over height."""
    boxes = layout.get("panels", [])
    return min(_aspect(p["bbox"]) for p in boxes) if boxes else 1.0


def is_strip(layout: dict) -> bool:
    """A layout whose skinniest panel is 1:3 or thinner.

    On an A4-portrait page a 1:3 vertical strip cannot carry a readable drawing —
    the model fills it with a smear. These layouts are withheld from the pick
    lists: they are a failure, not an option.
    """
    return min_aspect(layout) < 0.34


def layout_strip(template_id: str) -> bool:
    """Is a layout id a strip, in either library?"""
    moss = moss_layout(template_id)
    if moss is not None:
        return is_strip(moss)
    return False


def _focus(panels: list[dict]) -> dict | None:
    """The dominant panel: the largest one, its share of the page, and where it sits.

    The strategy of a page is mostly the choice of this panel — a beauty shot of
    the protagonist, or the decisive moment of the story (`comic-planning.md` §11).
    """
    if not panels:
        return None
    areas = [_area_of(p["bbox"]) for p in panels]
    total = sum(areas) or 1.0
    i = max(range(len(panels)), key=lambda k: areas[k])
    return {
        "n": panels[i].get("n", i + 1),
        "share": round(areas[i] / total, 3),
        "position": panels[i].get("position", ""),
    }


def _area_of(box: list[float]) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def moss_layout_summary(detail_panels: bool | None = None) -> list[dict]:
    out = []
    for lay in moss_layouts():
        detail = is_detail(lay)
        out.append({
            "id": lay["id"],
            "name": lay["name"],
            "name_en": lay["name_en"],
            "category": lay["category"],
            "panels": len(lay["panels"]),
            "detail": detail,
            "strip": is_strip(lay),
            "inset": any(p.get("parent") for p in lay["panels"]),
            "focus": _focus(lay["panels"]),
        })
    return out


def pickable_layouts(detail_panels: bool | None = None) -> list[dict]:
    """Layouts the agent may choose: no strip panels, detailed cuts only when
    the project opted in.

    Each entry also carries the **page type** it fits — what the page delivers —
    and the geometry that decides it, because that is what the agent should be
    choosing on (`comic-planning.md` §11, §12).
    """
    out = []
    for m in moss_layout_summary(detail_panels):
        if m["strip"]:
            continue
        lay = moss_layout(m["id"])
        out.append({**m, "page_type": classify(lay)})
    return out


def dominant(lay: dict) -> dict:
    """The page's dominant panel: its share of the page and how far ahead of the
    second panel it is. Both measured, neither guessed."""
    areas = [
        (p["bbox"][2] - p["bbox"][0]) * (p["bbox"][3] - p["bbox"][1])
        for p in lay["panels"]
    ]
    total = sum(areas) or 1.0
    srt = sorted(areas, reverse=True)
    second = srt[1] if len(srt) > 1 else 0.0
    return {
        "share": round(srt[0] / total, 3),
        "ratio": round(srt[0] / second, 2) if second else 0.0,
        "n": lay["panels"][areas.index(srt[0])]["n"],
    }


def classify(lay: dict) -> str:
    """What kind of page this layout is for, from the geometry alone.

    Two ways a page can be cut, and they are measured, not named after a story
    beat — dominance is the largest panel against the second, and share is the
    largest against the page:

    - `single`  one panel carries the page: the subject, seen whole or close.
    - `even`    panels of near-equal weight, in one order.
    """
    d = dominant(lay)
    # two ways a page can be cut, measured from the boxes
    if d["ratio"] >= 1.8:
        return "single"         # one panel carries the page; the rest are beside it
    return "even"               # panels of near-equal weight, in one order


def tier_layout_summary() -> list[dict]:
    """The 13 kata, resolved at M so the dominant panel can be reported too."""
    out = []
    for tpl in library()["templates"]:
        panels = instantiate(tpl["id"], "M", "rtl")
        out.append({
            "id": tpl["id"], "name_en": tpl["name_en"], "name_ja": tpl["name_ja"],
            "panels": len(panels), "tiers": len(tpl["tiers"]),
            "source": "tier", "detail": False,
            "focus": _focus([{"n": p["n"], "bbox": p["bbox"],
                              "position": f"tier {p['tier']}"} for p in panels]),
        })
    return out


def instantiate_moss(layout_id: str, tier: str, reading: str) -> list[dict]:
    """A dataset layout (normalised fractions) -> panels in absolute pixels."""
    lay = moss_layout(layout_id)
    if lay is None:
        raise KeyError(layout_id)
    width, height = tier_size(tier)

    def box(fraction: list[float]) -> list[int]:
        x1, y1, x2, y2 = fraction
        if reading == "ltr":
            x1, x2 = 1 - x2, 1 - x1
        return [round(x1 * width), round(y1 * height), round(x2 * width), round(y2 * height)]

    panels = []
    for p in sorted(lay["panels"], key=lambda x: x["n"]):
        panels.append({
            "n": p["n"],
            "tier": p["n"] - 1,
            "bbox": box(p["bbox"]),
            "content_bbox": box(p.get("content_bbox", p["bbox"])),
            "shape": p.get("shape", "rectangular"),
            "position": p.get("position", ""),
            "parent": p.get("parent"),
        })
    return panels


def panel_boxes(template_id: str, tier: str, reading: str) -> tuple[list[dict], str]:
    """Panels for a layout id, from either library. Returns (panels, kind)."""
    if moss_layout(template_id) is not None:
        return instantiate_moss(template_id, tier, reading), "moss"
    return instantiate(template_id, tier, reading), "tier"


def composition(composition_id: str) -> dict | None:
    doc = json.loads(
        _res("manga-craft/templates/moss-compositions.json").read_text(encoding="utf-8")
    )
    return next((c for c in doc["compositions"] if c["id"] == composition_id), None)


# --------------------------------------------------------------- text captions
def _orientation(vertical: bool) -> str:
    return "vertical" if vertical else "horizontal"


LANG_NAME = {"ko": "Korean", "en": "English", "ja": "Japanese"}


def _lang_word(lang: str | None) -> str:
    """The lettering language, named per item — `prompt-formats.md` §2 / §7.

    `None` leaves it out (the manga build passes none, so its output is unchanged).
    """
    return (LANG_NAME.get(lang or "", "") + " ") if lang else ""


def text_caption(kind: str, bubble: str, vertical: bool, tail: str | None,
                 lang: str | None = None) -> str:
    """The treatment, written as a caption the compiler and preview both read.

    The shape follows the role (`comic-planning.md` §6.0): speech carries a tail to
    the speaker's mouth, narration is a rectangle with no tail, SFX is lettering on
    the art. `lang` names the lettering language so a recompile swaps it.
    """
    o = _orientation(vertical)
    w = _lang_word(lang)
    tail_phrase = f", the tail pointing toward {tail}" if tail else ""
    if kind == "sfx":
        return (f"Bold {w}{o} comic sound effect lettering drawn on the art at the "
                "source of the sound, with a white halo around the letters.")
    if kind == "narration":
        if bubble == "solid":
            return f"Clean {w}{o} narration text in a solid black rectangular box with white lettering, no balloon tail."
        return f"Clean {w}{o} narration text in a plain white rectangular box, no balloon tail."
    if kind == "thought":
        return f"Clean {w}{o} thought text in a cloud-shaped balloon with a dotted outline and no solid tail."
    if kind == "sign":
        return f"Clean {w}{o} signage text painted on the surface of the object."
    if kind == "title":
        return f"Clean {w}{o} title lettering set over the art."
    if bubble == "round":
        return f"Clean {w}{o} dialogue text in a rounded speech balloon{tail_phrase}."
    if bubble == "oval":
        return f"Clean {w}{o} dialogue text in an oval speech balloon{tail_phrase}."
    if bubble == "jagged":
        return f"Clean {w}{o} shouted dialogue text in a jagged balloon{tail_phrase}."
    if bubble == "rect":
        return f"Clean {w}{o} dialogue text in a flat rectangular balloon{tail_phrase}."
    return f"Loose {w}{o} floating lettering on the art, no balloon outline."


def join_lines(entry: dict, lang: str) -> str:
    lines = (entry.get("lines") or {}).get(lang)
    if not lines:
        lines = (entry.get("lines") or {}).get("en") or []
    return "\n".join(lines)


# ------------------------------------------------------------- cast index prose
def cast_index_prose(ids: list[str], characters: dict[str, dict]) -> str:
    """`label: anchor, anchor.` per line — never the name (a prompt draws)."""
    out = []
    for cid in ids:
        card = characters.get(cid)
        if not card:
            continue
        label = card.get("identifier_label") or "the figure"
        terms = [str(a).strip() for a in card.get("anchors", []) if str(a).strip()]
        sig = str(card.get("signature") or "").strip()
        # the signature is often already one of the anchors — do not emit it twice
        if sig and sig.lower() not in ", ".join(terms).lower():
            terms.append(sig)
        out.append(f"{label}: {', '.join(terms)}.")
    return "\n".join(out)


# ------------------------------------------------------------------ the build
def build_page(
    conti: dict[str, Any],
    project: dict[str, Any],
    characters: dict[str, dict],
    lang: str,
    tier_override: str | None = None,
) -> dict[str, Any]:
    """A conti plus the layout library -> a compile_layout draft (abs/xyxy)."""
    layout = conti.get("layout") or {}
    template_id = layout.get("template_id") or "DAN3"
    tier = tier_override or layout.get("size_tier") or project.get("canvas", {}).get("tier", "M")
    reading = layout.get("reading") or project.get("reading_direction", "rtl")

    panels, kind = panel_boxes(template_id, tier, reading)
    width, height = tier_size(tier)

    # map conti panels onto layout panels: the dataset layouts read in order,
    # the tier templates group by tier
    by_tier: dict[int, list[dict]] = {}
    counters: dict[int, int] = {}
    order = sorted(panels, key=lambda p: p["n"])
    if kind == "tier":
        for p in panels:
            by_tier.setdefault(p["tier"], []).append(p)

    cl = script("compile_layout.py")
    items: list[dict[str, Any]] = []
    present: list[str] = []
    assigned: dict[int, dict] = {}     # conti panel n -> layout panel
    placed = 0

    for cp in sorted(conti.get("panels", []), key=lambda p: p.get("n", 0)):
        if kind == "moss":
            lp = order[placed] if placed < len(order) else order[-1]
            placed += 1
        else:
            t = int(cp.get("tier", 0))
            row = by_tier.get(t) or panels
            i = counters.get(t, 0)
            counters[t] = i + 1
            lp = row[i] if i < len(row) else row[-1]
        assigned[int(cp.get("n", placed))] = lp

        caption = str(cp.get("beat", "")).strip()
        anchor = cp.get("anchor_of")
        if anchor:
            card = characters.get(anchor)
            if card and card.get("descriptor"):
                caption = f"{caption} {card['descriptor']}".strip()
        shape = lp.get("shape", "rectangular")
        tags: list[str] = []
        if shape and shape != "rectangular":
            caption = f"A {shape} manga panel. {caption}".strip()
            # a slanted/oval panel's bounding box may overlap a neighbour's; the
            # tag tells the validator this rectangle is a stand-in for a polygon
            tags = [f"shape:{shape}"]
        item: dict[str, Any] = {
            "label": "character" if anchor else "object",
            "caption": caption,
            "bbox": list(lp["bbox"]),
            # wiring key for stage 8: which conti panel this box is. `note` is
            # dropped at compile time, so it never reaches the prompt.
            "note": f"panel-{int(cp.get('n', len(items) + 1))}",
        }
        if tags:
            item["tags"] = tags
        if anchor:
            item["ref_id"] = anchor
        items.append(item)
        for cid in cp.get("characters", []):
            if cid not in present:
                present.append(cid)

    # text items, placed per §5
    for entry in sorted(conti.get("texts", []), key=lambda e: e.get("id", "")):
        body = join_lines(entry, lang)
        if not body.strip():
            continue
        vertical = bool(entry.get("vertical"))
        bbox = _text_bbox(entry, assigned, width, height, body, vertical, cl)
        if bbox is None:
            continue
        items.append({
            "label": "text",
            "caption": text_caption(
                entry.get("kind", "dialogue"),
                entry.get("bubble", "round"),
                vertical,
                entry.get("tail"),
            ),
            "text": body,
            "bbox": bbox,
            # wiring key: stage 8 keys its lettering captions by this id, and
            # compile_layout drops it before the prompt is written
            "ref_id": entry.get("id"),
        })

    style = str(conti.get("style", "")).strip()
    index = conti.get("cast_index")
    if index:
        index_prose = "\n".join(
            f"{c.get('label', 'the figure')}: {', '.join(c.get('anchors', []))}."
            for c in index
        )
    else:
        index_prose = cast_index_prose(present, characters)
    caption = style if not index_prose else f"{style}\n{index_prose}"

    draft: dict[str, Any] = {
        "width": width,
        "height": height,
        "bbox_coord_space": "abs",
        "bbox_format": "xyxy",
        "summary": {
            "meta": ["comic", "multi_panel", "digital_painting"],
            "canvas": "multi_panel",
            "caption": caption.strip(),
        },
        "items": items,
    }
    if str(project.get("art_style", "")).startswith("fkey"):
        draft["prefix"] = FKEY_PREFIX
    return draft


def panel_geometry_key(sheet: dict) -> str:
    """A stable key for a sheet's drawn boxes.

    The artist's captions are written against the panel boxes, not against the
    lettering boxes: re-sizing a text box does not invalidate the drawing, while
    moving a panel does. Stage 9 compares this key instead of file times.
    """
    import hashlib

    parts = [f"{sheet.get('width')}x{sheet.get('height')}"]
    for it in sheet.get("items", []):
        if it.get("label") == "text":
            continue
        box = it.get("bbox")
        if isinstance(box, list) and len(box) == 4:
            parts.append(",".join(str(round(float(v))) for v in box))
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:16]


def _font_floor(height: int) -> float:
    """The smallest letter size that still reads at this canvas height."""
    return max(9.0, 11.0 * height / 1536)


def _text_bbox(entry, assigned, width, height, body, vertical, cl):
    """A box the lettering can actually be read in.

    The conti's box is taken only when the text already fits it at a readable
    size. A box too small for its own words is not a box — it would render the
    line at 9 px, so the words are re-boxed at a comfortable size instead. The
    new box starts inside its panel and grows out to the canvas when the panel
    cannot hold it (narration may sit over the art; a box may not leave the
    page).
    """
    floor = _font_floor(height)
    edge = max(28.0, height * 0.02)   # the compiler wants lettering off the edge
    raw = entry.get("bbox")
    if isinstance(raw, list) and len(raw) == 4:
        x1, y1, x2, y2 = raw
        inside = (edge <= x1 < x2 <= width - edge) and (edge <= y1 < y2 <= height - edge)
        if inside and cl.implied_font_size(x2 - x1, y2 - y1, body, vertical) >= floor:
            return [x1, y1, x2, y2]

    lp = assigned.get(entry.get("panel_ref")) or (next(iter(assigned.values())) if assigned else None)
    base = (lp or {}).get("content_bbox") or (lp or {}).get("bbox") or [0, 0, width, height]

    font = max(height / 70.0, floor * 1.25)
    need_w, need_h = cl.required_box(body, vertical, font)
    pad = font * 0.6
    # the compiler wants lettering off the canvas edge by a margin
    margin = max(28.0, pad)
    w = min(need_w + pad * 2, width - margin * 2)
    h = min(need_h + pad * 2, height - margin * 2)
    bx1, by1, bx2, by2 = base
    x1 = bx1 + ((bx2 - bx1) - w) / 2
    y1 = by1 + pad
    # keep the whole box on the canvas; a panel too small lets it grow outward
    x1 = max(margin, min(x1, width - w - margin))
    y1 = max(margin, min(y1, height - h - margin))
    return [round(x1), round(y1), round(x1 + w), round(y1 + h)]


# --------------------------------------------------------------- compilation
def compile_draft(draft: dict[str, Any]) -> str:
    """Validate a draft and return the prompt text (with the trigger line)."""
    cl = script("compile_layout.py")
    tmp = _tmp("compile")
    tmp.write_text(json.dumps(draft, ensure_ascii=False), encoding="utf-8")
    try:
        normalized = cl.load_draft(tmp)
    finally:
        tmp.unlink(missing_ok=True)
    result = cl.compile_layout(normalized)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if normalized.get("prefix"):
        # the reference form is the trigger, then a LITERAL \n (two characters),
        # then the JSON — see verified-examples.md, "Trigger"
        payload = normalized["prefix"] + "\\n" + payload
    return payload


def compile_sections(draft: dict[str, Any]) -> str:
    """A Type B draft -> a sectioned prompt (docs/reference-prompts/B-*).

    The trigger line is first, followed by a **literal** `\\n` (the reference
    samples use the two characters, not a newline). Then the style section, then
    one section per region. No JSON, no boxes.
    """
    artist = str(draft.get("artist") or "fkey").strip()
    style = str(draft.get("style_and_aesthetic", "")).strip()
    parts = [f"<|artist|>{artist}<|/artist|>\\n"]
    parts.append(f"<|style_and_aesthetic|>{style}<|/style_and_aesthetic|>")
    for s in draft.get("sections", []):
        name = str(s.get("name", "")).strip()
        cap = str(s.get("caption", "")).strip()
        if not name:
            continue
        parts.append(f"<|{name}|>{cap}<|/{name}|>")
    return "\n".join(parts)


def _frame_bbox(width: int, height: int, box: Any = None) -> list[int]:
    """The single-frame item's box — the model's, or most of the canvas."""
    if isinstance(box, list) and len(box) == 4:
        return [round(v) for v in box]
    mx, my = width * 0.04, height * 0.04
    return [round(mx), round(my), round(width - mx), round(height - my)]


def _default_text_box(body: str, vertical: bool, width: int, height: int, slot: int) -> list[int]:
    """A safe box for a line the scene did not place."""
    cl = script("compile_layout.py")
    font = max(11.0, height / 70)
    need_w, need_h = cl.required_box(body, vertical, font)
    pad = font * 0.6
    w = min(need_w + pad * 2, width * 0.6)
    h = min(need_h + pad * 2, height * 0.3)
    x1 = width * 0.06 + (slot % 2) * width * 0.28
    y1 = height * 0.06 + (slot // 2) * h
    x1 = min(x1, width - w - 8)
    y1 = min(y1, height - h - 8)
    return [round(x1), round(y1), round(x1 + w), round(y1 + h)]


def compile_single_frame(
    scene: dict[str, Any],
    project: dict[str, Any],
    characters: dict[str, dict],
    lang: str,
    tier_override: str | None = None,
) -> dict[str, Any]:
    """A comic scene -> a Type C draft: one still frame plus its lettering.

    A comic page is a single frame (`summary.canvas: "single"`), so there are no
    panel boxes to instantiate — the frame is the whole picture and the scene
    describes what is drawn inside it. Text boxes come from the scene, or are
    placed safely inside the frame.

    **Identity is described, never labelled.** A figure's FULL description appears
    exactly once per page (`reference-prompts/README.md` R-A), and a comic page
    is one frame — so that frame always carries the character's full `descriptor`.
    The `summary.caption` also carries the cast total (`authoring-spec.md` §10.6.7,
    §10.7). A bare `identifier_label` or `ref_id` never stands in for a person.
    """
    tier = tier_override or project.get("canvas", {}).get("tier", "M")
    width, height = tier_size(tier)

    style = str(scene.get("style", "")).strip()
    texts = scene.get("texts", []) or []

    # Who is drawn on this frame, lead first. `characters` is the frame's cast;
    # `anchor_of` names the lead. Falls back to the speakers when neither is
    # given. R-A: EVERY character on the page gets their FULL description once,
    # and R-D: every one of them enters the cast index.
    present: list[str] = []
    for cid in (scene.get("characters") or []):
        if cid and cid not in present:
            present.append(cid)
    anchor = scene.get("anchor_of")
    if anchor and anchor not in present:
        present.insert(0, anchor)
    if not present:
        for t in texts:
            sp = t.get("speaker")
            if sp and sp not in present:
                present.append(sp)
    if anchor in present:
        present.remove(anchor)
        present.insert(0, anchor)
    present = [c for c in present if c in characters] or present

    index_prose = cast_index_prose(present, characters)
    caption = style if not index_prose else f"{style}\n{index_prose}"

    scene_text = str(scene.get("scene", "")).strip()
    # each present figure's canonical descriptor, lead first; §9 keeps its
    # `Apparent age group:` head at the head, and the scene/action follows.
    descs = [
        str(characters[c]["descriptor"]).strip()
        for c in present
        if characters.get(c, {}).get("descriptor")
    ]
    head = " ".join(descs)
    frame_cap = f"{head} {scene_text}".strip() if head else scene_text
    # any figure on the page makes it a `character` frame
    label = "character" if present else (scene.get("label") or "object")

    frame_item: dict[str, Any] = {
        "label": label,
        "caption": frame_cap,
        "bbox": _frame_bbox(width, height, scene.get("frame_bbox")),
    }
    if anchor:
        frame_item["ref_id"] = anchor
    items: list[dict[str, Any]] = [frame_item]

    for t in sorted(texts, key=lambda e: e.get("id", "")):
        body = join_lines(t, lang)
        if not body.strip():
            continue
        vertical = bool(t.get("vertical"))
        bbox = t.get("bbox")
        if not (isinstance(bbox, list) and len(bbox) == 4):
            bbox = _default_text_box(body, vertical, width, height, len(items))
        # R-C: a tail points at the character's identifier label, never the raw
        # card id — a slug is not a description.
        tail_id = t.get("tail")
        tail_label = (characters.get(tail_id) or {}).get("identifier_label") or tail_id
        items.append({
            "label": "text",
            "caption": text_caption(
                t.get("kind", "dialogue"), t.get("bubble", "round"), vertical, tail_label, lang,
            ),
            "text": body,
            "bbox": [round(v) for v in bbox],
            "ref_id": t.get("id"),
        })

    draft: dict[str, Any] = {
        "width": width,
        "height": height,
        "bbox_coord_space": "abs",
        "bbox_format": "xyxy",
        "summary": {
            "meta": ["comic", "single", "digital_painting"],
            "canvas": "single",
            "caption": caption.strip(),
        },
        "items": items,
    }
    if str(project.get("art_style", "")).startswith("fkey"):
        draft["prefix"] = FKEY_PREFIX
    return draft


def check_draft(draft: dict[str, Any]) -> list[str]:
    """Validation issues, from load_draft and the geometry report."""
    cl = script("compile_layout.py")
    tmp = _tmp("check")
    tmp.write_text(json.dumps(draft, ensure_ascii=False), encoding="utf-8")
    try:
        normalized = cl.load_draft(tmp)
    except ValueError as e:
        return [str(e)]
    finally:
        tmp.unlink(missing_ok=True)
    report = cl.build_report(normalized, "layout")
    return [
        line.strip()[2:]
        for line in report.splitlines()
        if line.strip().startswith("! ")
    ]


def negative(style: str, age: str = "adult") -> str:
    bn = script("build_negative.py")
    texture = bn.TEXTURE_SETS.get(style, bn.TEXTURE_PAINTERLY)
    age_body = bn.AGE_SETS.get(age, bn.AGE_ADULT)
    return "\n".join([
        bn.wrap("texture_and_style_neg", texture),
        bn.wrap("age_and_body_neg", age_body),
        bn.wrap("universal_anatomy_neg", bn.ANATOMY),
    ])


def negative_style(project: dict[str, Any]) -> str:
    return "clean" if str(project.get("art_style", "")).startswith("fkey_clean") else "painterly"


# --------------------------------------------------------------------- temp
def _tmp(tag: str) -> Path:
    import os
    import tempfile

    fd, name = tempfile.mkstemp(prefix=f"cm-{tag}-", suffix=".json")
    os.close(fd)
    return Path(name)
