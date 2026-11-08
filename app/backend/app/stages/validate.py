"""Deterministic validation — the scripts decide, not the model.

Two things are checked, at every stage:

- **Structure.** Only the fields the schema defines, and every field the schema
  requires. A compiled prompt carries no wiring key: `ref_id` is dropped at
  compile time, so finding one means the build skipped a step.
- **Geometry.** The one rule a comic cannot bend: **panel boxes never overlap.**
  Balloons and lettering may sit over each other and over a panel, but two コマ
  cannot share a pixel. Boxes must also stay inside the canvas and be big enough
  to hold their lettering.

Every problem is a machine-readable issue, so the runner can hand the list
straight back to the model and ask for a fix — the stage is not done until the
errors are gone.
"""

from __future__ import annotations

import re
from typing import Any

from .. import pageshape
from . import build

LABELS = ("object", "character", "text", "panel", "subject")
DRAWN = ("object", "character", "panel", "subject")
DRAFT_ITEM_FIELDS = {
    "label", "caption", "bbox", "text", "tags", "palette",
    "note", "identity", "salience", "colors", "ref_id",
}
PROMPT_ITEM_FIELDS = {"label", "caption", "bbox", "text", "tags", "palette"}
KINDS = ("dialogue", "narration", "sfx", "thought", "sign", "title")
STRATEGIES = ("routine", "thought", "character", "space", "pair", "ensemble")
BUBBLES = ("round", "jagged", "rect", "oval", "none", "solid")
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
STYLE_WORDS = (
    "gouache", "watercolor", "watercolour", "lineart", "line art", "painterly",
    "3d render", "cgi", "photograph", "cel shading", "brushwork",
)

# An overlap smaller than this is treated as boxes merely touching.
OVERLAP_ABS = 400.0
OVERLAP_FRACTION = 0.02


def issue(level: str, code: str, where: str, message: str) -> dict:
    return {"level": level, "code": code, "where": where, "message": message}


def errors(issues: list[dict]) -> list[dict]:
    return [i for i in issues if i["level"] == "error"]


def warnings(issues: list[dict]) -> list[dict]:
    return [i for i in issues if i["level"] == "warning"]


def _min_font(height: int) -> float:
    return max(9.0, 11.0 * height / 1536)


def _overlap(a: list[float], b: list[float]) -> float:
    x = min(a[2], b[2]) - max(a[0], b[0])
    y = min(a[3], b[3]) - max(a[1], b[1])
    return max(0.0, x) * max(0.0, y)


def _area(box: list[float]) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def _encloses(outer: list[float], inner: list[float]) -> bool:
    """True when `inner` sits entirely inside a strictly larger `outer`."""
    return (
        _area(outer) > _area(inner)
        and outer[0] <= inner[0] and outer[1] <= inner[1]
        and outer[2] >= inner[2] and outer[3] >= inner[3]
    )


def _is_inset(a: list[float], b: list[float]) -> bool:
    """A declared inset: one panel floats inside another. The one legal overlap."""
    return _encloses(a, b) or _encloses(b, a)


def _overlaps_matter(a: list[float], b: list[float]) -> bool:
    area = _overlap(a, b)
    if area <= 0:
        return False
    smallest = min(_area(a), _area(b))
    return area > OVERLAP_ABS and area > smallest * OVERLAP_FRACTION


# ------------------------------------------------------------------ items core
def _check_bbox(box: Any, width: int, height: int) -> str | None:
    if not isinstance(box, list) or len(box) != 4:
        return "bbox must be [x1, y1, x2, y2]"
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in box):
        return "bbox must be four numbers"
    x1, y1, x2, y2 = box
    if not (x1 < x2 and y1 < y2):
        return "bbox must have positive width and height"
    if not (0 <= x1 and 0 <= y1 and x2 <= width and y2 <= height):
        return f"bbox {box} escapes the {width}x{height} canvas"
    return None


