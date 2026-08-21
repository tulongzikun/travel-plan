#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""hotel_research.py —— 酒店实时价查询(travel-plan-viz 可选调研工具,飞猪 FlyAI 官方 API 直连)

个人调研用:用用户自备的飞猪 FlyAI API Key,按「城市 入住日 离店日」查酒店候选与实时价,
输出 JSON + Markdown(含查询时间戳),供 Agent 填 hotelAreas[].options 的 price/priceQueriedAt/actionLink。
只走官方渠道,不爬 OTA;价格随订位实时变动,输出一律标注「以订房页为准」。

⏰ 调用时机(2026-08-21 拍板):**仅在出发日期确定后调用**。行程仍为 dateTBD(估算日)时
   一律不查实时价,只给参考区间;用户定档并把 HTML 丢回来重算时才查并回填。

用法:
  export FLYAI_API_KEY=...        # flyai.open.fliggy.com 控制台申领(淘宝账号+支付宝实名,5000 次免费)
  python3 hotel_research.py search 晋城 2026-09-20 2026-09-21 [--keyword 汉庭] [--top 5] [--out DIR]
  python3 hotel_research.py selftest        # 解析器自检(不需要 Key 与网络)

⚠️ 端点与鉴权字段以官方文档为准(需登录):flyai.open.fliggy.com/docs
   下面两个常量是按常见形态写的占位,首跑 401/404 时先核对文档,或用 --base/--path 覆盖,别改解析器。
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

API_BASE = os.environ.get("FLYAI_API_BASE", "https://flyai.open.fliggy.com/api/v1")  # ← 首跑核对
SEARCH_PATH = "/hotels/search"                                                      # ← 首跑核对
AUTH_HEADER = "Authorization"                                                       # ← 首跑核对(或 X-API-Key)

# ---------- 纯解析函数(不依赖网络,可 selftest) ----------

def _first(d, keys, default=""):
    for k in keys:
        if isinstance(d, dict) and d.get(k) not in (None, ""):
            return d[k]
    return default


def _price_of(item):
    p = _first(item, ["price", "lowestPrice", "avgPrice", "amount", "value"])
    if isinstance(p, dict):
        p = _first(p, ["amount", "value", "total"])
    try:
        return float(p)
    except (TypeError, ValueError):
        return None


def parse_hotels(payload):
    """官方 API 返回 → 统一酒店列表,按价格升序。

    官方返回结构文档在登录墙后,这里对常见包裹层级(data/hotels/items/result/list…)
    与字段别名做容错;真实结构确认后如需调整,改这里并跑 selftest。
    """
    items = None
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        for k in ("hotels", "offers", "items", "result", "data"):
            v = payload.get(k)
            if isinstance(v, list):
                items = v
                break
            if isinstance(v, dict):
                for k2 in ("hotels", "offers", "items", "list", "result"):
                    if isinstance(v.get(k2), list):
                        items = v[k2]
                        break
                if items is not None:
                    break
    if items is None:
        return []
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        rating = _first(it, ["score", "rating", "commentScore"])
        if isinstance(rating, dict):
            rating = _first(rating, ["value", "score"])
        h = {
            "name": str(_first(it, ["hotelName", "name", "title"])),
            "star": str(_first(it, ["star", "starRating", "level"])),
            "rating": rating,
            "price": _price_of(it),
            "currency": str(_first(it, ["currency"], "CNY")),
            "address": str(_first(it, ["address", "addr", "location"])),
            "distance": _first(it, ["distance", "distanceDesc", "distanceText"], ""),
            "bookingUrl": str(_first(it, ["bookingUrl", "link", "url", "deepLink"])),
        }
        if h["name"]:
            out.append(h)
    out.sort(key=lambda x: x["price"] if x["price"] is not None else float("inf"))
    return out


# ---------- 请求侧(仅标准库) ----------

