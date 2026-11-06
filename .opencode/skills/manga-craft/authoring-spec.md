<!--
Authoritative behavior spec for MOSS-Image prompt authoring (CANONICAL COPY).
Provenance: originally obtained as the project root `SKILL.md`, now archived at
project root `moss-image-prompt-nsfw-v2.md`. Preserved verbatim below.

This file is the single source of truth. Edit it here. The root
`moss-image-prompt-nsfw-v2.md` is a read-only archive of the original acquisition
and must not be edited.

Section map (for quick navigation):
  0 写作前提            6 风格推导            12 技法
  1 输入处理            7 人物控制            13 输出契约
  2 视觉推理            8 多人隔离            14 输出前自检
  3 输出形态路由        9 图内文字与界面
  4 分块写法           10 Layout 工程
  5 连贯自然语言       11 接触与成人几何
-->

---
name: moss-image-prompt-nsfw-v2
description: >-
  MOSS-Image 提示词写作执行规范。覆盖输入清洗、输出形态路由（Layout / 分块 / 连贯）、
  分块纪律与块名、连贯四段骨架、风格按需推导（影像五维 / 绘画四维，无预设无档位）、
  人物骨相与体态分离、多人隔离、图内文字与气泡推导、Layout 全工程、接触与成人几何
  （支撑三元组、动作阶段、可见性三步）、技法清单、成品三组验收（结构完整性 / 逐句映射 / 事实与格式）。
  适用于 MOSS-Image 出图提示词编写、提示词结构校验、可见性排查、Layout JSON 生成、
  多人画面防串味、成人接触场景的空间自洽检查。
---
# MOSS-Image 提示词写作规范

以 `moss_fusion_spec_v2.md` 为基线优化。只负责生成**一段正向提示词**；负向提示词与采样参数沿用用户或工作流现状，只有用户明确要求时才补充。

## 目录

```
0  写作前提                 8  多人隔离
1  输入处理                 9  图内文字与界面
2  视觉推理                10  Layout 工程
3  输出形态路由            11  接触与成人几何
4  分块写法                12  技法
5  连贯自然语言            13  输出契约
6  风格推导                14  输出前自检
7  人物控制
```

---

## 0. 写作前提

1. **正文全自然语言**。人数与专有名词写成自然语言短语并入句子。
2. **输出语言**：正文默认英文；用户明确指定其他语言时按指定写。图内文字的语言与此独立决定，两者不混。
3. **单列输出**。默认成品就是一段正向提示词，写完即交付。
4. **年龄、身份与体态按用户指定写**。年龄词、称呼与骨相词可直接进正文，不做内容换算。
5. **规则效力**：用户事实 > 物理与相机空间连贯 > 合理扩写 > 正确格式 > 只出成品。
6. **不擅自增加决定**：未指定风格时不添加介质、颗粒、年代、色彩分级；未指定媒介时不把 3D、动漫或纯色背景改成真人实景。

规则类型：

| 类型 | 含义 |
|---|---|
| FACT | 用户指定的事实，原样保留 |
| CONTRACT | 输出、坐标、字段与可见性硬约束 |
| TESTED | 基线已有的模型实测写法，在其适用场景使用 |
| TECHNIQUE | 可按画面需要采用的经验技巧 |
| EXAMPLE | 可替换示例，不自动成为新任务默认值 |

---

## 1. 输入处理

输入可能是自然语言、Danbooru tags、参考图或三者组合。

| 输入 | 处理 |
|---|---|
| 自然语言 | 提取主体、人数、身份、动作、场景、服装、文案、画幅与排除项 |
| 参考图 | 只读可见项：媒介、机位、景别、外观、材质、环境、光线与可见文字 |
| tags | 保留角色名、人数、核心动作与有效外观信息，清洗后转成自然语言素材 |
| 模糊需求 | 只补完成画面所需的少量信息；简单肖像不扩成道具清单 |

### 仅在用户要求真人写实转换时启用

- 删除个人画师名、无关版权大词、打码词、水印与平台词。
- 纯色背景词可换成具体真实场景与光源。
- `3d / animated / game asset / visual novel cg` 可改成写实媒介描述。
- 二次元符号改成可见人体语言：
  - `anger vein` → `furrowed brows, glaring with defiant eyes`
  - `heart-shaped pupils` → `glossy, watery dazed eyes`
  - `nose blush` → `faint pink blush on cheeks`
  - `long earlobes` → `silver punk earrings`
- cosplayer 按天生具有该外观的真实人物写。