def _check_items(
    items: list[dict],
    width: int,
    height: int,
    project: dict | None,
    *,
    compiled: bool,
) -> list[dict]:
    out: list[dict] = []
    allowed = PROMPT_ITEM_FIELDS if compiled else DRAFT_ITEM_FIELDS
    cl = build.script("compile_layout.py")
    min_font = _min_font(height)

    for i, item in enumerate(items):
        where = f"items[{i}]"
        if not isinstance(item, dict):
            out.append(issue("error", "item.not-object", where, "item must be an object"))
            continue

        unknown = set(item) - allowed
        if unknown:
            out.append(issue("error", "item.unknown-field", where,
                             f"unknown field(s) {sorted(unknown)}"))
        if compiled and "ref_id" in item:
            out.append(issue("error", "item.ref-id-leaked", where,
                             "compiled prompts carry no ref_id — the build must drop it"))

        label = item.get("label")
        if label not in LABELS:
            out.append(issue("error", "item.bad-label", where, f"label {label!r} is not one of {LABELS}"))
        cap_text = str(item.get("caption", ""))
        if not cap_text.strip():
            out.append(issue("error", "item.no-caption", where, "caption is empty"))
        # style belongs to the summary; a caption says what this box draws
        leaked = [w for w in STYLE_WORDS if w in cap_text.lower()]
        if leaked:
            out.append(issue("warning", "item.style-in-caption", where,
                             f"caption carries style words {leaked} — style lives in the summary "
                             "(prompt-formats.md §2)"))

        box_err = _check_bbox(item.get("bbox"), width, height)
        if box_err:
            out.append(issue("error", "item.bad-bbox", where, box_err))
            continue

        if label == "text":
            body = item.get("text")
            if not isinstance(body, str) or not body.strip():
                out.append(issue("error", "item.text-empty", where, "a text item needs lettering"))
            else:
                x1, y1, x2, y2 = item["bbox"]
                vertical = (y2 - y1) > (x2 - x1) * 1.15
                font = cl.implied_font_size(x2 - x1, y2 - y1, body, vertical)
                if font < min_font:
                    out.append(issue("warning", "item.text-too-small", where,
                                     f"lettering renders at ~{font:.0f}px (need >= {min_font:.0f}px)"))

    # the rule: panel boxes never overlap each other
    panels = [(i, it) for i, it in enumerate(items)
              if isinstance(it, dict) and it.get("label") in DRAWN and isinstance(it.get("bbox"), list)]
    def non_rect(it: dict) -> bool:
        """A diagonal/oval panel: its box is a stand-in, so its polygon may meet a
        neighbour. The dataset marks these; the tag survives compilation."""
        return any(
            str(t).startswith("shape:") and t != "shape:rectangular"
            for t in it.get("tags", [])
        )

    for a in range(len(panels)):
        for b in range(a + 1, len(panels)):
            ia, pa = panels[a]
            ib, pb = panels[b]
            if non_rect(pa) or non_rect(pb):
                continue
            if _overlaps_matter(pa["bbox"], pb["bbox"]) and not _is_inset(pa["bbox"], pb["bbox"]):
                pct = _overlap(pa["bbox"], pb["bbox"]) / min(_area(pa["bbox"]), _area(pb["bbox"])) * 100
                out.append(issue("error", "panels.overlap", f"items[{ia}]∩items[{ib}]",
                                 f"panel boxes overlap by {pct:.0f}% — コマ must never overlap. "
                                 "The only legal overlap is an inset, one panel inside another"))

    if project:
        lo = project.get("panels", {}).get("min", 1)
        hi = project.get("panels", {}).get("max", 8)
        n = len(panels)
        if not (lo <= n <= hi):
            out.append(issue("warning", "page.panel-count", "items",
                             f"{n} panels outside the project range {lo}..{hi}"))
        if n >= 5 and not project.get("detail_panels", False):
            out.append(issue("warning", "page.detail-cuts", "items",
                             f"{n} panels — five or more means small, detailed cuts, which "
                             "the model draws poorly. Turn on detailed cuts to allow this"))
    return out


# ------------------------------------------------------------------- surfaces
def validate_draft(draft: dict, project: dict | None = None) -> list[dict]:
    out: list[dict] = []
    width, height = draft.get("width"), draft.get("height")
    if not (isinstance(width, int) and isinstance(height, int) and width > 0 and height > 0):
        return [issue("error", "canvas.bad", "draft", "draft needs integer width and height")]
    if width % 16 or height % 16:
        out.append(issue("error", "canvas.not-multiple-16", "draft",
                         f"{width}x{height} must be a multiple of 16"))
    summary = draft.get("summary") or {}
    if not str(summary.get("caption", "")).strip():
        out.append(issue("error", "summary.no-caption", "summary", "summary.caption is empty"))
    items = draft.get("items")
    if not isinstance(items, list) or not items:
        return out + [issue("error", "items.empty", "draft", "items must be a nonempty array")]
    out += _check_items(items, width, height, project, compiled=False)
    return out