def cmd_search(args):
    date_re = r"^\d{4}-\d{2}-\d{2}$"
    import re
    if not (re.match(date_re, args.checkin) and re.match(date_re, args.checkout)):
        sys.exit("日期须为 YYYY-MM-DD,当前: %s / %s" % (args.checkin, args.checkout))
    if args.checkout <= args.checkin:
        sys.exit("离店日须晚于入住日: %s → %s" % (args.checkin, args.checkout))
    key = os.environ.get("FLYAI_API_KEY", "")
    if args.key_file and Path(args.key_file).exists():
        key = Path(args.key_file).read_text(encoding="utf-8").strip()
    if not key:
        sys.exit("缺 API Key:export FLYAI_API_KEY=… 或 --key-file 指定"
                 "(flyai.open.fliggy.com 控制台申领,淘宝账号+支付宝实名,5000 次免费)")

    url = args.base.rstrip("/") + args.path
    body = {"city": args.city, "checkIn": args.checkin, "checkOut": args.checkout}
    if args.keyword:
        body["keyword"] = args.keyword
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST", headers={
        "Content-Type": "application/json",
        AUTH_HEADER: "Bearer " + key,
        "User-Agent": "travel-plan-viz-hotel-research/0.1",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        hint = {401: "Key 无效或过期", 403: "无权限/实名未完成",
                404: "端点路径不符——按官方文档用 --path 覆盖"}.get(e.code, "HTTP %d" % e.code)
        sys.exit("请求失败:%s(官方文档 flyai.open.fliggy.com/docs 需登录核对端点与鉴权)" % hint)
    except urllib.error.URLError as e:
        sys.exit("网络错误:%s" % getattr(e, "reason", e))

    args.out.mkdir(parents=True, exist_ok=True)
    try:
        payload = json.loads(raw)
    except ValueError:
        (args.out / "hotel-raw.txt").write_text(raw, encoding="utf-8")
        sys.exit("返回非 JSON,原文已存 hotel-raw.txt 供排查")
    if args.dump:
        (args.out / "hotel-raw.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    hotels = parse_hotels(payload)[: args.top]
    if not hotels:
        (args.out / "hotel-raw.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        sys.exit("未解析到酒店:原始返回已存 hotel-raw.json——对照结构修 parse_hotels 并跑 selftest")

    result = {
        "city": args.city,
        "checkin": args.checkin,
        "checkout": args.checkout,
        "keyword": args.keyword or "",
        "queriedAt": datetime.now().isoformat(timespec="seconds"),
        "source": "飞猪 FlyAI API 直连(用户自备 Key)",
        "disclaimer": "价格随订位实时变动,以订房页为准;本结果仅供调研参考。",
        "hotels": hotels,
    }
    slug = "%s-%s" % (args.city, args.checkin)
    jpath = args.out / ("hotels-%s.json" % slug)
    mpath = args.out / ("hotels-%s.md" % slug)
    jpath.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    mpath.write_text(_markdown(result), encoding="utf-8")
    print("已写出:\n  %s\n  %s" % (jpath, mpath))


def _markdown(r):
    lines = [
        "# 酒店实时价:%s %s→%s" % (r["city"], r["checkin"], r["checkout"]),
        "",
        "- 查询时间:**%s**;来源:%s" % (r["queriedAt"], r["source"]),
        "- %s" % r["disclaimer"],
        "",
        "| 酒店 | 星级/档位 | 评分 | 地址/距离 | 价格 | 链接 |",
        "|---|---|---|---|---|---|",
    ]
    for h in r["hotels"]:
        price = ("%.0f %s/晚" % (h["price"], h["currency"])) if h["price"] is not None else "—"
        rating = str(h["rating"]) if h["rating"] != "" else "—"
        addr = h["distance"] or h["address"] or "—"
        link = ("[订房](%s)" % h["bookingUrl"]) if h["bookingUrl"] else "—"
        lines.append("| %s | %s | %s | %s | %s | %s |"
                     % (h["name"], h["star"] or "—", rating, addr, price, link))
    return "\n".join(lines) + "\n"


# ---------- selftest(解析器纯函数,内嵌两种形态 fixture) ----------

_FIXTURE_NESTED = {
    "code": 0,
    "data": {
        "hotels": [
            {"hotelName": "汉庭酒店(晋城泽州路国贸店)", "star": "舒适型", "score": 4.8,
             "price": 210, "currency": "CNY", "address": "晋城城区泽州路1932号",
             "bookingUrl": "https://www.fliggy.com/h?id=1"},
            {"name": "全季酒店(晋城凤台街店)", "starRating": "高档型",
             "rating": {"value": 4.6}, "lowestPrice": {"amount": 280.0},
             "addr": "凤台街", "link": "https://www.fliggy.com/h?id=2"},
        ]
    },
}

_FIXTURE_FLAT = [
    {"title": "如家商旅(长治漳泽湖店)", "avgPrice": 180, "distanceDesc": "距机场驾车约10分钟"},
]


def cmd_selftest(_args=None):
    problems = []
    a = parse_hotels(_FIXTURE_NESTED)
    if not (len(a) == 2
            and a[0]["name"].startswith("汉庭") and a[0]["price"] == 210.0    # 按价格升序
            and a[1]["name"].startswith("全季") and a[1]["price"] == 280.0
            and a[1]["rating"] == 4.6
            and a[0]["bookingUrl"].startswith("https://")):
        problems.append("嵌套形态解析不符:%r" % (a,))
    b = parse_hotels(_FIXTURE_FLAT)
    if not (len(b) == 1 and b[0]["name"].startswith("如家") and b[0]["price"] == 180.0
            and b[0]["distance"] == "距机场驾车约10分钟"):
        problems.append("扁平形态解析不符:%r" % (b,))
    if problems:
        for x in problems:
            print("✗ " + x)
        sys.exit(1)
    print("✓ selftest 通过:嵌套/扁平两种返回形态解析正常,按价格升序")


def main():
    ap = argparse.ArgumentParser(description="酒店实时价查询(travel-plan-viz 可选调研工具,飞猪 FlyAI 直连;仅定档后调用)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest", help="解析器自检(无需 Key 与网络)")
    se = sub.add_parser("search", help="查酒店实时价(出发日期确定后才用)")
    se.add_argument("city", help="城市名,如 晋城")
    se.add_argument("checkin", help="入住日期 YYYY-MM-DD")
    se.add_argument("checkout", help="离店日期 YYYY-MM-DD")
    se.add_argument("--keyword", help="可选关键词,如品牌名「汉庭」/地标「皇城相府」")
    se.add_argument("--top", type=int, default=5, help="取最低价前 N 条(默认 5)")
    se.add_argument("--out", type=Path, default=Path("hotel-notes"), help="输出目录(默认 ./hotel-notes)")
    se.add_argument("--base", default=API_BASE, help="API base(默认 %(default)s,首跑按官方文档核对)")
    se.add_argument("--path", default=SEARCH_PATH, help="搜索端点路径(默认 %(default)s)")
    se.add_argument("--key-file", help="Key 文件路径(替代 FLYAI_API_KEY 环境变量)")
    se.add_argument("--dump", action="store_true", help="保存原始返回 JSON 供排查")
    args = ap.parse_args()
    {"search": cmd_search, "selftest": cmd_selftest}[args.cmd](args)


if __name__ == "__main__":
    main()
