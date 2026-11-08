# 출력 3종 설계 v3 — 일러스트(도구) · 컷 만화 · 만화

`docs/design.md`(현행 정본)의 부속 설계.

> **v3 변경 (사용자 지적 반영)**
> - **컷 만화(comic)는 컷 분할이 없다.** 페이지마다 정적 프레임 한 컷이다. 그래서 만화
>   9단계를 공유하지 않는다. **프로젝트 설정·캐스트·레퍼런스 시트(2·3·4)만** 공유하고,
>   컷을 자르는 계열(5 계획의 컷 배치 · 7 컷 시트 · 8 아트워크의 패널 · 9의 다컷 컴파일)은
>   **쓰지 않는다.** comic 전용 4단계(브리프 → 순간 계획 → 장면 → 프롬프트)를 둔다.
> - **`registry` 를 모드별 단계 목록으로 바꾼다.** 지금은 평평한 9단계 하나뿐이다.
> - 일러스트는 v2 그대로 — **프로젝트가 아닌 상단 도구**(Type B).

근거: `docs/reference-prompts/`의 실제 예제(A/B/C)와 그 분석, `manga-craft/templates/type-b-sections.md`.

---

## 0. 한 줄 요약

| | 이름 | 정체 | 자리 | 산출물 |
| --- | --- | --- | --- | --- |
| **a** | `manga` | 다컷 만화 원고, 여러 페이지 | 프로젝트 | Type A Layout JSON `canvas: multi_panel` |
| **b** | `comic` | **이어지는 여러 페이지**, 페이지마다 **정적 한 컷**, 대사 있음 | 프로젝트 (자체 파이프라인) | Type C Layout JSON `canvas: single` |
| **c** | `illustration` | **한 장** 일러스트, 대사 없음, 배경 글자만 | **상단 도구 (프로젝트 아님)** | Type B 섹션 프롬프트 (JSON 없음) |

---

## 1. 출력 3종의 정의 — 레퍼런스가 정본

| 타입 | 파일 | 형태 | 네거티브 |
| --- | --- | --- | --- |
| **A** | `A-ryokan-2koma.positive.json` | Layout JSON, `summary.canvas: "multi_panel"` | painterly 3블록 |
| **B** | `B-commercial-clean.positive.txt` | `\|...\|` 섹션 프롬프트, **JSON·bbox 없음** | clean 3블록 |
| **C** | `C-akiha-single.positive.json` | Layout JSON, `summary.canvas: "single"`, 단일 프레임 + 내레이션/대사 | painterly 3블록 |

a = Type A, b = Type C, c = Type B (`docs/archive/pipeline-design-v0.2.md` §1.1 확정 매핑).

### 1.1 지금 코드 상태

| 조각 | A (manga) | B (illustration) | C (comic) |
| --- | --- | --- | --- |
| 프롬프트 컴파일러 | ✅ `build_page`→`compile_draft` | ❌ 섹션 컴파일러 없음 | ❌ 단일 프레임 컴파일러 없음 |
| 컷 분할 기계(5·7·8·9) | ✅ | — | ❌ **불필요 — 안 씀** |
| 캐스트·시트 | ✅ | — | ✅ **같은 방식으로 재사용** |
| 대사 3언어 | ✅ | — | ✅ 재사용 (검증 규칙만 공유) |
| 프레임워크(단계 목록) | 평평한 9단계 | — | ❌ **모드별 단계 목록 필요** |
| 저장소(즐겨찾기) | ❌ | ❌ | ❌ |

---

## 2. `illustration` (Type B) — 프로젝트 없는 상단 도구

**프로젝트·에피소드·단계가 없다.** 상단 메뉴 탭 하나가 화면 하나를 연다. 명령을 한 줄
넣으면 완성 프롬프트가 나오고, 즐겨찾기로 담거나 다음 것을 만들면 앞의 것은 버려진다.

```
명령(브리프)
   │  모델 (illustration-prompt 스킬)
   ▼
섹션 draft { style_and_aesthetic, sections:[{name, caption}], title }
   │  결정적 컴파일 (build.compile_sections)          ← 신규
   ▼
prompt.txt  =  <|artist|>fkey<|/artist|>\n
               <|style_and_aesthetic|>…<|/style_and_aesthetic|>
               <|region|>…<|/region|> …
negative.txt =  build.negative("clean")
```

