#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""xhs_research.py —— 小红书旅行攻略抓取(travel-plan-viz 可选调研工具)

个人调研用:登录自己的小红书账号,按关键词抓取攻略笔记,输出 JSON + Markdown 素材,
供 Agent 在「调研补全」阶段参考。走渲染后 DOM 提取,不碰签名 API;内置随机延时。

三个动词:
  login    建立会话(headed Chrome 扫码/手机号登录,cookies 存 JSON)
  search   按关键词抓笔记列表 + 正文,输出素材文件到 --out 目录
  selftest 解析器自检(纯函数,不需要 selenium 与网络)

依赖:selenium(tools/requirements.txt)+ 本机 Chrome 浏览器;Selenium 4.6+ 自带
Selenium Manager 自动匹配 chromedriver,无需手装。会话只存 cookies——注意未登录的
访客态也有 web_session cookie,登录成功与否靠人工在浏览器里确认(能进个人主页),
注入后若仍提示登录,重跑 login 即可。

边界(与 references/research-guide.md「本地可选工具」节一致):
  - 素材仅作玩法/路线/避坑/节奏的定性参考;坐标、票价、营业时间不直接采信
  - 图片一律不用小红书 CDN,成品页面图片仍走 Wikimedia + 200 校验
  - 默认抓 8 篇,别调大;仅供个人调研,请遵守平台条款
