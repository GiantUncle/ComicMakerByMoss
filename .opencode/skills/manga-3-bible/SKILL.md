---
name: Manga 3 Bible
description: Stage 3 of the manga pipeline. Builds the project's cast pool at projects/<slug>/bible/characters.json — each character with a name-slug id, anchor terms, one signature and one canonical appearance-only descriptor — and stamps bible/APPROVED. Extends the pool for a new episode. Use after project.json exists, or when the wizard hands over stage 3.
---

# Stage 3 — Bible

**Requires** — `episodes/<ep>/source/APPROVED`, `project.json`.
**Produces** — `projects/<slug>/bible/characters.json`,
`projects/<slug>/bible/APPROVED`, and the episode's `cast` list.
**Gate** — `bible/APPROVED`.

Character rules are in `../manga-craft/character-consistency.md` (R-A~R-E) and
`../manga-craft/authoring-spec.md` §7. This stage owns the cast; it does not draw
them.

## Steps

1. Read the episode's source — `episodes/<ep>/source/novel.txt` (manga) or
   `episodes/<ep>/source/brief.md` (comic) — and list every character who speaks
   or matters in it, plus the recurring props. Those already in the pool stay as
   they are; the new ones are the work of this pass. Ask the user to confirm,
   rename, add or remove.
2. Record the episode's cast subset in `episodes/<ep>/episode.json` — the pool
   members who appear in this episode, by slug.
3. Write the pool:

```jsonc
{
  "characters": [
    {
      "id": "sol-eum",                              // slug — also the folder name
      "name": { "ko": "김솔음", "en": "Kim Sol-eum", "ja": "キム・ソルム" },  // optional; omit or leave empty if unnamed
      "role": { "ko": "주임", "en": "junior officer", "ja": "主任" },
      "age_phrase": "a woman in her mid-twenties",
      "anchors": ["a soft oval face", "calm dark eyes", "a low ponytail"],
      "signature": "a small mole under the left eye",
      "body": "slender, held upright",
      "default_outfit": "a fitted charcoal studio suit over a crisp white shirt",
      "descriptor": "Apparent age group: young adult. She is a woman with a soft oval face, calm dark eyes and a small mole under the left eye, her sleek dark hair pulled into a low ponytail; she is slender and held upright, and wears a fitted charcoal studio suit over a crisp white shirt.",
      "identifier_label": "the young woman",
      "reference": { "sheet": null, "approved": false },
      "consistency_risk": "HIGH",
      "first_seen_episode": "ep01"
    }
  ],
  "objects": [ { "id": "rag-bear", "name": {…}, "descriptor": "…" } ]
}
```

**The example above is a shape, not content.** Never copy its names, anchors or
outfits — derive every card from the source. A card whose anchors match the
example instead of the story is wrong.

4. **`id` is a kebab-case slug of the character's name** — `sol-eum`, `brown`,
   `lee-jaheon`. It is the folder name and the wiring key.
   A walk-on with no name takes a slug of the role: `masked-chief`, `bus-driver`.
   **`identifier_label` carries the single strongest identifier** — the one
   adjective that tells this character from every other on the page (reference:
   `the bald traveler`, `the petite 15-year-old sailor-uniform schoolgirl`).
   `the young woman` / `the young man` is too weak: they differ only by the noun.

5. **`descriptor` is appearance only, and its shape is fixed by
   `../manga-craft/character-consistency.md` §9.** Write it as that contract
   says:

   - **Start with the apparent age group**, exactly one of `child · young
     teenager · older teenager · young adult · adult in their thirties ·
     middle-aged · elderly`, in the form `Apparent age group: young adult.`
   - then apparent sex, then **face shape · build · distinctive facial features
     (moles, freckles) · skin tone · eye shape, size and colour · hair (length,
     colour, style, bangs) · headwear · accessories · clothing (collar, sleeves,
     decorations)**.
   - **Clothing is the garment, not its current state.** A fastener is described
     as part of the garment (`a fitted jacket with a front zip`), never in a
     position the story will change (`zipped to the collar`, `sleeves pushed up`).
     The descriptor is pasted onto every page, so a baked state contradicts the
     action on the page where it changes.
   - Cover **each item in the §9 list** — do not drop **eye size**, hair style, or
     the collar/sleeves of the clothing.
   - **Never** pose, expression, gaze, camera angle, framing, lighting,
     background, art style or medium, a numeric age, or invented names,
     personality or backstory. If several figures are visible, describe one.
   - **One concise English paragraph** — no headings, bullets or JSON inside it.
   - **Write positives only.** A descriptor never says what a figure lacks
     (`no hair`, `no skin tone`, `no accessories`): say what is there instead
     (`a bare CRT television head`, `unpainted metal`, `bare hands`). A
     "no X" sentence is mis-read as "X" by the drawing model
     (`../manga-craft/authoring-spec.md` §11.4).

   Style belongs to the project and is applied when the sheet is rendered;
   baking "gouache 2D illustration" into a character makes every character carry
   the same style sentence and says nothing about the face.

   **The `default_outfit` follows the story.** The descriptor is copied onto the
   frame that anchors the character, so it must match what the source/brief has
   them wearing (a uniform, a costume, a specific garment). If the brief puts the
   character in a high-neck zip dress, that is the `default_outfit` — not a
   generic cardigan. A deliberately different outfit is a per-frame change, not
   the card.
6. **`name` is optional.** If the story names the character, write the name in
   all three languages. If the story gives no name, **leave `name` empty** (all
   three empty, or omit the field) — do not invent one. A person is
   **described, not named**: identity is the `descriptor`, and `id` (the slug) is
   the wiring key. A name enters an image only where the name itself is drawn — a
   name tag, a sign, a title. `descriptor` stays in English.
7. Stamp `bible/APPROVED`.

## Done when

- Every card has a slug `id`, 2-4 anchors, exactly one signature, and an
  appearance-only `descriptor`. `name` is in all three languages **or empty**
  (a character the story never names).
- The episode's `cast` lists every character who appears in it, by slug.
- `bible/APPROVED` exists.

## Hand over

Say the cast is locked, and that **stage 4 (`manga-4-refsheets`)** is next.
