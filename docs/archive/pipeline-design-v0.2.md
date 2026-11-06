> **보관본 — SUPERSEDED.** 에피소드 모델과 웹 UI 이전의 파이프라인 설계입니다.
> 현행 정본은 `docs/design.md` 입니다. 이 문서가 담고 있던 만화 문법 조사는
> `.opencode/skills/manga-craft/comic-planning.md` 로 옮겨졌습니다.

# 설계: 소설 → 만화 원고 프롬프트 웹 워크벤치

작성: 설계 v0.1 · 대상: 소설/스토리 → MOSS-Image용 만화 원고(1페이지 = 1이미지) 프롬프트

---

## 0. 한 줄 요약

소설을 넣으면 **8페이지 블록 단위**로 페이지를 할당하고, 각 페이지를 **글 콘티 → 컷 분할 시트 → MOSS Layout JSON 프롬프트**로
전개하는 웹 워크벤치. 기획은 LLM(스킬)이, 레이아웃·검증·좌표·프롬프트는 **결정적 도구**가 담당하고,
**파일이 둘을 잇는 인터페이스**가 된다.

두 가지가 이 설계의 골격이다.

- **한 페이지 = 이미지 1장.** 컷마다 이미지를 만드는 게 아니라, 한 장 안에 컷 bbox와 대사 bbox를 배치한다.
- **다국어로 만들되 한국어로 검수한다.** 원고는 ko/en/ja/zh 어느 언어로도 가능하지만,
  시트에는 **항상 한국어 뜻이 병기**되고 프롬프트에는 대상 언어만 들어간다(§8.6).

---

## 1. 전제 정정 (사용자 지적 반영)

이 설계가 바로잡아야 했던 오해:

| 잘못 | 올바름 |
| --- | --- |
| "한 페이지에 5컷이면 이미지 5장" | **1페이지 = 이미지 1장 = MOSS 생성 1회.** 그 한 장 안에 컷 5개의 bbox와 대사 bbox가 들어간다. |
| "시선 = 그림 속 캐릭터가 보는 방향" | **시선 = 독자가 페이지를 읽어나가는 동선(視線誘導).** 캐릭터 시선은 그와 별개인 *eyeline 매칭* 규칙. |
| "페이지 = 독립된 완결 이미지" | **페이지는 다음 페이지로 이어지는 원고.** 페이지 넘김 훅(page-turn hook)이 필수. |

MOSS-Image의 Layout JSON은 정확히 이 용도로 만들어져 있다: 한 캔버스에
`object`(컷 배경), `character`(인물), `text`(대사/내레이션/SFX) 아이템을 각자의 `bbox`로 배치한다.
즉 **1페이지 = 컴파일된 JSON 1개**.

### 1.1 출력 모드 3종 — 최상위 선택

무엇을 만드는지를 **먼저** 고른다. 모드가 페이지 구조·아이템 종류·프롬프트 형태를 전부 결정한다.

| 모드 | 정체 | 대사 | 배경 텍스트 | 페이지 구조 | FKEY 대응 |
| --- | --- | --- | --- | --- | --- |
| `illustration` | **대사 없는 완전한 일러스트레이션** | 없음 | **있을 수 있음** (간판·표지·화면 UI) | **없음** — N장의 그림 | Type B (섹션 프롬프트) |
| `comic` | 일러스트레이션 + **대사/효과음** | 있음 | 있음 | 캔버스 1장 = 단일 프레임 | Type C (`canvas: single`) |
| `manga` | **다컷 만화 원고** (현재 계획) | 있음 | 있음 | **있음** — 4페이지 단위, 컷 분할 | Type A (`canvas: multi_panel`) |

- **`illustration`에는 페이지 개념이 없다.** "4페이지 단위"는 `manga`에만 적용된다.
- `comic`은 한 장에 대사가 들어가지만 컷 분할은 없다(필요하면 `manga`로).
- 모드는 프로젝트 시작 시 고르고, **字コンテ·컷 시트 단계는 `manga`에서만 활성화**된다.
- UI는 모드에 따라 화면을 분기한다(§12).

---

## 2. 조사한 레퍼런스 — 만화 문법

문법을 임의로 만들지 않기 위해 아래를 근거로 삼는다. 각 항목은 "우리가 어디에 쓰는가"까지 명시.

| 개념 | 내용 | 출처 | 쓰는 곳 |
| --- | --- | --- | --- |
| **코마와리 (コマ割り)** | 페이지 전체의 컷 배치와 흐름 | CLIP STUDIO「Pro Artist's Guide to Comic & Manga Layouts」/ YouTube「Komawari and Panel Layouts for Manga」 | 레이아웃 템플릿 라이브러리 |
| **단구미 (段組)** | 페이지를 **단(tier/행)으로 먼저 나누고**, 각 단을 다시 컷으로 분할. 3단(sandangumi)/4단(yondangumi) | CLIP STUDIO TIPS「DANGUMI: The Secret to Manga Layout」 | **템플릿 DSL의 핵심 구조** |
| **네임 (ネーム) / blocking(nēmu o kiru)** | 컷 배치·대사·페이지 구성을 정하는 글 스토리보드 단계. "만화가가 가장 먼저 하는 메모" | ImageTexT「The Construction of Panels (Koma) in Manga」/ Too Corporation「Storyboard」 | **글 콘티 단계의 정체** |
| **T-rule** | "T의 기둥을 넘기 전에 팔을 넘지 마라". 4컷이 한 점에서 만나는 `+` 배치는 금지. 단을 어긋나게(stagger) 배치해 읽기 순서를 무의미하게 명확히 한다 | Rachel Thorn (교토세이카대), «On Manga Page Layouts» | **자유 분할 검증기 V1·V2** |
| **blocking (Neil Cohn)** | 위 T-rule의 인지과학적 정식화. 컷은 블록으로 묶이고 블록 안에서 읽는다 | N. Cohn, *The Visual Language of Comics* (2014) |同上 |
| **미세고마 (見せゴマ)** | 페이지에서 "보여주는" 단 하나의 초점 컷 | YouTube「The BEST Way To Layout Comic Panels」 | V11 (페이지당 미세고마 1개) |
| **거터 = 관계/호흡** | 거터가 얇으면 밀접(같은 비트), 두꺼우면 시간·장면 점프. 세로 거터보다 가로 거터를 두껍게 하는 관행 | CLIP STUDIO / YouTube | V3 (거터 균일), 템플릿 파라미터 |
| **컷 크기 = 시간** | 큰 컷 = 느림·중요, 작은 컷 = 빠름, 테두리 없음 = 무시간성·임팩트 | Scribd「Manga Paneling and Pacing Techniques」 | R4 |
| **읽기 방향** | 일본 만화는 우→좌, 상→하. 서구/한국 웹툰은 좌→우 | 다수 | 프로젝트 설정 |
| **시선 매칭 (eyeline)** | 인접 컷에서 대화하는 두 인물은 **서로를 향해** 봐야 한다. 게이지·움직임·말풍선도 동선을 유도 | Hamakua / salgoodsam「Flow & the Eyelines」 | **V9** |
| **페이지 넘김 훅 (めくり)** | 페이지 마지막 컷은 다음 장을 넘기게 만드는 질문/반전으로 끝낸다 | DrawlikeaSir「Make your OWN MANGA」 | R7, 콘티 필드 |
| **8페이지 読切 구조** | 1페이지=무대·환경·인물 정보, 이후 전개→반전→클라이맥스 8페이지 완결 구조 | CLIP STUDIO TIPS「From Plot to Storyboard: Creating an 8-page Shonen Manga」 | **8페이지 블록 설계 근거** |

