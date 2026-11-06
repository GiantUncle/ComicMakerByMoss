/**
 * The steps of one project, in order.
 *
 * 1 스토리 (episode)
 * 2 프로젝트 설정 (project)
 * 3 캐스트 (project)
 * 4 레퍼런스 시트 (project)
 * 5 페이지 계획 (episode)
 * 6 콘티 (episode)      — AI: 장면·대사·내레이션·효과음(KO/EN/JA)
 * 7 컷 시트 (episode)   — 결정적: 좌표/시트 생성
 * 8 프롬프트 (episode)  — 결정적: 최종 프롬프트 컴파일 (+ 미리보기/워크벤치)
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
    blurb: "이번 화의 소설입니다. 직접 붙여넣거나, 전제만 주면 AI가 소설로 쓸 수 있습니다.",
    stages: ["manga-1-source"],
  },
  {
    n: 2,
    label: "프로젝트 설정",
    scope: "project",
    blurb: "제목 · 읽기 방향 · 해상도 · 화풍 · 페이지당 컷 수 범위 · 에피소드 페이지 수.",
    stages: [],
  },
  {
    n: 3,
    label: "캐스트",
    scope: "project",
    blurb: "인물 카드 — 외형 앵커 · 시그니처 · 묘사. 프로젝트 전체가 함께 쓰는 풀입니다.",
    stages: ["manga-3-bible"],
  },
  {
    n: 4,
    label: "레퍼런스 시트",
    scope: "project",
    blurb: "인물마다 한 장의 기준 시트. 새 인물만 새로 만듭니다.",
    stages: ["manga-4-refsheets"],
  },
  {
    n: 5,
    label: "페이지 계획",
    scope: "episode",
    blurb: "몇 페이지에 무엇을 담을지. 페이지마다 컷 수와 구성이 정해집니다.",
    stages: ["manga-5-plan"],
  },
  {
    n: 6,
    label: "콘티",
    scope: "episode",
    blurb: "AI가 각 페이지의 장면·대사·내레이션·효과음(KO/EN/JA)을 콘티로 작성합니다.",
    stages: ["manga-6-conti"],
  },
  {
    n: 7,
    label: "컷 시트",
    scope: "episode",
    blurb: "콘티를 바탕으로 컷 좌표와 시트를 결정적으로 생성합니다.",
    stages: ["manga-7-sheets"],
  },
  {
    n: 8,
    label: "프롬프트",
    scope: "episode",
    blurb: "컷 시트를 최종 프롬프트로 컴파일합니다. 원고 미리보기와 워크벤치도 여기에서 확인합니다.",
    stages: ["manga-8-prompts"],
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

export type StageState = "done" | "ready" | "waiting" | "skip";

export function stageState(s: string | undefined | null): StageState {
  switch (s) {
    case "done":
      return "done";
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
  ready: { text: "실행 가능", cls: "" },
  waiting: { text: "다른 단계 먼저", cls: "chip--warn" },
  skip: { text: "이 프로젝트에는 없음", cls: "" },
};

/** "2 · 프로젝트 설정" */
export function stepTitle(n: number): string {
  const s = stepMeta(n);
  return s ? `${s.n} · ${s.label}` : "";
}
