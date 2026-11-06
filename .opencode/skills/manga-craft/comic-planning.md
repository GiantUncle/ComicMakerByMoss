# Comic layout planning

How to turn a script into a panel grid, and how to size the boxes so the
lettering lands where it should.

---

## 0. Panel grammar rules (R1-R18)

The full rule set. Numbers in brackets are the measured/sourced values. See the
bottom of this file for what each source is and which values are cross-checked.

**Structure**

| # | Rule | Value |
| --- | --- | --- |
| R1 | Reading order | `tier` ascending, then RTL: `x_min` descending / LTR: ascending. Order is **derived from the boxes**, never stored |
| R2 | **T-rule** | No four panels meeting at a `+`. Adjacent split tiers must offset their vertical cuts by >= 8% of the canvas width |
| R3 | Gutters | Uniform within a page. Horizontal > vertical. A thin gutter reads as "same beat", a thick one as a cut |
| R4 | Panel size = time | Bigger = slower/important. Borderless = timeless |
| R5 | Tier count | 3-4 standard, 2 for impact, max 4 |
| R6 | Panel count | **3-4 by default**, dialogue included. A conversation flows across three or four panels rather than multiplying them. **Impact comes from cutting panels, not adding them** — a climax or a turn takes 1-3. Five is the busy end; six is a rare rapid sequence and never the default |
| R7 | Page-turn hook (引き / メクリ) | End the last panel of a 見開き on a question; the reveal lands right after the turn. One per spread from page 2 |

**Direction**

| # | Rule |
| --- | --- |
| R8 | Shot variety: no three consecutive same-shot panels. Establishing shot when the location changes, close-up for emotional turns, insert for foreshadowing props |
| R9 | **Eyeline matching:** two characters talking in adjacent panels must face opposite directions across the gutter |
| R10 | Balloons: upper third of the panel, >= 80 px (at 1024 wide) from any other character's head, tail toward the speaker. Off-frame speaker -> tailless oval. Max 2 lines |
| R11 | Dialogue length: ~28 glyphs (2 lines) per balloon. More -> split the panel |
| R12 | Narration = rectangle, dialogue = round/jagged balloon. Captions may sit on the panel edge |
| R13 | Balloon tails point at a speaker inside the panel |
| R14 | Character intro box: once, at a named character's formal first appearance, in a corner that misses the face and action |

**Impact**

| # | Rule | Value |
| --- | --- | --- |
| R15 | **見せゴマ size** | Largest panel >= **2x** the second largest, and 30-40% of the page |
| R16 | **タチキリ (bleed)** | Extend a panel past the inner frame to the trim line - 見せゴマ only, never everywhere. Keep dialogue inside the inner frame |
| R17 | **見開き unit** | Lay out per **spread (2 pages)**, not per page. The page-count unit is 4 pages = 2 spreads |
| R18 | Variant panels | Diagonal / irregular panels only for striking moments; overuse burdens the reader |

**Density and flow**

| # | Rule | Value |
| --- | --- | --- |
| R19 | **Background budget** | Only the panels that establish a place carry a `bg`. Reaction, insert and close-up panels frame the subject tight and leave `bg` empty, so the art does not compete with the story. A page rarely needs more than two or three backgrounds |
| R20 | **Eye path** | The eye enters at the top-right (RTL) and leaves at the bottom-left. Put the largest panel on the entry or the exit, and let the weight fall away along the path. Two heavy panels sitting next to each other on the path read as one, and the page loses its beat |
| R21 | **Text budget** | A page carries only the lines the reader must have. Cut narration that repeats what the art already shows, and cut dialogue that repeats a beat. A panel holds at most two text items. When a page needs six balloons, it is two pages or fewer words |

`instantiate_layout.py` checks R2, R3, R5, R6, R15 and the margins when you
instantiate a template. R1 comes out of the box order. R4, R7-R14, R16-R18 are
authoring rules the tool cannot see.

---

## 1. Reading order