> 핵심: 컷 분할은 "자유 vs 경직"의 이분법이 아니다. **단(段)을 먼저 나누고 그 안을 쪼개는** 방식이면
> 자유로워 보이면서도 T-rule이 자동으로 지켜진다. 이게 문법을 지키면서 자유도를 주는 유일한 길이다.

### 2.1 교차검증 — 숫자는 복수 출처가 수렴할 때만 채택한다

초기 조사는 codex 레포 1개 + CLIP STUDIO 글 1개에 의존했다. 표본 1개를 정설로 가정한 것이다.
일본 만화 실무 소스 5개(copainter / atam-academy / MediBang / egaco / oyasumi-gamedev)를 추가 대조해
**수렴한 값만** 채택한다.

| 항목 | copainter | atam-academy | MediBang | egaco | **수렴값** |
| --- | --- | --- | --- | --- | --- |
| 표준 컷 수/페이지 | 5~6 | 5~7 (최대 8) | 5~6 | 평균 6까지 | **5~6, 상한 8** |
| 클라이맥스 | 1~3 | — | 見せゴマ 있으면 1~3 | — | **1~3** |
| 대사 위주 | 6~7 (초과 시 2p 분할) | — | 설명 페이지 8~10 | — | **6~7 (그 이상 분할)** |
| 단(段) 수 | 3段/4段 | — | 3~4 | — | **3~4** |
| 見せゴマ 크기 | 2번째의 **2배 이상**, 페이지의 3~4할 | — | — | 見開き당 1~3개 | **2번째의 ≥2배, 30~40%** |
| 세로 분할선 | 어긋나게 | — | — | 상하 겹치면 순서 혼란 | **인접 단과 stagger** |
| 거터 | 좁으면 다음 컷, 넓으면 단절 | 상하 넓게 / 좌우 좁게 | — | — | **상하 > 좌우** |
| 말풍선 | 컷마다 우상→좌하, 컷 넘김 금지 | — | — | — | **컷 내 우상→좌하** |

**초기 조사에서 틀렸던 것**
- "1페이지 3~6컷" → 실제 표준은 **5~6컷**. 3~6은 클라이맥스와 표준을 뭉갠 값이었다.
- "8페이지 단위"의 근거로 CLIP STUDIO 글 1개만 댔다. 실제 만화의 설계 단위는 **見開き(2페이지)** 다
  (oyasumi-gamedev: "コマ割りは1ページずつではなく、見開き単位で考えるのが基本", egaco 동일).
  → **4페이지 = 見開き 2개**. 사용자가 정한 4페이지 하드 단위는 만화 실무와 정확히 맞는다.

**새로 채택한 개념**
- **字コンテ(じコンテ)**: "1컷=1행, 화면·세리후·구도(앵글)를 메모"하는 **글 콘티의 정식 명칭**. → §8.3
- **タチキリ(bleed)**: 컷/그림을 내곽 밖 완성선까지 늘리는 연출. 見せゴマ에만, 남용 금지.
- **斜め/변형 컷**: 독자 부담이 크므로 인상적인 장면에 한정.

---

## 3. 유사 파이프라인 레퍼런스

| 프로젝트 | 가져올 것 |
| --- | --- |
| **lhfer/codex-novel-to-comic-studio** (Codex skill, MIT) | 12단계 파이프라인, **역할별 계약**(story-writer / script-writer / storyboard-writer / page-director), **on-disk 상태 + 게이트 파일**, `source_span` 추적, visual bible의 "Core-first → arc-expanded → chapter-checked" |
| **victorhuangwq/story-to-manga** | 스토리 분석 → 캐릭터 레퍼런스 → 레이아웃 계획 → 패널 생성 흐름 |
| **DreamingComics** | "LLM 레이아웃 생성기"가 스크립트 → 패널/캐릭터 bbox를 예측. 레이아웃을 학습 대상으로 본 관점 |
| **MOSS 공식 8-panel 예시** (512×4096, Scene JSON) | 패널마다 `identity` / `note` / `salience` / `shape` / `colors`를 갖는 **Scene JSON** 포맷. 세로 스트립에 적합 |

특히 codex 레포의 다음 문장이 우리 설계의 좌표가 된다:

> "Do not write a vague `2x2` or `3x2` grid as the layout. Describe manga panel geometry:
> splash, inset, tall strip, wide establishing panel, diagonal action panel, reaction close-up,
> borderless bleed, overlapping SFX, reading path, and page-turn hook."

그리고 storyboard-writer의 문법 체크:

> "avoid too many consecutive same-shot panels, add establishing shots for new locations,
> use close-ups for emotional turns, use insert shots for foreshadowing props,
> keep dialogue short enough for bubbles."

이 두 문장이 §6 문법 규칙의 절반이다.

---

## 4. MOSS-Image 제약 (설계에 직접 영향)

| 제약 | 값 | 영향 |
| --- | --- | --- |
| 캔버스 | 16의 배수, 1 / 1.5 / 2 MP, 최대 ~4MP | **기본 = A4 근사 세로(1:1.42)**. S/M/L/XL 해상도 티어(§8.1). 웹툰은 세로 스트립 |
| 입력 형식 | prose / tags / **Layout JSON** / **Scene JSON** | 페이지 프롬프트 = Layout JSON 1개 |
| bbox 단위 | `abs_centralized` + `yxyx` | 손계산 금지, `compile_layout.py` 사용 |
| 레이아웃 정확도 | **실험적.** "모델이 컷을 옮기거나 합칠 수 있다" | 컷 수를 줄이고, 검증 후 렌더 |
| 텍스트 렌더링 언어 | 공식 문서상 영어·중국어. **한국어도 실사용에서 정상**(사용자 확인) | 대사 언어를 선택(ko/en/ja/zh). 텍스트는 항상 **이미지에 직접** 렌더 |
| 프롬프트 길이 | 4096 토큰 | 페이지 1장당 충분 |
| 프롬프트 업샘플러 | 켜면 JSON 레이아웃을 덮어씀 | **반드시 OFF** |

---

## 5. 계획 판정

### 5.1 좋은 점 (그대로 간다)

1. **중간 산출물을 단계로 분리** — 소설 → 글 콘티 → 컷 시트 → 프롬프트. 프로 만화의
   **プロット → 字コンテ → ネーム** 공정에서 **字コンテ 단계**에 정확히 대응한다(§2.1).
   codex 레포의 설계와도 일치한다. 옳다.
2. **컷 분할 방식을 사용자가 고른다** — 맞다. 다만 축을 잘못 잡았다(§5.2-2).
3. **페이지당 컷 수를 정해 둔 것** — 맞다. 교차검증 결과 표준은 **5~6컷**(§2.1).
   초기 설계의 "3~6"은 클라이맥스와 표준을 뭉갠 값이라 수정했다.
4. **1페이지 = 1이미지** — MOSS Layout JSON의 설계 의도와 정확히 일치.
5. **페이지 단위를 하드로 둔 것** — 맞다. 단위를 **4페이지**로 정한 것은 만화의 설계 단위인
   **見開き(2페이지) 2개**와 정확히 일치한다(§2.1).

### 5.2 위험 / 수정

**위험 1 — 대사 언어별 렌더 품질 편차.**
대사는 ko/en/ja/zh 어느 것으로도 만든다. 공식 문서의 보증 언어는 영어·중국어이지만
**한국어도 실사용에서 정상**(사용자 확인). → 언어를 처음 쓸 때 **1페이지 테스트 렌더로 확정**한다.
텍스트는 항상 이미지에 직접 렌더된다. **오버레이 폴백은 없다**(§8.6).
시트의 한국어 병기는 별개 계층이라 렌더 결과와 무관하게 유지된다.

**위험 2 — "경직 vs 자유"는 잘못된 축이다.**
자유 분할은 T-rule을 위반하는 순간 읽기 순서가 무너진다. 정확한 축은 3단계다:

