# 웹 UI 설계

`manga-*` 단계 스킬과 `manga-craft` 자산을 **웹에서 돌리는 제작 도구**. 설계 v0.3.

출처: Chrome Modern Web Guidance(색·테마) · W3C WAI / WCAG 2.2(대비·여백) ·
Nielsen Norman Group(위저드·점진적 노출) · PatternFly(위저드 가이드라인) ·
Adobe Spectrum(색 역할 토큰).

---

## 0. 확정 사항

| # | 결정 |
| --- | --- |
| D1 | **설정과 프롬프트를 분리한다.** 캐릭터·세계 설정은 데이터이고, 프롬프트는 그것에서 파생된다 |
| D2 | **프로젝트 안에 에피소드를 둔다.** 캐스트·세계·화풍은 프로젝트 공유, 소스·페이지는 에피소드 소유 |
| D3 | **조회·수정 대상은 스킬 md 파일 자체다.** UI에서 `SKILL.md`·`manga-craft/*.md`를 읽고 고친다 |
| D4 | **OpenCode에 의존하지 않는다.** 프로바이더를 직접 설정하고 앱이 LLM을 호출한다 |
| D5 | **ko / en / ja 3언어를 동시 생성한다.** 번역 단계 없음 |
| D6 | **언어·해상도 전환은 재컴파일이다.** 파생층을 저장하지 않아 즉시 반영된다 |
| D7 | **모든 단계에 확인·수정·리테이크가 있다.** 승인해야 다음으로 간다 |
| D8 | **캐스트는 프로젝트 단위 풀이다.** 에피소드는 출연 부분집합을 참조한다. 새 인물만 시트를 만든다 |
| D9 | **원고 미리보기를 그린다.** bbox로 해상도 크기의 원고를 그리고, 칸마다 프롬프트를, 말풍선 자리에 대사를 언어별로 오버레이 |
| D10 | **리테이크는 페이지 단위와 컷 단위 둘 다** |
| **D11** | **Light / Dark / System 테마를 제공한다.** 색은 역할 토큰으로 정의하고 라이트·다크를 각각 검증한다 |
| **D12** | **스킬 편집은 복사본에서 한다.** 원본은 읽기 전용으로 보존되고, 언제든 초기 상태로 롤백한다 |
| **D13** | **컷 수 최소·최대는 프로젝트 설정이다.** 그 범위 안에서만 페이지가 만들어진다 |

---

## 1. 웹 디자인 원칙

초보자가 처음 열어도 겁나지 않아야 한다. 규칙을 먼저 고정하고 화면을 그린다.

### 1.1 테마 — Light / Dark / System (D11)

```
설정 화면과 상단바에 3상태 토글:  [ System | Light | Dark ]
```

- 기본값은 **System**. `prefers-color-scheme`를 따르고, `color-scheme` CSS 속성을 함께 지정해
  폼 컨트롤·스크롤바·스피너까지 테마에 맞춘다.
- 선택은 저장되고 프로젝트와 무관하게 앱 전체에 적용된다.
- **라이트와 다크를 각각 검증한다. 단순 반전 금지.** 배경·테두리·텍스트를 테마별로 따로 정한다.

### 1.2 색은 이름이 아니라 역할로 정의한다

`blue`, `teal` 같은 이름은 쓰지 않는다. "이 조합이 안전한가"를 알려주지 않기 때문이다.

| 토큰 | 역할 |
| --- | --- |
| `bg` | 페이지 배경 |
| `surface` / `surface-2` | 카드, 패널, 떠 있는 층 |
| `border` | 컴포넌트 경계 |
| `fg` | 본문 텍스트 |
| `fg-muted` | 보조 텍스트 (그래도 4.5:1 유지) |
| `primary` / `primary-fg` | 주요 동작 |
| `focus` | 포커스 링 |
| `success` / `warning` / `danger` | 상태 (반드시 아이콘·라벨 동반) |

### 1.3 대비 규칙 (WCAG 2.2)

| 대상 | 최소 |
| --- | --- |
| 본문 텍스트 | **4.5:1** |
| 큰 텍스트(18.66px bold 또는 24px)와 아이콘 | **3:1** |
| UI 컴포넌트 경계·상태(입력 테두리, 체크 표시, 토글 손잡이, 포커스 링) | **3:1** |

