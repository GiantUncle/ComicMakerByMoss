# ComicMakerByMoss

소설을 MOSS-Image 만화 원고 프롬프트로 바꾸는 도구. FastAPI 백엔드 + React/Vite 프론트엔드,
그리고 7단계 스킬 라이브러리(`.opencode/skills/`)로 이루어집니다.

한 단계는 산출물 하나를 만듭니다. 1단계 소설 → 2단계 프로젝트 설정 → 3단계 캐스트 →
4단계 레퍼런스 시트 → 5단계 페이지 계획 → 6단계 字コンテ → 7단계 컷 시트/프롬프트.

---

## 처음 설치 (새 컴퓨터)

필요한 것:

| 프로그램 | 버전 | 확인 |
| --- | --- | --- |
| Python | 3.10 이상 | `python --version` |
| Node.js | 18 이상 | `node --version` |

```bat
git clone <repo>
cd ComicMakerByMoss
run.bat
```

`run.bat` 이 알아서 합니다:

1. `python tools/doctor.py` — 이 컴퓨터에서 실행 가능한지 먼저 검사합니다.
   실패하면 **무엇을 고쳐야 하는지** 출력하고 멈춥니다 (이상한 오류로 죽지 않습니다).
2. 프론트엔드 의존성 설치 (`npm install`, 첫 실행만).
3. 백엔드 의존성 설치 (`pip install -r app/backend/requirements.txt`).
4. 8000 / 5173 포트 정리.
5. 백엔드(8000) + 프론트엔드(5173) 기동.
6. UI 가 응답할 때까지 대기 후 브라우저를 엽니다.

끄기: `stop.bat`.

### 직접 실행하고 싶다면

```bat
python -m pip install -r app\backend\requirements.txt
cd app\frontend && npm install && cd ..\..
start python -m uvicorn app.main:app --port 8000 --app-dir app\backend
cd app\frontend && npm run dev
```

- 백엔드: http://localhost:8000 (문서 `/docs`)
- 프론트엔드: http://localhost:5173

---

## 무엇이 문제인지 확인하기

```bat
python tools\doctor.py
```

검사 항목: Python 버전, Node, 백엔드 패키지, **스킬 라이브러리**, 프론트엔드 의존성,
레이아웃 데이터, `projects/` 쓰기 권한. 종료 코드 0 이면 정상.

에피소드 산출물 검사:

```bat
python tools\check_episode.py nostalgia-candy --ep ep01
```

계획·컨테·프롬프트를 한 번에 검사하고, `0 error(s)` 가 나와야 정상입니다.

백엔드만 확인:

```bat
curl http://localhost:8000/api/health
```

`{"ok": true, ...}` 이면 스킬 라이브러리까지 정상입니다.

---

## 프로젝트 구조

| 경로 | 내용 |
| --- | --- |
| `app/backend/` | FastAPI. `projects` `skills` `derive` `stages` `providers` |
| `app/frontend/` | React + Vite UI |
| `.opencode/skills/` | **배포되는 코드** — 7단계 스킬 + `manga-craft` 공용 라이브러리 |
| `projects/` | 사용자 프로젝트 (git 에 커밋하지 않음) |
| `tools/` | `doctor.py`, `check_episode.py`, 데이터 임포트 |

> `projects/` 는 git 에서 제외됩니다. `projects/` 를 지우면 작업 내용이 사라집니다.
> 반대로 `.opencode/skills/` 는 **반드시 커밋**되어야 합니다. 여기에는 레이아웃 도형
> (`moss-layouts.json`)과 프롬프트 컴파일 스크립트가 들어 있고, 없으면 앱이 페이지를
> 한 장도 만들 수 없습니다.

---

## AI 모델 설정

화면 왼쪽 레일 하단의 **AI 프로바이더 설정**에서 API 키와 엔드포인트를 넣습니다.
이 버튼은 프로젝트를 열지 않아도 항상 보입니다 — 모델을 못 부르면 앱이 아무 일도
못 하기 때문입니다.

설정 파일은 저장소 밖(`~/.comicmaker/`)에 저장되므로 clone 해도 키가 따라오지 않습니다.

---

## 환경 변수

| 변수 | 기본값 | 용도 |
| --- | --- | --- |
| `CM_SKILL_ORIGIN` | `<repo>/.opencode/skills` | 원본 스킬 위치 (읽기 전용) |
| `CM_SKILL_EDITED` | `~/.comicmaker/skills` | 사용자가 고친 스킬 사본 |
| `MOSS_DATASET_SRC` | `<repo>/../ComfyUI-MossPanelDataset` | `tools/import_moss_dataset.py` 원본 경로 |

---

## 라이선스

레이아웃 데이터셋: [sepiablue-ai/ComfyUI-MossPanelDataset](https://github.com/sepiablue-ai/ComfyUI-MossPanelDataset) (MIT).