"""

import argparse
import html as html_mod
import json
import random
import re
import sys
import tempfile
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

DEFAULT_STATE = Path.home() / ".cache" / "xhs-research" / "session.json"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

# ---------- 纯解析函数(不依赖 playwright,可 selftest) ----------

_TAG_RE = re.compile(r"<[^>]+>")


def _clean(s):
    s = _TAG_RE.sub("", s or "")
    s = html_mod.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


_CARD_RE = re.compile(
    r'<a\b[^>]*href="(?P<href>/(?:search_result|explore)/[^"]+)"[^>]*>(?P<body>.*?)</a>',
    re.S,
)


def _cls(name, body):
    m = re.search(r'class="[^"]*\b%s\b[^"]*"[^>]*>(.*?)<' % name, body, re.S)
    return _clean(m.group(1)) if m else ""


def parse_search_cards(page_html):
    """搜索结果页 → [{noteId,url,title,author,likes}]。

    小红书前端无公告改版,选择器会漂移;返回空列表时用 --dump 保存现场排查。
    """
    seen, out = set(), []
    for m in _CARD_RE.finditer(page_html):
        href = html_mod.unescape(m.group("href"))
        mid = re.search(r"/(?:search_result|explore)/([0-9a-f]{12,})", href)
        note_id = mid.group(1) if mid else href
        if note_id in seen:
            continue
        body = m.group("body")
        title = _cls("title", body) or _clean(body)[:60]
        if not title:
            continue
        seen.add(note_id)
        out.append({
            "noteId": note_id,
            "url": "https://www.xiaohongshu.com" + href.split("#")[0],
            "title": title,
            "author": _cls("name", body),
            "likes": _cls("count", body),
        })
    return out


_COUNT_PAIR_RE = re.compile(r">\s*([\d.,]+\s*[万亿]?)\s*</span>\s*<span[^>]*>\s*(喜欢|收藏|评论)")


def parse_note_detail(page_html):
    """笔记详情页 → {title,date,desc,tags,counts,imageCount};缺失字段为空串/空 dict。"""
    title_m = re.search(r'id="detail-title"[^>]*>(.*?)<', page_html, re.S) \
        or re.search(r'class="title"[^>]*>(.*?)<', page_html, re.S)
    date_m = re.search(r'class="date"[^>]*>(.*?)<', page_html, re.S)
    desc_m = re.search(r'id="detail-desc"[^>]*>(.*?)</div>', page_html, re.S)
    desc_html = desc_m.group(1) if desc_m else ""
    tags = [_clean(t) for t in re.findall(r'class="[^"]*\btag\b[^"]*"[^>]*>(.*?)</a>', desc_html, re.S)]
    counts = {}
    for num, label in _COUNT_PAIR_RE.findall(page_html):
        counts[label] = num.strip()
    return {
        "title": _clean(title_m.group(1)) if title_m else "",
        "date": _clean(date_m.group(1)) if date_m else "",
        "desc": _clean(desc_html)[:3000],
        "tags": [t for t in tags if t],
        "counts": counts,
        "imageCount": len(re.findall(r"<img\b", page_html)),
    }


# ---------- 浏览器侧(依赖 selenium + Chrome,import 放函数内,selftest 无需装) ----------

def _import_selenium():
    try:
        from selenium import webdriver
    except ImportError:
        sys.exit("缺 selenium 依赖。安装: python3 -m pip install -r tools/requirements.txt"
                 "(本机还需 Chrome 浏览器;Selenium 4.6+ 自动匹配 chromedriver,无需手装;"
                 "或不用本工具,skill 照常走联网调研)")
    return webdriver


def _make_driver(webdriver, headless):
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--user-agent=" + USER_AGENT)
    options.add_argument("--window-size=1280,900")
    # 独立临时 profile:与本机其他 Chrome 实例/默认 profile 隔离,根治
    # chromedriver "user data directory is already in use"(临时目录由系统清理)
    options.add_argument("--user-data-dir=" + tempfile.mkdtemp(prefix="xhs-research-"))
    return webdriver.Chrome(options=options)


def _save_cookies(driver, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"cookies": driver.get_cookies()}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _load_cookies(driver, path):
    """注入会话 cookies。Selenium 规则:须先落地同域页面再 add_cookie。"""
    data = json.loads(path.read_text(encoding="utf-8"))
    driver.get("https://www.xiaohongshu.com")
    for c in data.get("cookies", []):
        try:
            driver.add_cookie({k: c[k] for k in ("name", "value", "domain", "path") if k in c})
        except Exception:
            pass  # 个别 cookie 域不匹配/过期,跳过即可
    driver.refresh()


def cmd_login(args):
    webdriver = _import_selenium()
    driver = _make_driver(webdriver, headless=False)
    try:
        driver.get("https://www.xiaohongshu.com")
        print("请在打开的浏览器窗口里完成登录(扫码 / 手机号)。")
        print("登录成功、能看到首页内容后,回到终端按回车保存会话…")
        input()
        cookies = driver.get_cookies()
        if not cookies:
            print("⚠ 未取到任何 cookie,会话可能未建立——请确认已登录成功,否则重跑 login。")
        _save_cookies(driver, args.state)
    finally:
        driver.quit()
    print("会话已保存:", args.state)


def cmd_search(args):
    if not args.state.exists():
        sys.exit("未找到会话 %s —— 先跑: python3 xhs_research.py login" % args.state)
    webdriver = _import_selenium()
    args.out.mkdir(parents=True, exist_ok=True)
    driver = _make_driver(webdriver, headless=not args.headed)
    try:
        _load_cookies(driver, args.state)
        driver.get(
            "https://www.xiaohongshu.com/search_result?keyword=" + urllib.parse.quote(args.keyword)
        )
        time.sleep(4)
        for _ in range(3):  # 滚两三屏凑够目标条数
            driver.execute_script("window.scrollBy(0, document.body.scrollHeight)")
            time.sleep(random.uniform(2.0, 3.5))
        html_text = driver.page_source
        if args.dump:
            (args.out / "search-raw.html").write_text(html_text, encoding="utf-8")
        cards = parse_search_cards(html_text)
        if not cards:
            logged_out = ("login-modal" in html_text   # 访客态搜索:全屏登录弹窗,0 结果渲染(2026-08-23 实测)
                          or "扫码登录" in html_text or "登录" in html_text)
            hint = "疑似未登录/会话过期(重跑 login)" if logged_out \
                else "选择器可能漂移(加 --dump 保存现场排查)"
            sys.exit("未解析到笔记卡片:" + hint)

        notes = []
        for i, c in enumerate(cards[: args.notes], 1):
            print("[%d/%d] %s" % (i, min(len(cards), args.notes), c["title"][:40]))
            driver.get(c["url"])
            time.sleep(random.uniform(3.0, 5.0))
            raw = driver.page_source
            if args.dump:
                (args.out / ("note-%d-raw.html" % i)).write_text(raw, encoding="utf-8")
            notes.append(dict(c, **parse_note_detail(raw)))
            time.sleep(random.uniform(2.0, 4.0))
    finally:
        driver.quit()

    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    slug = re.sub(r"[^\w一-鿿]+", "-", args.keyword).strip("-")[:30] or "notes"
    payload = {
        "keyword": args.keyword,
        "fetchedAt": datetime.now().isoformat(timespec="seconds"),
        "notes": notes,
    }
    jpath = args.out / ("xhs-%s-%s.json" % (slug, stamp))
    mpath = args.out / ("xhs-%s-%s.md" % (slug, stamp))
    jpath.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    mpath.write_text(_markdown(payload), encoding="utf-8")
    print("已写出:\n  %s\n  %s" % (jpath, mpath))


def _markdown(payload):
    lines = [
        "# 小红书攻略素材:" + payload["keyword"],
        "",
        "- 抓取时间:%s;共 %d 篇" % (payload["fetchedAt"], len(payload["notes"])),
        "- 声明:社区笔记,仅供调研参考;坐标/票价/营业时间须另行核实,图片不用于成品页面。",
        "",
    ]
    for i, n in enumerate(payload["notes"], 1):
        head = []
        if n.get("author"):
            head.append("作者:" + n["author"])
        if n.get("date"):
            head.append("日期:" + n["date"])
        if n.get("likes"):
            head.append("赞:" + n["likes"])
        for k, v in n.get("counts", {}).items():
            head.append("%s:%s" % (k, v))
        lines.append("## %d. %s" % (i, n["title"] or "(无标题)"))
        if head:
            lines.append("   ".join(head))
        lines.append("")
        lines.append(n.get("desc") or "(未抓到正文,可手动打开:%s)" % n.get("url", ""))
        if n.get("tags"):
            lines.append("")
            lines.append("标签:" + " ".join("#" + t for t in n["tags"]))
        lines.append("")
        lines.append("链接:" + n.get("url", ""))
        lines += ["", "---", ""]
    return "\n".join(lines)


# ---------- selftest(解析器纯函数,内嵌真实结构的最小 fixture) ----------

_CARD_FIXTURE = """
<section class="note-item">
  <a href="/search_result/64ab00ef0000000022334455?xsec_token=ABC123&amp;xsec_source=pc_search" class="cover dm-mask">
    <div class="footer">
      <div class="title">东京5天4晚亲子全攻略</div>
      <span class="author-wrapper"><span class="name">旅行家小明</span></span>
      <span class="like-wrapper"><span class="count">1.2万</span></span>
    </div>
  </a>
