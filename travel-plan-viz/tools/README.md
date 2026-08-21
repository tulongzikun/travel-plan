# tools/ — 可选调研工具（软依赖）

travel-plan-viz 的**可选**调研侧工具，供 Agent 在「调研补全」阶段参考/取数。
没配置它们 skill 照常工作（走联网调研），**不是硬依赖**——与设计 skill / 官方旅行 skill 的软依赖语义一致。
工具不被内联进成品 HTML，不引入运行时依赖，纯 JS 引擎的可移植性不因它们破例。

| 工具 | 用途 | 依赖 |
|------|------|------|
| `xhs_research.py` | 抓小红书攻略笔记（定性参考素材） | Python 3 + Playwright（`requirements.txt`） |
| `flight_research.py` | 机票实时价查询（飞猪 FlyAI 官方 API 直连） | 仅 Python 3 标准库，零第三方依赖；需自备 API Key |

## xhs_research.py — 小红书攻略抓取

### 安装

```bash
cd travel-plan-viz/tools
python3 -m pip install -r requirements.txt       # playwright
python3 -m playwright install chromium
```

### 用法

```bash
# 1) 建立会话(需要显示器,扫码或手机号登录;登录后回终端按回车)
python3 xhs_research.py login

# 2) 抓素材(默认 8 篇,输出到 ./xhs-notes/)
python3 xhs_research.py search "东京 亲子 攻略"

# 解析器自检(不需要网络与 playwright)
python3 xhs_research.py selftest
```

- **无显示器的服务器**:在有浏览器的本地机器跑一次 `login`,把 `~/.cache/xhs-research/session.json` 拷到服务器同路径即可。
- **选择器漂移**:小红书前端改版后 `search` 可能解析为空,加 `--dump` 保存原始 HTML,对照修 `parse_search_cards` / `parse_note_detail`(纯函数,改完跑 `selftest`)。
- 会话过期(突然全部解析为空且页面提示登录)→ 重跑 `login`。

### 输出

`xhs-notes/xhs-<关键词>-<时间戳>.{json,md}`:每篇笔记含标题/作者/日期/正文/标签/赞藏评数/链接。
**给 Agent 的用法约定见 `../references/research-guide.md`「本地可选工具」节**——素材仅作定性参考,坐标/票价/营业时间不直接采信,图片不用于成品页面。

### 边界

- 仅供个人调研用途,请遵守平台条款;保持默认条数与延时,别调大。
- 走渲染后 DOM 提取,不逆向签名 API。

## flight_research.py — 机票实时价（飞猪 FlyAI 直连）

### Key 申领（用户自备）

flyai.open.fliggy.com 控制台：淘宝账号 + 支付宝实名 → API Key（5000 次免费，无过期）。
**Key 绝不写进仓库、成品页或提交记录**——只用环境变量或 `--key-file` 传入。

### 用法

```bash
export FLYAI_API_KEY=...        # 或 --key-file 指向 Key 文件
python3 flight_research.py search PEK SHA 2026-10-20 [--top 5] [--out DIR]

python3 flight_research.py selftest      # 解析器自检(不需要 Key 与网络)
```

输出 `flight-notes/flights-<航线>-<日期>.{json,md}`：航班候选表（航司/航班号/起降时刻/价格/订票链接），**必带查询时间戳与来源**，供 Agent 填 `flights.candidates`（`price` + `priceQueriedAt`），页面注明「价格随订位实时变动，以订票页为准」。

### 端点核对（首跑必读）

FlyAI 官方文档在登录墙后（flyai.open.fliggy.com/docs）。脚本顶部的 `API_BASE` / `SEARCH_PATH` / `AUTH_HEADER` 三个常量按常见形态写成占位——首跑 401/404 时：

1. 登录官方文档核对 base 路径、搜索端点与鉴权头；
2. 用 `--base` / `--path` 覆盖（或直接改常量并提交修正）；
3. 返回结构对不上时 `--dump` 存原始 JSON，修 `parse_flights`（纯函数）并跑 `selftest`。

### 边界

- 只走飞猪官方 API，不爬 OTA、不代订、不背书；结果仅供调研参考。
- 单次调用即单次查询，保持低频（填一次 `flights.candidates` 通常 1 条航线 1 次足够）。