def validate_prompt(prompt: dict, width: int, height: int, project: dict | None = None) -> list[dict]:
    """Validate a compiled prompt (abs_centralized / yxyx)."""
    out: list[dict] = []
    summary = prompt.get("summary") or {}
    if not str(summary.get("caption", "")).strip():
        out.append(issue("error", "summary.no-caption", "summary", "summary.caption is empty"))
    if prompt.get("bbox_coord_space") != "abs_centralized" or prompt.get("bbox_format") != "yxyx":
        out.append(issue("error", "prompt.coord-space", "prompt",
                         "compiled prompts must be abs_centralized / yxyx"))
    items = prompt.get("items")
    if not isinstance(items, list) or not items:
        return out + [issue("error", "items.empty", "prompt", "items must be a nonempty array")]

    # centred yxyx -> absolute xyxy so the geometry checks read the same space
    absolute = []
    for it in items:
        box = it.get("bbox") if isinstance(it, dict) else None
        if isinstance(box, list) and len(box) == 4:
            y1, x1, y2, x2 = box
            absolute.append({**it, "bbox": [x1 + width / 2, y1 + height / 2,
                                            x2 + width / 2, y2 + height / 2]})
        else:
            absolute.append(it)
    out += _check_items(absolute, width, height, project, compiled=True)
    return out


# -------------------------------------------------------------------- conti
def _layout_panel_count(template_id: str | None) -> int | None:
    """Panels a layout id lays out, from either library; None if unknown."""
    if not template_id:
        return None
    for tpl in build.library()["templates"]:
        if tpl["id"] == template_id:
            return sum(len(tier["panels"]) for tier in tpl["tiers"])
    moss = build.moss_layout(template_id)
    if moss is not None:
        return len(moss["panels"])
    return None


def _tier_size(tier: str) -> tuple[int, int] | None:
    sizes = build.library()["sizes"]
    if tier not in sizes:
        return None
    return sizes[tier]["w"], sizes[tier]["h"]


def validate_conti(conti: dict, project: dict) -> list[dict]:
    out: list[dict] = []
    where = f"page {conti.get('page', '?')}"

    if not str(conti.get("story_job", "")).strip():
        out.append(issue("error", "conti.no-story-job", where, "story_job is empty"))

    layout = conti.get("layout") or {}
    template_id = layout.get("template_id")
    tier = layout.get("size_tier") or project.get("canvas", {}).get("tier", "M")
    size = _tier_size(tier)
    if size is None:
        out.append(issue("error", "conti.bad-tier", where, f"unknown size tier {tier!r}"))
    if layout.get("reading") not in ("rtl", "ltr"):
        out.append(issue("error", "conti.bad-reading", where, "reading must be rtl or ltr"))

    panels = conti.get("panels")
    if not isinstance(panels, list) or not panels:
        return out + [issue("error", "conti.no-panels", where, "panels must be a nonempty array")]

    want = _layout_panel_count(template_id)
    if want is None:
        out.append(issue("error", "conti.bad-template", where,
                         f"layout {template_id!r} is not in either library"))
    elif want != len(panels):
        out.append(issue("error", "conti.panel-mismatch", where,
                         f"layout {template_id} lays out {want} panels but the conti has {len(panels)}"))
    else:
        layout = pageshape.load(template_id)
        if layout is not None:
            # what the plan asked the page to do, and what the layout actually does
            for problem in pageshape.problems(layout, conti.get("split")):
                out.append(issue("error", "layout.wrong-shape", where, problem))

    lo = project.get("panels", {}).get("min", 1)
    hi = project.get("panels", {}).get("max", 8)
    if not (lo <= len(panels) <= hi):
        out.append(issue("error", "conti.panel-count", where,
                         f"{len(panels)} panels outside the project range {lo}..{hi}"))

    band: dict[str, int] = {}
    panel_numbers = set()
    for i, panel in enumerate(panels):
        pw = f"{where}/panels[{i}]"
        n = panel.get("n")
        panel_numbers.add(n)
        if not str(panel.get("beat", "")).strip():
            out.append(issue("error", "conti.panel-no-beat", pw, "panel beat is empty"))
        if not isinstance(panel.get("tier"), int):
            out.append(issue("error", "conti.panel-no-tier", pw, "panel needs an integer tier"))
        anchor = panel.get("anchor_of")
        if anchor:
            band[anchor] = band.get(anchor, 0) + 1
    for cid, count in band.items():
        if count != 1:
            out.append(issue("error", "conti.anchor-count", where,
                             f"{cid} has {count} anchor panels (need exactly one)"))
    # the anchor panel is where the figure is fully drawn: a part-only frame
    # (extreme close-up, insert) cannot hold a whole person
    for i, panel in enumerate(panels):
        if panel.get("anchor_of") and str(panel.get("shot", "")) in ("extreme_close", "insert"):
            out.append(issue("error", "conti.anchor-on-part-shot", f"{where}/panels[{i}]",
                             f"{panel['anchor_of']} is anchored on a {panel['shot']} frame — "
                             "anchor a character where the whole figure is in frame"))

    texts = conti.get("texts", [])
    seen_ids = set()
    for i, text in enumerate(texts):
        tw = f"{where}/texts[{i}]"
        tid = text.get("id")
        if tid in seen_ids:
            out.append(issue("error", "conti.dup-text-id", tw, f"duplicate text id {tid!r}"))
        seen_ids.add(tid)
        if text.get("kind") not in KINDS:
            out.append(issue("error", "conti.bad-kind", tw, f"kind {text.get('kind')!r} is not one of {KINDS}"))
        if text.get("bubble") not in BUBBLES:
            out.append(issue("error", "conti.bad-bubble", tw, f"bubble {text.get('bubble')!r} is not one of {BUBBLES}"))
        if text.get("panel_ref") not in panel_numbers:
            out.append(issue("error", "conti.bad-panel-ref", tw,
                             f"panel_ref {text.get('panel_ref')!r} matches no panel"))
        lines = text.get("lines") or {}
        lengths = {}
        for lang in ("ko", "en", "ja"):
            value = lines.get(lang)
            if not isinstance(value, list) or not value:
                out.append(issue("error", "conti.missing-lang", tw, f"lines.{lang} is missing"))
                lengths[lang] = 0
            else:
                lengths[lang] = len(value)
        served = {v for v in lengths.values() if v}
        if len(served) > 1:
            out.append(issue("error", "conti.line-count", tw, f"line counts differ across languages {lengths}"))
        box = text.get("bbox")
        if box is None:
            out.append(issue("warning", "conti.no-text-box", tw,
                             "no bbox — the build will place this line in its panel"))
        elif size is not None:
            err = _check_bbox(box, size[0], size[1])
            if err:
                out.append(issue("error", "conti.text-box-off-canvas", tw,
                                 f"{err} — move the whole box inside the canvas"))

    return out