</section>
<a href="/search_result/64ab00ef0000000022334455?xsec_token=ABC123" class="cover"><div class="title">重复卡片应被去重</div></a>
"""

_DETAIL_FIXTURE = """
<div class="note-detail-mask">
 <div class="note-content">
  <div id="detail-title">东京5天4晚亲子全攻略</div>
  <div class="bottom-container"><span class="date">2025-04-01</span></div>
  <div id="detail-desc" class="note-note">第一天浅草寺人少要早去;晴空塔下午场人少。带娃节奏放慢,每天排两个主点就够。<a class="tag" href="/search_result?keyword=东京旅行">东京旅行</a><a class="tag" href="#">亲子游</a></div>
 </div>
 <div class="interact-container">
   <span class="count">3456</span><span>喜欢</span>
   <span class="count">789</span><span>收藏</span>
   <span class="count">12</span><span>评论</span>
 </div>
</div>
"""


def cmd_selftest(_args=None):
    problems = []
    cards = parse_search_cards(_CARD_FIXTURE)
    if not (len(cards) == 1
            and cards[0]["title"] == "东京5天4晚亲子全攻略"
            and cards[0]["author"] == "旅行家小明"
            and cards[0]["likes"] == "1.2万"
            and "xsec_token" in cards[0]["url"]):
        problems.append("parse_search_cards 提取不符:%r" % (cards[:1],))
    d = parse_note_detail(_DETAIL_FIXTURE)
    if not (d["title"] == "东京5天4晚亲子全攻略"
            and "浅草" in d["desc"]
            and d["date"] == "2025-04-01"
            and d["counts"].get("喜欢") == "3456"
            and "东京旅行" in d["tags"]):
        problems.append("parse_note_detail 提取不符:%r" % (d,))
    if problems:
        for x in problems:
            print("✗ " + x)
        sys.exit(1)
    print("✓ selftest 通过:搜索卡片 %d 张(去重生效)/ 详情字段齐全" % len(cards))


def main():
    ap = argparse.ArgumentParser(description="小红书旅行攻略抓取(travel-plan-viz 可选调研工具)")
    ap.add_argument("--state", type=Path, default=DEFAULT_STATE,
                    help="cookies 会话文件(默认 %(default)s)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("login", help="建立会话(headed Chrome,需显示器)")
    sub.add_parser("selftest", help="解析器自检(无需网络与 selenium)")
    se = sub.add_parser("search", help="抓取攻略素材")
    se.add_argument("keyword", help='搜索词,如 "东京 亲子 攻略"')
    se.add_argument("--notes", type=int, default=8, help="笔记数上限(默认 8,礼貌起见别调大)")
    se.add_argument("--out", type=Path, default=Path("xhs-notes"), help="输出目录(默认 ./xhs-notes)")
    se.add_argument("--headed", action="store_true", help="显示浏览器窗口(调试)")
    se.add_argument("--dump", action="store_true", help="保存原始 HTML,供选择器漂移排查")
    args = ap.parse_args()
    {"login": cmd_login, "search": cmd_search, "selftest": cmd_selftest}[args.cmd](args)


if __name__ == "__main__":
    main()