用户明确要纯色背景、3D、插画或动漫时，以上替换不生效。

---

## 2. 视觉推理

落笔前在内部完成，不输出分析。

### 2.1 事实提取

先认出画面属于哪些事实类型，只作标签，不携带任何句子模板：

| 事实 | 内容 |
|---|---|
| 媒介 | 真人摄影 / 数字绘画 / 2D 角色与真实三维场景共处 / 漫画 / 游戏截图 / 印刷版式 |
| 主体 | 人物与物件、数量、身份锚点 |
| 动作 | 姿态、接触、手部归属、动作阶段 |
| 场景 | 地点、时间、环境细节 |
| 取景 | 机位、景别、裁剪、焦点 |
| 光线 | 光源、方向、软硬、明暗面 |
| 内容 | 图内文字、界面部件、精确文案 |
| 排除 | 用户明确不要的元素 |

媒介是事实，不是风格来源。写它是什么，不用它自动带出任何摄影或绘画词。

### 2.2 推理八步

1. 判媒介、主体、人数、主动作、场景、机位、景别、焦点与光线。
2. 建立前／中／后景，明确主体与近物的关系。
3. 标 **FIXED**（用户定死）／**FLEXIBLE**（画面需要但可调整）／**OPTIONAL**（装饰）。
4. 校验姿势支撑、接触路径、手部归属、遮挡与裁剪可见性。
5. 选少量能传达真实感或媒介特征的细节：材质、生活痕迹、布料行为、可信道具。
6. 显著性顺序：主体与动作 → 机位与取景 → 空间与接触 → 衣物与身份 → 环境 → 细纹理。
7. 长度由复杂度决定；简单画面不膨胀，拥挤动作戏优先保证关系清楚。
8. 批量出图变机位、动作、场景与动作阶段，不靠同义替换制造差异。

### 2.3 任务模式

| 模式 | 行为 |
|---|---|
| 创作／转换 | 建立或保留完整画面事实 |
| 局部修复 | 只改出错部分，不重跑全篇创作 |
| 系列生成 | 锁定人物、画布、风格与负面词，只改指定变量 |

---

## 3. 输出形态路由

用户显式指定格式时直接服从；未指定时按序判定，撞中即停：

```text
Q1 海报 / UI / 多面板 / 精确坐标 / 固定文字位置？
   → Layout JSON

Q2 两人全身交叠 / 背抱 / carrying / grappling？
   或单人胸上特写？
   或 2D 人物要自然融入真实 3D、不能出现分镜线？
   → 连贯自然语言

Q3 多人需要分区隔离？或多层景深？或独立冷暖光？
   → 闭合标签分块

Q4 其余
   → 连贯自然语言
```

- 高细节本身不构成 Layout 的理由。
- 图内文字位置自由时不必 Layout；精确位置才走 Q1。
- 成人内容不自动决定格式，按身体交叠与空间隔离判断。
- **格式只路由一次**。后续人物、文字、接触各节只补内容，不重新改格式。
- 分块标签不是分镜；块内写方位介词，不写“第一格／上半部”。
- 跨次元合成同样走 Q2，不分块：拆块会在画面正中切出分镜线。

专项触发：

| 触发 | 章节 |
|---|---|
| 多人易串脸、串手、串灯 | §8 |
| 有图内文字、字幕、界面部件 | §9 |
| 精确坐标或多面板 | §10 |
| 身体接触或性接触 | §11 |

---

## 4. 分块写法

### 五条纪律

1. 按人物或空间层次分，不按发色、衣物等零散属性分。
2. 同一人的方位、外观、服装、配饰、道具与专属受光写在同一块。
3. 块内第一句保留方位介词，标签名不替代空间关系。
4. 顺序：全局镜头与光线 → 主体或前景 → 次要人物或中远景 → 图内文字 → 必要材质。
5. 一行一块、成对闭合、不嵌套，以 3～5 块为预算；简单画面不凑数。

块内仍是完整自然语言，不是关键词堆叠。

### 块名

块名是空间槽位标签，可按画面改，不强制枚举：

```text
style_and_camera / foreground_blur / left_subject / right_subject
midground_subject / background / text_or_subtitle / texture_lock
```

### 人数分组

- 单人且确需分块：style + midground_subject + texture_lock
- 双人分区：style + left_subject + right_subject + texture_lock
- 3～6 人：style + 各方位组块 + texture_lock
- 身体交叠者放回同一连续空间，不强行左右分块。

### 成块示例

