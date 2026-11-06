# 레퍼런스 프롬프트 원본 + 캐릭터 묘사 분포 관찰

FKEY 어댑터(CivitAI 3013321)가 배포한 3개 템플릿을 그대로 보관한다. 임의 편집하지 않는다.

| 파일 | 타입 | 형태 |
| --- | --- | --- |
| `A-ryokan-2koma.positive.json` / `.negative.txt` | **A** | Layout JSON, `canvas: multi_panel`, 18 items |
| `B-commercial-clean.positive.txt` / `.negative.txt` | **B** | 섹션 프롬프트(JSON 없음), 3 블록 |
| `C-akiha-single.positive.json` / `.negative.txt` | **C** | Layout JSON, `canvas: single`, 11 items |

---

## 1. 관찰: 캐릭터 묘사가 어디에 어떻게 박히는가

예제 A를 항목별로 스캔한 결과(직접 실행한 분석):

| item | label | 캐릭터 언급 | 형태 |
| --- | --- | --- | --- |
| 0 | object | `traveler` | 한 단어 지시 |
| **1** | **object** | **남성** | **FULL 묘사 (220자)** |
| 2 | object | — | (여관 외관) |
| 3 | text | — | (타이틀) |
| **4** | **character** | **소녀** | **FULL 묘사 (830자, 5문장)** |
| 5 | object | 소녀 + 남성 | **짧은 라벨 2개** |
| 14, 15, 16 | text | 소녀 / 남성 | 위치 지시어 |
| 6~13, 17 | text | — | 내레이션·SFX·이름표 |

### 규칙 1 — 한 페이지에서 각 인물의 FULL 묘사는 **정확히 1회**

```
소녀 FULL → item 4   (830자)   "Our slender 15-year-old Japanese teenage schoolgirl
                                (Misaki Shirosawa) with true adolescent grace—
                                neither a big-headed 10-year-old child nor a mature
                                20-year-old woman. She has a softly tapered chin,
                                …silky dark-brown hair tied up into a slightly loose,
                                cute round bun…" (5문장)

남성 FULL → item 1   (220자)   "A 40-year-old bald, heavy-set man in a casual
                                short-sleeve shirt and trousers standing beside a
                                parked car, holding a travel suitcase handle in his
                                left hand and looking calmly toward the inn."
```

### 규칙 2 — FULL 묘사가 놓이는 item의 `label`은 **고정이 아니다**

- 소녀 → `character` (그림의 주역)
- 남성 → `object` (상단 패널 **장면의 일부**로 등장)

**기준은 "그 아이템에서 그 인물이 무엇인가"다.** 인물이 독립적으로 보여지는 주역이면 `character`,
패널 장면의 구성 요소면 그 패널을 서술하는 `object` 아이템 안에서 묘사된다.

> 이게 중요하다. "캐릭터마다 `character` 아이템을 하나씩 만든다"가 **아니다.**
> 패널 아이템의 caption 안에 인물 FULL 묘사가 들어갈 수 있다.

### 규칙 3 — 재등장은 **"the + 식별형용사 + 명사"** 로 축약한다

FULL 블록을 반복하지 않는다. 식별 형용사가 그 인물의 **최고 특징**을 담는다.

| 인물 | 재등장 표현 | 식별자 |
| --- | --- | --- |
| 소녀 | `the girl` / `the petite 15-year-old sailor-uniform schoolgirl` | **sailor-uniform** |
| 남성 | `the bald traveler` / `the bald man` | **bald** |

item 5의 전문:

```
Lower-left vertical sub-panel: Inside the wooden hallway entrance,
the bald traveler stands on the left facing the petite 15-year-old
sailor-uniform schoolgirl holding her school bag on the right as they chat.
```

→ 인물 2명이 한 아이템에 있으면 **둘 다 짧은 라벨**. FULL 묘사는 각자의 앵커 아이템에만.

### 규칙 4 — `summary.caption`에는 **인물 묘사가 없다**

```
"…1girl, 1boy, school uniform, sailor collar, hair bun,
 traditional Japanese inn, ryokan, luggage, uncensored."
```

