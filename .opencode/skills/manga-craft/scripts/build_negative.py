#!/usr/bin/env python3
"""Assemble the sectioned negative prompt used by MOSS-Image comic workflows.

MOSS-Image reads three independent negative blocks, each wrapped in its own
structural token pair.  Keeping them apart means one block can be swapped
without touching the others:

    <|texture_and_style_neg|>...<|/texture_and_style_neg|>
    <|age_and_body_neg|>...<|/age_and_body_neg|>
    <|universal_anatomy_neg|>...<|/universal_anatomy_neg|>

Usage
-----
    python build_negative.py
    python build_negative.py --style clean --age teen17
    python build_negative.py --style painterly --ban "extra limbs, watermark"
    python build_negative.py --base-only
    python build_negative.py --list

Sets come from the FKEY style adapter templates for MOSS-Image-SFT
(CivitAI model 3013321), which are the reference comic configuration.
"""

from __future__ import annotations

import argparse
import sys

TEXTURE_PAINTERLY = (
    "photorealistic, real human, 3d render, cgi, photograph, monochrome, greyscale, "
    "black and white, screentones, draft, messy lines, manga draft, lineart only, sketch, "
    "rough sketch, messy construction lines, uncolored patches, unpolished, camera flash, "
    "microscopic pores, film grain, green skin, zombie skin, blotchy skin patches, "
    "harsh unblended skin blocks, over-sharpened hard edges, vector art, plastic skin, "
    "oversaturated neon colors, gaudy gold embroidery, wet long hair covering eyes, "
    "thick black outlines"
)

TEXTURE_CLEAN = (
    "nsfw, nude, naked, cleavage, underwear, bra, panties, exposed skin, sexual, bodily fluids, "
    "sweat, cum, unfinished, unpolished, rough brushwork, visible brushstrokes, gouache, "
    "watercolor bleed, impasto, painterly, sketch, rough sketch, draft, wip, work in progress, "
    "messy lines, loose lines, uncolored patches, flat shading, blurry edges, smudged, "
    "photorealistic, real human, 3d render, cgi, photograph, monochrome, greyscale, screentones, "
    "camera flash, microscopic pores, film grain, blotchy skin, vector art, plastic skin, "
    "thick black outlines, pokemon, nintendo, cosplay, wig"
)

TEXTURE_LINEART = (
    "photorealistic, real human, 3d render, cgi, photograph, color, colored, full color, "
    "flat color, cel shading, screentones, blotchy skin, plastic skin, wet long hair covering eyes, "
    "thick black outlines, messy lines, rough sketch, watermark, signature"
)

AGE_TEEN = (
    "child, toddler, preteen, loli, 6 years old, 8 years old, 10 years old, oversized head, "
    "big round babyface, short stubby neck, wide-open staring eyes, doll-like stiff face, "
    "flat chest, mature 20-year-old woman, adult woman, milf, old, 25 years old, 30 years old, "
    "curvy, plump, chubby, fat, wide adult hips, large breasts, huge breasts, C-cup, "
    "hard muscle planes, six-pack abs, gaunt ribs, heavy makeup, thick black eyelashes"
)

AGE_TEEN17 = (
    "11 years old, 12 years old, 13 years old, 5-head-tall, 6-head-tall, short legs, stubby legs, "
    "round chubby cheeks, baby fat, elementary school student, child, toddler, preteen, loli, "
    "6 years old, 8 years old, 10 years old, oversized head, big round babyface, short stubby neck, "
    "wide-open staring eyes, doll-like stiff face, flat chest, mature 30-year-old woman, milf, old, "
    "curvy, plump, chubby, fat, wide adult hips, huge breasts, D-cup, hard muscle planes, "
    "six-pack abs, gaunt ribs, heavy makeup"
)

AGE_ADULT = (
    "child, toddler, preteen, loli, oversized head, big round babyface, short stubby neck, "
    "doll-like stiff face, wide-open staring eyes, heavy makeup, thick black eyelashes"
)

ANATOMY = (
    "blurry, out of focus, lowres, censored, mosaic censoring, bar censor, ugly face, "
    "distorted face, overly squished grotesque cheek, worst quality, bad anatomy, fused bodies, "
    "fused legs, extra limbs, extra arms, extra legs, extra hands, three hands, extra fingers, "
    "mutated hands, fused fingers, six fingers, extra penis, two penises, detached penis, "
    "floating hand, watermark, signature"
)

ANATOMY_WITH_TEXT = (
    "blurry, out of focus, lowres, ugly face, distorted face, worst quality, bad anatomy, "
    "fused bodies, fused legs, extra limbs, extra arms, extra legs, extra hands, three hands, "
    "extra fingers, mutated hands, fused fingers, six fingers, polydactyly, malformed hands, "
    "claw hand, cramped fingers, twisted wrist, broken finger joints, feet cut off, "
    "watermark, text, signature"
)

BASE_ONLY = "nsfw, worst quality, bad anatomy, watermark, jpeg artifact"

TEXTURE_SETS = {
    "painterly": TEXTURE_PAINTERLY,
    "clean": TEXTURE_CLEAN,
    "lineart": TEXTURE_LINEART,
}

AGE_SETS = {
    "teen": AGE_TEEN,
    "teen17": AGE_TEEN17,
    "adult": AGE_ADULT,
}


def wrap(name: str, body: str) -> str:
    return f"<|{name}|>{body}<|/{name}|>"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a sectioned MOSS-Image negative prompt for comics."
    )
    parser.add_argument(
        "--style",
        choices=sorted(TEXTURE_SETS),
        default="painterly",
        help="texture/style block: painterly (default), clean, lineart",
    )
    parser.add_argument(
        "--age",
        choices=sorted(AGE_SETS),
        default="teen",
        help="age/body block: teen (default), teen17, adult",
    )
    parser.add_argument(
        "--ban-text",
        action="store_true",
        help="also ban rendered text (destroys dialogue - only for text-free art)",
    )
    parser.add_argument(
        "--ban", action="append", default=[], help="extra negative terms (repeatable)"
    )
    parser.add_argument(
        "--base-only",
        action="store_true",
        help="print the official MOSS base negative instead of the sectioned blocks",
    )
    parser.add_argument(
        "--list", action="store_true", help="list the available sets and exit"
    )
    args = parser.parse_args(argv)

    if args.list:
        print("style sets : " + ", ".join(sorted(TEXTURE_SETS)))
        print("age sets   : " + ", ".join(sorted(AGE_SETS)))
        print("base only  : " + BASE_ONLY)
        return 0

    if args.base_only:
        print(BASE_ONLY)
        return 0

    texture = TEXTURE_SETS[args.style]
    age = AGE_SETS[args.age]
    anatomy = ANATOMY_WITH_TEXT if args.ban_text else ANATOMY

    if args.ban:
        extra = ", ".join(term.strip() for term in args.ban if term.strip())
        if extra:
            texture = f"{texture}, {extra}"

    print(wrap("texture_and_style_neg", texture))
    print(wrap("age_and_body_neg", age))
    print(wrap("universal_anatomy_neg", anatomy))
    return 0


if __name__ == "__main__":
    sys.exit(main())