# ------------------------------------------------------------------ episode
def validate_episode(contis: list[dict], project: dict | None = None) -> list[dict]:
    """Rules that hold across the pages of one episode, not inside one page.

    A layout is used on one page only. Two pages sharing a layout means the
    reader turns the page and sees the same boxes again.
    """
    out: list[dict] = []
    seen: dict[str, int] = {}
    for conti in contis:
        page = int(conti.get("page", 0))
        where = f"page {page or '?'}"
        tpl = (conti.get("layout") or {}).get("template_id")
        if not tpl:
            out.append(issue("error", "episode.no-layout", where,
                             "page has no layout.template_id"))
            continue
        if tpl in seen:
            out.append(issue("error", "episode.repeat-layout", where,
                             f"layout {tpl} is also on page {seen[tpl]} — "
                             "a layout is used on one page of the episode only"))
        else:
            seen[tpl] = page
    return out


# ------------------------------------------------------------------ artwork
# Stage 8 is the artist: it rewrites the page as a drawing. It must not fall
# back to the conti's own words, must not name the panel's position (the box
# already says it, authoring-spec §10.1), and must not carry coordinates.
POSITION_PREFIX = re.compile(
    r"^(top|upper|bottom|lower|middle|main|center|centre|left|right)[ -]",
    re.IGNORECASE,
)
COORDINATE_IN_CAPTION = re.compile(r"\[\s*-?\d")