```text
<|style_and_camera|>Gritty 1990s Hong Kong cinema widescreen shot inside a dimly lit night diner, heavy 35mm film grain.<|/style_and_camera|>
<|foreground_blur|>In the immediate left foreground, an out-of-focus dark silhouette of a man's shoulder and a rain-streaked glass partition with neon reflections partially frame the view.<|/foreground_blur|>
<|left_subject|>In sharp focus on the left under cold cyan neon light sits a European teenage girl with curly blonde hair, round gold glasses, and light freckles, wearing a dark denim jacket and holding a silver camera.<|/left_subject|>
<|right_subject|>In sharp contrast, on the right under warm amber lamp light sits an East Asian teenage girl with straight jet-black bob hair, NO glasses, and spotless porcelain skin with zero freckles, wearing a cream knit sweater and stirring a glass of iced lemon tea.<|/right_subject|>
<|background|>Through the window in the far background, a blurry wet asphalt street glows with deep blue traffic lights and a passing red taxi.<|/background|>
```

此例演示块结构与差异隔离；其中的年代、色调、人种细节只属于该场景。

---

## 5. 连贯自然语言

Q2、Q4 及不需要隔离的画面使用。长度按复杂度控制，85／150 词只作预算参考。

| 段 | 内容 |
|---|---|
| P1 | 用户指定的媒介与风格（可空）→ 机位、景别、裁剪、主光、主动作 |
| P2 | 主导主体：位置 → 外观 → 服装材质 → 姿态 → 头脸朝向 → 可见表情 → 与近物关系 |
| P3 | 每个附加主体写必要信息：位置、动作、视线、接触与职责；两人的手不混写 |
| P4 | 主体立住后写环境、景深、材质与收尾细节 |

- 风格句若存在，融入 P1，不另立说明段。
- **P1 是闸门**：机位、景别、裁剪在这里定死，后面每写一个部位都要落在它的视野内（推导方法见 §11.4）。
- 非人物图按“取景 → 主体物 → 材质与功能 → 场景 → 光线与视觉组织”写。
- 已确立角色不靠长串五官词重建，以免覆盖角色锚点。
- 不枚举无关手指、衣物与关节，不写空泛 `interacting`。
- 同系列保持风格与句式稳定，变化来自构图与动作。

### 完整示例

```text
Airy Japanese overexposed pastel film photograph, high-key diffused soft window daylight, chest-up medium shot from a slightly high angle. A young woman with loose dark-brown real hair and stray strands on her damp temple sits sideways by the open window, chin resting on her right hand, eyes sliding toward the lens without lifting her head, faint pink blush, thin white cotton camisole slipping off one shoulder, her left hand flat on the warm windowsill. Behind her a cluttered desk with a half-drunk glass and a paperback, milky lifted shadows and pale cyan-mint color cast across the whole frame.
```

此例演示 P1～P4 结构；其风格只在用户需要同类效果时采用。

---

## 6. 风格推导

**没有档位、没有预设、没有对照表。**风格从用户的视觉目标现场推导成句。

### 6.1 何时写风格

| 情况 | 行为 |
|---|---|
| 用户未提视觉目标 | 风格层为空，只写画面事实与必要现场光 |
| 用户提出目标（纪实、柔润、暗室、电影感、手机感、偷窥视角等） | 只推导实现该目标所需的维度 |
| 用户明确指定某项 | 照写，其余维度留空 |

### 6.2 推导维度

摄影与绘画共用同一套推导逻辑，只是维度的具体词不同。

**影像类**

| 维度 | 回答的问题 |
|---|---|
| 记录方式 | 像真实记录还是精心设计 |
| 光线 | 光源、方向、软硬、明暗面 |
| 镜头 | 焦段、景深、透视 |
| 影调色彩 | 明暗、反差、色彩倾向 |
| 表面质感 | 干净数码、颗粒、噪点、晕光 |

**绘画类**

| 维度 | 回答的问题 |
|---|---|
| 画种材料 | 用什么画的：赛璐璐、水彩、油画、像素、水墨 |
| 线条 | 轮廓怎么处理：粗墨线、无描边、铅笔稿、墨线轮廓 |
| 上色 | 颜色怎么铺：平涂、晕染、厚涂刮刀、抖动、矿物平涂 |
| 载体年代 | 画在什么上：纸纹、和纸、宣纸、CRT 扫描线、制作稿纸 |

只写已确定项，其余留空。不要求填满所有维度。

**每个风格词必须有来源。**写下一个风格词前，它必须能指向下面两者之一：

