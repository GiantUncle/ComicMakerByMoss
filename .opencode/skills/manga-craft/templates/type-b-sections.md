# Type B - sectioned prose template

No JSON, no boxes. The trigger line plus one style section plus one section
per region. Use for split compositions, character sheets, before/after pairs,
and cinematic pages where boxes would fight the painting.

Copy the block, replace the angle-bracket placeholders, and keep the section
names tight (`<|...|>` with no spaces inside).

---

## Template

```
<|artist|>fkey<|/artist|>\n
<|style_and_aesthetic|><medium and rendering quality>. <palette>. <light>. <subject count and framing>. <the one thing that makes this image work>.<|/style_and_aesthetic|>
<|<region_name_1|><what occupies this region, in full detail>.<|/region_name_1|>
<|<region_name_2|><what occupies this region, in full detail>.<|/region_name_2|>
```

---

## Worked shape (from the reference clean variant)

```
<|artist|>fkey<|/artist|>\n
<|style_and_aesthetic|>Ultra-polished, high-completion commercial 2D anime illustration, character duality split-composition on a clean pastel-blue and warm cream gradient background. Crisp, refined delicate lineart, smooth seamless skin shading with luminous specular highlights, intricately rendered floral lace patterns, and silky hair strands - fully finished studio masterpiece with zero rough brushstrokes and zero sketch lines. Sophisticated warm peach skin, pure white, and pale sky-blue color palette under soft bright indoor daylight, 1girl, multiple views, same character in two states, tall slender 17-year-old girl, 7.5-head-tall proportions, platinum-blonde braided hair, white sundress, safe, wholesome.<|/style_and_aesthetic|>
<|left_close_up|>Occupying the left half of the frame in a large waist-up close-up: <full character descriptor>.<|/left_close_up|>
<|right_full_body|>In sharp contrast, standing on the right side in a smaller full-body view: the exact same <character descriptor, repeated>.<|/right_full_body|>
```

---

## Rules

1. The trigger is the first line, tight token, then the separator. The reference
   samples use a literal `\n` there.
2. `style_and_aesthetic` carries the medium, palette, light and rendering
   quality - the same job as `summary.caption` in the JSON types. If the page
   is meant to look painterly, say so here and use the `painterly` negative set.
   If it is meant to look clean, say "zero rough brushstrokes and zero sketch
   lines" and use the `clean` negative set.
3. Each region section states its position in words ("Occupying the left half
   of the frame", "In sharp contrast, standing on the right side").
4. The same character appearing in two regions is described twice, and the
   second description opens with "the exact same".
5. No coordinates. This type has no boxes.
6. Ship the three sectioned negative blocks with it.