PART_ONLY = re.compile(
    r"extreme close-up|isolates the|inset panel|only the (?:hand|hands|eyes|mouth|face|fingers)",
    re.IGNORECASE,
)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def validate_artwork(art: dict, conti: dict, characters: dict | None = None) -> list[dict]:
    out: list[dict] = []
    page = conti.get("page", "?")
    where = f"page {page}"

    if int(art.get("page", 0) or 0) != int(page or 0):
        out.append(issue("error", "art.missing-page", where,
                         f"artwork says page {art.get('page')!r} — it must be page {page}"))
    summary = str(art.get("summary_caption", "")).strip()
    if not summary:
        out.append(issue("error", "art.no-summary", where,
                         "summary_caption is empty — the page needs its art direction"))
    elif not re.search(r"balloon|lettering|speech|dialogue text", summary, re.IGNORECASE):
        out.append(issue("error", "art.summary-no-lettering-clause", where,
                         "the summary does not say how the lettering is rendered "
                         "(Type A: 'crisp ... dialogue text in clean speech bubbles')"))
    if summary and not re.search(r"\b(?:skin|complexion|flesh)\b", summary, re.IGNORECASE):
        out.append(issue("warning", "art.summary-no-skin", where,
                         "the summary does not state the figures' skin tone "
                         "(Type A: 'warm peach skin', 'smooth creamy skin tones')"))

    want_panels = {int(p.get("n", 0)) for p in conti.get("panels", [])}
    beat_of = {int(p.get("n", 0)): str(p.get("beat", "")).strip() for p in conti.get("panels", [])}
    seen_panels: set[int] = set()
    for i, p in enumerate(art.get("panels", [])):
        pw = f"{where}/panels[{i}]"
        n = int(p.get("n", 0) or 0)
        caption = str(p.get("caption", "")).strip()
        if not caption:
            out.append(issue("error", "art.empty-caption", pw, "panel caption is empty"))
            continue
        seen_panels.add(n)
        if n not in want_panels:
            out.append(issue("warning", "art.extra-panel", pw,
                             f"panel {n} is not in the conti ({sorted(want_panels)})"))
        if POSITION_PREFIX.match(caption):
            out.append(issue("warning", "art.position-prefix", pw,
                             "caption opens with a panel position — the box already says where"))
        if COORDINATE_IN_CAPTION.search(caption):
            out.append(issue("warning", "art.coordinates-in-caption", pw,
                             "caption carries coordinates — those live in the box"))
        if beat_of.get(n) and caption == beat_of[n]:
            out.append(issue("warning", "art.conti-copied", pw,
                             "caption is the conti's beat verbatim — the artist rewrites the page"))
        leaked = [w for w in STYLE_WORDS if w in caption.lower()]
        if leaked:
            out.append(issue("error", "art.style-in-caption", pw,
                             f"caption names the medium or technique {leaked} — style belongs to the "
                             "summary; a caption says what this panel draws"))
        neg = re.findall(r"\bno\s+(?:hair|skin tone|headwear|accessories|makeup|shoes)\b",
                         caption, re.IGNORECASE)
        if neg:
            out.append(issue("error", "art.negative-phrasing", pw,
                             f"caption says what is missing {neg} — write what is there "
                             "(authoring-spec.md §11.4)"))
    for n in sorted(want_panels - seen_panels):
        out.append(issue("error", "art.panel-missing", where, f"no caption for panel {n}"))

    # R-A: one full descriptor per character, on the panel that anchors them,
    # and the signature attribute stated once on the page.
    if characters:
        anchors: dict[str, int] = {}
        for p in conti.get("panels", []):
            cid = p.get("anchor_of")
            if cid:
                anchors[str(cid)] = int(p.get("n", 0))
        by_n = {int(p.get("n", 0)): str(p.get("caption", "")) for p in art.get("panels", [])}
        for cid, n in anchors.items():
            card = characters.get(cid) or {}
            desc = _norm(card.get("descriptor", ""))
            cap = _norm(by_n.get(n, ""))
            if desc and desc not in cap:
                out.append(issue("error", "art.anchor-not-verbatim", f"{where}/panels[{n}]",
                                 f"the panel anchoring {cid} must carry its cast descriptor word for "
                                 "word (character-consistency.md R-A)"))
            if PART_ONLY.search(cap):
                out.append(issue("error", "art.anchor-on-part-frame", f"{where}/panels[{n}]",
                                 f"panel {n} is a part-only frame but it anchors {cid} — a part frame "
                                 "is an object that shows only its part, and the full descriptor "
                                 "belongs on the frame where the figure is the subject"))
            sig = _norm(card.get("signature", ""))
            if sig:
                n_hits = sum(1 for cap2 in by_n.values() if sig in _norm(cap2))
                if n_hits > 1:
                    out.append(issue("error", "art.signature-repeated", where,
                                     f"the signature {sig!r} is stated {n_hits} times — an attribute "
                                     "is stated once on the page"))

        # a re-appearance gets the label and AT MOST one anchor, never the set
        anchors_of = {str(cid): [a for a in (characters.get(str(cid)) or {}).get("anchors", [])]
                      for cid in anchors}
        for p in art.get("panels", []):
            n = int(p.get("n", 0))
            if n in anchors.values():
                continue          # the anchor frame carries the descriptor
            cap = _norm(p.get("caption", ""))
            for cid, terms in anchors_of.items():
                hits = [t for t in terms if t and _norm(t) in cap]
                if len(hits) > 1:
                    out.append(issue("error", "art.reappearance-too-detailed", f"{where}/panels[{n}]",
                                     f"panel {n} re-describes {cid} with {len(hits)} anchors {hits} — "
                                     "a re-appearance carries the label and at most one anchor"))

    want_texts = {str(t.get("id")) for t in conti.get("texts", [])}
    lines_of: dict[str, list[str]] = {}
    for t in conti.get("texts", []):
        body = (t.get("lines") or {})
        lines_of[str(t.get("id"))] = [
            str(v).strip()
            for lang in ("ko", "en", "ja")
            for v in (body.get(lang) or [])
            if str(v).strip()
        ]
    seen_texts: set[str] = set()
    for i, t in enumerate(art.get("texts", [])):
        tw = f"{where}/texts[{i}]"
        tid = str(t.get("id"))
        caption = str(t.get("caption", "")).strip()
        if not caption:
            out.append(issue("error", "art.empty-caption", tw, f"caption for text {tid!r} is empty"))
            continue
        seen_texts.add(tid)
        # the caption describes the box; the words themselves live in the conti
        if any(line and line in caption for line in lines_of.get(tid, [])):
            out.append(issue("warning", "art.text-restates-words", tw,
                             "caption restates the lettering — describe the box, the words stay in the conti"))
        if not re.search(r"korean|english|japanese", caption, re.IGNORECASE):
            out.append(issue("warning", "art.text-language-missing", tw,
                             "caption does not name its language (Korean / English / Japanese)"))
        leaked = [w for w in STYLE_WORDS if w in caption.lower()]
        if leaked:
            out.append(issue("error", "art.style-in-caption", tw,
                             f"caption names the medium or technique {leaked} — style belongs to the "
                             "summary"))
        if want_texts and tid not in want_texts:
            out.append(issue("warning", "art.extra-text", tw,
                             f"text {tid!r} is not in the conti"))
    for tid in sorted(want_texts - seen_texts):
        out.append(issue("error", "art.text-missing", where, f"no caption for text {tid!r}"))
    return out