- **규칙** (`type-b-sections.md`): 트리거 라인이 첫 줄. `style_and_aesthetic` 1개 + 리전 ≥1.
  좌표 없음. 두 번째 등장은 `the exact same` 으로 시작.
- **검증** `validate.validate_sections`: 트리거 첫 줄 · style 1개 · 리전 ≥1 · `<|...|>` 짝 균형.
- 화면: 캔버스·화풍 인라인, 결과 섹션 카드 + prompt/negative 복사, **★ 즐겨찾기**, 다음 프롬프트.
- **즐겨찾기**(§5)는 앱 전역. 프로젝트가 없어도 동작.

---

## 3. `comic` (Type C) — 자체 파이프라인 (컷 분할 없음)

페이지마다 **정적 프레임 한 컷**. 페이지들이 한 장소에서 조금씩 달라지는 **짧은 순간의
연속**으로 이어지고, 대사가 진행을 끌고 간다. 컷을 자르지 않으므로 **컷 시트·레이아웃
템플릿·split/focus 가 없다.**

### 3.1 단계 — 만화에서 2·3·4만 공유

| # | 단계 | 성격 | 산출물 | 게이트 |
| --- | --- | --- | --- | --- |
| 1 | **comic-1-brief** | 모델 | `episodes/<ep>/source/brief.md`, `episode.json` | `source/APPROVED` |
| 2 | `manga-2-project` (공유) | present | `project.json` | — |
| 3 | `manga-3-bible` (공유) | 모델 | `bible/characters.json` | `bible/APPROVED` |
| 4 | `manga-4-refsheets` (공유) | 결정적 | `bible/characters/*/sheet.prompt.txt` | `bible/SHEETS_APPROVED` |
| 5 | **comic-5-plan** | 모델 | `episodes/<ep>/plan/comic-plan.json` | `plan/APPROVED` |
| 6 | **comic-6-scene** | 모델 | `episodes/<ep>/pages/page-NNN.scene.json` | — |
| 7 | **comic-7-prompts** | 결정적 | `episodes/<ep>/prompts/page-NNN.{prompt,negative}.txt` | — |

- 공유 2·3·4 는 **id 그대로** 쓴다(`manga-` 접두사는 이름일 뿐, 산출물·게이트가 동일).
- **5·7·8·9(만화) 는 comic 에 없다.**

### 3.2 comic 전용 스키마 (컷·템플릿 없음)

**계획** `comic-plan.json` — 페이지 = 순간:

```jsonc
{
  "page_total": 4,                       // 기본 4. 블록 재사용을 위해 4의 배수(4/8/…)
  "moment_basis": "왜 이 장면 수인가",
  "pages": [
    { "page": 1, "moment": "그녀가 창밖을 본다",
      "change": "이전 프레임과 무엇이 달라지는가",
      "dialogue_intent": "무슨 말이 오가는가", "place": "cafe_interior" }
  ]
}
```

**장면** `page-NNN.scene.json` — 한 페이지 = 한 프레임:

```jsonc
{
  "page": 1,
  "scene": "the drawing: framing, placement, background or its absence, light, figure",
  "frame_bbox": [x1, y1, x2, y2],        // 프레임 아이템 박스 (없으면 캔버스 중앙 기본값)
  "style": "one line for this page",
  "texts": [
    { "id": "p1-d1", "kind": "dialogue", "speaker": "char-001",
      "lines": { "ko": ["…"], "en": ["…"], "ja": ["…"] },
      "bubble": "round", "tail": "char-001",
      "bbox": [x1, y1, x2, y2], "vertical": false }
  ]
}
```

- `texts` 는 만화 콘티의 texts 와 **같은 필드** → `validate_conti` 의 텍스트 검사 규칙을
  공유한다(3언어 줄 수 일치·kind·bubble·panel_ref 없음 등 조정).
- `scene` 은 만화 8단계(아트워크)의 "그림을 글로 그린다" 계약을 따른다 — 좌표·이름 금지.

### 3.3 프롬프트 컴파일 (신규 `build.compile_single_frame`)