- **색만으로 의미를 전달하지 않는다.** 경고 아이콘과 라벨을 함께 붙인다.
- 컴포넌트의 기본·호버·포커스·선택·비활성·오류 상태를 **전부** 검사한다.
  기본 상태만 통과하고 상태 색이 깨지는 경우가 흔하다.
- 테두리·구분선을 `box-shadow`·`background-image`에 의존하지 않는다. 강제 색상 모드에서 사라진다.
- **빌드 시 대비 검사 도구를 돌린다.** 토큰 쌍을 전부 검사하고 실패하면 빌드를 멈춘다.

### 1.4 여백이 관계를 만든다

W3C의 인지 접근성 패턴이다. **여백이 관계를 설명한다** — 붙어 있으면 한 덩어리, 떨어져 있으면 다른 덩어리.

- 8px 배수 스케일: `4 · 8 · 12 · 16 · 24 · 32 · 48 · 64`
- 묶음 안 간격 < 묶음 사이 간격. 이 규칙 하나로 레이아웃이 읽힌다.
- 모든 화면에 충분한 여백. 답답하면 초보자는 읽지 않는다.

### 1.5 초보자를 위한 위저드 규칙 (NN/g · PatternFly)

| # | 규칙 |
| --- | --- |
| 1 | **한 화면에 한 가지만 묻는다.** 한 화면에 두 질문을 넣지 않는다 |
| 2 | **모든 것에 기본값.** 모르면 Enter만 눌러도 끝까지 간다 |
| 3 | **진행률을 정확히 보여준다.** 단계 이름이 있는 사이드바, 현재 단계 강조 |
| 4 | **단계는 건너뛸 수 있다.** 나중에 checklist로 남긴다 |
| 5 | **앞의 답으로 뒤를 분기한다.** 모드가 illustration이면 페이지 단계가 아예 안 나온다 |
| 6 | **커밋 전에 검토 화면.** 지금까지의 선택을 한 화면에 모아 보여준다 |
| 7 | **끝나면 텅 빈 화면이 아니라 뭔가 있는 작업대로 데려간다.** 샘플이 있으면 삭제 가능함을 명시 |
| 8 | **점진적 노출.** 고급 옵션(템플릿 강제, 자유 배치)은 기본적으로 접혀 있다 |

### 1.6 화면 구조 규칙

- **상단바**: 프로젝트 이름 · 테마 토글 · 언어 토글 · 저장 상태
- **좌측 사이드바**: 단계(위저드) 또는 화 목록. 어디에 있는지 항상 보인다
- **주 영역**: 현재 작업 하나
- **우측 패널**: 선택한 것의 상세(프롬프트 전문, 메타)
- 파괴적 동작(삭제·롤백)은 확인을 받고, 되돌릴 수 있게 한다

---

## 2. 핵심 개념 — 3계층

```
① 설정 (Settings)     사람이 정하고, 프롬프트에 직접 안 들어간다
   프로젝트 · 캐스트 풀 · 세계 · 에피소드

② 산출물 (Artifacts)   단계가 만들고, 사람이 고치는 데이터
   characters.json · page-story-plan.json · conti.json

③ 파생물 (Derived)     다시 만들 수 있는 것 — 저장하지 않는다
   sheet.json · prompt.txt · negative.txt · 원고 미리보기
```

```
prompt  = compile(conti, cast, language, canvas_tier)
sheet   = instantiate(template, canvas_tier) + merge(conti) + descriptor(cast)
preview = render(prompt)
```

---

## 3. 데이터 모델

### 3.1 프로젝트 (공유)

```jsonc
// projects/talk-show/project.json
{
  "slug": "talk-show",
  "title": { "ko": "브라운의 심야토크쇼", "en": "Brown's Late Show", "ja": "ブラウンの深夜トークショー" },
  "mode": "manga",
  "canvas": { "tier": "M", "ratio": "a4_portrait" },
  "reading_direction": "rtl",
  "languages": { "default": "ko", "all": ["ko", "en", "ja"] },
  "art_style": "fkey_painterly",
  "panels": { "min": 2, "max": 4 },        // D13 — 이 범위 안에서만 페이지가 만들어진다
  "provider": { "id": "main" },
  "episodes": ["ep01", "ep02"]
}
```

**컷 수 범위(D13)** — `panels.min` / `panels.max`. 기본값은 `min 3 · max 5`.
프로젝트 설정 화면에서 조절하고, 5단계 계획과 6단계 콘티가 이 범위를 **강제**한다.
범위를 벗어난 페이지는 저장되지 않는다.