```text
① 用户说了（纪实、柔润、暗室、复古、手机感……）
② 画面物理必需（室内只有一盏灯，所以是单一暖光；正午室外，所以是顶光硬影）
```

两条都指不上，就删掉。`flat daylight`、`natural skin tones`、`cinematic`、`moody` 这类词最容易无来源地溜进来——它们听起来中性，实际都在替用户决定光线质感和色彩倾向。

### 6.3 视角先翻译成空间证据

「偷窥视角」优先写机位、遮挡、距离与人物未察觉，不自动变成红外 CCTV：

```text
An unposed view from behind a partially open doorway, the doorframe forming a dark blurred foreground along one side of the frame. The subject remains unaware of the camera and does not look toward the lens, seen at a distance under the room's existing practical light.
```

只有用户明确要求监控、红外或录像机成像时，才加入固定高机位、荧光绿、扫描线、时间戳。

### 6.4 推导示例（验证逻辑，不是对照表）

- 「像随手拍到的，别复古」→ 推导记录方式＋现场光＋自然透视＋中性色彩＋干净细节 → `Candid documentary photograph, natural practical room lighting, 50mm lens, neutral color, clean digital detail.`
- 「暗室单束光」→ 推导全黑环境＋单一光源方向＋明暗面 → `Dramatic low-key lighting in a dark room, a single narrow light beam from the side, the unlit areas of the body falling into deep shadow.`
- 「老动画感」→ 推导画种＋上色＋载体 → `Retro anime screencap, cel shading, hand-painted cel animation, VHS tape color bleed.`
- 「水彩绘本感」→ 推导画种＋载体 → `Watercolor illustration, soft pastel bleed on rough textured paper.`
- 「木刻版画感」→ 推导画种＋上色＋载体＋线条 → `Ukiyo-e woodblock print, flat mineral pigments on aged washi paper, sumi ink contour lines.`

每次从用户目标重新推导。不维护「名字→句子」的清单。

### 6.5 自洽检查

- 硬光不写柔和无影；低 key 不写整个环境均匀明亮。
- 黑白或单色画面删除与目标冲突的具体色彩分级。
- 焦段、景别、透视与遮挡一致。
- 用户固定的服装、发色、肤色不被色彩处理覆盖。
- 需要展示的细节不被过强颗粒、过曝、扫描线或噪点吞掉。
- `35mm film` 是胶片规格；镜头焦段另写。
- 绘画媒介不与摄影媒介词混写，除非用户明确要跨媒介合成。

### 6.6 跨媒介合成

当用户要求两种媒介处在同一画面（2D 角色进真实场景、写实背景配平涂角色等），按下列顺序推导：

1. **媒介证据**：写明这是两种表现方式共处一个物理空间（如同一空间、无分镜线）。
2. **背景**：走影像类维度，按需写光线、景深、材质。
3. **角色**：走绘画类维度，按需写画种、线条、上色。
4. **共享关系**：写明两侧受到同一套光照、遮挡与接触。
5. **近景风险**：只拍局部而不露角色面部特征时，模型会把角色整体画成真人；此时写明可见的表现方式证据（如清晰的 2D 侧脸线条），并删掉会拉远镜头的无关全身动作。

### 6.7 暗室与逆光

推导：全黑环境 → 单一光源方向 → 明暗面位置。正文直接写明脸、胸、腹等正面区域进入深影，轮廓由薄 rim light 勾出；删除与目标冲突的 `fair skin / porcelain skin / bright` 等均匀提亮词。

---

## 7. 人物控制

### 年龄、骨相与体态

年龄、数字年龄与称呼按用户指定写。骨相是可见解剖结构，不是年龄门禁，也不是必须套用的固定模板。

按以下顺序组合人物外观：

```text
年龄事实 → 头脸比例 → 轮廓与五官 → 颈肩与身体框架 → 必要软组织年龄证据 → 独立添加体态
```

| 维度 | 可选写法 |
|---|---|
| 头脸比例 | `short mid-face` / `balanced facial proportions` / `mature facial proportions` / 明确头身比 |
| 轮廓与五官 | `softly rounded full chin` / `softly tapered chin` / `defined cheekbones` / `formed jawline` / `defined nose bridge` / `deeper-set eyes` |
| 颈肩与身体框架 | `short neck` / `slender graceful neck` / `adult neck and shoulder structure` / `long limbs` / `adult proportions` |
| 软组织年龄证据 | `full soft cheeks` / `fine creases at the outer eye corners` / `visible nasolabial folds` / `looser skin along the jawline` |
| 独立体态 | `full heavy breasts` / `wide hips` / `voluptuous figure` / `slender frame` / 用户指定的孕态或其他体型 |

