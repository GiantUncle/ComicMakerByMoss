# Character consistency

How a character description is distributed across panels and pages, and how a
**reference image** is wired in to hold a character's identity across them.

Rules R-A~R-E below are **measured** from the FKEY reference templates
(raw originals archived at `docs/reference-prompts/`, analysis in
`docs/reference-prompts/README.md`). The wiring facts come from the CharRef v2
and Moss-Image-Edit model cards.

---

## 1. How the reference prompts distribute a character

Measured from example A (18 items, 2 characters):

| item | label | mention | form |
| --- | --- | --- | --- |
| 1 | **object** | the man | **FULL (220 chars)** |
| 4 | **character** | the girl | **FULL (830 chars, 5 sentences)** |
| 5 | object | both | **two short labels** |
| 14-16 | text | either | position pointer only |

### R-A — Each character gets exactly ONE full description per page

The girl is fully described once (item 4). The man is fully described once
(item 1). Everywhere else they are referenced by a short label.

The description itself is the card's `descriptor`, a single string composed when
the card is written. Exactly one panel per page marks `anchor_of` for the
character, and the build pastes the descriptor there. A descriptor rephrased per
page yields a different face per page, so it is stored once and copied, never
recomposed.

### R-B — The label of the full-description item is NOT fixed

```
girl  FULL -> item 4, label = "character"   (she is the subject of the page)
man   FULL -> item 1, label = "object"      (he is part of a panel scene)
```

The deciding question is **what the character is inside that item**. If the
character is the subject of the page, use `character`. If they are a component
of a panel scene, the full description goes inside that panel's `object`
caption.

So the item count follows the staging: one `character` item for the page
subject, and the rest of the cast described inside the panel items they inhabit.

### R-C — Re-appearance is shortened to `the + identifying adjective + noun`

The full block is not repeated. The adjective carries the character's single
strongest identifier.

| character | re-appearance | identifier |
| --- | --- | --- |
| girl | `the girl` / `the petite 15-year-old sailor-uniform schoolgirl` | **sailor-uniform** |
| man | `the bald traveler` / `the bald man` | **bald** |

Item 5 verbatim:

```
Lower-left vertical sub-panel: Inside the wooden hallway entrance,
the bald traveler stands on the left facing the petite 15-year-old
sailor-uniform schoolgirl holding her school bag on the right as they chat.
```

Two characters in one item -> both use short labels.

### R-D — `summary.caption` carries style, plus a pointer index at most

On a **single page** the summary carries style and count tags only. Example A
ends with `1girl, 1boy, school uniform, sailor collar, hair bun, ryokan,
luggage` — no face, build or hair colour. The appearance lives in the items.

On **multi-page work** the summary additionally carries a compact **cast index**
for the characters present on that page (authoring-spec §10.7). The index is a
pointer, not prose:

```
Character 1 (이자헌 / the gaunt chief): gaunt, deep-set eyes, thin scar on the right hand.
Character 2 (김솔음 / the young woman): soft face, dark eyes, mole under the left eye.
```

Name, `identifier_label`, and the anchor terms — one line each. The full
description stays in the anchor panel (R-A). An index that restates the full
description duplicates tokens and gives the model two competing versions of the
character.

### R-E — A character named in a `text` item is a position pointer

`"...in speech bubble to the right of the girl's head."` /
`"...between the girl and the bald man."` These restate the `bbox` in words.
They are not descriptions.

### Example B follows the same shape

```
<|style_and_aesthetic|>... 1girl, multiple views, same character in two states,
   tall slender 17-year-old girl, 7.5-head-tall proportions,
   platinum-blonde braided hair, white sundress ...<|/style_and_aesthetic|>
<|left_close_up|>   FULL description
<|right_full_body|> "In sharp contrast, ... the exact same tall, long-legged
                    17-year-old blonde braided girl with elegant 7.5-head-tall
                    bishoujo proportions, a small head, and long slender legs. ..."
```

The summary anchors live in the **style section** (B's equivalent of
`summary.caption`), and re-appearance opens with **`the exact same`** and
repeats only proportions/hair/outfit.

### Example C: one appearance -> one full description