| 값 | 의미 |
| --- | --- |
| `min: 2, max: 4` | 대화·심리 위주. 임팩트 컷은 2컷까지 내려간다 |
| `min: 3, max: 5` | 기본값 |
| `min: 5, max: 6` | 정보량 많은 화. 빠른 연속용 |

### 3.2 캐스트 풀 (프로젝트 공유 — 설정층, D8)

```jsonc
// projects/talk-show/bible/characters.json
{
  "characters": [ {
    "id": "char-001",
    "name": { "ko": "이자헌", "en": "Lee Ja-heon", "ja": "イ・ジャホン" },
    "role": { "ko": "D조 과장", "en": "Section chief", "ja": "D班 課長" },
    "age_phrase": "a man in his late thirties",
    "anchors": ["gaunt hollow cheeks", "deep-set dark eyes", "a sharp blade-like stillness"],
    "signature": "a thin pale scar crossing the back of his right hand",
    "body": "lean and slightly stooped, long-fingered hands",
    "default_outfit": "a dark charcoal suit, sleeves rolled, tie loosened",
    "descriptor": "He is a man in his late thirties, …; he wears a dark charcoal suit…",
    "identifier_label": "the gaunt chief",
    "reference": { "sheet": "bible/characters/sol-eum/sheet.png", "approved": true },
    "consistency_risk": "HIGH",
    "first_seen_episode": "ep01"
  } ],
  "objects": [ { "id": "obj-bear", "name": {...}, "descriptor": "…" } ]
}
```

**시트는 인물마다 한 번** 만든다. 에피소드는 풀에서 골라 쓴다.

| 화 | 출연 | 시트 |
| --- | --- | --- |
| 1화 | 주인공 + A · B | 주인공·A·B 생성 |
| 2화 | 주인공 + C · D | 주인공은 재사용. **C·D만 신규** |
| 3화 | 주인공 + A · C | **둘 다 재사용. 신규 없음** |

### 3.3 에피소드

```jsonc
// projects/talk-show/episodes/ep02/episode.json
{
  "id": "ep02",
  "title": { "ko": "두 번째 밤", "en": "The Second Night", "ja": "二夜目" },
  "source": "episodes/ep02/source/novel.txt",
  "source_origin": "provided",
  "cast": ["char-001", "char-007", "char-008"],
  "page_budget": "estimate",
  "page_total": 16,
  "stages": { "source": true, "plan": true, "conti": false }
}
```

### 3.4 콘티 — 3언어 + 정규화 좌표

```jsonc
// episodes/ep02/pages/page-003.conti.json
{
  "page": 3, "spread": 2,
  "story_job": "…", "page_turn_hook": "…", "style": "…",
  "layout": { "template_id": "T4B" },
  "cast_index": [ { "id": "char-005", "label": "the bespectacled witness" } ],
  "panels": [ {
    "n": 1, "tier": 0, "shot": "medium", "angle": "level",
    "beat": "…", "anchor_of": "char-005",
    "characters": ["char-005"], "ref_ids": ["char-005"],
    "bg": "train_interior", "eyeline": { "subject": "char-005", "dir": "left" },
    "transition": "cut", "dialogue": ["p3-d1"], "sfx": ["p3-s1"]
  } ],
  "texts": [ {
    "id": "p3-d1", "kind": "dialogue", "panel_ref": 1, "speaker": "char-005",
    "lines": {
      "ko": ["아, 저번에도 말씀드렸었지만…", "저는 휴가 중이었습니다. 과장님."],
      "en": ["Ah, as I mentioned before…", "I was on leave, chief."],
      "ja": ["あの、以前も申し上げましたが…", "私は休暇中でした。課長。"]
    },
    "bubble": "round", "tail": "char-005",
    "bbox_norm": [0.065, 0.037, 0.202, 0.105], "vertical": false
  } ]
}
```

---

## 4. 파이프라인 — 앱이 LLM을 직접 부른다

### 4.1 프로바이더 (D4)

```jsonc
// ~/.comicmaker/providers.json
{ "providers": [ {
  "id": "main", "kind": "openai-compatible",
  "base_url": "https://…/v1", "api_key": "{env:CM_KEY}",
  "models": { "default": "…", "plan": "…", "conti": "…" }
} ] }
```

