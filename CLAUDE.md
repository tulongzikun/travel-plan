# CLAUDE.md

给在本仓库**开发/维护这个 skill** 的 AI。终端用户怎么用 skill 见 `README.md`，skill 运行逻辑见 `travel-plan-viz/SKILL.md`。

## 这是什么

`travel-plan-viz` —— 一个 Claude Code / Codex 通用 Skill（也可适配其他 Agent），把旅行行程生成为单文件、离线可读、手机优先的 HTML（交互地图 + 每日时间轴 + 出发前提醒 + 行前须知 + 待选航班 + 片区价位酒店）。

> **命名分层（别去"统一"）**：README 门面品牌名是 **Migo · 旅行领航（魔改版）**（2026-08-23 起加「魔改版」后缀，如实标注本 fork 已大幅领先上游；英文 README 对应 "(Modded Edition)"；Migo = 候鸟领航员吉祥物），但技术 id、SKILL.md `name`、触发词、GitHub 仓库名一律保持 `travel-plan-viz` 不变——这是有意的分层设计（门面品牌与技术标识各司其职，保持安装路径与触发词稳定）。README 与 SKILL.md 名称"不一致"属正常，请勿为对齐而改动触发词或仓库名。

## 架构红线

- **混合架构**：易错的机械逻辑固化为可复用 JS 引擎，视觉表现每次交给**设计步骤**重新生成。改动时别把布局/配色写死进引擎，也别把日期/导航逻辑塞给设计步骤临场生成。
- **设计步骤可插拔（无硬依赖）**：优先用 `frontend-design` 或 `huashu-design` skill（任一已安装），都没有则走 `references/design-guidelines.md` 内置准则。这样 skill 可独立分享，不强制别人先装别的 skill。别把它改回硬依赖某个外部 skill。`assets/page-template.html` 是从已发布样例（长治/武汉/太原）蒸馏的公共骨架（`__TRIP_DATA__`/`__ENGINES__` 占位符 + 与样例同源的渲染层），定位是设计步骤的**加速器/兜底**，不是唯一出品路径；模板注释里**别写占位符或 trip-data script 标签的字面量**——校验器与组装脚本按字符串定位，注释里的字面量会被误当成真块（实测踩过）。
- **第三方旅行 skill 可选适配（软依赖，非代言）**：用户若**同时装了**飞猪、高德、腾讯地图、滴滴等官方旅行类 skill / MCP，本 skill 可调用它们拿实时/权威数据（航班、酒店、坐标、**路线规划**、用车等）来补全调研，并在成品里附「去预订 / 导航 / 叫车」行动链接；**没装则走现有静态调研，功能不缺失、不降级**。这跟「设计步骤可插拔」同构——永远是软依赖、优雅降级，**别改成硬依赖或强制安装**。底线（2026-08-24 拍板更新）：①**责任边界**——官方 skill / 官方 API 拿来的数据其实时性与真实性由对方负责，本 skill 只做适配与编排，页面标注数据来源、中性措辞、不背书不替某一家打广告；②**机票价格渠道不限**（废除旧「只经官方渠道」「不爬 OTA」两条红线）——飞猪 FlyAI、飞常准 MCP、比价工具（Google Flights 类）、OTA/聚合页面皆可作调研来源；**产出必须标来源+查询时间戳，页面声明「机票价格仅作参考、以订票页为准」（强制）**；不代订、不背书不变。细则见 `references/research-guide.md` 的「第三方 skill 适配」节（含具名官方入口），字段见 `assets/page-contract.md`。另：`map.js` 自带按境内外分流的高德/Google **免 key URI 点位链接**，以及「高德打开当日点位」**多点标注**链接 `buildAmapDayMarkersLinks`（2026-08-22 调研定论：高德路书无公开创建/导入 API，官方免 key 通道里最接近的是多点标注 URI，单链接上限 10 点、超出分块；该 URI 与导航 URI 参数表均无 coordinate 参数，坐标须先经 `wgs84ToGcj02` 转 GCJ-02，引擎已内置）——均属官方公开 URI 规范、不承载实时数据，不属于 actionLink 的「绝不手拼」禁令，边界见 page-contract「可选适配元素」。2026-07-15 拍板不变：高德 JS API 不嵌进成品页；引擎/成品页**不自建 REST 直连**——直连只发生在调研侧 CLI 工具（如 `tools/flight_research.py`），成品页仍零运行时请求。
- **引擎双端可用**：`assets/map.js`、`assets/reminders.js` 同时跑在浏览器和 Node，靠文件底部的 `if (typeof module !== 'undefined' && module.exports)` 守卫导出。改这两个文件别破坏这个守卫。`assets/validate.js` 是第三个引擎（契约机械校验，Node 侧用，含 CLI），不内联进页面。
- **坐标一律 WGS-84**：OSM 瓦片是 WGS-84，高德/腾讯返回 GCJ-02——来自它们的坐标必须经 `map.js` 的 `gcj02ToWgs84` 转换再入 `trip`，否则境内点位偏移几百米。别删这个转换，也别默认所有坐标都要转（静态调研的坐标通常已是 WGS-84）。
- **数据与呈现分离**：完整 `trip` 以 `<script id="trip-data" type="application/json">` 内嵌进成品页面，迭代修改读这块 JSON、不反解析 DOM。别把这个约定改掉。
- **离线能力如实表述**：对外说「离线可读」（文字行程离线可读；地图/图片需联网、有 onerror 降级），别写成"完全离线可用"。
- **`escapeHTML` 在 map.js 与 reminders.js 各有一份，是故意重复**——两文件须各自独立，别合并去重。
- **内容契约是权威**：`assets/page-contract.md` 定义 `trip` 数据结构和必须包含的区块。改了引擎导出的函数名/数据字段，必须同步这份契约和 `SKILL.md`。
- **tools/ 是调研侧可选工具（软依赖，不进页面）**：`tools/xhs_research.py` 抓小红书攻略素材，仅在本机装了 Python+Selenium+Chrome 且已 `login` 时可用（细则见 `references/research-guide.md`「本地可选工具」节）。它不被内联进 HTML、不引入运行时硬依赖，纯 JS 引擎的可移植性不因它破例。素材只作定性参考——坐标/票价/营业时间/图片一律不直接采信。个人自用 + 默认限速，改动别放大抓取量；解析器保持纯函数，改完 `python3 tools/xhs_research.py selftest` 必须绿。`tools/flight_research.py` 机票实时价直连（飞猪 FlyAI 官方 API，仅标准库零依赖）：`FLYAI_API_KEY` 用户自备且**绝不入库/入页面**；端点/鉴权常量按官方文档核对（CLI 可 `--base`/`--path` 覆盖）；解析器纯函数，改完 `python3 tools/flight_research.py selftest` 必须绿。`tools/gflights_research.py` 机票比价（fli 逆向 Google Flights，PyPI 包名 `flights`，零 Key）：与 flight_research 并列的机票渠道，需连通 www.google.com；逆向接口可能失效，失败如实留空换渠道；整理器纯函数，改完 `python3 tools/gflights_research.py selftest` 必须绿。`tools/hotel_research.py` 酒店实时价直连（同一 FlyAI Key 与鉴权形态，仅标准库零依赖）：**仅在出发日期确定后调用**（dateTBD 期间只给参考区间，定档重算时回填 `price`/`priceQueriedAt`/`actionLink`）；其余边界同上，`selftest` 必须绿。

