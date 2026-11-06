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

1. Read the episode's source and list every character who speaks or matters in
   this episode, plus the recurring props. Those already in the pool stay as they
   are; the new ones are the work of this pass. Ask the user to confirm, rename,
   add or remove.
2. Record the episode's cast subset in `episodes/<ep>/episode.json` — the pool
   members who appear in this episode, by slug.
3. Write the pool:

```jsonc
{
  "characters": [
    {
      "id": "sol-eum",                              // name slug — also the folder name
      "name": { "ko": "김솔음", "en": "Kim Sol-eum", "ja": "キム・ソルム" },
      "role": { "ko": "주임", "en": "junior officer", "ja": "主任" },
      "age_phrase": "a woman in her mid-twenties",
      "anchors": ["a soft oval face", "calm dark eyes", "a low ponytail"],
      "signature": "a small mole under the left eye",
      "body": "slender, held upright",
      "default_outfit": "a fitted charcoal studio suit over a crisp white shirt",
      "descriptor": "She is a woman in her mid-twenties with a soft oval face, calm dark eyes and a small mole under the left eye, her sleek dark hair pulled into a low ponytail; she is slender and held upright, and wears a fitted charcoal studio suit over a crisp white shirt.",
      "identifier_label": "the young woman",
      "reference": { "sheet": null, "approved": false },
      "consistency_risk": "HIGH",
      "first_seen_episode": "ep01"
    }
  ],
  "objects": [ { "id": "rag-bear", "name": {…}, "descriptor": "…" } ]
}
```

4. **`id` is a kebab-case slug of the character's name** — `sol-eum`, `brown`,
   `lee-jaheon`. It is the folder name and the wiring key.
   A walk-on with no name takes a slug of the role: `masked-chief`, `bus-driver`.

5. **`descriptor` is appearance only.** Age, build, face, hair, eyes, the one
   signature detail, and the default outfit. **No art style, no medium, no
   camera, no lighting.** Style belongs to the project and is applied when the
   sheet is rendered; baking "gouache 2D illustration" into a character makes
   every character carry the same style sentence and says nothing about the
   face.
6. `name` carries all three languages. A name enters an image only where the
   name itself is drawn — a name tag, a sign, a title. Everywhere else a person
   is **described, not named**: the `descriptor` and the `identifier_label`
   carry identity. `descriptor` stays in English.
7. Stamp `bible/APPROVED`.

## Done when

- Every card has a name-slug `id`, a 3-language `name`, 2-4 anchors, exactly one
  signature, and an appearance-only `descriptor`.
- The episode's `cast` lists every character who appears in it, by slug.
- `bible/APPROVED` exists.

## Hand over

Say the cast is locked, and that **stage 4 (`manga-4-refsheets`)** is next.