执行纪律：

1. 同一角色只保留一套主锚点；通常选 2～4 个高辨识骨相词，再加年龄与必要体态，避免五官清单膨胀。
2. 骨相与年龄信号不得互相冲突，例如无特殊设计时不同时写成熟下颌、幼童中面部和青春期四肢比例。
3. 乳房、臀部、腹部等属于体态，与骨相分开描述，不以 `curvy` 一词代替整个人物。
4. 背面、剪影、远距离或脸出画时，不详细描写看不见的五官骨相，把预算给轮廓、肩颈、手与体态。
5. 系列图逐字复用核心锚点，只换表情、动作、机位和服装等指定变量。
6. 需要锁定中间年龄段时可使用双向描述；多格画面避免无关年龄词干扰身份锚点。

组合示例：

```text
a 38-year-old woman with a mature oval face, softly defined cheekbones, a gently tapered jaw, fine creases at the outer corners of her eyes, a long elegant neck, wide hips and full heavy breasts
```

### 头发、表情与肢体

- 头发按角色设计写；需要真实发丝时用 `natural fine [发色] real human hair, thin wispy bangs, loose flyaway strands`，不覆盖秃头、极短发与特殊发型。
- 双色发写清主色与发梢：`blonde hair with pastel-pink tips`。
- 脸红需要克制时写 `faint pink blush`。
- 趴枕且不想压脸：`resting sideways against a soft pillow without squishing her cheek`。
- 遮眼、闭眼或熟睡时不写矛盾的眼神动词。
- 露脚趾可写 `five distinct, natural toes clearly visible`。
- 半脱衣写静态结果：`shirt already pushed up, skirt hem already lifted`，避免无谓增加手部动作。
- 全身镜头写清双脚与地面、鞋袜或悬空支点，防止比例漂移。
- 两人身体重叠时优先斜角或能分清肢体归属的机位。

---

## 8. 多人隔离

多人同框先写准确人数与构图，再写每个人的身份锚点、位置、手与道具归属。

需要群像隔离时可用：

```text
Featuring exactly [N] distinct [按实际人物填写], each appearing once, in an asymmetric ensemble composition (not a rigid grid).
```

它不是所有多人图的强制开头，也不统一替换人物性别与身份。

### 分区与差异

- 2 人并排：left_subject / right_subject
- 4 人围坐：top_left / bottom_left / top_right / bottom_right
- 6 人：center_sofa + standing_behind 等实际方位组

每个人在自己的块内写全必要发色、发型、肤色、服装与专属受光。后续人物可用反向阻断切断串扰：

```text
In sharp contrast, the person on the right has NO glasses, no freckles, and straight dark hair instead of curly blonde hair.
```

只写有助于区分的差异，不强造与用户设定冲突的对比。身体交叠者优先保证接触与归属，不机械套群像模板。

---

## 9. 图内文字与界面

### 基础

1. 要显示的字串用英文双引号括起；用户文案逐字保留，换行直接写或转 `\n`。
2. 高密度小字写 `small dense multi-column body text filling the entire page, tight line spacing, uniform character size`，并同步提高有效字号与分辨率。
3. 标题、UI、字幕写 `large crisp readable title text, generous letter spacing, high contrast against background`。
4. 文字越多，字号与文字版面占比要同步增加。

### 气泡形状的推导

不记固定分类。按两个问题推导：

1. **说话人在画面内还是画面外？** 画面内 → 气泡可带尾巴指向本人；画面外 → 无尾椭圆，防止自动连到画面人物。
2. **情绪强弱？** 平静陈述 → 圆角或直角；咆哮惊叫 → 短句用锯齿，长句用加宽圆角。

气泡位置贴近说话人自身头肩部，远离其他人物头部。Layout 中与他人头部保持足够距离（基线实测参考值 ≥80px，按画布比例推导）。

### 气泡三败

1. 气泡离其他人物头部太近，尾巴会就近连错人。
2. 画外说话人用带尾气泡，会连到画面人物。
3. 固定 Seed 修气泡时，在前序 item 塞入长描述会使后方人物走样。

### 界面部件

游戏截图、UI、海报类画面，界面部件的**种类、位置、引号内数值**都要写具体；只声明「有 HUD」而不写部件与数值，画面上不会出现可辨认界面。

HUD 类界面通常分布在画面四角（状态条、罗盘、装备槽、计数器等），按用户给的实际部件与数值写，不预填内容。

