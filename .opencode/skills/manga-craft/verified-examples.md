# The three reference prompts, verified

The three reference prompts were decomposed box by box. Everything below is
measured from them, and it is the evidence behind the numbers in
`comic-planning.md`.

> **Note on position words.** Every reference prompt opens its item captions
> with a location - "Top-left horizontal panel:", "Main lower-center portrait
> focus:", "on the upper-right". The authoring spec (§10.1) now forbids this,
> because `bbox` already carries the position and the extra words invite the
> model to draw borders or labels. **Follow the spec when writing new prompts.**
> The measurements below (box sizes, canvas, panel map) are still valid; only
> the caption wording is legacy.

---

## 1. Type A - Ryokan 2-koma, selective-focus gouache

**Form:** Layout JSON, `summary.canvas = "multi_panel"`, 18 items.
**Trigger:** `<|artist|>fkey<|/artist|>` then a literal `\n`.

### Derived canvas

The item extents are x in [-490, 490] and y in [-740, 740]. That resolves to:

- width 1024 (x range -512..512, margins 22 px left and 32 px right)
- height 1536 (y range -768..768, margins 28 px top and bottom)

Both are multiples of 16 and 1024x1536 = 1.57 MP, just inside MOSS-Image's
1.5 MP band.

### Panel map (absolute pixels, 1024x1536)

```
  0    22                                            602                 992
  28   +----------------------------------------------+  +------------------+
       |  PANEL A  top-left horizontal               |  | PANEL B         |
       |  (32,28)-(632,248)  traveler stretching     |  | upper-right     |
 248   +----------------------------------------------+  | tall column     |
 268   +----------------------------------------------+  | (592,38)        |
       |  PANEL C  middle-left, inn exterior         |  | -(992,738)      |
       |  (22,268)-(602,618)                         |  | traveler + car  |
 618   +---------------------------+                  |  |                 |
       |  TITLE logo               |                  |  |                 |
 748   +---------------------------+                  |  |                 |
       |  PANEL E  lower-left      |  +-------------------------------+
 808   |  narrow vertical         |  | PANEL D  main portrait         |
       |  (22,808)-(242,1448)      |  | (252,728)-(1002,1508)          |
       |  hallway, girl + traveler |  | girl, waist-up, greets         |
1448   +---------------------------+  +-------------------------------+
```

Reading order: left to right, top to bottom (Chinese-comic order).

### Item table

| # | label | role | absolute xyxy (px) | size | glyph pitch |
| --- | --- | --- | --- | --- | --- |
| 0 | object | Panel A, top-left horizontal | 32,28,632,248 | 600x220 | - |
| 1 | object | Panel B, upper-right tall | 592,38,992,738 | 400x700 | - |
| 2 | object | Panel C, middle-left inn | 22,268,602,618 | 580x350 | - |
| 3 | text | Title logo | 22,618,362,748 | 340x130 | 28 px horizontal |
| 4 | character | Panel D, main portrait | 252,728,1002,1508 | 750x780 | - |
| 5 | object | Panel E, lower-left sub-panel | 22,808,242,1448 | 220x640 | - |
| 6 | text | SFX 咔嗒 | 902,28,982,158 | 80x130 | 53 px |
| 7 | text | Narration, upper-right | 772,48,852,258 | 80x210 | 19 px |
| 8 | text | Narration, top-center | 532,28,607,208 | 75x180 | 23 px |
| 9 | text | Narration, upper-left panel | 212,38,357,238 | 145x200 | 18 px |
| 10 | text | Narration, far upper-left | 42,38,162,238 | 120x200 | 13 px |
| 11 | text | Narration, middle-center | 452,288,522,488 | 70x200 | 14 px |
| 12 | text | Narration, above inn roof | 332,288,432,488 | 100x200 | 13 px |
| 13 | text | Balloon 你好！ | 122,588,202,738 | 80x150 | 45 px |
| 14 | text | Balloon 您是今天预约的客人吗？ | 672,728,777,1028 | 105x300 | 25 px |
| 15 | text | Balloon 你好啊 / 今天请多关照 | 692,998,792,1198 | 100x200 | 30 px |
| 16 | text | Balloon 哇—谢谢您！… | 242,738,372,1108 | 130x370 | 20 px |
| 17 | text | Name tag 白泽美咲（15） | 242,1388,482,1458 | 240x70 | 34 px horizontal |

### What to copy from this page

- **Narration over detailed art is small**: 13-23 px glyphs, 33-40 px column
  pitch. Six narration boxes on this page all sit at that size.
- **Balloon glyph size scales inversely with the line length**: 45 px for a
  3-glyph greeting, 20 px for an 18-character line. Body dialogue should
  land at 20-30 px.
- **Text boxes float over art panels.** Items 11 and 12 sit inside the inn
  panel's area (22,268)-(602,618) - that is intended, narration overlays the
  painting.