- Japanese manga: **right to left, top to bottom**. Panel 1 is top-right.
- Chinese comics (and the reference pages here): **left to right, top to bottom**,
  but vertical Chinese text inside a box reads right to left.
- Western comics: left to right.

State the choice in the final note. If the script has no explicit order, build
the grid so the eye follows the main character's line of action.

---

## 2. Page geometry

### Margins and gutters (measured on the reference 1024x1536 page)

| Feature | Value |
| --- | --- |
| Outer margin | 22-32 px (2-3% of width) |
| Panel gutter | ~10 px |
| Panel border | drawn by the model; the item caption carries content, and `bbox` carries the frame |

Keep important text at least 5% (≈50 px) from the edge; the model clips the
outermost ring.

### Grid recipes (all on a 1024x1536 page)

**2-koma, stacked** - the simplest 2-panel page:

```
(32,28)   ┌──────────────────────────────┐
          │  PANEL 1                     │
          └──────────────────────────────┘
          ┌──────────────────────────────┐
          │  PANEL 2                     │
          └──────────────────────────────┘
          (32,1508)
```
Split at y=768. Keep the split off-centre (a 55/45 split reads better than
50/50 unless the beat is a hard cut).

**4-koma, 2x2**

```
x split at 512, y split at 768; four 490x740 panels with 10px gutters.
```

**Vertical 3-panel strip (webtoon)**

```
(22,28)-(1002,528)  (22,538)-(1002,1038)  (22,1048)-(1002,1508)
```
Equal thirds with 10px gutters.

**Asymmetric feature page** (what the reference ryokan page uses)

```
top-left wide panel  +  tall right column
middle-left panel     +  lower-left narrow sub-panel
main portrait         +  title block in the gutter
```
This gives the page a focal point and leaves room for narration boxes to float
over quieter areas.

**8-panel strip** - the official OpenMOSS example uses 512x4096 with eight
square panels and slim cream gutters. For that, use Scene JSON: it has
`salience`, `identity` and `note` fields that let each panel carry its own
narrative job.

### Choosing between them

- 2 panels of equal weight -> 2-koma.
- A page with a lot of narration and one strong image -> asymmetric feature
  page: a quiet panel field with one large focal panel.
- A story beat that needs a punchline -> leave the punchline panel the tallest
  and the emptiest.

---

## 3. Panel items

One `object` or `panel` item per panel, describing the scene inside it.
Caption pattern:

```
"<panel shape and setting>: <what happens in it>."
```

Examples:

- `A wide horizontal panel: a traveler seen from behind stretching his arms high overhead in relief against a peaceful mountain village landscape.`
- `Inside the wooden hallway entrance of a country inn, the bald traveler stands facing the petite sailor-uniform schoolgirl as they chat.`

The `bbox` carries the item's position (authoring spec §10.1), so the caption
describes only what is inside the box. Position phrasing such as "top-left",
"upper half" or "main lower-center portrait focus" invites the model to draw a
border or a label.

**Do state left/right for figures *inside* the panel.** The model does not
inherit the box's position for the people within it, so write "the traveler
stands on the left facing the girl on the right" - that is an internal
composition fact, not a restatement of the item's own location.

Panel *shape* is still worth a word, because it tells the model what kind of
frame to draw: `a wide horizontal panel`, `a tall vertical panel`, `a narrow
vertical sub-panel`, `an extreme close-up inset panel showing ONLY …`.

---

## 4. Character bible

Write the recurring cast once, then paste the block **verbatim** into every
panel item that shows them. This is what keeps a face identical across a page.

Template:

```
Our <age> <nationality> teenage <gender> (<Name> <romanised>) with <age-specific
grace phrase> - neither a big-headed 10-year-old child nor a mature 20-year-old
woman. <face>. <hair>. <eyes>. <signature marks>. <clothing>. <default pose and
expression>.
```

The reference page's block for Misaki:

```
Our slender 15-year-old Japanese teenage schoolgirl (Misaki Shirosawa) with true
adolescent grace-neither a big-headed 10-year-old child nor a mature 20-year-old
woman. She has a softly tapered chin, a slender graceful neck, a small mole under
her left eye, fair creamy peach-flushed skin, bright expressive light-amber eyes,
and silky dark-brown hair tied up into a slightly loose, cute round bun at the back
with airy, translucent wisps of bangs falling naturally across her forehead. She
wears a plain matte dark-navy short-sleeve sailor school uniform top with three
clean white stripes and a pleated navy skirt, leaning slightly forward with her
hands clasped politely in front of her lap and a warm, welcoming smile as she
greets the bald man seen from behind in the lower-right foreground.
```

Then, per panel, append only what changes: `Now seen from behind, his bald
head filling the lower-right foreground.`

Rules:

- Name the age explicitly and anchor it: "15-year-old", "true adolescent
  grace", "neither a big-headed 10-year-old child nor a mature 20-year-old
  woman". The negative block does the rest.
- Give one signature detail (a mole, a hairband, a braid) so the model has an
  anchor.
- State the expression as a word plus a description: "a warm, welcoming smile,
  eyes creased at the corners".
- For a second appearance, start with "the same <Name>" or "the exact same …".

---

## 5. Text roles and how to size their boxes

Measured from the two reference comic pages (both 1024x1536). The box covers
the **lettering**, not the balloon shape - the model draws the balloon around
the text.

### Vertical Chinese narration

| Situation | glyph pitch | column pitch | width | height |
| --- | --- | --- | --- | --- |
| Over a detailed painting (ryokan page) | 13-23 px | 33-40 px | lines x 36 | chars x 14 |
| Over a clean single canvas (Akiha page) | 21-34 px | 45-75 px | lines x 55 | chars x 30 |

Rule of thumb:

```
vertical box width  = number of lines  x 36..55 px
vertical box height = longest line length x 14..30 px
```

Pick the low end when the text sits over busy artwork (it has to stay legible
without fighting the painting) and the high end over empty or simple space.
Each `\n`-separated segment is one vertical column; the first segment is the
**rightmost** column. Full-width punctuation (`！`, `。`, `，`) counts as a
glyph.

### Speech balloons

| Reference | lines | glyphs | box | glyph pitch |
| --- | --- | --- | --- | --- |
| 你好！ | 1 | 3 | 80x150 | 45 px |
| 您是今天预约的客人吗？ | 1 | 11 | 105x300 | 25 px |
| 你好啊 / 今天请多关照 | 2 | 5 | 100x200 | 30 px |
| 哇—谢谢您！… | 2 | 18 | 130x370 | 20 px |

A short greeting gets a big font (45 px and up); a long line gets a smaller
one (20-25 px). Aim for **20-30 px glyphs in a body balloon** and **40-55 px in
a short exclamation balloon**.

### Horizontal text (name tags, title)

| Reference | text | box | pitch |
| --- | --- | --- | --- |
| 白泽美咲（15） | 7 glyphs | 240x70 | 34 px / glyph |
| 《深山秘汤与看板娘美咲》 title | 2 lines | 340x130 | - |

Horizontal box width = glyphs x 30-35 px; height = lines x 45-65 px.

### The compiler's estimate

```bash
python scripts/compile_layout.py --fit "您好！\n今天请多关照" --vertical --font-size 30
```

`compile_layout.py` also flags `TEXT TOO SMALL` in its report when a box
implies a glyph size below ~11 px on the page. Fix those before delivering.

---

## 6. Balloon and text placement rules

### 6.0 The shape follows the role — a balloon is not the default

The reference pages were read to extract a **grammar, not a catalogue**: the same
three roles recur on every page, and the meaning of a shape is stable enough that
a reader learns it in one page. Copy the grammar; never copy a page.

**Three roles. The carrier is decided by the role, not by the page.**