### 修复纪律

- 不动 `summary.caption`、负面词及无故障 item。
- 只改出错 text 项的 bbox 或句式。
- 全篇 Token 长度差尽量控制在 ±15 内。
- 竖排多位阿拉伯数字改汉字，中文姓名去半角空格；横排包装与屏幕保留数字。

---

## 10. Layout 工程

Layout 是分块的坐标版，仅用于精确布局。

### 10.1 与分块映射

| 分块 | Layout |
|---|---|
| style_and_camera | summary.caption 开头 |
| texture_lock | summary.caption 结尾 |
| 人物块 | label:"character" |
| 背景、道具、局部特写 | label:"object" |
| 图内文字、界面部件 | label:"text" + text 字段 |

三条约束：

1. item 的位置主要由 bbox 决定，caption 不再重复“左侧／上半部／第一格”等位置词。
2. 一个 item 只描述一个对象。
3. 精确文案只进 text 项，不写进人物 caption。

### 10.2 草稿

```json
{
 "width":1536,
 "height":1024,
 "bbox_coord_space":"abs",
 "bbox_format":"xyxy",
 "summary":{"caption":"整幅画面描述","meta":["可选媒介"],"canvas":"single","palette":["可选颜色"]},
 "items":[{"label":"object","caption":"被放置对象的可见外观","bbox":[176,224,800,864]}]
}
```

- 根键为 width / height / bbox_coord_space / bbox_format / summary / items。
- 画布尺寸与真实出图一致；用户尺寸不合法时报告，不静默修改。
- bbox 满足 `0 ≤ x1 < x2 ≤ width`、`0 ≤ y1 < y2 ≤ height`。
- label 为 object / character / text；text 项必须有非空 text。
- 不加未知键、children 或 parent。
- 用户文案逐字保留。

### 10.3 换算成中心原点整数 yxyx

```text
[ floor(round(y1,9)) - height/2,
  floor(round(x1,9)) - width/2,
  ceil(round(y2,9))  - height/2,
  ceil(round(x2,9))  - width/2 ]
```

先 round 再向外扩包；不归一化、不换轴、不静默裁剪。逐项复核 `top < bottom`、`left < right`。

例：1536×1024，草稿 `[176,224,800,864]` → `[-288,-592,352,32]`。

### 10.4 palette 锁色

参考图取 4～5 个主色 HEX 填 palette；正文删除冲突颜色词，末尾加 `dominated strictly by the specified palette`。人物、构图与动作保持不变。

### 10.5 成品

```json
{"summary":{"caption":"..."},"items":[{"label":"object","caption":"...","bbox":[-288,-592,352,32]}],"bbox_coord_space":"abs_centralized","bbox_format":"yxyx"}
```

单行紧凑 JSON，不加 Markdown 围栏，不套额外 caption 外壳。

### 10.6 分镜做法

1. 完整人物用 character；眼、唇、手、衣褶、文字特写用 object，caption 写 `Extreme close-up inset panel showing ONLY...`。
2. 同格双人需要分开时用两个 character item，留出实际空间间隔（按画布比例推导）。
3. 并排小格对齐共同边界。
4. 多格小分镜按格子大小选景别，格子小则放大主体，避免人物缩成 Q 版。
5. 旁白与对话用不同几何形状区分；情绪强烈的短句与长句用不同宽度的气泡。
6. 标题与草稿标号作为 text item。
7. 跨页在 summary.caption 写角色总表，各分镜重复必要身份锚点。

### 10.7 多分镜漫画母版

母版是占位骨架，提交前必须把方括号与字符串占位替换为实际文案与整数坐标。

```json
{
  "summary": {
    "meta": ["comic", "multi_panel", "digital_painting"],
    "canvas": "multi_panel",
    "caption": "[整体版式与画法描述]. Character 1 ([角色名]): [固定骨相、瞳色、发色、标志物与服饰]. Character 2 ([角色名]): [固定外观]."
  },
  "items": [
    {"label":"character","caption":"[景别]：[该角色的必要身份锚点与动作]","bbox":[0,0,100,100]},
    {"label":"object","caption":"Extreme close-up inset panel showing ONLY [局部或道具]","bbox":[0,0,100,100]},
    {"label":"text","caption":"[旁白框几何描述]","text":"[旁白]","bbox":[0,0,100,100]},
    {"label":"text","caption":"[对话气泡几何描述与指向]","text":"[台词]","bbox":[0,0,100,100]}
  ],
  "bbox_coord_space":"abs_centralized",
  "bbox_format":"yxyx"
}
```

