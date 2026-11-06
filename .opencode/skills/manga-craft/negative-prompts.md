# Negative prompts for MOSS-Image comics

> **When to ship these.** The authoring spec (§13.2) says the default deliverable
> is a single positive prompt, and negatives or sampling parameters are added
> only when the user asks. This comic workflow is the exception: the three
> sectioned blocks are part of the standard comic output. So: **emit the three
> blocks for comic/manga requests, and follow the spec for everything else.**

MOSS-Image's negative branch works best as three **independent, sectioned**
blocks. Each block can be swapped without touching the others, which is what
makes them practical for a comic workflow where one page may need a different
texture treatment from the next.

```
<|texture_and_style_neg|>…<|/texture_and_style_neg|>
<|age_and_body_neg|>…<|/age_and_body_neg|>
<|universal_anatomy_neg|>…<|/universal_anatomy_neg|>
```

Build them with:

```bash
python scripts/build_negative.py --style painterly --age teen
python scripts/build_negative.py --style clean --age teen17
python scripts/build_negative.py --style painterly --ban "extra ears, mask"
python scripts/build_negative.py --base-only
```

---

## 1. The three blocks and what they are for

### `texture_and_style_neg` - kills the wrong medium

This is the block that decides whether the page looks like a painted illustration
or like a photograph / sketch / 3D render. It is the single most important
block for a comic page.

- `painterly` (default for comics): bans photorealism, 3D render, CGI,
  monochrome, screentones, sketch lines, construction lines, uncolored patches,
  film grain, vector art, plastic skin, neon oversaturation, heavy outlines.
  Keeps the FKEY gouache brushwork alive.
- `clean`: the opposite move. It bans `rough brushwork, visible brushstrokes,
  gouache, watercolor bleed, impasto, painterly, sketch, wip, flat shading` and
  also adds `nsfw, nude, cleavage, underwear, bra, panties, exposed skin,
  sexual, bodily fluids, sweat, cum`. Used when you want a commercially clean
  line-art illustration instead of a painterly one. The positive prompt must
  then explicitly ask for "crisp, refined delicate lineart … zero rough
  brushstrokes and zero sketch lines", because the adapter's default is the
  opposite.
- `lineart`: for monochrome ink pages - bans colour, cel shading and heavy
  skin rendering, keeps the drawing.

One texture block at a time: `painterly` and `clean` contradict each other.

### `age_and_body_neg` - pins the age

Keeps a teenage character from drifting into child proportions or into adult
proportions. It works as a *bracketing* block: it bans the age below the target
and the age above it.

- `teen` (default): bans `child, toddler, preteen, loli, 6/8/10 years old,
  oversized head, big round babyface, short stubby neck, wide-open staring eyes,
  doll-like stiff face, flat chest` and, on the other side, `mature 20-year-old
  woman, adult woman, milf, old, 25 years old, 30 years old, curvy, plump,
  chubby, fat, wide adult hips, large breasts, huge breasts, C-cup, hard muscle
  planes, six-pack abs, gaunt ribs, heavy makeup, thick black eyelashes`.
- `teen17`: for a tall 7.5-head-tall 17-year-old. Adds the proportion terms
  `5-head-tall, 6-head-tall, short legs, stubby legs, round chubby cheeks,
  baby fat, elementary school student` and bans `11/12/13 years old`. Use it
  whenever the character is described as tall or long-limbed, or the model will
  shorten the legs.
- `adult`: keeps the page adult - bans child terms only.

The `thick black eyelashes` term in the `teen` set is there to stop the model
from rendering adult femme-fatale makeup; it is intentional, not a typo.

### `universal_anatomy_neg` - the broken-image guard

`blurry, out of focus, lowres, censored, mosaic censoring, bar censor, ugly
face, distorted face, overly squished grotesque cheek, worst quality, bad
anatomy, fused bodies, fused legs, extra limbs, extra arms, extra legs, extra
hands, three hands, extra fingers, mutated hands, fused fingers, six fingers,
extra penis, two penises, detached penis, floating hand, watermark, signature`.

A second variant swaps the censoring terms for `polydactyly, malformed hands,
claw hand, cramped fingers, twisted wrist, broken finger joints, feet cut off`
and adds `text`.

> **A page with dialogue keeps `text` out of its negative branch.** `text` there
> removes the rendered lettering. `build_negative.py --ban-text` is opt-in for
> that reason.

---

## 2. The official base negative

The OpenMOSS user guide suggests:

```
nsfw, worst quality, bad anatomy, watermark, jpeg artifact
```

That is the whole official recommendation. Use it (`--base-only`) for
non-comic work or as a base to extend. The sectioned sets above are the
community-standard comic configuration and are strictly more specific.

---

## 3. Term blocks to mix in

| Situation | Add to `texture_and_style_neg` |
| --- | --- |
| Cosplay / mascot look | `cosplay, wig, pokemon, nintendo` |
| Clean commercial look | see the `clean` set |
| No halftone / screentone | `screentones` (already in every set) |
| Keep skin warm and matte | `green skin, zombie skin, blotchy skin patches, harsh unblended skin blocks` (already in `painterly`) |
| No metallic filigree | `gaudy gold embroidery` (already in `painterly`) |

| Situation | Add to `universal_anatomy_neg` |
| --- | --- |
| Hands are a problem | `polydactyly, malformed hands, claw hand, cramped fingers, twisted wrist, broken finger joints` |
| Extra digits | `six fingers, extra fingers, fused fingers` |
| Framing | `feet cut off` |

---

## 4. Keeping the negative and the positive consistent

The negative is a subtraction from the positive. Two rules keep them aligned:

1. **The negative is a subtraction from the positive.** A term the positive
   asks for stays out of the negative: if the positive wants "visible painterly
   gouache brushwork on the sailor uniform", the negative carries neither
   `painterly` nor `gouache`.
2. **When you switch the negative, switch the positive too.** The `clean` set
   only makes sense next to a positive that asks for "ultra-polished,
   high-completion commercial 2D anime illustration … fully finished studio
   masterpiece with zero rough brushstrokes and zero sketch lines".

---

## 5. Delivery

Ship the three blocks as three separate lines under the positive prompt. Do not
merge them into one comma list: the section wrappers are what let the model
treat them as independent regions of the negative branch.

```
<|texture_and_style_neg|>…<|/texture_and_style_neg|>
<|age_and_body_neg|>…<|/age_and_body_neg|>
<|universal_anatomy_neg|>…<|/universal_anatomy_neg|>
```