```
① 템플릿(권장 기본)  : 명명된 단(段) 템플릿에서 고른다      → 항상 가독
② 밸런스(중간)       : 페이지 기능으로 템플릿을 고르고       → 가독 + 변화
                       단 비율·병합/분할을 조정
③ 자유               : bbox를 직접 제안하되                → 검증 통과 시에만
                       T-rule 검증기(V1·V2)를 반드시 통과
```
자유를 막지 않되, **검증을 통과해야만 렌더 버튼이 열린다.**

**위험 3 — 고정 페이지 수 할당은 스토리를 망친다.**
codex 레포는 강하게 반대한다: *"Page count is story-first... do not force a source chapter into a
fixed page budget if the story becomes choppy."* → `8/16/24/32`는 **소프트 목표**로 두고,
"스토리 우선" 모드와 "쿼터 강제" 모드를 둘 다 제공. 초과/부족을 리포트하고 사용자가 재배분.

**위험 4 — 컷마다 LLM이 bbox를 즉석 생성하면 비용·일관성이 무너진다.**
레이아웃은 **템플릿 라이브러리에서 선택**하고, LLM은 "어느 템플릿 + 각 컷에 무엇"만 정한다.
좌표는 결정적 생성기가 만든다.

### 5.3 계획에 빠진 것 (추가 필요)

| 빠짐 | 추가 |
| --- | --- |
| 캐릭터/배경 레퍼런스 고정 | **visual bible** — 캐릭터 카드·설정 카드를 페이지 생성 전에 잠근다. 안 하면 페이지마다 얼굴이 바뀐다 |
| 원문 추적 | 모든 컷에 `source_span` 또는 `adaptation_added` 표시 |
| 독자 상태 추적 | 페이지마다 "독자가 아는 것 / 새로 아는 것 / 다음에 궁금한 것" → 페이지 넘김 훅의 근거 |
| 페이지 넘김 훅 | 콘티 필수 필드 |
| 검수 게이트 | 렌더 전 구조·문법·텍스트 검사 |
| 대사 길이 규율 | 말풍선에 들어가도록 컷당 2줄/약 28자 제한 |
| 인물 소개 박스 | 명명된 캐릭터 첫 등장 시 1회 |
| **대사 이중언어 병기** | 시트는 한국어 병기, 프롬프트는 대상 언어만 → **§8.6 계약** |

---

## 6. 만화 문법 — 인코딩할 규칙

### 6.1 읽기·구조

- **R1 읽기 순서**: `tier` 오름차순 → 같은 tier 안에서 `x1` 내림차순(RTL) / 오름차순(LTR).
  순서는 **좌표에서 파생**되며 별도 번호를 저장하지 않는다.
- **R2 T-rule**: 4컷이 한 점에서 만나는 `+` 금지. 인접한 두 단이 모두 세로 분할을 가지면
  분할 x가 최소 캔버스 폭의 8% 이상 어긋나야 한다.
- **R3 거터**: 한 페이지 안에서 가로 거터 전부 동일, 세로 거터 전부 동일. 얇은 거터 = 같은 비트.
- **R4 컷 크기 = 시간**: 중요한 순간일수록 크게. 페이지당 **미세고마 1개**(가장 큰 컷).
- **R5 단 개수**: 3~4단이 표준. 2단은 임팩트·액션.
- **R6 컷 수**: 표준 **5~6**, 상한 8. 클라이맥스·감정 페이지는 **1~3**. 대사 위주는 6~7,
  그 이상이면 다음 페이지로 분할한다(§2.1).
- **R7 페이지 넘김 훅(引き)**: 見開き의 마지막 컷을 "다음 장이 궁금한" 내용으로 끝낸다.
  넘긴 직후 페이지(メクリ)에 임팩트 컷을 둔다. 2페이지째부터 매 見開き에 하나.

### 6.2 연출

- **R8 샷 다양성**: 같은 샷 3연속 금지. 장소가 바뀌면 establishing(원경) 삽입.
  감정 전환엔 클로즈업, 복선 소품엔 인서트.
- **R9 시선 매칭(eyeline)**: 인접 컷에서 대화하는 두 인물의 시선 벡터는 **반대**여야 한다.
  (오른쪽 인물이 왼쪽을 봄 ↔ 왼쪽 인물이 오른쪽을 봄)
- **R10 말풍선**: 컷 상단 1/3에 배치, 다른 인물 머리에서 캔버스 폭 기준 ≥80px 이격, 꼬리는 화자 방향.
  화면 밖 화자는 무미(無尾) 타원. 화자당 2줄 이하.
- **R11 대사 길이**: 말풍선당 약 28자(2줄). 넘으면 컷 분할을 검토.
- **R12 내레이션/대사 구분**: 내레이션=직사각 박스, 대사=둥근/톱니 풍선. 캡션은 컷 밖 경계에 붙여도 됨.
- **R13 화면 밖 대상**: 컷 밖을 가리키는 말풍선 꼬리 금지.
- **R14 미등장 인물 소개 박스**: 명명 캐릭터 정식 첫 등장 시 1회, 얼굴·액션을 가리지 않는 모서리.
- **R15 見せゴマ 크기**: 가장 큰 컷은 2번째로 큰 컷의 **2배 이상 면적**, 페이지의 **30~40%**.
- **R16 タチキリ(bleed)**: 컷/그림을 내곽 밖 완성선까지 늘리는 연출. **見せゴマ에만** 쓰고 남용 금지.
  대사는 내곽 안에 넣는다.
- **R17 見開き 단위**: 레이아웃은 1페이지가 아니라 **見開き(2페이지)** 단위로 설계한다.
  4페이지 하드 단위 = 見開き 2개.
- **R18 변형 컷**: 사선·변형 컷은 인상적인 장면에 한정한다. 남용하면 읽기 부담.

---

## 7. 아키텍처 — UI는 OpenCode를 LLM 백엔드로 쓴다

**질문: UI에 API를 넣으면 OpenCode 스킬을 그대로 쓸 수 있나?**
**답: 그렇다. 우회가 필요 없다. OpenCode 서버 API에 스킬 활성화 엔드포인트가 이미 있다.**

OpenCode V2 HTTP API에서 확인한 것:

| 엔드포인트 | 용도 |
| --- | --- |
| `GET /api/skill` | 사용 가능한 스킬 목록 |
| `POST /api/experimental/session/{sessionID}/skill` | **스킬 활성화** |
| `POST /api/session` | 세션 생성 |
| `POST /api/session/{sessionID}/prompt` | 프롬프트 전송 (`PromptInput.SkillAttachment`로 스킬 첨부 가능) |
| `POST /api/session/{sessionID}/agent` · `/model` | 에이전트·모델 전환 |
| `GET /api/event` | 이벤트 스트림 (`session.text.delta`, `session.tool.called`, `session.skill.activated` …) |
| `GET /api/fs/*` · `POST /api/shell` | 파일 읽기/쓰기, 셸 실행 |

즉 UI는 **세션 생성 → 스킬 활성화 → 프롬프트 전송 → 이벤트 스트림 표시**만 하면 되고,
스킬 로딩·툴 호출·파일 쓰기는 OpenCode가 처리한다. `@opencode/client` SDK도 같은 계약을 제공한다.

### 7.1 3계층

```
① OpenCode API  (창작 계층 — 스킬을 그대로 사용)
   소설 분석 · 페이지 할당 · 字コンテ · 컷에 내용 배정
   스킬: moss-comic-layout (정본 references/authoring-spec.md)
                    │  세션 프롬프트 / 이벤트 스트림
② UI 백엔드 (FastAPI) — 결정적 계층, LLM 불필요
   템플릿→bbox · T-rule/거터/시선/見せゴマ 검증 · canvas 티어 재계산
   · compile_layout.py · build_negative.py · 내보내기
                    │  REST + SSE
③ 웹 UI (Vite + React + TS)
   검토 · 편집 · 레이아웃 미리보기 · 검증 표시 · 프롬프트 복사
```