## 测试

```bash
node --test test/*.test.js          # 注意是 glob，不是 `node --test test/`（后者在本机 Node 会报模块找不到）
```
只覆盖纯函数（提醒日期计算、导航链接、路线坐标、GCJ-02→WGS-84 转换、契约校验）；地图初始化与 HTML 生成靠 `samples/` 手动验证。生成成品的机械校验用 `node travel-plan-viz/assets/validate.js <成品.html>`（现存样例均为 trip-data 内嵌约定后的产物，校验应通过；早期一代样例已于 2026-08 删除）。

## 数据采集约束（写在 references/research-guide.md，改动要同步）

- **机票给建议班次**（航司+航班号+起降时刻，联网核实当季真实存在，别凭记忆写）；价格渠道不限（2026-08-24 拍板，废除「只经官方渠道」/「不爬 OTA」红线）——飞猪 skill、`tools/flight_research.py`（key 用户自备）、`tools/gflights_research.py`（Google Flights 比价，零 Key）、飞常准 MCP、OTA 页面均可（分工经验：核班次存废/全量时刻/国际与远期日期优先 gflights 全量口径，境内精确价+预订链用飞猪——飞猪体验模式列表按价截断、国际线返回空；**gflights 空≠无班**——薄/新航线 Google 可能不收录（上海-大同直飞实测 Google 全无、飞猪在售），**「无直飞」类否定结论须两渠道交叉后才可下**；飞猪体验模式远期日期（约 30 天外）可能整线返回空、近期才与 App 一致，多机场城市 gflights 须逐机场查）；结果标查询时间戳与来源，**页面声明「机票价格仅作参考、以订票页为准」（强制）**。**查航班时机刻意靠后：清单对齐之后、逐日方案之前**（首尾日以班次为约束），日期未定则推迟到调研补全。**门票只给参考区间**（不查实时）。
- **图片必须能加载**：用 `https://commons.wikimedia.org/wiki/Special:FilePath/<URL编码文件名>?width=N`（不要手拼 `upload.wikimedia.org/.../thumb/...` 哈希直链），且每个 URL 要 `curl` 校验返回 200 才用；图片 CSS 用 `object-fit: cover` 防变形。
- **图片按景点优先级后补、不阻塞正文（2026-08-21 拍板）**：正文数据齐就先生成交付（可无图版，`photo` 留空走降级），图片按「门面/顶流→核心/国保孤本→古镇古堡→自然/长尾」优先级逐点 200 校验后补进 trip-data 重渲染。Commons：存在性用批量 imageinfo 一次摸底，逐 URL 校验 ≥8s 间隔 + retry 退避（1s 连发第 5 个起 429）；同景区通用图须在 note 如实标注。细则见 research-guide「图片按优先级后补」节。
- **全覆盖免责声明**：所有联网信息（含天气、餐厅、评分）都标注为 AI 整理、可能过时、需自行核实。
- **文保覆盖靠名录枚举（2026-08-21 拍板，无条件）**：**国保与世遗必须逐条纳入考虑——可低优先级、不可遗漏**，任何行程都把走廊穿越各县的国保名录逐县拉全（境外对照世遗名录；第六批后乡野国保在热度内容里不可见），清单对齐时逐条给入选/排除结论，值得备选的进当日 alternatives——「验证式写准」不等于「枚举式摸齐」。细则见 research-guide「文保等级」条。
- **区域词先枚举行政区划再谈轴线（2026-08-26 拍板）**："滇西北""晋东南""潮汕"这类区域称谓，先把所辖州市县展开成全集再选走廊——热门旅游轴线 ≠ 区域地理全部（实测：滇西北轮按"大丽香"轴线摸底、漏掉整个怒江州被用户点名；同族=潮汕轮漏揭阳）。权威落点 SKILL.md 第 2 步。
- **整体优化后必报「舍弃点位 Top10」（2026-08-21 拍板⑧）**：行程级优化（换点/改线/加减点位/**改档期**）后，把当前未入选点位按含金量排 Top10，逐条带当初舍弃原因与翻案代价——排除理由会随线路改版失效（实测：定林寺/清梦观/晋城二仙庙的「绕路」理由在 D4 改线后反转为顺路），复盘清单是唯一重捞机制。**表格固定列（2026-08-30 补钉④）**：**所属县域**（精确到县/县级市/市辖区，组合条目逐一注明）｜点位与文保牌面｜当初舍弃原因｜翻案代价——县域列是读「翻案代价」的前提，读者不该为判断绕行成本再查一次地图。**触发绑定行为、不绑产出形态（2026-08-30 补钉）**：未出页的纯文字方案/骨架讨论同样触发，当轮回复必附——「还在讨论」不豁免（实测：长治改档方案轮漏报被点名）。**入表即核（2026-08-30 补钉②）**：清单条目入表前核完批次/坐标/开闭，不得带「待核」入表——核实债不许转嫁给用户拍板时刻（实测：Top20 首版十余条挂「待核」被点名；补核一轮清零还捞出两个同镇顺路递补）。**建池全枚举（2026-08-30 补钉③）**：候选池按主题线×县域全枚举（古建/石窟/红色近现代/大景区/博物馆），非动线县也要过一遍才能定「方位死位」（实测：只扫古建线→长子 4 处国七漏列、黄崖洞从未入池，两次被点名）。
- **演出/情景剧非必选（2026-08-22 拍板）**：驻场演艺（如《又见平遥》《如梦晋阳》类）不进清单默认入选、不当「必看」占位，只在用户点名时排入主线；调研可记场次/票价作参考信息，但不得与住宿/排程硬绑定。
- **点到点交通链（任何交通方式，2026-08-21 拍板泛化）**：住宿点→首站→景点间→末站→住宿点，每段方式+耗时（自驾/包车加距离、公共交通加票价），**起点为前一晚住宿点**（写错起点车程直接低估）；坐标直线×道路系数（平原 1.3/山区 1.6–2.0）估算 + 关键腿联网核实，页面标注以导航为准。**链条里每个浏览型点位附大概浏览时长（2026-08-23 拍板）**：写成「景点名（浏览约2小时）」跟在点位名后、再接下一段车程——只有车程没有浏览时长的链条会让人误判当天装不装得下；时长与当日 slot 的 `time` 字段一致（slot 已有时段就把差值带过来），交通型节点（机场/车站）标候车/值机约 X 分钟或省略，住宿节点标寄存/退房约 X 分钟。
- **联票/城市卡/年卡必查（2026-08-23 拍板）**：排完行程主动搜「目的地 联票/city pass/通票/年卡」，逐个做回本数学（单买总和 vs 卡价、预约坑），结论写进当日 tips 或行前须知；**不划算也如实写"算过、不值"**。
- **开放限制必写进景点详情（2026-08-23 拍板）**：闭馆日/仅周日短开/免费时段限制等写入 slot `openingHours`/`closedDays`，**即使当日排程已避开**——读者改期时才知道边界；别只在当日 tips 一笔带过。
- **境外交通卡+避免出租车（2026-08-23 拍板）**：境外行程每城查交通卡/次票/机场线补价，写 `preTrip.transitCards`；欧洲/日本等打车贵，车程链与 slot 交通一律公交/地铁/步行/铁路优先，打车仅作兜底并标参考价；短停城市算过不值就直说买单程。
- **境外网友推荐酒店（2026-08-23 拍板）**：境外酒店经小红书（`tools/xhs_research.py`）调研网友实测优缺点，写入 `hotelAreas[].crowdPicks`（{name, priceNote 带实付年份, note, source}，渲染带"非实时"脚注）；每片区 1–3 家，素材只作定性参考。**挖掘方法论**（正反检索/降级链/可信度分层）见 research-guide「网友实测情报挖掘」节——要点：小红书内容不进通用搜索引擎，无本地登录会话时降级到中文旅记长文/订房平台差评摘译，再没有就省略字段，**别指望用户递料、更别用软文凑数**。
- **每晚住宿随日标注（2026-08-22 拍板）**：`days[].stayArea` 标当晚住宿的大体区域（城区/镇名，返程日可省），当日车程链终于「→当晚住宿」段（末段住宿腿不得散在链外）；`hotelAreas[].lat/lng` 成对给城区级锚点（WGS-84、过县城/镇区锚点核验，宁缺勿猜），`initTravelMap` 经 `opts.stays` 画 🏨 锚点（不编号、不进路线连线）。`validate.js` 对应校验：lat/lng 不成对=ERROR、非返程日缺 stayArea/车程链无「宿」收尾=WARN。
- **天黑不走山路（安全硬约束，2026-08-21 拍板）**：日落后只走高速/国道/少量平原省道，山路段不得排在日落前后；排程对照目的地日落时刻逐日核验首尾山路腿，赶不上就收晚点/挪住宿/绕高速，清晨摸黑同理。
- **酒店连锁品牌优先（2026-08-21 拍板）**：同档位优先华住会/首旅如家/锦江/亚朵/东呈尚美系；连锁未进驻地区（景区山上、乡镇）如实降级本地口碑款并注明「非连锁」；位置优先于品牌，别为连锁多跑路。
- **酒店实时价仅定档后查（2026-08-21 拍板）**：dateTBD 期间只给 `priceRange` 参考区间、不查实时价（估算日查价无意义）；定档重算时才经官方渠道（飞猪 skill 首选 / `tools/hotel_research.py`）查，回填 `price`+`priceQueriedAt`+官方 `actionLink` 并登记 `dataSources`，页面注明以订房页为准；每片区每晚 1 次，保持低频。

**同步指针（本节是开发者侧摘要镜像，上文保留原文；权威文本在 skill 侧下列落点——改任何一侧先同步另一侧，2026-08-23 建立防漂移）**：

| 本节条目 | skill 侧权威落点 |
|---|---|
| 机票班次/实时价/查航班时机、门票参考区间 | research-guide「航班（待选，给建议班次）」「本地可选工具：flight_research」「本地可选工具：gflights_research」；page-contract `flights.candidates` |
| 图片 200 校验、按优先级后补 | research-guide「每个景点/酒店需采集」「图片按优先级后补」；page-contract `photo`（可选） |
| 全覆盖免责声明 | research-guide「免责声明（必给，覆盖全部信息）」；page-contract 免责区块 |
| 文保名录枚举 | research-guide「每个景点/酒店需采集」文保等级条；SKILL.md 第 2/3 步 |
| 舍弃点位 Top10 | SKILL.md 第 5 步（汇报格式权威） |
| 演出/情景剧非必选 | SKILL.md 第 3 步（清单默认不含驻场演艺条） |
| 点到点交通链、浏览时长、天黑不走山路 | research-guide「点到点交通」（含安全硬约束条）；page-contract `days[].tips` 交通链 |
| 联票/城市卡/年卡、境外交通卡、开放限制 | research-guide「行前须知」+「每个景点/酒店需采集」；page-contract `preTrip.transitCards`、slot `openingHours`/`closedDays` |
| 境外网友推荐酒店（crowdPicks） | research-guide「酒店」+「网友实测情报挖掘」；page-contract `hotelAreas[].crowdPicks`；tools/xhs_research.py（tools/README） |
| 每晚住宿随日标注、连锁优先、实时价定档后查 | research-guide「酒店」「本地可选工具：hotel_research」；page-contract `days[].stayArea`、`hotelAreas[].lat/lng`、`price`+`priceQueriedAt`+`actionLink`（成对）；validate.js 对应校验 |

## 部署与仓库

- **跨 Agent 安装**（软链接）：Claude Code → `~/.claude/skills/`；OpenAI Codex → `~/.codex/skills/`。
- 平台无关：核心是指令 + 纯 JS 引擎，无厂商专有依赖。其他 Agent 的适配方法与通用提示词见 `references/porting-to-other-agents.md`；改动 skill 时别引入某个 Agent 的专有工具名（如直接写 `WebSearch`），用「联网搜索工具」这类通用说法。
- 远程：**origin = fork `tulongzikun/travel-plan`**（本仓库，日常开发推送走这里）；**上游 = `zexuanw958-svg/travel-plan-viz`**（已配置 `upstream` remote，同步上游改动用 `git fetch upstream && git merge upstream/main`）。README 的「Fork 说明」节指向上游仓库（2026-08-23 拍板：删 Star History 展示、声明 Fork of 上游 + 原项目 star 数时点、本 fork Star 从 0 重新开始），属预期，别在本 fork 里"修正"它
- `git push` 若报 `HTTP2 framing layer` / SSL 瞬时错，用 `git -c http.version=HTTP/1.1 push` 并重试几次。
- **Star History 图自绘自托管**：GitHub 2026-06-30 起 starred_at 数据仅仓库管理员/协作者可读，star-history.com 的 README 热链失效且不会恢复。`.github/workflows/star-history.yml` 每日用本仓库 Actions 令牌读自己的 stargazer 数据、以 `.github/scripts/star-history-chart.js` 自绘手绘风图表，强推到单提交分支 `star-history`。**2026-08-23 拍板后本 fork README 已不再引用该图**（改「Fork 说明」节，Star 从 0 开始）——本 fork 继承的该 workflow 与 `star-history` 分支已无展示位（**2026-08-24 拍板：保留**，别再提议删除）；上游仓库与其主页仓库（`zexuanw958-svg/zexuanw958-svg`）引用的是上游自己的分支，不受本 fork 改动影响。**别把图改回热链 star-history.com**。
- **提交信息要诚实、有含金量**：这是公开仓库，提交历史是门面。用 `feat/fix/docs/chore` 如实归类，**别把真功能埋进 `chore: 加 logo` 这类装修标题**（一条 commit 只干一类事，样例/功能单独成条）。公开文件（README、CLAUDE.md）只写中性的工程说明，内部策略（如命名分层的 SEO 考量）留在 Agent 记忆里，别写进仓库。

## 文档分层

- `README.md`（中文）/ `README_en.md`（英文）—— 给终端用户/外部读者；两个独立文件、顶部超链接互切（2026-08-21 拆分，不再是单文件双语）。改任一语言的内容须同步另一语言
- `INSTALL.md` —— 给零基础终端用户的保姆级安装指南（纯中文，含 Windows；来自抖音评论区反馈）
- `CLAUDE.md`（本文件）—— 给开发本仓库的 AI
- `docs/` —— 仅存 README 用的静态素材（如 banner.png）；原设计文档与实现计划（docs/superpowers/）已于 2026-08-21 删除，内容过时且与现行 SKILL.md 演进脱节，历史在 git 中
