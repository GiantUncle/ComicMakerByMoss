# MOSS-Image prompt formats

Everything here was checked against the OpenMOSS `USERGUIDE.md`, the ComfyUI
`MOSSImageLayoutPrompt` node source, the OpenMOSS `moss-image-prompt-enhancer`
skill, and the official OpenMOSS example prompts (all Apache-2.0).

---

## 1. The forms MOSS-Image accepts

| # | Form | Shape | Use |
| --- | --- | --- | --- |
| 1 | Natural-language prose | one or more paragraphs | default; the model was trained on long descriptive captions |
| 2 | Tag sequence | comma-separated tags | anime-style images, no text |
| 3 | **Layout JSON** | `summary` + `items` + boxes | posters, multi-panel comics, anything with text placement |
| 4 | **Scene JSON** | `scene_type` + `gen_brief` + `elements` | long multi-panel strips, dense scene control |
| 5 | **Sectioned wrappers** | `<\|section\|>…<\|/section\|>` | regional control, FKEY style adapters |

Forms 3-5 can be mixed with plain prose. The text encoder is a frozen Qwen3.5-9B
LLM, so it parses JSON and understands `<|...|>` structural tokens.

**Language:** English has the most training data and is the safer default for
*descriptive* prose. Chinese is well supported for both prose and rendered
text - write the Chinese characters directly.

**Length:** up to 4096 tokens.

---

## 2. Layout JSON (the bbox format)

### Schema

```json
{
  "summary": {
    "meta": ["comic", "multi_panel", "digital_painting"],
    "canvas": "multi_panel",
    "caption": "High-taste, fully colored 2D digital painting comic with selective focus: …"
  },
  "items": [
    {
      "label": "character",
      "caption": "Main lower-center portrait focus: …",
      "bbox": [-40, -260, 740, 490]
    },
    {
      "label": "text",
      "caption": "Clean vertical Chinese narration text on the upper-right.",
      "text": "人生过四十之后，我把\n旅行定为了自己的爱好",
      "bbox": [-720, 260, -510, 340]
    }
  ],
  "bbox_coord_space": "abs_centralized",
  "bbox_format": "yxyx"
}
```

### Fields

| Field | Required | Meaning |
| --- | --- | --- |
| `summary.caption` | yes | The whole scene and its style. Medium, palette, lighting, rendering quality. Not the plot. |
| `summary.meta` | no | Array of medium/genre tags: `poster`, `comic`, `multi_panel`, `digital_painting`, `photograph`. |
| `summary.canvas` | no | `single`, `multi_panel`, `collage`. |
| `summary.palette` | no | Array of colour names or hex codes. |
| `items[].label` | yes | `text`, `object`, `character`, `panel`, `subject`. |
| `items[].caption` | yes | What the element looks like. The box says *where*; the caption says *what and how*. |
| `items[].text` | for `text` | The exact characters to render. Verbatim, original language, `\n` for line breaks. |
| `items[].bbox` | yes | `[y_min, x_min, y_max, x_max]`, absolute pixels, origin at canvas centre. |
| `items[].tags` | no | Short keyword tags for the element. |
| `items[].palette` | no | Colours for the element. |
| `bbox_coord_space` | yes | `abs_centralized`. |
| `bbox_format` | yes | `yxyx`. |

The ComfyUI node writes `text` / `object` / `character`; the official OpenMOSS
examples additionally use `panel` (a background or frame region) and `subject`
(the main figure of a frame).

### Label semantics

- `panel` - a background, frame, UI region, or the whole-canvas backdrop.
- `subject` - the principal figure of a frame (the official Chinese-textbook and
  livestream examples use it for this).
- `character` - a person with an identity; the ComfyUI node's "character" flag.
- `object` - a prop, a setting, a secondary figure, a whole panel scene.
- `text` - rendered lettering; requires `text`.

Use `character` for recurring cast members so the model treats them as people
rather than props.

### Coordinate maths

`abs_centralized` means absolute pixels with the **canvas centre as the origin**.
x grows right, y grows down. For a canvas of width W and height H:

```
x_centred = x_abs - W / 2
y_centred = y_abs - H / 2
```

Worked example on a 1024x1024 canvas: a box at top-left 128,64 to bottom-right
896,192 becomes