Only item 0 (`character`) has the full block; the other ten items are narration.
No re-appearance, so no shortening.

---

## 2. Multi-page (32 / 64 pages)

The reference templates are single-page, so they have no cross-page rule. The
short label only works while its referent is on the same page. Across pages the
referent is off-screen.

Two options:

| option | content | cost |
| --- | --- | --- |
| (a) re-state FULL every page | paste the full block on each page the character appears | 830 chars x appearances |
| (b) cast roster + short labels | put a cast summary in `summary.caption`, keep short labels per panel | cheap |

The prompt spec (`references/authoring-spec.md` §10.7) prescribes **(b)**:

> 跨页在 summary.caption 写角色总表，各分镜重复必要身份锚点
> (across pages, write the cast roster in summary.caption; each panel repeats the necessary identity anchors)

**Use (b).** Per page: cast summary in `summary.caption`, FULL once on the
anchor item, short labels after.

---

## 3. The anchor item — where a reference image attaches

R-A/R-B give the natural attachment point: **a character's full-description item
is their identity anchor**. A reference image is attached to that item, via a
`ref_id` field.

```jsonc
{
  "label": "character",
  "caption": "Main lower-center portrait focus: <full description>",
  "ref_id": "misaki",                // the wiring key; the prompt carries the description
  "bbox": [-40, -260, 740, 490]
}
```

Example A with refs:

```
item 1  object     ref_id: bald-man   <- the man's anchor
item 4  character  ref_id: misaki     <- the girl's anchor
item 5  object     ref_id: -          <- short labels only
item 14-16 text    ref_id: -          <- position pointers
```

`ref_id` is consumed by the **reference wiring** at compile time. It is not
written into the prompt.

---

## 4. Wiring — CharRef v2 (one reference per page)

`7err4/MOSS-Image-CharRef` (CharRef v2, Apache-2.0, for MOSS-Image **Base**)

- One picture as *Picture 1* plus a prompt -> the same character (face, hair,
  outfit, art style) in a new scene. The identity travels in the reference, so a
  character needs no trained adapter.
- **Works on whole comic pages** (MOSS JSON layouts with panels and speech
  bubbles).
- Limits: one reference per image; multi-character scenes only carry Picture 1's
  identity reliably; anime-trained (photoreal/3D faces drift); a reference cut
  from a comic panel drags its props along, so crop to the character.

**ComfyUI wiring (>= 0.42)**

```
MOSSImageOstrisEditModelPatch (kv_cache on)
  -> LoraLoaderModelOnly (CharRef 1.0)
  -> TextEncodeMOSSImageOstrisEdit  image1 = character sheet
                                    prompt = "Same character and art style as Picture 1." + scene
  -> negative: same encoder, empty prompt
  -> 50 steps, cfg 3, euler / sgm_uniform, SLG single layer 22
```

**Prompt rules**

- Start with the literal prefix `Same character and art style as Picture 1.`
- A few appearance words after it (hair style, eye colour, key outfit) raise
  fidelity noticeably - **keep the short label from R-C in the prompt**.
- Outfit follows the reference unless the prompt names other clothing.
- Use a clean, large reference (full body or bust, plain background) - **a
  single clean front view**, not a multi-view turnaround montage.

**Character sheet pipeline**

1. Character card: 2-4 anchor terms + age fact + body type + one signature
   detail (authoring-spec §7).
2. Generate 4 candidates (single figure, clean, plain background) -> approve 1.
3. `bible/characters/misaki/sheet.png` + `approved: true`.

---

## 5. Several characters on one page - the "per-box" assignment

CharRef v2 takes one reference per image, so the wiring depends on the page:

| page | wiring | refs |
| --- | --- | --- |
| one dominant character | that character's sheet as `image1` | 1 |
| several, one lead | the `ref_id` with the largest anchor item (usually the 見せゴマ character) as `image1` | 1 |
| several, all important | **Moss-Image-Edit (1-4 references)** | 2-4 |

**Multi-reference is the real per-box path.** `Moss-Image-Edit` / the ai-toolkit
format prepends references as `Picture N:` tokens and **lets the text encoder
see the images**, so each item caption can name its own reference:

```jsonc
{ "label": "character", "ref_id": "sol-eum",
  "caption": "Main portrait focus: the young woman, exactly as in Picture 1. <full description>",
  "bbox": [-40, -260, 740, 490] },
{ "label": "object", "ref_id": "brown",
  "caption": "The man, exactly as in Picture 2. <FULL description>",
  "bbox": [-730, 80, -30, 480] }
```

**Unverified - test before relying on it:**

1. does the text encoder actually bind `Picture N` to the right item
2. does `bbox` place that identity in the right region
3. do 2-4 references stay unmixed
4. does the FKEY style adapter survive alongside the reference path

When only one reference is used, keep the other characters on short labels plus
their text anchors, and pull the moment their identity matters as a separate
**Edit LoRA** correction (§6).

---

## 6. Correction - Edit LoRA

`chinoll/Moss-Image-Edit` (1-4 references, native ComfyUI PR #17296,
`edit_format`: `ai-toolkit` / `ai-toolkit (kv_cache off)` / `Moss-Image-Edit`).
When one panel's face is wrong, fix that panel **without regenerating the page**.

---

## 7. Consistency QC

After generating a page:

1. Crop each character's face region and compare it against the **character
   sheet** - embedding similarity or a VLM judgement.
2. Below threshold -> flag for regeneration.
3. Record `character_drift: [{char, score}]` in the QC report.

---

## 8. Checklist

- [ ] Each character has a character card with 2-4 anchor terms, one signature, and a single canonical `descriptor`.
- [ ] Each character appearing on a page has **exactly one** `anchor_of` panel, whose caption carries that `descriptor` verbatim.
- [ ] That item's label is chosen by R-B (subject -> `character`, panel part -> `object`).
- [ ] Every re-appearance uses a short label carrying the identifier adjective.
- [ ] `summary.caption` carries the style, plus a compact cast index (name + `identifier_label` + anchors) when the work spans pages.
- [ ] Reference images attach to the anchor items via `ref_id`; the prompt text carries the description alone.
- [ ] One-reference pages pick the lead via the largest anchor item.
- [ ] The CharRef prefix `Same character and art style as Picture 1.` is present when references are used.
- [ ] Character sheets are single clean front views, cropped to the character.

---

## 9. Describing a character from a reference image

The card's `descriptor` can come from a reference image instead of being written
by hand. The extraction contract below is the one the MOSS reference tooling
uses; it is a **rule set, not a prompt to copy**, and it is the same contract a
hand-written descriptor must satisfy.

**What to extract, in order.** Start with the apparent sex, then: face shape ·
build · distinctive facial features (moles, freckles) · eye shape and size · hair
length, colour or grayscale shade, hairstyle, bangs, braids · animal ears if
present · headwear · accessories · clothing including collar, sleeves and
decorations.

**A side belongs to the character, not the viewer.** `a mole under her left eye`
is *her* left — it reads on the viewer's right when she faces the camera, and it
stays on that side in every frame, never mirrored and never doubled. Say a side
once, from the character's own body.

**What never enters the descriptor.**

- pose, expression, gaze
- camera angle, framing, lighting, background
- art style, medium, rendering
- an age or age group (see below)
- invented hidden details, names, personality, backstory

**Age is a separate question.** Manga draws nearly every age with smooth skin, so
an age read from the face is unreliable. Ask it on its own and pick exactly one:
`child · young teenager · older teenager · young adult · adult in their thirties ·
middle-aged · elderly`. Put the answer at the **head** of the descriptor:

```
Apparent age group: young adult. She is a woman …
```

**One figure.** If several people are visible, describe only the largest
foreground figure. The output is **one concise English paragraph**, no headings,
bullets or JSON.

**When the descriptor is used in a panel**, append `One person, drawn once in this
panel.` and keep the recurring character identical across pages. The summary
carries the standing instruction: draw each character at the apparent age and
natural proportions of their own descriptor, one frozen moment per panel.

**This text is a setting, not a prompt for the sheet.** Style, medium and camera
belong to the project and are applied when the sheet is rendered (§4, §6), so a
style sentence never enters the descriptor — it would make every character carry
the same sentence and say nothing about the face.