**왜 이 구조인가**

- **스킬 이중화가 없다.** 스킬은 OpenCode가 로드한다. UI는 세션만 만든다.
- **에이전트 루프를 재구현하지 않는다.** 툴 호출(파일 읽고·쓰고·검증 실행)은 OpenCode가 한다.
- **결정적 작업에는 LLM을 쓰지 않는다.** 템플릿 인스턴스화·검증·좌표 변환·컴파일은 순수 함수다.
  UI 백엔드가 직접 호출한다. 여기에 LLM을 넣으면 느려지고 틀려진다.
- **창작만 LLM.** "이 페이지는 어떤 비트를 어떻게 나눌까"는 OpenCode 세션 + 스킬이 한다.

**대안 (OpenCode 없이 배포해야 할 때만)**
스킬이 전부 Markdown 파일이라는 점을 이용해, UI 백엔드가 `SKILL.md` + `references/*.md`를
시스템 프롬프트에 주입하고 자체 툴 루프를 돌린다. 가능하지만 에이전트 루프를 다시 짜야 하므로
**권장하지 않는다.** OpenCode가 있는 환경이면 §7.1을 쓴다.

**상태(SoT)**: 프로젝트 산출물은 계속 on-disk 파일(§8)이다. OpenCode는 그 파일을 읽고 쓰고,
UI 백엔드도 같은 파일을 읽고 쓴다. 파일이 두 계층의 합의 지점이다.

---

## 8. 데이터 모델

### 8.1 프로젝트

```jsonc
// projects/<slug>/project.json
{
  "slug": "tamna-train",
  "mode": "manga",                             // illustration | comic | manga ← 최상위
  "canvas": { "w": 992, "h": 1408,             // 기본 A4 근사(1:1.419)
              "tier": "M",                      // S|M|L|XL ← 변경 시 bbox 자동 재계산
              "ratio": "a4_portrait" },
  "reading_direction": "rtl",                  // 기본 rtl(일본 만화). UI에서 ltr 변경
  "art_style": "fkey_painterly",               // 스킬의 스타일 프리셋 키
  "dialogue_language": "en",                   // 기본 en / ko | ja | zh ← 프롬프트에 들어가는 언어
  "sheet_language": "ko",                      // 시트·UI 병기 언어 (항상 한국어, §8.6)

  // ↓ manga 모드에서만 사용
  "page_total": 8,                             // 4의 배수만. 9/10/11 페이지는 존재하지 않음
  "cut_mode": "balanced",                      // template | balanced | free

  "render": { "backend": "comfyui", "lora_strength": 0.6, "steps": 28 }
}
```

**페이지 수 규칙 (`manga` 모드)**

- 페이지 수는 **4의 배수만** 허용: 4, 8, 12, 16, 20, 24, 28, 32 …
- **9·10·11 같은 값은 존재하지 않는다.** UI 입력 자체를 4단위 스테퍼로 만든다.
- 기본 총량은 **8페이지**(= 4페이지 블록 2개 = 見開き 4개). 사용자가 4단위로 늘린다.
- 기준 단위는 **4페이지 = 見開き 2개**. 묶음·바인딩 단위는 8페이지.

**캔버스 해상도 티어** (모두 16의 배수, A4 비율 ≈1:1.42 유지)

| 티어 | px | MP | 용도 |
| --- | --- | --- | --- |
| `S` | 704×992 | 0.70 | 미리보기·테스트 컷 |
| `M` | **992×1408** | **1.40** | **기본** (MOSS 권장 1.5MP 대역) |
| `L` | 1248×1760 | 2.20 | 확정 원고 |
| `XL` | 1408×1984 | 2.79 | 인쇄 고해상 (MOSS 외삽 범위 내) |

티어를 바꾸면 **컷이 아니라 좌표계만 재계산**한다. 컷 비율(단 구성·컷 분할 비율)은 0~1 정규화 값으로
저장하고, 실제 bbox는 컴파일 시점에 `정규화 × (w,h)`로 계산한다. 따라서 **티어 변경이 언제든 안전**하고,
이미 만든 프롬프트도 `compile_layout.py`를 다시 돌리면 끝난다(사용자 지적대로).

### 8.2 바이블 (페이지 생성 전에 잠금)

```jsonc
// projects/<slug>/bible/characters.json
{ "characters": [{
    "id": "char-001", "name": "이자헌", "role": "D조 과장",
    "bible": "a tired 40s Korean man, ...",       // 스킬의 캐릭터 앵커 블록(2~4개) + 연령/골격
    "anchor_terms": ["softly tapered chin","..."],
    "outfits": [{ "id": "office", "desc": "..." }],
    "approved": true
}]}
// bible/settings.json, bible/style.md 동일 구조
```

### 8.3 字コンテ (글 콘티)

```jsonc
// projects/<slug>/pages/page-001.conti.json
{
  "page": 1, "block": 1,
  "story_job": "무대(불 꺼진 사무실·타자 소리)와 인물(이자헌)을 소개한다",
  "source_span": "source/ch01.txt:1-14",
  "reader_state": {
    "knows": [], "learns": ["이자헌이 보고서를 쓰고 있다"],
    "question": "무슨 사건의 보고서인가?"
  },
  "page_turn_hook": "화면에 드러나는 사건의 제목 — 독자는 다음 장을 넘긴다",
  // 대사 항목은 항상 이중언어: text = 프롬프트에 들어갈 대상 언어, gloss = 시트 표시용 한국어(§8.6)
  "panels": [
    { "n": 1, "shot": "establishing", "angle": "high",
      "beat": "불 꺼진 사무실 전경, 한 점의 모니터 불빛",
      "characters": ["char-001"], "bg": "office_dark",
      "eyeline": null, "transition": "start",
      "dialogue": [], "sfx": [] },
    { "n": 4, "shot": "medium", "angle": "over_shoulder",
      "beat": "은하제가 조장 자리에 서서 이자헌을 내려다본다",
      "characters": ["char-002"], "bg": "office_dark",
      "eyeline": { "subject": "char-002", "dir": "left" },
      "transition": "reaction",
      "dialogue": [
        { "speaker": "char-002", "lang": "en",
          "text": "That is enough, chief.",
          "gloss": "이제 그만하십쇼.",
          "bubble": "round", "tail": "char-002" }
      ],
      "sfx": [] }
  ]
}
```

### 8.4 컷 분할 시트 (= bbox 확정)

```jsonc
// projects/<slug>/pages/page-001.sheet.json
{
  "page": 1,
  "layout": { "template_id": "T3C", "stagger": 0.35 },
  "panels": [
    { "n": 1, "conti_ref": 1, "tier": 0, "bbox": [519, 40, 984, 516],
      "shot": "establishing", "angle": "high", "misegoma": false,
      "characters": ["char-001"], "caption": "..." }
  ],
  "texts": [
    { "id": "t1", "kind": "dialogue", "panel_ref": 4, "speaker": "char-002",
      "lang": "en", "text": "That is enough, chief.", "gloss": "이제 그만하십쇼.",
      "bbox": [620, 1060, 880, 1180], "bubble": "round", "tail": "char-002",
      "vertical": false, "lines": 1 },
    { "id": "t2", "kind": "sfx", "panel_ref": 1,
      "lang": "ko", "text": "타타닥", "gloss": "타타닥",
      "bbox": [700, 380, 820, 480], "bubble": "none", "tail": null, "vertical": false }
  ],
  "validation": {
    "passed": true,
    "issues": [],
    "render_text": ["t1", "t2"],          // 프롬프트에 실제로 들어가는 항목
    "sheet_only": ["gloss"]               // 시트에만 표시, 프롬프트에는 안 들어감
  }
}
```