### 4.2 단계 실행 = 스킬 md를 시스템 프롬프트로 조립 (D3)

```
system = SKILL.md (해당 단계, 편집본)     ← 고치면 다음 실행부터 반영
       + manga-craft/*.md (필요한 자산)
       + 실행 계약 (스키마·경계·게이트)
user   = 프로젝트 설정 + 캐스트 풀 + 에피소드 데이터 + 앞 단계 산출물
output = 산출물 JSON
       → 검증(validate.py: 필드·좌표·패널 겹침)  ← 판정은 스크립트가 한다
       → 오류가 있으면 그 목록을 되돌려 고칠 때까지 다시 부른다 (강제 교정)
       → 오류 0 → 저장 → 게이트 → 사람이 확인하고 리테이크
```

### 4.3 단계 경계 — 프로젝트 단위와 에피소드 단위가 섞인다

| 단계 | 스킬 | 범위 | 산출물 | 게이트 |
| --- | --- | --- | --- | --- |
| 1 | manga-1-source | 에피소드 | `episodes/<ep>/episode.json`, `episodes/<ep>/source/novel.txt` | `episodes/<ep>/source/APPROVED` |
| 2 | manga-2-project | **프로젝트** | `project.json` | — |
| 3 | manga-3-bible | **프로젝트**(풀 확장) | `bible/characters.json`, 화의 `cast` | `bible/APPROVED` |
| 4 | manga-4-refsheets | **프로젝트**(빠진 시트만) | `bible/characters/<name-slug>/sheet.*` | `bible/SHEETS_APPROVED` |
| 5 | manga-5-plan | 에피소드 | `episodes/<ep>/plan/page-story-plan.json` | `episodes/<ep>/plan/APPROVED` |
| 6 | manga-6-conti | 에피소드 | `episodes/<ep>/pages/page-NNN.conti.json` | — |
| 7 | manga-7-pages | 에피소드 | `pages/page-NNN.sheet.json`, `prompts/` | — |

2·3·4는 프로젝트에 한 번, 새 인물이 나올 때만 증분으로. 1·5·6·7은 에피소드마다(6·7은 4페이지 블록 단위).

---

## 5. 화면

| 화면 | 내용 | 상태 |
| --- | --- | --- |
| **S0 프로젝트 목록** | 카드(제목·에피소드 수·진행률), [+ 새 프로젝트] | 있음 |
| **S1 프로젝트 설정** | 제목 3언어, 캔버스, 읽기방향, 기본 언어, 화풍, **컷 수 최소·최대(D13)** | 위저드 3단계 |
| **S2 캐스트 풀** | 인물 카드 편집, 시트, 소품, **출연 이력** | 있음 |
| **S3 에피소드 목록** | 화 목록, 진행률, [+ 새 에피소드] | 위저드·목록에 포함 |
| **S4 에피소드 위저드** | 소스 → 캐스트 → 계획 → 컷, 단계별 실행·확인·리테이크 | 있음 |
| **S5 페이지 워크벤치** | 컷 시트 + 콘티(3언어) + **원고 미리보기** + 템플릿 전환 | 있음 |
| **S6 프롬프트 뷰어** | 완성 프롬프트, 언어 탭, 해상도, **컷 선택 리테이크** | 미리보기·워크벤치에 포함 |
| **S7 스킬 편집기** | 편집본 편집 + **원본 보기 + 롤백(D12)** | 있음 |
| **S8 프로바이더** | base URL·키·모델 | 있음 |
| **S9 내보내기** | prompt/negative 묶음, 원고 이미지/PDF/CBZ | 남음 |

---

## 6. 원고 미리보기 (D9)

그림이 없어도 완성 프롬프트만으로 원고를 그린다. 좌표도 대사도 해상도도 이미 알고 있다.

### 6.1 그리는 법

| item | 표현 |
| --- | --- |
| `object`/`character`/`panel` | bbox 테두리 + 옅은 채움 + **caption을 박스 안에 잘라 표시**. 모서리에 `CH`/`OBJ` 라벨과 `ref_id` |
| `text` 대사·내레이션 | **`lines[lang]`의 실제 텍스트**를 bbox 위치에. `round`/`jagged`/`oval` → 타원, `rect` → 사각, `none`(SFX·floating) → 테두리 없이 굵게 |
| 이름표·타이틀 | bbox 위치에 이름·제목 |