| role | carrier | shape by delivery |
| --- | --- | --- |
| **speech** | balloon, **tail to the speaker's mouth** | rounded/oval for a calm line · **rectangular** for a flat, clipped, phone or mechanical line · **jagged/spiky** for a shout, a panic, a sudden grab · **cloud with a dotted outline** for thought (no solid tail) |
| **narration** | **rectangle, no tail** | prose over art, time and place, the inner voice. Thin outline or solid white; **solid black with white text** when the inner voice is heavy. Usually vertical along a panel edge, and it may span panels for a narrator's voice |
| **sfx** | **lettering drawn on the art, no balloon** | bold, hand-drawn, with a white halo so it survives busy art · placed at the source of the sound (impact, mouth, door, object) · may break the panel border · a hard hit takes a jagged burst shape |

Text that belongs to a surface — a shop sign, a nameplate, a posted notice, a
phone screen, a door number, a paper strip (短冊) — is **drawn as part of the
scene**, never as a balloon. A page title is integrated over the art, not boxed.

- **Density follows the scene, not the script.** A talky panel carries several
  small balloons and little art; an action or impact panel carries **one large
  SFX and few or no balloons**. Crowding every line into a balloon is what makes
  a page read flat.
- **One dominant element per page** — a big panel, a title, or a big SFX — with
  everything else subordinate.
- **Throwaway lines** are floating lettering set straight on the art; balloons
  are reserved for the lines that carry the scene.
- **A page with action carries at least one SFX.** Sound is part of the panel:
  the door, the splash, the keystroke, the footsteps.
- **Every narration box is not the same box.** Vary thin / solid / black across a
  page, and name the variation in the caption so two boxes do not come out
  identical.
- **A prompt says only what to draw.** Ids, folder names, episode numbers, gate
  names, file paths and production notes live in the sheets and the files.
- **A person is described, not named.** The `identifier_label` and the anchors
  identify them; a name appears only where the name itself is drawn.

### 6.1 Placement

1. **Balloons sit clear of the face.** Put them in the empty third of a panel,
   above or beside the head, with the eyes and mouth left unobstructed.
2. **Upper-outer corner** of the panel for narration; the eye reads top-down.
3. **Keep a balloon inside its panel.** A box that crosses a panel boundary
   will be rendered as one box on the wrong panel.
4. **Text boxes may overlap art items** - that is normal. Narration floats over
   the painted scene. Only text-over-text overlaps are a problem.
5. **One voice per box.** Two speakers in one box are hard to read; split them.
6. **SFX** sits in the corner of the action panel, bold, 1-4 characters.
7. **Narration vs dialogue:** narration is prose in a rectangle; dialogue is in
   a balloon. Name the carrier and its geometry, not the location - "Clean
   vertical Chinese narration text in a plain white rectangular box" versus
   "Clean vertical Chinese dialogue in a rounded speech balloon, the tail
   pointing toward the girl". The `bbox` decides where it sits.
8. **Speaker in frame or out?** In frame -> the balloon may carry a tail toward
   the speaker. Off frame -> use a tailless oval, or the tail will attach to
   whoever is nearest (authoring spec §9).
9. **Keep balloons >=80 px (at a 1024-wide canvas) from any other character's
   head**, scaled to the canvas width, or the tail attaches to the wrong person.
10. **First speaker sits on the right** on an RTL page; order balloons so their
    placement matches the reading order, not the order the lines were written.
11. **Narration may span panels**; a balloon may not. A caption that crosses a
    gutter is read as one narrator's voice; a balloon that crosses one is a bug.
12. **SFX sits at the source.** The door, the fist, the mouth, the falling object
    — not the panel corner by habit. It may leave the panel; its lettering grows
    with the loudness of the moment.
13. **Empty is a choice.** A silent panel with strong art carries no box at all;
    the reader fills it. Reserving boxes for the lines that matter is what gives
    the page its weight.

---

## 7. Writing item captions

A good caption answers: what, what shape, what light, what expression.
One to three sentences. **No coordinates, no restatement of the box's own
position** (spec §10.1), and no instructions like "draw a box around it".

For a character:

```
<character bible>. <what they are doing right now>.
<where their gaze goes and how>. <foreground/background relationship>.
```