### 8.5 산출물

```
projects/<slug>/
├─ project.json
├─ bible/{characters,settings,style}.json
├─ plan/page-story-plan.json          # 블록별 할당 (manga)
├─ pages/page-001.conti.json          # 字コンテ (manga)
├─ pages/page-001.sheet.json          # 컷 분할 시트 (manga)
├─ prompts/page-001.prompt.txt        # 컴파일된 Layout JSON (+ 트리거)
├─ prompts/page-001.negative.txt      # 네거티브 3블록
├─ render/page-001.png                # MOSS 생성 원고 (대사 포함, 이미지에 직접 렌더)
└─ qc/page-001.qc.json
```

### 8.6 이중언어 시트 계약 (핵심 요구사항)

**번역 단계는 없다.** 원문 → 대상 언어 → 한국어로 옮기는 파이프라인이 아니다.
대사·내레이션·효과음은 **字コンテ 단계에서 처음부터 대상 언어로 창작**하고, 같은 항목에
**한국어 병기**를 함께 적는다. 창작과 기록이 한 번에 일어난다.

**규칙**

1. 모든 대사·내레이션·SFX 항목은 **두 개의 문자열**을 가진다.
   - `text` — 字コンテ에서 **창작한 대상 언어** (`dialogue_language`). 프롬프트에 그대로 들어간다.
   - `gloss` — 같은 항목의 **한국어 병기**. 작업자(한국인)가 읽기 위한 것이며 **프롬프트에 절대 들어가지 않는다.**
2. `dialogue_language == "ko"` 이면 `text == gloss`.
3. 프롬프트 컴파일 시 `gloss`는 **버린다.** `text`만 Layout JSON의 `text` 필드로 들어간다.
4. 시트·콘티·검수 화면은 **항상 `text`와 `gloss`를 나란히** 보여준다.
5. 언어 혼용 허용: 한 페이지에 `ja` 내레이션 + `en` 대사가 공존할 수 있다(항목별 `lang`).
6. 검증기는 **`gloss` 누락을 오류로 차단**한다. (`lang != ko` 인데 `gloss`가 비어 있으면 통과 불가)

**텍스트는 이미지에 직접 렌더된다. 오버레이 합성 계층은 없다.**
`text`는 Layout JSON의 `text` 아이템으로 들어가 MOSS가 풍선·박스와 함께 그린다.
배경 텍스트(간판·표지·화면 UI)도 같은 방식으로 `text` 아이템에 넣는다.

**UI 표현 (S4 글 콘티 / S5 컷 분할 시트)**

```
┌───────────────────────────────────────────────┐
│ ④ [medium / over-shoulder]        char-002     │
│   은하제가 조장 자리에 서서 이자헌을 내려다본다    │
│                                                │
│   💬  "That is enough, chief."                 │
│       이제 그만하십쇼.              ← 병기(회색) │
└───────────────────────────────────────────────┘
```

**언어별 동작**

| `dialogue_language` | 시트에 보이는 것 | 프롬프트에 들어가는 것 |
| --- | --- | --- |
| `ko` | 이제 그만하십쇼. | 이제 그만하십쇼. |
| `en` | "That is enough, chief." ＋ **이제 그만하십쇼.** | That is enough, chief. |
| `ja` | もうやめなさい。 ＋ **이제 그만하십쇼.** | もうやめなさい。 |
| `zh` | 算了吧，课长。 ＋ **이제 그만하십쇼.** | 算了吧，课长。 |

이 계약 하나로 "다국어로 만들되 나는 한국어로 검수한다"가 성립한다.
프롬프트 정본(`references/authoring-spec.md` §13.5 "사용자 지정 문안은 글자 그대로 보존")과도 충돌하지 않는다 —
`text`만 프롬프트로 가고 `gloss`는 시트 계층에 머문다.

---

## 9. 컷 분할 — `manga` 모드 전용

> 이 절은 **`manga` 모드에서만** 적용된다. `illustration`·`comic`은 컷 분할이 없으므로
> 템플릿 선택·단 구성·컷 시트가 전부 비활성화된다.

### 9.0 컷 분할 3단계 (사용자 질문에 대한 답)

> "컷 분할이 자유롭다 / 완전히 경직 / 중간. 사용자가 선택할 수 있어도 좋겠지"

**가능하다. 단 "자유"에는 안전장치가 필요하다.** 세 단계를 실제로 구현한다.

| 모드 | LLM이 하는 일 | 도구가 하는 일 | 렌더 조건 |
| --- | --- | --- | --- |
| `template` | 템플릿 ID만 고른다 | bbox 생성 | 항상 통과 |
| `balanced` (기본) | 템플릿 ID + 단 비율 + (선택) 컷 병합/분할 | bbox 생성 + 검증 | 검증 통과 |
| `free` | 컷 bbox를 직접 제안 | **T-rule·거터·순서 검증** | **검증 통과 시에만** |

`free`에서 실패하는 전형: 4컷이 `+`로 만남, 인접 단의 세로 분할 x가 일치, 거터 불균일, 순서 모호.
검증기가 잡아서 "이 컷을 왼쪽으로 12% 밀거나, 위 컷과 병합하세요"라고 제안한다.

**"컷 분할 시트"의 UI**: 페이지 위에 컷 사각형을 그리고, 각 컷에 콘티 번호를 붙이고,
말풍선을 놓고, 실시간으로 T-rule 위반을 빨간 테두리로 표시한다.

---

## 10. 레이아웃 템플릿 라이브러리

**핵심 아이디어: 페이지를 단(tier)으로 먼저 나누고, 각 단을 컷으로 쪼갠다.**
이러면 T-rule이 구조적으로 보장된다.

### 10.1 DSL

```jsonc
{
  "id": "T3C",
  "name": "3단 · 상단 분할(대사) → 하단 광폭(임팩트)",
  "use_for": ["dialogue", "reveal"],
  "stagger": 0.35,
  "tiers": [
    { "weight": 1, "panels": [1, 1] },   // 위 단을 좌우 2컷
    { "weight": 1, "panels": [1] },       // 가운데 1컷
    { "weight": 1, "panels": [1] }        // 아래 1컷(임팩트)
  ]
}
```

생성기가 `weight`(단 높이 비율)와 `panels`(단 안 컷 수·폭 비율)로 bbox를 계산한다.

### 10.2 기본 세트 — 일본 만화의 型에서 시드한다

임의로 만들지 않고, 실무에서 **이름이 붙어 있는 기본 型**(§2.1의 copainter 분류)을 시드로 쓴다.
`[단]/[단]` 표기, RTL 기준 컷 번호는 오른쪽 위가 1번. 여기에 기능별 변형을 더한다.

**씨앗 型 (실무 표준)**

| ID | 型 이름 | 구조 | 컷 | 용도 | 실무 주의점 |
| --- | --- | --- | --- | --- | --- |
| `FULL1` | 全面1コマ | `[1]` | 1 | 장면전환·초등장·결정적 순간 | 前ページ 引き가 약하면 효과 없음 |
| `T_JI2` | 2段割り(大+小) | `[1]/[1,1]` w 2:1 | 3 | 見せ場 1개 | 大ゴマ에 정보 과밀 주의 |
| `DAN3` | 3段均等割り | `[1]/[1]/[1]` | 3 | 상황설명·연결 | 전 컷 같은 크기면 강약이 사라짐 |
| `T_JI` | T字 | `[1]/[1,1]` | 3 | 상황→반응 | 상단 가로가 너무 길면 내용이 안 들어감 |
| `DAN4` | 4段割り | `[1]/[1]/[1]/[1]` | 4 | 세리후 응수·템포 | 1단이 얇아 전신이 안 들어감 |
| `TA_NOJI` | 田の字 | `[1,1]/[1,1]` | 4 | 4요소 병렬 | 병렬이라 시간 흐름이 안 남 |
| `YONKOMA` | 4コマ | `[1,1]/[1,1]` + 굵은 거터 | 4 | 개그 | — |