스타일 + **카운트 태그**만 있다. 얼굴·체형·머리색은 여기 없다. 실제 외모는 아이템에 있다.

### 규칙 5 — 텍스트 아이템의 인물 언급은 **위치 지시용**일 뿐

```
"…in speech bubble to the right of the girl's head."
"…between the girl and the bald man."
```

묘사가 아니라 **배치 좌표의 언어판**이다. `bbox`와 같은 일을 말로 보강한다.

---

## 2. 예제 B / C 대조

### B (섹션 프롬프트) — 요약 앵커가 style 섹션에 있다

```
<|style_and_aesthetic|>… 1girl, multiple views, same character in two states,
   tall slender 17-year-old girl, 7.5-head-tall proportions,
   platinum-blonde braided hair, white sundress, safe, wholesome.<|/style_and_aesthetic|>
<|left_close_up|>  FULL 묘사 (전신 서술)
<|right_full_body|> "In sharp contrast, … the exact same tall, long-legged
   17-year-old blonde braided girl with elegant 7.5-head-tall bishoujo
   proportions, a small head, and long slender legs. …"
```

- 카운트 + 요약 앵커가 **style 섹션**에 있다 (A/C의 `summary.caption`에 해당).
- 재등장은 **`the exact same`** 로 시작해 **비례·머리·복장만** 반복한다. FULL은 아니다.
- 즉 B도 **"FULL 1회 + 재등장은 축약"** 규칙을 따른다.

### C (단일 캔버스) — 인물이 1회만 나오면 FULL도 1개

item 0(`character`)에만 FULL 묘사, 나머지 10개는 전부 내레이션. 재등장이 없으니 축약도 없다.

---

## 3. 32·64페이지로 확장할 때 (예제에서 도출)

예제는 **단일 페이지**라 페이지 간 규칙이 없다. 축약 라벨(`the bald traveler`)은
**그 지시 대상이 같은 페이지 안에 FULL로 존재할 때만** 작동한다. 페이지를 넘어가면 지시 대상이 화면에 없다.

그래서 다페이지에서는 두 가지 중 하나가 필요하다:

| 방식 | 내용 | 비용 |
| --- | --- | --- |
| **(a) 매 페이지 FULL 재기재** | 등장하는 페이지마다 그 인물의 FULL 블록을 다시 넣는다 | 830자 × 등장 페이지 수 |
| **(b) 캐스트 총표 + 축약** | `summary.caption`에 페이지의 캐스트 요약을 넣고, 각 컷은 짧은 라벨 + 최소 앵커 | 저렴 |

프롬프트 정본(`authoring-spec.md` §10.7)은 **(b)** 를 지시한다:

> 跨页在 summary.caption 写角色总表，各分镜重复必要身份锚点
> (페이지를 넘어갈 때 summary.caption에 캐스트 총표를 쓰고, 각 컷은 필요한 신원 앵커를 반복)

예제 A/C는 (b)를 쓰지 않았는데, **단일 페이지라 총표가 불필요**했기 때문이다.
B는 style 섹션에 요약 앵커를 둠으로써 사실상 (b)에 가깝다.

**결론: 다페이지 = (b).** 매 페이지 `summary.caption`에 그 페이지 등장 캐스트의 요약 앵커를 넣고,
각 아이템은 FULL 1회 + 이후 축약.

---

## 4. 레퍼런스 이미지를 어디에 붙일 것인가

위 관찰에서 **레퍼런스 이미지의 자연스러운 자리**가 결정된다.

- 각 인물의 **FULL 묘사 아이템 = 그 인물의 정체성 앵커 아이템**이다.
- 따라서 **레퍼런스 이미지도 그 아이템에 대응**시킨다.
- 여러 인물이 한 페이지에 있으면 **앵커 아이템도 여러 개**다.

```
item 1  object     [ref: char-002]  ← 남성 FULL 묘사 아이템
item 4  character  [ref: char-001]  ← 소녀 FULL 묘사 아이템
item 5  object     [ref: -]         ← 축약 라벨만. 참조 없음
```

이 태그를 **컴파일 시점에 참조 배선으로 변환**한다. 방법과 제약은 `docs/design.md` §14.