For a text item:

```
<Style> <language> <direction> <carrier and its geometry>: <optional note>.
```

Roles to name: `narration in a plain white rectangular box`, `dialogue in a
rounded speech balloon with a tail pointing left`, `bold sound effect lettering`,
`character name tag`, `title logo`.

For a panel/scene item, a shape word is allowed and useful
(`a wide horizontal panel`, `an extreme close-up inset panel showing ONLY …`),
but not a position word.

---

## 8. Failure modes

| Symptom | Cause | Fix |
| --- | --- | --- |
| Dialogue lands in the wrong panel | boxes are a soft hint | shrink the number of items, make the panel boxes unambiguous, re-check the ASCII map |
| Letters are cut or squeezed | box too small | enlarge the box; keep glyphs above 20 px |
| Text overflows the balloon | the model sized the balloon from the words | add "in a generous white speech balloon with room around the lettering" |
| Faces drift between panels | the full description was rewritten instead of reused | follow the distribution rules in `character-consistency.md` (FULL once, then a short label) |
| Panels merge | too many boxes | fewer, larger items; one scene item per panel |
| Style dies | LoRA strength too high or the prompt is already style-heavy | lower the strength to 0.4-0.5; the brushwork layer is the first thing to go |
| Boxes ignored | the prompt upsampler rewrote the JSON | turn the upsampler off |
| Everything clipped | boxes too close to the edge | keep 5% margin |
| A "clean" page still painterly | the painterly layer is in the positive prompt too | use `--style clean` and ask for "zero rough brushstrokes and zero sketch lines" |

---

## 9. Where the numbers come from

`R6` / `R15` and the gutter rules are **cross-checked across five independent
Japanese manga-craft sources** (copainter, atam-academy, MediBang, egaco,
oyasumi-gamedev) plus the classic `KOMA`/`ネーム` references; only values that
converged were adopted. The `T-rule` itself is Rachel Thorn's formulation
(Kyoto Seika University), formalised as "blocking" by Neil Cohn.

Measured box sizes in §5 come from the two reference comic pages archived at
`docs/reference-prompts/` (both resolve to 1024x1536). Those pages are a
**technique** reference, not a density target: their panel count and word count
are far above what a readable page carries. Take the text treatments from §6.0
and the box measurements from §5; do not copy their density.

The template library in `templates/layouts.json` is seeded from the named kata
(3段均等割り / 2段割り / 4段割り / 全面1コマ / 田の字 / T字 / 4コマ) and validated
by `scripts/instantiate_layout.py`.

Sources, and the values that were rejected as single-source:
`docs/design.md` §2.1 and appendix A.

---

## 10. Layout and composition libraries

Two layout libraries feed a page; pick by id.

| file | what | how |
| --- | --- | --- |
| `templates/layouts.json` | 13 named kata (tiers + weights) | `instantiate_layout.py`, T-rule validated |
| `templates/moss-layouts.json` | **196 layouts** imported from the MOSS panel dataset (MIT), 2-6 panels, all RTL, 1024x1536 | normalised fractions, scaled to any canvas tier |

A dataset layout's own panels carry `bbox`, a **`content_bbox`** (the inner area
where people and balloons go), a reading-order `position`, and a `shape`. Two
facts matter:

- **Insets are the one legal overlap.** Ten layouts float a small panel inside a
  large one (`parent` / `allow_insets`). Every other pair must not cross: the
  validator allows a box fully inside another and rejects a partial overlap.
- **Diagonal and oval panels have overlapping bounding boxes.** MOSS receives the
  rectangle plus a prose shape, so the build tags those items `shape:…`; the
  validator reads the tag and skips the box-overlap test for them. The polygons
  themselves do not overlap.

**Detailed cuts are opt-in.** A page of five or more panels, or any inset, means
small cuts the model draws poorly. `project.json` carries `detail_panels`; with it
off, the 5-6 panel and inset layouts are withheld and the page range stops at 4.

### Compositions