**기능별 변형 (우리 확장)**

| ID | 구조 | 컷 | 용도 |
| --- | --- | --- | --- |
| `T3C` | `[1,1]/[1]/[1]` | 4 | 상단 대사 → 하단 임팩트 |
| `T3B` | `[1]/[1]/[1,1]` | 4 | 하단 반응 2컷 |
| `T3D` | `[1]/[1,1]/[1]` | 4 | 가운데 대화 교환 |
| `T4B` | `[1]/[1,1]/[1]/[1]` | 5 | 템포 빠른 대화 |
| `T4C` | `[1]/[1,1]/[1,1]/[1]` | 6 | 잡담·군상 (상한 6) |
| `HALF_SPLASH` | `[1]/[1]/[1,1]` w 2:1:1 | 4 | 半スプラッシュ + 전개 |
| `INSET` | `[1]/[1]/[1]` + 인서트 중첩 | 4 | 복선 소품 강조 |

**페이지 기능 → 型 매핑** (LLM이 템플릿을 고를 때의 기본값)

| 페이지 기능 | 우선 型 |
| --- | --- |
| `opening` (도입·상황) | `DAN3`, `T_JI` |
| `dialogue` (회화) | `DAN4`, `T4B` |
| `reaction` (감정) | `T_JI2`, `T3B` |
| `climax` (見せ場) | `FULL1`, `HALF_SPLASH` |
| `turn` (페이지 넘김) | `FULL1` (引き) |
| `comedy` (개그) | `YONKOMA` |

### 10.3 실제 좌표 예 (검증용 앵커)

기본 티어 `M`(992×1408), 여백 40, 거터 14 → live 912×1328.

`T3C` (3단, 상단 2분할):

```
단 높이 = (1328 - 2*14) / 3 = 433
T1: y 40..473    → 컷2 x 40..489 / 컷1 x 503..952   (RTL: 오른쪽이 먼저)
T2: y 487..920   → 컷3 x 40..952
T3: y 934..1368  → 컷4 x 40..952
좌우 폭 = (912 - 14) / 2 = 449
```

`DAN4` (4단): 단 높이 = (1328 - 3*14) / 4 = 321 (반올림 분배)

이 좌표는 `scripts/compile_layout.py`가 그대로 `abs_centralized/yxyx`로 변환한다.
티어를 바꾸면 컷 비율(0~1 정규화)에 `(w,h)`를 곱해 다시 계산하므로, 프롬프트를 이미 만들어도 재컴파일만 하면 된다.

---

## 11. 파이프라인 단계 & 게이트

| # | 단계 | 산출물 | 게이트 |
| --- | --- | --- | --- |
| 0 | 프로젝트 설정 | `project.json` | — |
| 1 | 소스 수집 | `source/chNN.txt` | — |
| 2 | 스토리 바이블 | `bible/*.json`, plot-beats | `STORY_APPROVED` |
| 3 | 비주얼 바이블 | 캐릭터·설정·스타일 카드 | `STYLE_APPROVED`, `REFS_APPROVED` |
| 4 | 페이지 할당 | `plan/page-story-plan.json` | `PLAN_APPROVED` |
| 5 | **字コンテ (글 콘티)** | `page-NNN.conti.json` | CONTI 게이트 |
| 6 | **컷 분할 시트** (見開き 단위로 설계) | `page-NNN.sheet.json` + 검증 | `GRAMMAR_OK` |
| 7 | 프롬프트 컴파일 | `prompts/page-NNN.{prompt,negative}.txt` | `COMPILE_OK` |
| 8 | 검수 | `qc/page-NNN.qc.json` | `QC_PASS` |
| 9 | 바인딩 | 4페이지 블록 묶음 / PDF / CBZ | — |

**모드에 따라 단계가 갈린다** (`mode`, §1.1):

| 단계 | `illustration` | `comic` | `manga` |
| --- | --- | --- | --- |
| 4 페이지 할당 | ✗ | ✗ | ✓ |
| 5 字コンテ | ✗ | ✓ (컷 1개) | ✓ |
| 6 컷 시트 | ✗ | △ (단일 프레임) | ✓ (4페이지·컷 분할) |
| 배경 텍스트 | ✓ | ✓ | ✓ |
| 대사 | ✗ | ✓ | ✓ |

`illustration`은 프롬프트 컴파일까지만 간다(그림 N장). 페이지 단계 전체가 없다.

단계 5~6은 **페이지 1장이 아니라 見開き(2페이지)를 한 화면으로** 놓고 작업한다. 4페이지 블록 = 見開き 2개.

게이트 파일이 없으면 다음 단계 버튼이 잠긴다. codex 레포의 "recoverable pipeline" 방식.

---

## 12. 웹 UI 화면

| 화면 | 내용 | 활성 모드 |
| --- | --- | --- |
| **S0 모드 선택** | **최상위.** `illustration` / `comic` / `manga` 중 하나. 이후 화면 구성이 여기서 갈린다 | 전체 |
| **S1 프로젝트 설정** | 모드에 따라 항목이 바뀐다. 공통: 캔버스 티어 · 읽기 방향 · 스타일 · 대사 언어. `manga`만: 총 페이지 수(4단위) · 컷 모드 | 전체 |
| **S2 소스 & 바이블** | 소설 붙여넣기/업로드, 추출 인물·설정 카드 검토·수정·승인 | 전체 |
| **S3 페이지 할당** | 비트 카드를 페이지로 드래그. 페이지 목적 1줄, 독자 상태, 넘김 훅. **총 페이지 수는 4의 배수만** | `manga` |
| **S4 字コンテ** | 페이지별 컷 리스트: 샷 · 앵글 · 인물 · 비트 · 대사 · SFX. 대사는 **영문 창작 + 한국어 병기**(§8.6) | `comic`, `manga` |
| **S5 컷 분할 시트** | 캔버스 위 컷 사각형. 템플릿 선택, 드래그, 말풍선 배치, **T-rule 위반 실시간 하이라이트**. 見開き 단위 표시 | `manga` |
| **S6 프롬프트** | 컴파일된 Layout JSON + 네거티브, 복사, 검증 리포트, ASCII 페이지 맵 | 전체 |
| **S7 렌더 큐** | 썸네일, 페이지 단위 재생성, 이전 버전 비교 | 전체 |
| **S8 내보내기** | 4페이지 블록 PDF/CBZ(묶음 단위 8페이지), 프롬프트 팩(JSON) | 전체 |

- **S0가 최상위**다. `illustration`을 고르면 S3~S5가 아예 나타나지 않는다(페이지 개념 없음).
- `illustration`도 S4는 쓸 수 있다 — 단 대사가 아니라 **배경 텍스트 항목**만.
- **S5가 `manga`의 핵심 화면**이다. 여기서 "병신되는" 레이아웃을 도구가 막는다.

---

## 13. 기술 스택 & 리포 구조

