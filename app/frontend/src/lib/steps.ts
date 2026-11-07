/**
 * The steps of one project, in order.
 *
 * 1 스토리 (episode)
 * 2 프로젝트 설정 (project)
 * 3 캐스트 (project)
 * 4 레퍼런스 시트 (project)
 * 5 페이지 계획 (episode)
 * 6 콘티 (episode)      — AI 설계 + 만화가가 페이지를 그림 + 코드가 프롬프트로 내보냄
 * 7 프롬프트 (episode)  — 원고 미리보기/워크벤치 (+ MOSS-Image 프롬프트)
 *
 * Internal creation state may still use step 1 in the wizard when no project exists.
 */

export type Scope = "project" | "episode";

export interface StepMeta {
  n: number;
  label: string;
  scope: Scope;
  /** One line, said out loud, so the order has a reason. */
  blurb: string;
  /** The stage ids that own this step's artifacts. */
  stages: string[];
  /** Shown when the step cannot run yet. */
  needs?: string;
}

export const STEPS: StepMeta[] = [
  {
    n: 1,
    label: "스토리",
    scope: "episode",
    blurb:
      "이번 화의 원본 소설을 확정하는 단계입니다. 소설을 직접 붙여넣으면 그대로 쓰고, 전제만 주면 AI가 소설로 쓴 뒤 여기서 잠급니다. 이후 단계는 이 글을 읽고만 씁니다.",
    stages: ["manga-1-source"],
  },
  {
    n: 2,
    label: "프로젝트 설정",
    scope: "project",
    blurb:
      "프로젝트 전체에 적용되는 규칙을 정하는 단계입니다. 제목 · 읽기 방향 · 해상도 · 화풍 · 페이지당 컷 수 범위 · 에피소드당 페이지 수를 정하며, 에피소드가 바뀌어도 다시 정하지 않습니다.",
    stages: [],
  },
  {
    n: 3,
    label: "캐스트",
    scope: "project",
    blurb:
      "등장인물 카드 풀을 만드는 단계입니다. 외형 앵커 · 시그니처 · 묘사를 한 번만 정해두면 이후 모든 에피소드가 같은 인물로 그립니다. 새 인물이 나올 때만 카드를 추가합니다.",
    stages: ["manga-3-bible"],
  },
  {
    n: 4,
    label: "레퍼런스 시트",
    scope: "project",
    blurb:
      "인물마다 기준 시트 문장을 만드는 단계입니다. 이미지 모델이 붙었을 때 이걸 기준 삼아 그립니다. 이미 시트가 있는 인물은 새로 만들지 않습니다.",
    stages: ["manga-4-refsheets"],
  },
  {
    n: 5,
    label: "페이지 계획",
    scope: "episode",
    blurb:
      "소설을 읽고 내용을 페이지에 나눠 담는 단계입니다. 페이지마다 무엇을 그릴지(story job) · 컷 수 · 읽기가 무엇을 알고 무엇을 새로 알아야 하는지 · 페이지를 넘기는 훅을 정하고, 그 페이지의 성격에 맞는 페이지 템플릿을 골라 template_suggestion으로 남깁니다. 여기서 컷을 실제로 자르는 게 아니라, 각 페이지에 어떤 성격의 칸막이를 쓸지 미리 정하는 단계입니다.",
    stages: ["manga-5-plan"],
  },
  {
    n: 6,
    label: "콘티",
    scope: "episode",
    blurb:
      "설계도(콘티)를 그리는 단계입니다. 컷마다 샷 · 앵글 · 행동(beat)과 대사·내레이션·효과음 3개국어를 적고, 이어서 만화가가 그 콘티를 보고 각 페이지를 실제로 그립니다 — 컷마다 무엇이 어떻게 보이는지, 배경을 넣을지 인물만 강조할지, 누가 어디에 서는지, 빛과 표정까지. 4페이지씩 블록으로 만듭니다.",
    stages: ["manga-6-conti", "manga-7-sheets", "manga-8-artwork", "manga-9-prompts"],
  },
  {
    n: 7,
    label: "프롬프트",
    scope: "episode",
    blurb:
      "만화가가 그린 페이지를 MOSS-Image가 바로 읽는 프롬프트(prompt.txt · negative.txt)로 내보내는 단계입니다. 언어를 바꾸면 여기서 다시 내보내며, 번역하지 않습니다. 원고 미리보기와 워크벤치도 이 단계 안에서 봅니다.",
    stages: ["manga-9-prompts"],
  },
];

export const STEP_BY_N = new Map(STEPS.map((s) => [s.n, s]));

export function stepMeta(n: number): StepMeta | undefined {
  return STEP_BY_N.get(n);
}

export const SCOPE_LABEL: Record<Scope, string> = {
  project: "프로젝트 전체",
  episode: "에피소드마다",
};

export type StageState = "done" | "stale" | "ready" | "waiting" | "skip";

export function stageState(s: string | undefined | null): StageState {
  switch (s) {
    case "done":
      return "done";
    case "stale":
      return "stale";
    case "ready":
      return "ready";
    case "blocked":
    case "waiting":
      return "waiting";
    default:
      return "skip";
  }
}

export const STATE_LABEL: Record<StageState, { text: string; cls: string }> = {
  done: { text: "완료", cls: "chip--ok" },
  stale: { text: "변경됨 · 재작업 필요", cls: "chip--warn" },
  ready: { text: "실행 가능", cls: "" },
  waiting: { text: "다른 단계 먼저", cls: "chip--warn" },
  skip: { text: "이 프로젝트에는 없음", cls: "" },
};

/** "2 · 프로젝트 설정" */
export function stepTitle(n: number): string {
  const s = stepMeta(n);
  return s ? `${s.n} · ${s.label}` : "";
}