# --------------------------------------------------------------------- plan
def validate_plan(plan: dict, project: dict) -> list[dict]:
    out: list[dict] = []
    total = plan.get("page_total")
    if not isinstance(total, int) or total <= 0:
        return [issue("error", "plan.no-page-total", "plan", "page_total must be a positive integer")]
    if total % 4:
        out.append(issue("error", "plan.not-multiple-of-4", "plan",
                         f"page_total {total} is not a multiple of 4"))

    pages = plan.get("pages")
    if not isinstance(pages, list) or not pages:
        return out + [issue("error", "plan.no-pages", "plan", "pages must be a nonempty array")]
    if len(pages) != total:
        out.append(issue("error", "plan.page-count", "plan",
                         f"{len(pages)} pages listed but page_total is {total}"))

    lo = project.get("panels", {}).get("min", 1)
    hi = project.get("panels", {}).get("max", 8)
    for i, page in enumerate(pages):
        pw = f"page {page.get('page', i + 1)}"
        if not str(page.get("story_job", "")).strip():
            out.append(issue("error", "plan.no-story-job", pw, "story_job is empty"))
        state = page.get("reader_state")
        if not isinstance(state, dict) or not all(k in state for k in ("knows", "learns", "question")):
            out.append(issue("error", "plan.no-reader-state", pw, "reader_state needs knows/learns/question"))
        target = page.get("panel_target")
        if not isinstance(target, int) or not (lo <= target <= hi):
            out.append(issue("error", "plan.panel-target", pw, f"panel_target {target!r} outside {lo}..{hi}"))
        split = page.get("split")
        tpl_id = page.get("template_suggestion")
        if split not in ("even", "single"):
            out.append(issue("error", "plan.bad-split", pw,
                             "split must be even or single"))
        else:
            # the split and the layout must agree, and that is checkable here
            layout = pageshape.load(tpl_id) if _layout_panel_count(tpl_id) else None
            if layout is not None:
                for problem in pageshape.problems(layout, split):
                    out.append(issue("error", "plan.shape-mismatch", pw, problem))
        if _layout_panel_count(tpl_id) is None:
            out.append(issue("warning", "plan.bad-template", pw,
                             f"template_suggestion {page.get('template_suggestion')!r} not in either library"))
        if int(page.get("page", 0)) >= 2 and not str(page.get("page_turn_hook", "")).strip():
            out.append(issue("error", "plan.no-hook", pw, "page 2 onward needs a page_turn_hook"))
        strat = page.get("focus")
        if page.get("split") == "even" and strat:
            out.append(issue("error", "plan.focus-on-even", pw,
                             "an even page carries no single subject — focus must be empty"))
        if page.get("split") == "single" and strat not in ("person", "place", "moment"):
            out.append(issue("error", "plan.missing-focus", pw,
                             "a single page names its subject: person, place or moment"))
    # no layout twice: every page must be its own drawing
    seen: dict[str, int] = {}
    for i, page in enumerate(pages):
        tpl_id = page.get("template_suggestion")
        pw = f"page {page.get('page', i + 1)}"
        if tpl_id in seen:
            out.append(issue("error", "plan.repeat-layout", pw,
                             f"layout {tpl_id} is also on page {seen[tpl_id]} — "
                             "a layout is used on one page of the episode only"))
        else:
            seen[tpl_id] = int(page.get("page", i + 1))
    return out


# -------------------------------------------------------------------- bible
# ---------------------------------------------------------------- illustration
# Type B (docs/reference-prompts/B-*): a sectioned prose prompt. No JSON, no
# boxes. The trigger line comes first; then one style section and one section
# per region. Anything else is not a Type B prompt.
SECTION_NAME = re.compile(r"^[A-Za-z0-9_]+$")