```
summary.caption = style + 캐스트 인덱스(등장 인물 identifier_label + anchors + signature)
summary.meta    = ["comic", "single", "digital_painting"]
summary.canvas  = "single"
items = [
  { label: "character", caption: "<descriptor — 앵커 인물의 정본 묘사> <scene>", bbox: frame_bbox },
  { label: "text", caption: text_caption(kind,bubble,vertical,tail), text: lines[lang], bbox }
]
negative.txt = build.negative("painterly")
```

- **`anchor_of` 프레임은 항상 그 인물의 `descriptor` 전문을 담는다.** R-A 는 "한 페이지당 인물
  묘사 정확히 1회"이고 **한 페이지 = 한 프레임**이므로, 프레임마다 전문이 들어간다
  (`character-consistency.md` R-A, R-D). 요약의 캐스트 인덱스는 **포인터**(이름·앵커)일 뿐,
  묘사를 대신하지 않는다. **사람을 라벨/`ref_id`로 대신 표현하지 않는다.**
- 묘사는 캡션 **앞머리**에 온다 — §9가 요구하는 `Apparent age group:` 헤드가 캡션 중간에 박히지
  않도록. 장면/행동은 묘사 뒤에 온다.
- 말풍선 꼬리는 캐릭터의 `identifier_label`을 가리킨다(R-C) — raw 카드 id(`young-woman`)는
  프롬프트에 나가지 않는다.
- `anchor_of` 가 있는 프레임의 `label` 은 `character`(모델이 인물로 취급하도록). 없으면 `object`.
- 캐스트 묘사·앵커 규칙은 `character-consistency.md`·A/C 레퍼런스 README §1 을 따른다.
- 컴파일은 `canvas: single`(Type C)이며 `validate_prompt`(기존)로 검증한다.
- **선택**: ★ 즐겨찾기(§5)로 저장.

### 3.4 만화와 다른 점 요약

| | manga | comic |
| --- | --- | --- |
| 페이지당 컷 | 여러 컷(2~6) | **1 (고정)** |
| 컷 시트·템플릿·split/focus | 있음 | **없음** |
| 페이지 수 | 4의 배수 | 4의 배수(기본 4) |
| 프롬프트 캔버스 | `multi_panel` | `single` |
| 프롬프트 방식 | 다컷 구도 | 정적 프레임·순간의 연속 |

---

## 4. `manga` (Type A) — 변경 없음

기존 9단계 그대로.

---

## 5. 즐겨찾기 저장소 (모든 형식 공용)

원래 요구(*"여러 개 저장·불러오기"*)를 앱 전역 즐겨찾기 하나로 통일한다. 일러스트 탭이
읽고 쓰며, comic·manga 프롬프트 화면에도 ★ 버튼을 둔다.

```
~/.comicmaker/favorites/            ← 프로젝트 밖
  index.json
  fav-001/{ meta.json, prompt.txt, negative.txt, draft.json }
```

```
GET    /api/favorites            POST /api/favorites
GET    /api/favorites/{id}       PUT  /api/favorites/{id}      DELETE /api/favorites/{id}
```

---

## 6. 백엔드 변경

### 6.1 새 모듈

| 파일 | 역할 |
| --- | --- |
| `app/backend/app/illustration.py` | 일러스트 도구 — `generate(...)` + 라우터 |
| `app/backend/app/favorites.py` | 공용 즐겨찾기 CRUD + 라우터 |

### 6.2 고치는 곳

- **`stages/registry.py` — 모드별 단계 목록**
  ```python
  Stage(..., modes=("manga",))            # 각 단계가 어느 모드 소속인지
  STAGES_BY_MODE = {"manga": (...), "comic": (...)}
  status_for(root, project, ep, episode)  # project.mode 의 목록만
  ```
  comic 목록: `comic-1-brief`, `manga-2-project`, `manga-3-bible`, `manga-4-refsheets`,
  `comic-5-plan`, `comic-6-scene`, `comic-7-prompts`.
- **`stages/build.py`**
  - `compile_sections(draft)` (Type B).
  - `compile_single_frame(scene, project, characters, lang)` (Type C).
  - (manga의 `build_page` 는 그대로; comic 은 안 씀.)