---

## 11. 接触与成人几何

在身体接触或性接触需要精确空间关系时启用。年龄、人数、身份、体态、体位与露骨程度按用户指定，本节不做内容换算。

### 11.1 三级触发

| 级别 | 启用内容 |
|---|---|
| C1 身体接触 | 支撑、朝向、手部归属、主画面 |
| C2 明确性接触 | 加接触路径、端点、动作阶段 |
| C3 生理细节 | 用户指定或画面确实呈现时，加体液、形变与材质 |

### 11.2 八层检查表

```text
相机归属 → 支撑 → 朝向 → 主画面 → 接触路径 → 接触端点 → 体液 → 形变材质
```

它是脑内检查表，不是正文八段。落笔从接触路径与主画面起，其余只写必要信息。

- **相机归属**：POV 持机者身体按取景画入，不另算一个人。
- **支撑**：床面、椅背、前臂、墙面、悬空与缠住的腿。
- **朝向**：各人相对镜头与彼此的方向。
- **主画面**：中景或主框被哪个身体面占据。
- **接触路径**：来源、方向、轨迹与落点。
- **接触端点**：口、舌、手、器具或身体接触位置；不混写孔位。
- **体液**：来源、位置、量级与运动状态。
- **形变材质**：受力来源、可见部位、皮肤与汗液等可见细节。

**孔位锁定的具体写法**（每种情况的正确写法，不是禁令清单）：

| 接触类型 | 正确写法 |
|---|---|
| 肛门 | `anal stays anal` —— 写 anus／anal entry，不换成阴道 |
| 阴道 | 仅在明确阴道意图时写 vaginal entry，否则不猜 |
| 口部 | 写清唇还是舌的目标：`her lips around his glans` / `her tongue on her clit` |
| 跨性别主体 | 按设定写器官，不凭外观猜；`her penis` / `her testicles` 用所属格，代词一致 |
| 后入 | rear entry 时写 anus，除非明确写成阴道 |

每条接触只写一个来源与一个落点；跨性别主体按设定写器官，代词与所属格一致。

**作物门控速查**（两种最常见的裁剪，预先算好结论）：

| 主画面 | 直接删掉 | 理由 |
|---|---|---|
| 后位臀部占主框 | 正面胸部与面部细节 | 机位看不到正面 |
| 脸出画 | 表情、眼神 | 镜头给不出 |

这两条不用推导，命中即删。

**支撑三元组必须同时成立**：支撑（靠什么承重）＋朝向（各人朝哪）＋接触路径（从哪到哪）。写完其中一项，回头核另两项是否还对得上。站立接触尤其要交代：双腿分开程度、双脚落点、鞋跟高度、身高差怎么对齐（屈膝、垫高、抱离地面）。

### 11.3 动作阶段

一张静帧只锁定一个主要阶段：

```text
接近 → 初触 → 部分进入 → 完全进入 → 抽出 → 事后
```

阶段同时决定可见长度、进入深度、接触边缘、肌肉与重心、体液状态及手部发力。反复抽送属于动作循环，另写节奏，不与单次进入混写。

### 11.4 可见性

**先定机位，再推可见范围，然后才写细节。**顺序反了就会写出这个机位看不见的东西。

推可见范围三步：

```text
① 定机位：从哪一侧、什么高度、离主体多远
② 沿视线列出遮挡：谁的身体、哪条肢体、什么衣物或环境物件挡在前面
③ 只写没被挡住的部位；被挡住的部位换说法，或换机位
```

身体接触场景里最常见的遮挡：抬起的腿挡住交合处、俯下的躯干挡住女方面部、绕过去的手臂挡住接触点、长发或布料盖住胸腹。

写细节前的五条：

- 脸出画不写可见表情；背面机位不补正面细节。
- 普通外部机位只写外部可见结构、接触边缘与受力。
- 布料遮挡与裁剪之外的内容不冒充外景可见。
- 需要剖面、透视或医学示意时，明确指定相应媒介。
- 内容可以自由指定，镜头证据仍需自洽。
- **体内不可见**：插入体内的顶端、龟头、手指或器具不可见——只写外部轴身或手腕与入口边缘。**不写「看不见什么」的否定句**（否定词里的内容会被模型误提取）。

如果某个关键部位必须可见，就改机位（越过肢体、降低高度、侧移到不受遮挡的一侧），不要保留原机位又硬写它看得见。

### 11.5 体液与形变