- **백엔드**: Python + FastAPI (기존 `scripts/compile_layout.py`·`build_negative.py`를 서비스로 감싼다)
- **프론트엔드**: Vite + React + TypeScript, 컷 편집은 SVG(무거운 캔버스 라이브러리 불필요)
- **렌더**: ComfyUI API(`/prompt`) 1순위, 또는 MOSS Gradio/vLLM-Omni `/v1/images/generations`
- **창작 계층(LLM)**: **OpenCode 서버 API** — `POST /api/session`, `POST /api/session/{id}/skill`, `POST /api/session/{id}/prompt`, `GET /api/event`(§7). `@opencode/client` SDK 사용
- **텍스트**: 이미지에 직접 렌더한다. 앱이 글자를 합성하는 레이어는 없다(§8.6)

```
ComicMakerByMoss/
├─ .opencode/skills/moss-comic-layout/   # 기존: 프롬프트 정본 + 좌표 도구
├─ app/
│  ├─ backend/  (FastAPI: routers, services/layout.py·grammar.py·compile.py·render.py, schemas)
│  └─ frontend/ (Vite React TS)
├─ templates/layouts.json                # §10 템플릿 라이브러리
├─ projects/<slug>/                      # on-disk 상태 (gitignore)
└─ docs/design.md
```

---

## 14. 캐릭터 일관성 시스템 — 레퍼런스 이미지 기반

**로라 훈련은 채택하지 않는다.** 캐릭터마다 개별 LoRA를 학습하는 방식은 쓰지 않는다.
**레퍼런스 이미지를 참조시키는 방식**으로 간다.

### 14.1 관찰 — 예제 프롬프트가 이미 답을 갖고 있다

`docs/reference-prompts/README.md`의 실측 분석 결과:

| 규칙 | 내용 |
| --- | --- |
| **R-A** | 한 페이지에서 각 인물의 **FULL 묘사는 정확히 1회** |
| **R-B** | FULL 묘사 아이템의 `label`은 **고정이 아니다** — 주역이면 `character`, 패널 장면의 일부면 `object` |
| **R-C** | 재등장은 **`the + 식별형용사 + 명사`** 로 축약 (`the bald traveler`, `the girl`) |
| **R-D** | `summary.caption`에는 인물 묘사가 없다 — 스타일 + 카운트 태그만 |
| **R-E** | 텍스트 아이템의 인물 언급은 **위치 지시용**일 뿐 |

예제 A 실측: 소녀 FULL = item 4(830자, `character`), 남성 FULL = item 1(220자, `object`),
재등장 = item 5(축약 라벨 2개), item 14~16은 위치 지시.

### 14.2 문제

MOSS-Image는 **참조 이미지 입력이 없는** text-to-image 모델이다. 같은 프롬프트라도 시드가 바뀌면
매번 다른 사람이 나온다. 32·64페이지를 진행하면 주역의 얼굴이 페이지마다 갈라진다.

> 출처: MOSS-Image 기술보고 — 참조 기반 생성(R2I)은 "탐구 중(exploring)". ASCII 리뷰 —
> 「同じプロンプトでも、シード値が変わると、毎回別の人になる」.

### 14.3 레퍼런스 이미지의 자리 — "앵커 아이템"

R-A/R-B에서 도출된다. 각 인물의 **FULL 묘사 아이템이 곧 그 인물의 정체성 앵커**다.
레퍼런스 이미지도 그 아이템에 대응시킨다. 아이템에 `ref_id`를 붙인다.

```jsonc
{
  "label": "character",
  "caption": "Main lower-center portrait focus: <인물 FULL 묘사>",
  "ref_id": "char-001",              // ← 시트 참조. 프롬프트 본문에는 안 들어간다
  "bbox": [-40, -260, 740, 490]
}
```

예제 A에 대입하면:

```
item 1  object     ref_id: char-002   ← 남성 FULL 묘사 아이템
item 4  character  ref_id: char-001   ← 소녀 FULL 묘사 아이템
item 5  object     ref_id: -          ← 축약 라벨만. 참조 없음
item 14~16 text    ref_id: -          ← 위치 지시용
```

`ref_id`는 컴파일 시 **참조 배선에만** 쓰이고 프롬프트 텍스트에는 들어가지 않는다.

### 14.4 참조 배선 — CharRef v2

`7err4/MOSS-Image-CharRef` (CharRef v2, Apache-2.0, MOSS-Image **Base**용, 좋아요 43)

- 캐릭터 사진 **1장(Picture 1) + 프롬프트 → 같은 캐릭터**(얼굴·머리·의상·화풍)를 새 장면에 그린다.
- **캐릭터별 LoRA 훈련이 필요 없다.**
- **만화 페이지 전체(MOSS JSON 레이아웃, 컷·말풍선 포함)에서 동작한다.** ← 정확히 우리 용도
- Fumika 앱(`github.com/7err4/fumika`)의 "reference picture" 옵션.

**배선 (ComfyUI ≥ 0.42)**

```
MOSSImageOstrisEditModelPatch (kv_cache on)
  → LoraLoaderModelOnly (CharRef 1.0)
  → TextEncodeMOSSImageOstrisEdit  image1 = 캐릭터 시트
                                   prompt = "Same character and art style as Picture 1." + 씬
  → negative: 같은 인코더, 빈 프롬프트
  → 50 steps, cfg 3, euler / sgm_uniform, SLG single layer 22
```

**프롬프트 규칙**

- 접두어 **`Same character and art style as Picture 1.`** 로 시작한다.
- 그 뒤에 외모 단어 몇 개(머리 스타일·눈 색·핵심 의상)를 넣으면 충실도가 눈에 띄게 오른다.
- 의상은 참조를 따른다. 프롬프트에 다른 옷을 쓰면 바꿀 수 있다.
- 참조는 **깨끗하고 큰 것**(전신 또는 반신, 단색 배경)이 최적.

**한계 — 설계에 직접 영향**

1. **이미지당 참조 1개.** 여러 인물이 나오는 장면은 **Picture 1의 정체성만** 안정적으로 가져온다. → §14.6
2. 미세한 머리 디테일(색 한 줄기, 정확한 포니테일)은 외모 단어 없이는 흔들린다.
3. 애니 화풍으로 훈련됨. 실사/3D 얼굴은 안정적으로 유지되지 않는다(의상·머리는 유지).
4. 만화 컷에서 잘라낸 참조는 소품(문·머그·말풍선)까지 따라온다 → **캐릭터만 크롭**.

### 14.5 캐릭터 시트

1. **캐릭터 카드** 작성 (§8.2): 앵커 2~4개 + 연령 사실 + 체형 + 시그니처 1개. authoring-spec §7 준수.
2. **시트 후보 생성**: 단일 인물, 클린, 단색 배경, 전신 또는 반신. 후보 4장 → 1장 승인.
3. `bible/characters/char-001/sheet.png` + `approved: true`.

CharRef는 이미지 1장만 쓰므로, 여러 뷰를 한 장에 몰아넣기보다 **깨끗한 정면 1컷**이 낫다.
turnaround·표정 시트는 별도로 만들어 참고용으로만 둔다.

### 14.6 "박스마다 지정" — 다중 참조 배선

CharRef v2는 **이미지당 참조 1개**다. 여러 인물이 나오는 장면은 Picture 1의 정체성만 안정적으로 가져온다.
그래서 §14.3의 `ref_id` 태그를 실제 배선으로 바꾸는 방법이 페이지 상황별로 갈린다.

| 페이지 상황 | 배선 | 참조 수 |
| --- | --- | --- |
| **1인 지배 페이지** | 그 인물의 시트를 `image1`로 | 1 |
| **다인, 주역 1명** | 그 페이지 `ref_id` 중 **가장 비중 큰 인물**(보통 見せゴマ에 있는 인물)의 시트를 `image1`로 | 1 |
| **다인, 여러 명 중요** | **Moss-Image-Edit(참조 1~4장)** 로 배선 | 2~4 |

**다중 참조 = 진짜 "박스마다 지정" 경로**