### 6.2 조작

- **언어 토글(ko/en/ja)** → 텍스트만 다시 그린다
- **해상도(S/M/L/XL)** → 캔버스를 다시 그리고 `bbox_norm`을 스케일
- **컷 클릭** → 우측 패널에 그 컷 프롬프트 전문
- **컷 선택 → 리테이크** / **페이지 전체 → 리테이크** (D10)
- 토글: 컷 테두리 · 텍스트 · 캡션 · 좌표 눈금
- 확대/축소, 원고 여백 표시

### 6.3 구현

프롬프트(`abs_centralized`/`yxyx`)를 **SVG**로 그린다. 역변환은 한 줄:

```
x_abs = x_centered + W/2      y_abs = y_centered + H/2
```

캡션은 `<foreignObject>` 또는 줄바꿈 계산. 대사는 3언어를 이미 갖고 있으므로 언어 전환은 문자열 교체뿐이다.

**이 미리보기가 곧 원고 검수 화면이다.** 그림을 뽑기 전에 구성을 확정한다.

---

## 7. 리테이크 (D10)

**모든 단계는 끝나고 나서 사람이 확인하고 리테이크를 고른다.** 리테이크는 그 단계를
더 좁은 범위로 다시 실행하는 것 — 같은 경로에 메모와 범위를 얹는다. 범위의 단위는
그 단계가 일하는 단위다.

| 단계 | 다시 만드는 범위 | 유지되는 것 |
| --- | --- | --- |
| 1 스토리 | 에피소드 전체 | — |
| 3 캐스트 | 고른 인물 카드 | 나머지 풀 |
| 4 시트 | 고른 인물의 시트 | 나머지 시트 |
| 5 계획 | 고른 페이지 | 나머지 페이지, `page_total` |
| 6 字コンテ | 고른 페이지 / **고른 컷** | 나머지 |
| 7 프롬프트 | 고른 페이지 / **고른 컷** | 나머지 |

리테이크도 **저장 전에 검증**된다: 다시 만든 결과가 규칙을 어기면 모델이 고칠 때까지
반복하고, 그래도 오류가 남으면 게이트를 덮지 않는다.

`GET /api/stages/review` 가 단계의 산출물·검증·요약을 돌려주고(모델 없이),
`POST /api/stages/retake` 가 메모+범위로 다시 실행한다. **컷 리테이크**는 미리보기에서
컷을 골라 그 패널만 다시 쓰고(`POST /api/stages/retake-cut`) 그 페이지만 재빌드한다.

리테이크·수동 편집은 **덮어쓰기 전에 `history/`에 스냅샷**을 남긴다 → 되돌리기.

**오케스트레이터**는 이 표를 1→7 순서로 자동으로 돈다. 검증이 단계마다 강제되므로
자동 진행이라도 오류 위에 게이트를 덮지 않는다.

---

## 8. 즉시 반영 (D6)

| 바꾸는 것 | 다시 만드는 것 | 안 건드리는 것 |
| --- | --- | --- |
| 언어 | `lines[lang]` 선택 → 재컴파일 + 미리보기 | 컷·좌표·서술 |
| 해상도 | `instantiate(tier)` + `bbox_norm` 스케일 | 컷 구성·대사 |
| 화풍 | `style` 문자열 | 그 외 전부 |
| 캐릭터 서술 | `descriptor` | 컷 구성·대사 |
| 컷 템플릿 | 컷 박스 | 대사 |

---

## 9. 3언어 (D5)

- 대사·효과음·내레이션·이름표·타이틀: **`lines`에 ko/en/ja 동시 작성.** 번역이 아니라 병렬 창작.
- 이미지 서술(`descriptor`·`beat`·`style`)은 **영어 한 벌**.
- 이미지 안 **이름**은 `name[lang]`.
- 파이프라인에 번역 단계가 **없다**.

---

## 10. 스킬 편집 — 복사본과 롤백 (D12)

**원본 스킬은 읽기 전용이다.** 사용자는 복사본을 고친다.

```
skills/                         ← 원본 (배포 자산, 읽기 전용)
  manga-6-conti/SKILL.md
  manga-craft/comic-planning.md

~/.comicmaker/skills/           ← 편집본 (사용자 작업)
  manga-6-conti/SKILL.md        ← 없으면 원본을 읽는다
  manga-craft/comic-planning.md
```

읽기 규칙:

```
read(path):
  1. 편집본이 있으면 편집본
  2. 없으면 원본
```

UI 동작:

| 버튼 | 동작 |
| --- | --- |
| **편집** | 처음 누르면 원본을 편집본으로 **복사**하고 그 복사본을 연다 |
| **원본 보기** | 읽기 전용으로 원본을 나란히 보여준다 |
| **되돌리기** | 편집본을 지운다 → 다음부터 원본을 쓴다 |
| **비교** | 원본 vs 편집본 diff |

- 어느 파일이 편집됐는지 배지로 표시한다(`편집됨`).
- 상단에 **"편집된 스킬 N개"** 요약과 **전체 롤백** 버튼을 둔다.
- 프로젝트 산출물(`projects/`)은 당연히 그냥 수정된다 — 이 규칙은 **스킬 자산에만** 적용된다.

---

## 11. 리포 구조 (Q4 확정 — 평면 구조 폐기)

```
ComicMakerByMoss/
├─ app/
│  ├─ backend/
│  │  ├─ providers.py    LLM 클라이언트 (OpenAI 호환 직접 호출)
│  │  ├─ stages/         실행기 (SKILL.md 조립 → 호출 → 검증 → 산출물·게이트)
│  │  │   ├─ registry.py 스킬 7개의 표 (소유 산출물 · 게이트 · 선행조건)
│  │  │   ├─ runner.py   단계별 실행 (모델 1·3·5·6 / 결정적 4·7)
│  │  │   └─ build.py    7단계 좌표·컴파일·네거티브 (재현 가능)
│  │  ├─ derive/         파생 컴파일 · 미리보기 렌더러
│  │  ├─ skills.py       원본/편집본 로더, 복사, 롤백
│  │  └─ projects.py     프로젝트·에피소드·위저드 CRUD
│  └─ frontend/          React + Vite + TS + 디자인 토큰
├─ skills/               편집 대상 스킬 원본 (읽기 전용)
├─ tools/                compile_layout.py · instantiate_layout.py · build_negative.py
├─ projects/
│  └─ <slug>/
│     ├─ project.json
│     ├─ wizard.json
│     ├─ bible/
│     │  ├─ characters.json
│     │  ├─ APPROVED
│     │  ├─ SHEETS_APPROVED
│     │  ├─ characters/sol-eum/sheet.prompt.txt
│     │  └─ characters/rag-bear/sheet.prompt.txt
│     └─ episodes/
│        └─ ep02/
│           ├─ episode.json
│           ├─ source/novel.txt   + APPROVED
│           ├─ plan/page-story-plan.json  + APPROVED
│           ├─ pages/page-NNN.conti.json
│           ├─ pages/page-NNN.sheet.json
│           ├─ history/
│           └─ prompts/          (파생 캐시, 선택)
└─ docs/
```

---

## 12. 스킬에 반영해야 할 변경

| 스킬 | 변경 |
| --- | --- |
| manga-1-source | 경로 `episodes/<ep>/source/` |
| manga-2-project | 프로젝트 단위 유지. **`panels.min`/`panels.max` 추가(D13)**, `episodes` 배열 |
| manga-3-bible | **풀 확장**으로 의미 변경 — 새 화의 새 인물만 추가 |
| manga-4-refsheets | **빠진 시트만** 생성 |
| manga-5-plan | 경로 변경. `cast` 부분집합을 읽고 **컷 수 범위를 강제** |
| manga-6-conti | 경로 변경. 3언어 `lines` 생성. 컷 수 범위 강제 |
| manga-7-pages | 컷 시트와 프롬프트를 저장. **언어·해상도 전환은 파생 컴파일**로 분리 |
| manga-craft/pipeline.md | 경계표를 프로젝트/에피소드 2열로. §2.1 검증·리테이크 |

---

## 13. 남은 것

1. **레퍼런스 시트 렌더** — 이미지 모델이 붙으면 `sheet.png` + `reference.approved`.
   지금은 `sheet.prompt.txt` 까지. (이미지 경로를 직접 넣는 분기는 있음)
2. **내보내기 (S9)** — prompt/negative 묶음, 원고 이미지/PDF/CBZ
3. **history 비교** — 지금은 되돌리기만. 버전 간 diff
4. **컷 수 조정 그 이상** — 워크벤치는 템플릿 전환까지. 컷 경계를 직접 미세조정하기
