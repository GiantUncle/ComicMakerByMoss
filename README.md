# ComicMakerByMoss

MOSS-Image 기반 만화 제작 도구. 대본 → **MOSS-Image 프롬프트**(Layout JSON / bbox, 분할 블록, 연속 자연어) + 네거티브 프롬프트로 변환합니다.

## 스킬 구조

`.opencode/skills/moss-comic-layout/` — OpenCode 스킬 `moss-comic-layout`.

두 계층으로 구성됩니다.

| 계층 | 위치 | 역할 |
| --- | --- | --- |
| **행동 규범 (정본)** | `references/authoring-spec.md` | 입력 정리 · 형태 라우팅 · 스타일 추론 · 인물 통제 · 다인 격리 · 말풍선 · Layout · 접촉 기하 · 출력 전 자검. **이 문서를 따릅니다.** |
| **도구 + 실측** | `SKILL.md`, `scripts/`, 나머지 references | 스펙이 손으로 하라고 한 좌표 변환을 스크립트로 대체. 포맷 인벤토리, 텍스트 박스 실측표, 네거티브 세트, 레퍼런스 역분석. |

> `references/authoring-spec.md`가 **정본(single source of truth)** 입니다. 수정은 이 파일에서 합니다.
> 루트 `moss-image-prompt-nsfw-v2.md`는 최초 입수본의 **읽기 전용 보관본**입니다 (수정 금지).
> 보관본과 정본의 본문은 바이트 단위로 동일합니다.

## 파일

| 파일 | 용도 |
| --- | --- |
| `SKILL.md` | 스킬 진입점 — 전달물, 라우팅, 도구 사용법, 충돌 해소, 체크리스트 |
| `references/authoring-spec.md` | **정본 행동 규범** (14개 섹션, 중국어 원문 보존) |
| `references/prompt-formats.md` | MOSS-Image가 받는 5가지 입력 형식 (prose / tags / Layout JSON / **Scene JSON** / `<\|…\|>` 블록), 스키마, 좌표 계산, 해상도·샘플링 표, 출처 |
| `references/comic-planning.md` | 읽기 순서, 패널 그리드, 거터, 텍스트 역할별 박스 크기(실측), 풍선 규칙, 캐릭터 바이블 |
| `references/negative-prompts.md` | 네거티브 3블록 표준과 상황별 세트 |
| `references/verified-examples.md` | 레퍼런스 A/B/C 역분석 — 파생 캔버스, 패널 맵, 아이템별 박스 측정표 |
| `scripts/compile_layout.py` | 초안(`abs`/`xyxy`) → 컴파일(`abs_centralized`/`yxyx`) + 검증 + 페이지 ASCII 맵 + 리포트. `--target scene`으로 Scene JSON 출력, 컴파일된 프롬프트 왕복 편집 |
| `scripts/build_negative.py` | 네거티브 3블록 생성기 (`painterly`/`clean`/`lineart` × `teen`/`teen17`/`adult`) |
| `templates/draft-layout.json` | Layout 초안 템플릿 |
| `templates/type-b-sections.md` | 닫힌 태그 블록 템플릿 |

## 출력 형태 3종

스펙 §3의 Q1~Q4 결정 트리로 라우팅합니다.

| 형태 | 조건 | 스펙 |
| --- | --- | --- |
| **Layout JSON** | 포스터 / 다패널 / 정확한 좌표 / 고정 텍스트 위치 | §10 |
| **닫힌 태그 블록** | 다인 구역 격리 / 다층 심도 / 독립 색온도 | §4 |
| **연속 자연어** | 전신 겹침·뒤에서 안기 / 단일 인물 흉상 / 2D→3D 합성 / 나머지 | §5 |

## 빠른 사용

```bash
S=.opencode/skills/moss-comic-layout/scripts

# 1. 템플릿을 복사해 draft.json 편집 (박스는 abs/xyxy, 좌상단 기준 픽셀)
# 2. 컴파일 + 검증 (리포트=stderr, 프롬프트=stdout)
python $S/compile_layout.py draft.json --output prompt.txt

# 3. 네거티브 (만화 기본)
python $S/build_negative.py --style painterly --age teen

# 참고
python $S/compile_layout.py --fit "您好！\n请多关照" --vertical --font-size 24
```

좌표는 **절대 손으로 계산하지 마세요.** 스펙 §10.3의 공식(floor/ceil 외곽 확장)을
`compile_layout.py`가 ComfyUI 노드와 동일하게 처리합니다.

## 권장 생성 설정

`sampler=euler`, `scheduler=sgm_uniform`, `steps=50`, `CFG=3.0~3.5`, `shift=5.0`,
SLG skip layer 22, LoRA strength `0.6`, **프롬프트 업샘플러 OFF**(레이아웃 보존).

## 설계 문서

- `docs/design.md` — **정본.** 웹 UI 설계 (3계층 설정/산출물/파생, 프로젝트·에피소드 모델,
  프로바이더 직접 호출, 3언어, 원고 미리보기, 테마·접근성 규칙, 화면)
- `docs/reference-prompts/` — FKEY 템플릿 A/B/C **원본 보관** + **캐릭터 묘사 분포 관찰**
- `docs/archive/` — 보관본 (에피소드 모델 이전 설계)

## 스킬

| 스킬 | 역할 |
| --- | --- |
| `start-wizard` | 묻고 `wizard.json` 기록 |
| `manga-orchestrator` | 전체를 자율 진행 |
| `manga-1-source` … `manga-7-pages` | 단계별 산출물 1개씩 |
| `manga-craft/` | 공용 자산 (스킬 아님): 문법 R1–R21, 좌표 도구, 템플릿 |

## 앱

- `app/backend/` — FastAPI (프로젝트·위저드 · 스킬 복사/롤백 · **단계 실행기** ·
  프로바이더 직접 호출 · 파생 컴파일/미리보기)
- `app/frontend/` — React + Vite + TS (테마 토큰 + 대비 검사)

## 캐릭터 일관성 (핵심)

**로라 훈련 없이 레퍼런스 이미지로 간다.** 관찰된 패턴:

- 한 페이지에서 각 인물의 **FULL 묘사는 정확히 1회** — 그 아이템이 그 인물의 **앵커 아이템**
- 재등장은 **`the + 식별형용사 + 명사`** 로 축약 (`the bald traveler`)
- 레퍼런스 이미지는 **앵커 아이템에 `ref_id`로 대응**시키고, 컴파일 시 참조 배선으로 변환

→ 상세는 `docs/design.md` §14, `docs/reference-prompts/README.md`

## 출처

- `references/authoring-spec.md` (정본) / 루트 `moss-image-prompt-nsfw-v2.md` (보관본) — MOSS-Image 프롬프트 작성 실행 규범
- [OpenMOSS/MOSS-Image](https://github.com/OpenMOSS/MOSS-Image) `USERGUIDE.md` (Apache-2.0)
- ComfyUI `comfy_extras/nodes_moss_image.py` (`MOSSImageLayoutPrompt` 노드)
- OpenMOSS `moss-image-prompt-enhancer` 스킬 및 공식 예시 프롬프트
- [FKEY Style Adapter for MOSS-Image-SFT](https://civitai.com/models/3013321) — 트리거 토큰과 네거티브 3블록 구성