`templates/moss-compositions.json` holds **120 camera compositions** (40 each for
one, two and three people). The `prompt` names **camera, framing, character
placement, body and face direction, pose and furniture** — never expression,
emotion, props or light, which the scene remains free to set. `boxes` are the
person regions, in reading order. Use one by appending its prompt to the panel's
scene and placing each actor inside its `content_bbox` per box, rather than
inventing a camera in prose.

---

## 11. Focus strategy — the dominant panel

A page works by spending **one dominant panel** well. Everything in this section
is a **strategy the agent chooses per project and per page** — never a rule to
apply everywhere. Read the project's `story_focus` and the page's job, then
choose. The reference pages bear this out: a typical page is 3-4 panels, a casual
one can reach 5, and almost always one panel carries the page.

**One dominant panel per page.** The largest panel is the page's focal point, and
what it shows follows from what the work is:

| when the work is… | the dominant panel shows |
| --- | --- |
| **character**-driven — a lead you are selling | the protagonist, as a beauty / character shot. Often very large; this is the art the reader came for |
| **narrative**-driven — thriller, drama, a crime | the decisive moment — the shock, the reveal, the scene of the act |
| **balanced** | whichever single moment the page turns on |

**A huge focus must stand alone.** A panel that fills a third of the page loses
its weight when other large panels compete for the eye:

- **one huge** focus → keep every other panel small and quiet; do not put a
  second big panel on the same page.
- **two focuses** → make **both medium**. Two mediums read as a deliberate pair;
  a huge plus a medium makes the medium look like an accident.
- a small **inset** reaction panel (a face) may sit inside a big panel without
  stealing focus — it is a detail *on* the focus, not a second focus.

**Match the layout to the focus.** Every layout's dominant panel sits somewhere;
the layout list reports it as `[big N%: position]`. Pick the layout whose large
panel is where this page's focus belongs — a bottom large panel for a reveal, a
top large panel for an establishing beauty shot.

**Keep a beauty shot clean.** The dominant character panel carries little or no
lettering. Put dialogue in the smaller panels and let narration carry time and
place, while the art carries the emotion. A page whose big character panels each
carry a balloon is a page with no focus at all.

### Page strategies

The project names a **default** (`story_focus`), but the agent decides **per
page**. A strategy fixes three things at once: the panel-size profile, what the
dominant panel shows, and how the background is handled.

| strategy | when the page is… | panel sizes | dominant panel | background |
| --- | --- | --- | --- | --- |
| `routine` | a daily flow, a conversation, an even exchange | mostly **equal**, 3-4 | none — the steady rhythm is the point | the location stays consistent across panels |
| `thought` | a thinking process unfolds | equal, 3-4 | the thought | **most panels simplified** — flat tone or a gradient, only the needed object (a desk) drawn, the rest dropped, so the thought itself reads |
| `character` | the protagonist appears, a body, a portrait | one large (≈ 40-60%) | the character | the large panel may **drop the background**; the smaller panels carry the place |
| `space` | an event, a shock, a reveal of the situation | one **huge** (≈ ⅓-½) | the **space** — the reader sees where it happened | the huge panel *is* the location; the rest are tight reactions |
| `pair` | a confrontation or a beat between two people | two **medium** | both | split across the two |
| `ensemble` | chatter, a crowd, an ensemble beat | 5-6 equal (needs detailed cuts) | none | shared location |

**At least one panel per page shows the place.** However tight the focus, one
panel must let the reader **confirm** — not imagine — where the scene is: where
the characters stand, which way they face. `space` satisfies it in the huge
panel; `character` satisfies it in the small panels around the focus; `thought`
keeps one panel with the real location and simplifies the others.

**These strategies sit under the focus rule above**, which still holds — a huge
`space` panel stands alone, and two focuses are both medium.

**These are choices, not rules.** The same layout serves a thriller and a
character piece; what changes is which panel you make dominant and what you put
in it. Read the project's default, then let each page's job pick its strategy —
and add your own when the story asks for something these do not cover.