def validate_sections(draft: dict, project: dict | None = None) -> list[dict]:
    """A Type B draft: trigger + style_and_aesthetic + one or more regions."""
    out: list[dict] = []
    style = str(draft.get("style_and_aesthetic", "")).strip()
    if not style:
        out.append(issue("error", "sections.no-style", "style_and_aesthetic",
                         "the style_and_aesthetic section is empty"))
    sections = draft.get("sections")
    if not isinstance(sections, list) or not sections:
        out.append(issue("error", "sections.empty", "sections",
                         "at least one region section is required"))
        return out
    seen: set[str] = set()
    for i, s in enumerate(sections):
        where = f"sections[{i}]"
        if not isinstance(s, dict):
            out.append(issue("error", "sections.not-object", where, "section must be an object"))
            continue
        name = str(s.get("name", "")).strip()
        if not name or not SECTION_NAME.match(name):
            out.append(issue("error", "sections.bad-name", where,
                             f"section name {name!r} must be one tight token (A-Za-z0-9_)"))
        elif name == "style_and_aesthetic":
            out.append(issue("error", "sections.dup-style", where,
                             "style_and_aesthetic is its own section — do not repeat it"))
        elif name in seen:
            out.append(issue("error", "sections.dup-name", where, f"duplicate section {name!r}"))
        else:
            seen.add(name)
        if not str(s.get("caption", "")).strip():
            out.append(issue("error", "sections.no-caption", where, "section caption is empty"))
    return out


# ----------------------------------------------------------------------- comic
def validate_comic_plan(plan: dict, project: dict | None = None) -> list[dict]:
    """A comic plan: pages are static moments, not panels. No cut/template fields."""
    out: list[dict] = []
    total = plan.get("page_total")
    if not isinstance(total, int) or total <= 0:
        return [issue("error", "comic-plan.no-page-total", "plan",
                      "page_total must be a positive integer")]
    if total % 4:
        out.append(issue("error", "comic-plan.not-multiple-of-4", "plan",
                         f"page_total {total} is not a multiple of 4"))
    pages = plan.get("pages")
    if not isinstance(pages, list) or not pages:
        return out + [issue("error", "comic-plan.no-pages", "plan", "pages must be a nonempty array")]
    if len(pages) != total:
        out.append(issue("error", "comic-plan.page-count", "plan",
                         f"{len(pages)} pages listed but page_total is {total}"))
    for i, page in enumerate(pages):
        pw = f"page {page.get('page', i + 1)}"
        if not str(page.get("moment", "")).strip():
            out.append(issue("error", "comic-plan.no-moment", pw, "moment (the still) is empty"))
        if int(page.get("page", 0)) >= 2 and not str(page.get("change", "")).strip():
            out.append(issue("error", "comic-plan.no-change", pw,
                             "page 2 onward says what changes from the previous frame"))
        # a comic page is one frame: the panel machinery must not leak in
        for forbidden in ("template_suggestion", "panel_target", "split", "focus"):
            if forbidden in page:
                out.append(issue("error", "comic-plan.forbidden-field", pw,
                                 f"{forbidden!r} is a manga cut field — a comic page is a single frame"))
    return out


def validate_comic_scene(scene: dict, project: dict | None = None) -> list[dict]:
    """A comic scene: one still frame plus its lettering. No panels, no layout."""
    out: list[dict] = []
    page = scene.get("page", "?")
    where = f"page {page}"
    if not str(scene.get("scene", "")).strip():
        out.append(issue("error", "comic-scene.no-scene", where,
                         "scene is empty — describe the whole frame"))
    if not str(scene.get("style", "")).strip():
        out.append(issue("warning", "comic-scene.no-style", where,
                         "no per-page style line — the summary will carry the project style"))

    tier = project.get("canvas", {}).get("tier", "M") if project else "M"
    size = _tier_size(tier)

    box = scene.get("frame_bbox")
    if box is not None:
        err = _check_bbox(box, *size) if size else None
        if err:
            out.append(issue("error", "comic-scene.frame-off-canvas", where,
                             f"frame_bbox: {err}"))

    texts = scene.get("texts", [])
    if not isinstance(texts, list):
        out.append(issue("error", "comic-scene.texts", where, "texts must be an array"))
        return out
    seen_ids: set = set()
    for i, text in enumerate(texts):
        tw = f"{where}/texts[{i}]"
        tid = text.get("id")
        if tid in seen_ids:
            out.append(issue("error", "comic-scene.dup-text-id", tw, f"duplicate text id {tid!r}"))
        seen_ids.add(tid)
        if text.get("kind") not in KINDS:
            out.append(issue("error", "comic-scene.bad-kind", tw,
                             f"kind {text.get('kind')!r} is not one of {KINDS}"))
        if text.get("bubble") not in BUBBLES:
            out.append(issue("error", "comic-scene.bad-bubble", tw,
                             f"bubble {text.get('bubble')!r} is not one of {BUBBLES}"))
        lines = text.get("lines") or {}
        lengths = {}
        for lang in ("ko", "en", "ja"):
            value = lines.get(lang)
            if not isinstance(value, list) or not value:
                out.append(issue("error", "comic-scene.missing-lang", tw, f"lines.{lang} is missing"))
                lengths[lang] = 0
            else:
                lengths[lang] = len(value)
        served = {v for v in lengths.values() if v}
        if len(served) > 1:
            out.append(issue("error", "comic-scene.line-count", tw,
                             f"line counts differ across languages {lengths}"))
        box = text.get("bbox")
        if box is None:
            out.append(issue("warning", "comic-scene.no-text-box", tw,
                             "no bbox — the build will place this line in the frame"))
        elif size is not None:
            err = _check_bbox(box, size[0], size[1])
            if err:
                out.append(issue("error", "comic-scene.text-box-off-canvas", tw, err))
    return out