- **The character descriptor is 5 sentences long and reused verbatim.** It
  carries age anchoring ("neither a big-headed 10-year-old child nor a mature
  20-year-old woman"), one signature mark (the mole under the left eye), hair,
  eyes, skin, and clothing.
- **The item captions name the panel position first** ("Top-left horizontal
  panel:", "Upper-right vertical panel:", "Middle-left panel:", "Lower-left
  vertical sub-panel:"), then the content.
- **The text captions name the role and the carrier** ("Clean vertical Chinese
  narration text in speech bubble on the middle-left", "Clean horizontal Chinese
  character name tag near the bottom-left").

### What to fix when copying it

- The `summary.caption` says "2-panel vertical 2D digital painting comic
  (2koma)" while the layout actually has five panels. The caption is a style
  brief, not a panel count - but if you want the model to draw five panels,
  say five in the caption too.
- Item 1 (the upper-right tall panel) overlaps item 2 (the inn panel) by 10 px
  in x, and the title box overlaps the portrait panel. Those overlaps are
  harmless, but a box that crosses a *panel border* is not.
- 1024x1536 is above the FKEY adapter's stated resolution range. Lower the
  LoRA strength to 0.4-0.5 at that size if the layout drifts.

---

## 2. Type B - Commercial clean variant, sectioned wrappers

**Form:** no JSON. Three sections after the trigger.

```
<|artist|>fkey<|/artist|>\n
<|style_and_aesthetic|>…<|/style_and_aesthetic|>
<|left_close_up|>…<|/left_close_up|>
<|right_full_body|>…<|/right_full_body|>
```

### Why this type exists

It is the control case: the same trigger and the same adapter, but the painterly
layer is switched off **by the negative prompt** rather than by lowering the
strength. The positive asks for the opposite of FKEY's usual rendering:
"Ultra-polished, high-completion commercial 2D anime illustration …
fully finished studio masterpiece with zero rough brushstrokes and zero sketch
lines."

### Structure

| Section | Job | Length |
| --- | --- | --- |
| `style_and_aesthetic` | medium, rendering quality, palette, light, subject count | 1 long sentence chain |
| one section per region | what occupies that region of the frame, in full detail | 3-6 sentences each |

The region sections work like invisible boxes: each one scopes its paragraph to
a part of the frame. The reference uses "Occupying the left half of the frame
in a large waist-up close-up:" and "In sharp contrast, standing on the right
side in a smaller full-body view:" - the position is stated in words.

### Character handling

The same girl is described twice, and the second description opens with "the
exact same tall, long-legged 17-year-old blonde braided girl with elegant
7.5-head-tall bishoujo proportions". Repeating the full descriptor is what
makes the two views read as one character.

### Negative

`--style clean --age teen17` is the matching pair. Note that this variant's
anatomy block includes `text` - correct for this page, because a split
character illustration has no lettering. It must not be copied to a page with
dialogue.

---

## 3. Type C - Single-frame portrait, dark window light

**Form:** Layout JSON, `summary.canvas = "single"`, 11 items (1 character +
10 narration boxes).

### Derived canvas

Same as type A: x in [-490, 480], y in [-680, 720] -> **1024x1536**.

### Item table

| # | label | role | absolute xyxy (px) | size | lines x glyphs | glyph pitch |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | character | Main diagonal portrait | 232,348,992,1488 | 760x1140 | - | - |
| 1 | text | Narration, top-right | 802,88,952,378 | 150x290 | 2 x 10 | 26 px |
| 2 | text | Narration, upper-right thin | 732,268,807,478 | 75x210 | 1 x 7 | 27 px |
| 3 | text | Narration, upper-center | 602,118,722,458 | 120x340 | 2 x 9 | 34 px |
| 4 | text | Narration, near center | 542,278,607,548 | 65x270 | 1 x 9 | 27 px |
| 5 | text | Narration, upper-left | 102,98,252,448 | 150x350 | 3 x 10 | 32 px |
| 6 | text | Narration, far upper-left | 52,338,117,518 | 65x180 | 1 x 6 | 27 px |
| 7 | text | Narration, middle-left | 202,578,352,888 | 150x310 | 3 x 8 | 33 px |
| 8 | text | Narration, middle-left thin | 147,728,212,1008 | 65x280 | 1 x 12 | 21 px |
| 9 | text | Narration, bottom-left | 67,1068,247,1418 | 180x350 | 4 x 10 | 30 px |
| 10 | text | Narration, far bottom-left | 22,1198,82,1478 | 60x280 | 1 x 9 | 28 px |

### What to copy from this page

- **On a single canvas the narration is roughly twice the size of the
  multi-panel page**: 21-34 px glyphs against 13-23 px. The single canvas has
  empty space to spend; the comic page is already full.
- **Column pitch 45-75 px**, glyph pitch 23-39 px.
- **Every narration caption says "in a white rectangular box"** - on a single
  canvas the boxes are drawn explicitly, because there is no panel border to
  imply them.
- **The narration column hugs the left and right margins** of the character,
  leaving the figure a clean corridor in the middle. Items 1-10 form two
  vertical stacks down the left and right sides.
- The single canvas has **one character item and ten text items** - the boxes
  are for the lettering, the character box is for the figure.

---

## 4. How the three types differ

| | Type A | Type B | Type C |
| --- | --- | --- | --- |
| Body | Layout JSON | sectioned prose | Layout JSON |
| `summary.canvas` | `multi_panel` | n/a | `single` |
| Items | 18 (5 scene + 1 character + 12 text) | 3 sections | 11 (1 character + 10 text) |
| Text size | 13-23 px glyphs over art | n/a | 21-34 px glyphs |
| Panel grid | explicit boxes | described in words | none |
| Best for | episodic pages, 2-koma, 4-koma | split compositions, character sheets, cinematic pages | a single portrait with a narration layer |
| Negative pair | `--style painterly --age teen` | `--style clean --age teen17` | `--style painterly --age teen` |

The trigger line, the negative block structure and the sampling settings are
identical across all three.
