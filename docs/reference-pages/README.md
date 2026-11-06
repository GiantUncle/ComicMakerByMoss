# Reference pages — what was extracted

Twenty-one real manga pages sit at the repository root as **technique
references**. They are read to extract **grammar, not art**: no page is copied,
and none is a density target. This note records what was taken from them and
where each rule now lives.

| file | note |
| --- | --- |
| `01.png` – `09.png` | A talk-show / office-worker set. 3-4 tiers, abutting panels with white gutters, vertical narration boxes, tails to the mouth, SFX on the art. |
| `001.jpg` – `008.jpg` | A domestic two-hander. The same grammar at a slower pace: rectangular narration for time and place, black-filled boxes for a heavy inner voice, jagged balloons for shocks, SFX at the source. |
| `0001.png` – `0004.png` | The adult/character set. The **focus strategy**: a huge heroine panel plus a small inset reaction, 2+2+1 and 1+2+1 pages, one or two focuses. |

These pages are the source for:

- **Text treatment grammar** — `manga-craft/comic-planning.md` §6.0. Three roles
  (speech / narration / SFX); the shape follows the role, not the page: rounded or
  oval for calm speech, rectangular for a flat line, jagged for a shout, cloud for
  thought, a tail to the mouth; narration is a **rectangle with no tail** (thin,
  solid white, or solid black with white text); SFX is lettering on the art with a
  white halo, at the source, allowed to break the border. Text on a surface
  (signs, notices, door numbers, 短冊) is part of the scene, never a balloon.
- **Placement and density** — §6.1. Balloons in negative space, clear of the face;
  first speaker on the right; narration may span panels, a balloon may not; density
  follows the scene (talky → several small balloons, action → one big SFX).
- **Focus strategy and page strategies** — §11. One dominant panel per page; a huge
  focus stands alone; two focuses are both medium; `routine / thought / character /
  space / pair / ensemble`, each fixing the panel-size profile, the focus and the
  background treatment; **at least one panel per page shows the place**; a huge
  `space` panel is a third to a half of the page.
- **Panel-count balance** — a typical page is 3-4 panels, a casual one reaches 5.
  This is why detailed cuts (5+ / insets) are opt-in (`detail_panels`).

Character description was **not** taken from these pages. It follows the
appearance-extraction contract in `manga-craft/character-consistency.md` §9
(apparent sex first, then face/build/features/hair/clothing; never pose,
expression, gaze, camera, light, background, style or age; age is a separate
question; one concise English paragraph).

The rule for using all of this is in `comic-planning.md` §11: these are
**strategies the agent chooses per project and per page**, not rules applied
everywhere.