体液按“来源 → 位置 → 量级 → 状态／方向”写。附着、拉丝、滴落与积聚须符合动作阶段。

**量级不虚标**：只有真重才写重档。轻（珠、滴、薄光）、中（抹痕、丝状、局部团块）、重（覆满、聚积）——多数画面落在轻与中。

**来源不确定时写外观，不猜名称**：写 `a thin white sheen` 或 `glistening strands`，不写精液或爱液，除非画面确实能确定来源。

形变绑定受力与可见部位。可用粗档词汇：胸的体量与挺度、阴茎勃起与弧度、外阴唇与耻毛、接触边缘的拉伸。没有受力或不在画面内时不展开。

---

## 12. 技法

按画面需要取用，不是默认配置。

| 技法 | 用途 |
|---|---|
| `selective focus`（中心精修、边缘写意） | 绘画类画面避免全图草稿感或塑料感：五官与发丝精细，衣物背景保留笔触 |
| `zero rough sketch lines` | 防止留白处露出铅笔结构线 |
| `without gaudy embroidery, plain matte borders` | 避免细碎花纹抢走面部注意力 |
| `Extreme close-up inset panel showing ONLY...` | 局部特写格用 object，防止每格长出人头 |
| 群像句 + 反向阻断句 | 多人防串脸、串发色、串灯光 |
| 明暗面直接写法 | 暗室逆光时防止正面被补成均匀亮面 |
| 半脱衣写静态结果 | 避免拉扯动词占用双手 |
| 双脚与支点写清 | 全身镜头防止比例缩成幼态 |

---

## 13. 输出契约

1. 只输出连贯自然语言、闭合标签分块或 Layout JSON 之一。
2. 默认只有一段正向提示词；用户明确要求负向词或采样参数时另列。
3. 无标题、无分析、无 meta、无中间草稿；Layout 不套额外 caption 外壳。
4. 自然语言里不带坐标，坐标只出现在 Layout。
5. 用户指定文案逐字保留，含标点、大小写与换行。

---

## 14. 输出前自检

只看成品，不看「有没有想过」。三组各管一类故障，互不重叠。

### 14.0 结构完整性 —— 查缺句

在成品文本里逐项找出对应句子，找不到即不合格。适用面按画面内容分：**S1、S7 恒查**；画面里有人物时加查 **S2、S3**；有身体接触或性接触时加查 **S4、S5**；S6 按框内框外取舍。

```text
S1 景别与机位句：全身/半身/特写 ＋ 从哪一侧、什么高度
S2 支撑句：每个人的脚、膝、手掌、背、坐面分别落在哪
S3 朝向句：每人朝哪边、彼此相对还是同向
S4 接触路径句：从哪到哪，外部可见边界停在哪
S5 阶段句：进入深度或动作停在哪一格，四肢与体液的描述是否同指一格
S6 框内表情句：脸在画面内才写；脸不在画面内则本项必须为空
S7 无同位冲突：任何两个实体不同占一处（腹部与墙、前臂与大腿、
   手臂与躯干、头与道具）
```

### 14.1 逐句映射 —— 查错句

1. 用一句朴素中文复述这个镜头能看到什么：

```text
镜头里：左边是她双手撑在砖墙上，背对着镜头略微前倾，肚子与墙之间空着一掌；
右边是老人站在她身后，屈膝，一手扣住她的髋，一手撑在墙上……
```

2. 把成品每一句对应到复述里的一个可见物。映射不上的句子删掉或改写：

```text
位置说不通 / 身体穿模 / 写了看不见的部位 / 头转方向与机位不符
```

### 14.2 事实与格式

```text
F1 用户事实、人数、身份、年龄、动作与排除项完整
F2 手、接触双方、道具归属明确
F3 未指定风格时不添加；每个风格词都能指向用户要求或画面物理必需
F4 未指定媒介时不擅自改变媒介
F5 光线、焦段、景别、色彩之间不冲突
F6 没有「名字→固定句」的预设套用
F7 只输出一种合法格式

G1 分块：每块有方位；一行一块；成对闭合；不嵌套
G2 多人：身份特征不互串；交叠人体未被错误分区
G3 连贯：主体动作先于环境；两人的手不混在一句
G4 Layout：JSON 可解析；字段合法；top < bottom、left < right
G5 Layout：画布一致；一 item 一对象；文字只在 text 项
G6 Layout：气泡指向与几何距离一致；文案逐字保留
G7 无残留占位符：方括号、y_min、[角色名] 等已全部替换
```