```
[ 64 - 512, 128 - 512, 192 - 512, 896 - 512 ] = [ -448, -384, -320, 384 ]
```

Worked example on the 1024x1536 comic page: the top-left panel at absolute
pixels (32,28)-(632,248) becomes

```
y:  28 - 768 = -740      x:  32 - 512 = -480
y: 248 - 768 = -520      x: 632 - 512 =  120
=> [-740, -480, -520, 120]
```

Never do this by hand. `scripts/compile_layout.py` takes `abs`/`xyxy` drafts
and emits `abs_centralized`/`yxyx`, flooring the top-left edge and ceilinging
the bottom-right edge exactly like the ComfyUI node and the official compiler.

### Rules the official docs state

- Start with two or three items. Every extra box is another constraint the
  model may bend.
- Give text room. A squeezed headline gets cut or shrunk.
- Keep important items ~5% away from the canvas edge.
- Put style in `summary.caption`, not repeated in every item caption.
- A box is a *placement annotation* - not a border, panel frame, divider or
  sticker to draw. Overlap and natural occlusion are allowed.
- The model may still move or merge things. Layout control is experimental.

---

## 3. Scene JSON (official multi-panel variant)

Used by the official eight-panel comic example (512x4096, CFG 5). It carries
more control vocabulary than Layout JSON: salience, identity, named colours.

```json
{
  "scene_type": "Eight-panel weekend comic strip",
  "gen_brief": "Create a finished Chinese slice-of-life comic in a very tall 1:8 format…",
  "elements": [
    {
      "type": "obj",
      "salience": "primary",
      "identity": "Eight-panel continuous weekend comic",
      "shape": "Eight equal square panels, slim cream gutters, rounded black borders…",
      "colors": [{ "color": "Warm paper", "hex": "#FFF7E8" }],
      "bbox": [-2048, -256, 2048, 256]
    },
    {
      "type": "obj",
      "salience": "secondary",
      "identity": "Panel one: prepared escape",
      "note": "Establishes completed work and the protagonist's weekend intention.",
      "shape": "Bob-haired woman in mustard hoodie closes laptop, grins…",
      "colors": [{ "color": "Mustard hoodie", "hex": "#E8B64C" }],
      "bbox": [-2036, -244, -1548, 244]
    },
    {
      "type": "text",
      "text": "周五 18:00｜周末摸鱼计划\n老板：周一的报告，别忘了。\n小夏：写完了，定时发送！",
      "shape": "Hand-lettered black Chinese; compact bold caption, two distinct rounded speech balloons…",
      "is_watermark": false,
      "bbox": [-2020, -223, -1851, 223]
    }
  ],
  "must_not": [
    "not a horizontal eight-panel strip or a two-column grid",
    "not a different protagonist or changing clothing between panels"
  ],
  "palette": ["#FFF7E8", "#292C35", "#E8B64C"],
  "bbox_coord_space": "abs_centralized"
}
```

| Field | Meaning |
| --- | --- |
| `scene_type` | one-line genre/format label |
| `gen_brief` | the long creative brief - genre, format, style, arc, consistency rules |
| `elements[].type` | `obj` (object/scene) or `text` |
| `elements[].salience` | `primary` or `secondary` - how much attention the element gets |
| `elements[].identity` | a short stable name for the element ("Panel three: apparent freedom") |
| `elements[].note` | the narrative job of the element |
| `elements[].shape` | its visual description |
| `elements[].colors` | `[{color, hex}]` named palette for the element |
| `elements[].text` | rendered copy (text elements) |
| `elements[].is_watermark` | always `false` for comic copy |
| `must_not` | negative constraints in natural language |
| `palette` | global hex palette |

Note: Scene JSON has **no `bbox_format` key** - its boxes are yxyx by
convention. `compile_layout.py --target scene` converts a Layout-JSON draft
into this shape.

---

## 4. Sectioned `<|...|>` wrappers

Qwen's tokenizer treats `<|...|>` as structural tokens. The FKEY style adapter
for MOSS-Image-SFT uses them as triggers and as region blocks.

### Trigger

```
<|artist|>fkey<|/artist|>
```

- Must be the **very first line** of the positive prompt.
- Tight token: no spaces inside, no trailing period.
- Then a separator. The published samples use a *literal* `\n` (backslash + n,
  two characters). A real newline also works.
