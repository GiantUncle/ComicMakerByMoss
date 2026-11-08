/**
 * Drawing-style presets — the user picks the look, not the story model.
 *
 * Each preset is one ready sentence for `summary.caption` (medium, rendering,
 * palette guidance). Picking one fills the editable box; editing it makes a
 * custom style. One list, shared by every screen that sets a look.
 */

export interface StylePreset {
  id: string;
  label: string;
  prompt: string;
}

export const STYLE_PRESETS: StylePreset[] = [
  {
    id: "painterly",
    label: "2D 페인팅 만화",
    prompt:
      "2D digital painting comic, finely rendered luminous facial features and delicate hair strands against breathable painterly brushwork, selective focus",
  },
  {
    id: "clean",
    label: "깔끔한 애니 셀",
    prompt:
      "crisp anime cel-shaded illustration, refined delicate lineart, smooth flat cel shading, clean uncluttered finish",
  },
  {
    id: "watercolor",
    label: "수채화",
    prompt: "watercolor illustration, soft pastel bleed on rough textured paper, gentle washes",
  },
  {
    id: "ink",
    label: "먹선 만화",
    prompt: "black-and-white manga ink illustration, bold sumi contour lines, screentone shading",
  },
  {
    id: "photoreal",
    label: "실사 사진",
    prompt: "photorealistic photograph, natural skin texture and honest lighting, shallow depth of field",
  },
];

export const DEFAULT_STYLE_PROMPT = STYLE_PRESETS[0].prompt;