- **`stages/validate.py`**
  - `validate_sections` (B), `validate_comic_plan`, `validate_comic_scene` (C).
- **`stages/runner.py`**
  - comic 러너 3개: `_run_comic_brief`, `_run_comic_plan`, `_run_comic_scene`(모델),
    `_run_comic_prompts`(결정적). `_RUNNERS` 에 등록.
  - 필요 craft: `character-consistency.md`(bible 공유), 새 `twitter-comic.md`(5·6단계).
- **`projects.py`** — 프로젝트 생성에서 `illustration` 제거. comic 기본값: 페이지 수 4,
  페이지당 컷 1(설정에서 컷 범위 자체를 숨김).
- **`main.py`** — `illustration.router`, `favorites.router` 등록.

### 6.3 스킬 문서

| 파일 | 내용 |
| --- | --- |
| `.opencode/skills/illustration-prompt/SKILL.md` (신규) | 명령 → Type B 섹션 draft |
| `.opencode/skills/comic-1-brief/SKILL.md` (신규) | 짧은 순간 이야기 |
| `.opencode/skills/comic-5-plan/SKILL.md` (신규) | 페이지 = 순간의 순서 |
| `.opencode/skills/comic-6-scene/SKILL.md` (신규) | 한 페이지 = 정적 장면 + 대사 |
| `.opencode/skills/comic-7-prompts/SKILL.md` (신규) | Type C 컴파일 |
| `.opencode/skills/manga-craft/twitter-comic.md` (신규) | comic 공용 브리프 — 정적·순간·대사 진행 |

---

## 7. 프런트엔드 변경

- **모드별 단계** `lib/steps.ts`: `stepsFor(mode)`.
  - `manga` 7단계(현행). `comic` 7단계: 브리프 · 설정 · 캐스트 · 시트 · **순간 계획** ·
    **장면** · 프롬프트. 설정 화면은 comic 에서 컷 범위·읽기방향을 숨긴다.
  - 만화/컷 만화는 **rail·위저드를 공유**하되 단계 정의만 모드로 갈린다.
- **일러스트 탭**: 상단바에 `Illustration` (프로바이더처럼 프로젝트 없이 항상 보임).
  새 화면 `screens/Illustration.tsx` — §2.
- **`Wizard.tsx`**: comic 단계에서 `comic-5-plan`→`comic-6-scene`→`comic-7-prompts` 렌더.
  comic 프롬프트 화면에 ★ 즐겨찾기.
- **`api.ts`**: `generateIllustration`, `favorites` 계열.

---

## 8. 구현 순서

1. **결정적 조각** — `build.compile_sections`, `build.compile_single_frame`,
   `validate.validate_sections`/`validate_comic_plan`/`validate_comic_scene`.
2. **registry 모드화** — `modes` + `STAGES_BY_MODE` + `status_for` 모드 분기.
3. **즐겨찾기** — `favorites.py` + 라우터.
4. **일러스트 도구** — 스킬 + `illustration.py` + 라우터.
5. **comic 러너** — 4개 러너 + 스킬 4개 + `twitter-comic.md` + 프로젝트 기본값.
6. **프런트** — `stepsFor(mode)` → 일러스트 탭 → comic 화면 → 즐겨찾기 버튼.
7. **검증** — 일러스트 Type B · comic 4페이지 `canvas: single` · 만화(`nostalgia-candy`) 회귀.

---

## 9. 확정 기본값 (v3)

| 항목 | 결정 |
| --- | --- |
| illustration 자리 | 프로젝트 **아님** — 상단 탭 즉석 도구, 즐겨찾기/버림 |
| comic 컷 분할 | **없음** — 페이지당 정적 프레임 1 |
| comic 단계 | 브리프·순간 계획·장면·프롬프트(전용) + 설정·캐스트·시트(만화 공유) |
| comic 페이지 수 | 4의 배수(기본 4) |
| comic 프롬프트 | `canvas: single` (Type C) |
| comic 인물 고정 | 만화와 같은 캐스트·캐릭터 시트 |
| 저장 | 앱 전역 즐겨찾기 `~/.comicmaker/favorites/` |
| 만화 | 변경 없음 |