- The published samples were generated with the literal form - copying the
  blocks verbatim is safest.

### Positive sections

```
<|style_and_aesthetic|>…medium, palette, lighting, rendering…<|/style_and_aesthetic|>
<|left_close_up|>…what occupies the left half of the frame…<|/left_close_up|>
<|right_full_body|>…what occupies the right half…<|/right_full_body|>
```

Section names are free-form labels; each one scopes its paragraph to a region
or a quality aspect. Use them for split compositions and for prose-heavy
pages where boxes would fight the painting.

### Negative sections

```
<|texture_and_style_neg|>…<|/texture_and_style_neg|>
<|age_and_body_neg|>…<|/age_and_body_neg|>
<|universal_anatomy_neg|>…<|/universal_anatomy_neg|>
```

See `negative-prompts.md`.

---

## 5. Tag sequences

Official order: **quality -> score -> meta -> year -> character -> series ->
artist -> general**.

```
best quality, highres, hatsune miku, vocaloid, @foo bar, 1girl, blue hair
```

Tags work, but the FKEY adapter was trained exclusively on prose, so natural
language gives more consistent results. Never lead with tags.

---

## 6. Canvas and resolution

| Ratio | 1 MP | 1.5 MP | 2 MP |
| --- | --- | --- | --- |
| 1:1 | 992x992 | 1232x1232 | 1408x1408 |
| 4:3 | 1152x864 | 1408x1056 | 1632x1232 |
| 3:2 | 1232x816 | 1504x992 | 1728x1152 |
| 16:9 | 1328x752 | 1632x912 | 1888x1056 |
| 21:9 | 1520x656 | 1872x800 | 2160x928 |
| 3:4 | 864x1152 | 1056x1408 | 1232x1632 |
| 2:3 | 816x1232 | 992x1504 | 1152x1728 |
| 9:16 | 752x1328 | 912x1632 | 1056x1888 |

- Both sides must be **multiples of 16**.
- The model stretches from 0.25 MP to ~4 MP. Official sweet spot: 1, 1.5 or 2 MP.
- The FKEY adapter's own recommendation is lower (~0.65-1.0 MP:
  768x1024, 848x1200, 1024x1024, 1200x848). A 1024x1536 comic page
  (1.57 MP) is legal for MOSS-Image and is what the reference comic pages use,
  but it sits above the adapter's stated range - lower the LoRA strength to
  0.4-0.5 if the layout starts to drift at that size.
- **The box coordinates are tied to the canvas.** Generate at exactly the size
  the boxes were written for.

---

## 7. Sampling settings

| Setting | Official | ComfyUI template | Notes |
| --- | --- | --- | --- |
| Steps | 50 | 25 | >=50 for best results; 30 is a usable middle. |
| CFG | 3.0 | 2.5 | range 3-6; the FKEY adapter burns out above ~4.5. |
| Shift | 5.0 | 5.0 | apply with `ModelSamplingSD3`. |
| Sampler | Euler | er_sde, simple | official plugin uses Euler + sgm_uniform. |
| SLG | skip layer 22 on the negative branch | layer 22, 0-0.5 | layers 22, 24, 26 all help. Off = more photoreal but details collapse. |
| Negative prompt | empty in the Python API | empty | suggested: `nsfw, worst quality, bad anatomy, watermark, jpeg artifact` |
| Prompt upsampler | - | on | **turn it off for layouts** - it rewrites the JSON and drops the boxes. |

Base vs SFT: **SFT for inference.** Base has no post-training and no CFG
distillation; it exists for further LoRA training. The FKEY adapter was
trained directly on SFT.

---

## 8. Sources

- OpenMOSS MOSS-Image `USERGUIDE.md` - layout prompt spec, settings, captioning recipe.
- ComfyUI `comfy_extras/nodes_moss_image.py` - `MOSSImageLayoutPrompt` node, the exact serialisation.
- OpenMOSS `skills/moss-image-prompt-enhancer` - the official agent skill for drafting layouts.
- OpenMOSS official examples (assets 002, 003) - Layout JSON and Scene JSON.
- FKEY Style adapter for MOSS-Image-SFT, CivitAI model 3013321 - the trigger line, the three prompt types, the negative block sets.
