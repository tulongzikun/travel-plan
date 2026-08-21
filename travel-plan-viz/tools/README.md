# tools/xhs_research.py — 小红书攻略抓取(可选调研工具)

travel-plan-viz 的**可选**调研侧工具:登录自己的小红书账号,按关键词抓攻略笔记,
输出 JSON + Markdown 素材,供 Agent 在「调研补全」阶段参考。
没配置它 skill 照常工作(走联网调研),**不是硬依赖**——与设计 skill / 官方旅行 skill 的软依赖语义一致。

## 安装

```bash
cd travel-plan-viz/tools
python3 -m pip install -r requirements.txt       # playwright
python3 -m playwright install chromium
```

## 用法

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

## 输出

`xhs-notes/xhs-<关键词>-<时间戳>.{json,md}`:每篇笔记含标题/作者/日期/正文/标签/赞藏评数/链接。
**给 Agent 的用法约定见 `../references/research-guide.md`「本地可选工具」节**——素材仅作定性参考,坐标/票价/营业时间不直接采信,图片不用于成品页面。

## 边界

- 仅供个人调研用途,请遵守平台条款;保持默认条数与延时,别调大。
- 走渲染后 DOM 提取,不逆向签名 API。