def validate_bible(pool: dict, cast: list[str] | None = None) -> list[dict]:
    out: list[dict] = []
    ids = set()
    for bucket in ("characters", "objects"):
        for i, card in enumerate(pool.get(bucket, [])):
            cw = f"{bucket}[{i}]"
            cid = card.get("id")
            if not isinstance(cid, str) or not SLUG.match(cid):
                out.append(issue("error", "bible.bad-id", cw, f"id {cid!r} must be a kebab-case slug"))
            elif cid in ids:
                out.append(issue("error", "bible.dup-id", cw, f"duplicate id {cid!r}"))
            else:
                ids.add(cid)
            if not str(card.get("descriptor", "")).strip():
                out.append(issue("error", "bible.no-descriptor", cw, "descriptor is empty"))
            elif bucket == "characters" and not re.match(
                r"\s*apparent age group\s*:", card["descriptor"], re.IGNORECASE
            ):
                out.append(issue("error", "bible.descriptor-shape", cw,
                                 "descriptor must open with 'Apparent age group: <one of the "
                                 "seven>' — the shape is fixed by character-consistency.md §9"))
            else:
                low = card["descriptor"].lower()
                hit = [w for w in STYLE_WORDS if w in low]
                if hit:
                    out.append(issue("error", "bible.style-in-descriptor", cw,
                                     f"descriptor carries style words {hit} — appearance only"))
            if bucket == "characters":
                name = card.get("name") or {}
                filled = [l for l in ("ko", "en", "ja") if str(name.get(l, "")).strip()]
                # a character with no name in the story leaves `name` empty and the
                # workflow proceeds — identity is the descriptor, not a name. Only a
                # half-filled name (some languages, not all) is a problem.
                if filled and len(filled) < 3:
                    out.append(issue("warning", "bible.name-langs", cw,
                                     f"name is in only {filled} — give all three languages or leave it empty"))
                anchors = card.get("anchors") or []
                if not (2 <= len(anchors) <= 4):
                    out.append(issue("error", "bible.anchors", cw, f"{len(anchors)} anchors (need 2-4)"))
                if not str(card.get("signature", "")).strip():
                    out.append(issue("error", "bible.no-signature", cw, "need exactly one signature detail"))
                if not str(card.get("identifier_label", "")).strip():
                    out.append(issue("error", "bible.no-identifier", cw, "identifier_label is empty"))
                neg = re.findall(r"\bno\s+(?:hair|skin tone|headwear|accessories|makeup|shoes)\b",
                                 str(card.get("descriptor", "")), re.IGNORECASE)
                if neg:
                    out.append(issue("warning", "bible.negative-phrasing", cw,
                                     f"descriptor says what is missing {neg} — write what is there "
                                     "(authoring-spec.md §11.4)"))
    if cast is not None:
        unknown = [c for c in cast if c not in ids]
        if unknown:
            out.append(issue("error", "bible.cast-unknown", "cast", f"cast names ids not in the pool: {unknown}"))
    return out


# ------------------------------------------------------------------ geometry
def panel_overlaps(items: list[dict]) -> list[tuple[int, int]]:
    """Just the overlap pairs, for a quick gate check."""
    boxes = [(i, it.get("bbox")) for i, it in enumerate(items)
             if it.get("label") in DRAWN and isinstance(it.get("bbox"), list)]
    out = []
    for a in range(len(boxes)):
        for b in range(a + 1, len(boxes)):
            if _overlaps_matter(boxes[a][1], boxes[b][1]):
                out.append((boxes[a][0], boxes[b][0]))
    return out