`Moss-Image-Edit` / ai-toolkit 포맷은 참조를 **`Picture N:` 토큰으로 프롬프트 앞에 붙이고,
텍스트 인코더가 그 이미지들을 직접 본다.** (ai-toolkit 포맷은 참조를 384×384로 줄여 프롬프트 선두에 배치)

이 구조에서는 **각 아이템 caption이 자기 참조를 이름으로 지목**할 수 있다:

```jsonc
{ "label": "character", "ref_id": "char-001",
  "caption": "Main portrait focus: the young woman, exactly as in Picture 1. <FULL 묘사>",
  "bbox": [-40, -260, 740, 490] },
{ "label": "object", "ref_id": "char-002",
  "caption": "The man, exactly as in Picture 2. <FULL 묘사>",
  "bbox": [-730, 80, -30, 480] }
```

→ 아이템마다 다른 참조를 붙이는 것이 **이 경로로 가능**하다. "박스마다 지정"이 여기서 성립한다.

**단, 실측이 필요하다.** 검증할 것:

1. 텍스트 인코더가 `Picture N` ↔ 아이템을 실제로 결합하는가
2. JSON 레이아웃의 `bbox`가 그 참조의 정체성을 해당 영역에 배치하는가
3. 참조 2~4장이 서로 섞이지 않는가
4. FKEY 스타일 어댑터와 동시에 걸 때 양쪽이 살아남는가(§14.9)

**주역 1명 규칙을 쓸 때**: 나머지 인물은 R-C대로 **축약 라벨 + 텍스트 앵커**로 둔다.
그 인물의 정체성이 꼭 필요한 순간(클로즈업)이 오면 **그 컷만 따로 뽑아 Edit LoRA로 교정**한다(§14.7).

### 14.7 교정 — Edit LoRA

`chinoll/Moss-Image-Edit` (참조 1~4장, 네이티브 ComfyUI PR #17296,
`edit_format`: `ai-toolkit` / `ai-toolkit (kv_cache off)` / `Moss-Image-Edit`).
특정 컷의 얼굴만 틀렸을 때 **페이지 전체를 재생성하지 않고** 그 부분만 고친다.

### 14.8 일관성 QC

페이지 생성 후:

1. 각 인물의 얼굴 영역을 잘라 **캐릭터 시트와 비교** — 임베딩 유사도 또는 VLM 판정.
2. 임계 이하 → 재생성 플래그.
3. `qc/page-NNN.qc.json` → `character_drift: [{char, score}]`.

### 14.9 실측이 필요한 미해결

- **Base vs SFT 호환.** CharRef는 **Base**용, FKEY 스타일 어댑터는 **SFT**용이다.
  둘을 체인 로드할 때 품질이 유지되는지 **실측 필요.** 안 되면 스타일과 캐릭터 중 하나를 포기하거나,
  SFT 기반 캐릭터 LoRA를 직접 훈련한다.
- **스타일 vs 캐릭터 충돌.** CharRef는 "same character **and art style**"이라 스타일까지 참조에서 가져온다.
  FKEY 화풍을 유지하려면 **시트를 FKEY 화풍으로 먼저 생성**해 두는 것이 안전하다.

---

## 15. 리스크 & 미해결 질문

### 리스크

1. **대사 언어별 렌더 품질 편차** — 공식 보증은 영어·중국어지만 한국어도 정상 동작(사용자 확인).
   언어를 처음 쓸 때 1페이지 테스트로 확정한다. **텍스트는 항상 이미지에 직접 렌더되며
   오버레이 계층은 없다**(§8.6). 시트의 한국어 병기는 별개 계층이라 무관하다.
2. **레이아웃 정확도** — MOSS는 bbox가 실험적이라고 명시. 컷이 합쳐질 수 있다.
   → 컷 수를 줄이고, 컷 경계를 `object` 아이템으로 명시하고, 렌더 후 검수.
3. **페이지 간 일관성** — 캐릭터 드리프트. 비주얼 바이블 + 캐릭터 앵커 재사용(스킬 §7).
4. **비용/시간** — 페이지당 1회 생성 × 32페이지. 미리보기(저해상·저스텝) → 확정 렌더 2단계 권장.

### 사용자 결정이 필요한 질문

**확정 (2026-11-05)**

| 항목 | 결정 |
| --- | --- |
| **출력 모드** | **`illustration` / `comic` / `manga` 3종, 최상위 선택**(§1.1) |
| 읽기 방향 | 기본 **`rtl`**(일본 만화). UI에서 `ltr`로 변경 가능 |
| 기본 대사 언어 | **`en`**. 字コンテ에서 처음부터 영문 창작 + 한국어 병기. **번역 단계 없음**(§8.6) |
| 페이지 수 | **4의 배수만**(4/8/12/…). 9·10·11 페이지는 존재하지 않음. `manga` 전용 |
| 렌더 백엔드 | 이번 범위 밖. **프롬프트 출력까지** |
| 캔버스 | **A4 근사 세로 + 티어 `M`(992×1408)**. S/L/XL 변경 가능(§8.1) |
| LLM 계층 | **OpenCode 서버 API를 백엔드로 사용**(§7) |

**남은 확인 사항**

1. **프롬프트 산출물 단위** — 페이지당 파일 1개인가, 4페이지(또는 8페이지) 묶음 1개인가?

---

## 부록 A. 이번 설계에 반영한 출처

**만화 문법 (교차검증, §2.1)**

- Rachel Thorn, *On Manga Page Layouts* — T-rule
- Neil Cohn, *The Visual Language of Comics* (2014) — blocking
- copainter「漫画のコマ割りの基本と型集」 — 페이지당 컷 수, 見せゴマ 크기, 型一覧, 거터·말풍선 규칙
- atam-academy「漫画のコマ割りの描き方」 — 컷 수 상한 8, 상하/좌우 거터, 템플릿
- MediBang「初心者マンガ講座06 コマ割り」 — 5~6컷, 3~4단, 字コンテ
- egaco「コマ割りは7つのコツ」 — 세로 분할선 stagger, 大ゴマ 1~3개, ヒキ/メクリ
- oyasumi-gamedev「漫画のコマ割りの基本とコツ」 — 見開き 단위 설계, 읽기 순서, 비트 분해 절차
- litmemo「コマ割りのやり方」 — 字コンテ 서식(1컷=1행, 화면·세리후·구도)
- art-school「漫画のコマ割り基本」 — ヒキ/メクリ, 単一ページ/見開き 배치
- CLIP STUDIO TIPS — Pro Artist's Guide / DANGUMI / 基本のコマ枠 / From Plot to Storyboard: 8-page Shonen Manga
- ImageTexT「The Construction of Panels (Koma)」 — 네임/블로킹
- Too Corporation「Storyboard」 — 만화 스토리보드 공정

**시스템·모델**

- lhfer/codex-novel-to-comic-studio (MIT) — 파이프라인·역할 계약 (§3에서 인용)
- victorhuangwq/story-to-manga, DreamingComics — 유사 시스템
- OpenCode V2 HTTP API — `skill` · `session` 엔드포인트(§7)
- OpenMOSS MOSS-Image USERGUIDE / 기술 보고서 / vLLM 레시피 — 포맷·해상도·텍스트 언어
- CivitAI FKEY Style Adapter — 스타일 프리셋

> **신뢰도 표기 원칙**: 수치는 **복수 출처 수렴**일 때만 규칙으로 채택하고(§2.1),
> 단일 출처에 기반한 내용은 문서에서 "출처 N개"로 명시한다. AI 생성 레포는 구조 참고용이지
> 만화 문법의 근거로 쓰지 않는다.
- `references/authoring-spec.md` (정본) — 프롬프트 작성 규범
