#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""flight_research.py —— 机票价格查询(travel-plan-viz 可选调研工具,飞猪 FlyAI 官方 API 直连)

个人调研用:用用户自备的飞猪 FlyAI API Key,按「出发地 目的地 日期」查航班候选,
输出 JSON + Markdown(含查询时间戳),供 Agent 在「调研补全」阶段填 flights.candidates。
价格随订位实时变动,输出一律标注「以订票页为准」(机票调研渠道不限,2026-08-24 拍板,
比价渠道见 gflights_research.py)。

用法:
  export FLYAI_API_KEY=...        # flyai.open.fliggy.com 控制台申领(淘宝账号+支付宝实名,5000 次免费)
  python3 flight_research.py search PEK SHA 2026-10-20 [--top 5] [--out DIR]
  python3 flight_research.py selftest        # 解析器自检(不需要 Key 与网络)

⚠️ 端点与鉴权字段以官方文档为准(需登录):flyai.open.fliggy.com/docs
   下面两个常量是按常见形态写的占位,首跑 401/404 时先核对文档,或用 --base/--path 覆盖,别改解析器。
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

API_BASE = os.environ.get("FLYAI_API_BASE", "https://flyai.open.fliggy.com/api/v1")  # ← 首跑核对
SEARCH_PATH = "/flights/search"                                                      # ← 首跑核对
AUTH_HEADER = "Authorization"                                                        # ← 首跑核对(或 X-API-Key)

# ---------- 纯解析函数(不依赖网络,可 selftest) ----------

def _first(d, keys, default=""):
    for k in keys:
        if isinstance(d, dict) and d.get(k) not in (None, ""):
            return d[k]
    return default


def _price_of(item):
    p = _first(item, ["price", "adultPrice", "lowestPrice", "amount", "value"])
    if isinstance(p, dict):
        p = _first(p, ["amount", "value", "total"])
    try:
        return float(p)
    except (TypeError, ValueError):
        return None


def parse_flights(payload):
    """官方 API 返回 → 统一航班列表,按价格升序。

    官方返回结构文档在登录墙后,这里对常见包裹层级(data/flights/offers/items…)
    与字段别名做容错;真实结构确认后如需调整,改这里并跑 selftest。
    """
    items = None
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        for k in ("flights", "offers", "items", "result", "data"):
            v = payload.get(k)
            if isinstance(v, list):
                items = v
                break
            if isinstance(v, dict):
                for k2 in ("flights", "offers", "items", "list", "result"):
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
        price = _price_of(it)
        f = {
            "airline": str(_first(it, ["airlineName", "airline", "carrier"])),
            "flightNo": str(_first(it, ["flightNo", "flightNumber", "fno", "flight"])),
            "depart": str(_first(it, ["departureTime", "depTime", "departTime", "departure"])),
            "arrive": str(_first(it, ["arrivalTime", "arrTime", "arriveTime", "arrival"])),
            "price": price,
            "currency": str(_first(it, ["currency"], "CNY")),
            "duration": _first(it, ["durationMinutes", "duration", "flyTime"], ""),
            "stops": _first(it, ["stops", "stopCount"], 0),
            "bookingUrl": str(_first(it, ["bookingUrl", "link", "url", "deepLink"])),
        }
        if f["airline"] or f["flightNo"]:
            out.append(f)
    out.sort(key=lambda x: x["price"] if x["price"] is not None else float("inf"))
    return out


# ---------- 请求侧(仅标准库) ----------

def cmd_search(args):
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", args.date):
        sys.exit("日期须为 YYYY-MM-DD,当前: " + args.date)
    key = os.environ.get("FLYAI_API_KEY", "")
    if args.key_file and Path(args.key_file).exists():
        key = Path(args.key_file).read_text(encoding="utf-8").strip()
    if not key:
        sys.exit("缺 API Key:export FLYAI_API_KEY=… 或 --key-file 指定"
                 "(flyai.open.fliggy.com 控制台申领,淘宝账号+支付宝实名,5000 次免费)")

    url = args.base.rstrip("/") + args.path
    body = json.dumps({
        "origin": args.origin, "destination": args.destination,
        "departDate": args.date, "cabin": "economy",
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": "application/json",
        AUTH_HEADER: "Bearer " + key,
        "User-Agent": "travel-plan-viz-flight-research/0.1",
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
        (args.out / "flight-raw.txt").write_text(raw, encoding="utf-8")
        sys.exit("返回非 JSON,原文已存 flight-raw.txt 供排查")
    if args.dump:
        (args.out / "flight-raw.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    flights = parse_flights(payload)[: args.top]
    if not flights:
        (args.out / "flight-raw.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        sys.exit("未解析到航班:原始返回已存 flight-raw.json——对照结构修 parse_flights 并跑 selftest")

    result = {
        "route": "%s-%s" % (args.origin, args.destination),
        "date": args.date,
        "queriedAt": datetime.now().isoformat(timespec="seconds"),
        "source": "飞猪 FlyAI API 直连(用户自备 Key)",
        "disclaimer": "价格随订位实时变动,以上订票页为准;本结果仅供调研参考。",
        "flights": flights,
    }
    slug = "%s-%s-%s" % (args.origin, args.destination, args.date)
    jpath = args.out / ("flights-%s.json" % slug)
    mpath = args.out / ("flights-%s.md" % slug)
    jpath.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    mpath.write_text(_markdown(result), encoding="utf-8")
    print("已写出:\n  %s\n  %s" % (jpath, mpath))


def _markdown(r):
    lines = [
        "# 航班候选:%s %s" % (r["route"], r["date"]),
        "",
        "- 查询时间:**%s**;来源:%s" % (r["queriedAt"], r["source"]),
        "- %s" % r["disclaimer"],
        "",
        "| 航司 | 航班 | 起飞→到达 | 价格 | 链接 |",
        "|---|---|---|---|---|",
    ]
    for f in r["flights"]:
        price = ("%.0f %s" % (f["price"], f["currency"])) if f["price"] is not None else "—"
        link = ("[订票](%s)" % f["bookingUrl"]) if f["bookingUrl"] else "—"
        lines.append("| %s | %s | %s → %s | %s | %s |"
                     % (f["airline"] or "—", f["flightNo"] or "—",
                        f["depart"] or "—", f["arrive"] or "—", price, link))
    return "\n".join(lines) + "\n"


# ---------- selftest(解析器纯函数,内嵌两种形态 fixture) ----------

_FIXTURE_NESTED = {
    "code": 0,
    "data": {
        "flights": [
            {"airlineName": "中国国航", "flightNo": "CA1501",
             "departureTime": "2026-10-20 08:30", "arrivalTime": "2026-10-20 10:45",
             "price": 780, "currency": "CNY", "durationMinutes": 135, "stops": 0,
             "bookingUrl": "https://www.fliggy.com/x?id=1"},
            {"airline": "东方航空", "flightNumber": "MU5101",
             "depTime": "2026-10-20 09:00", "arrTime": "2026-10-20 11:15",
             "adultPrice": {"amount": 850.0}, "link": "https://www.fliggy.com/x?id=2"},
        ]
    },
}

_FIXTURE_FLAT = [
    {"carrier": "海南航空", "fno": "HU7607", "departure": "07:55", "arrival": "10:10",
     "lowestPrice": {"value": 720}},
]


def cmd_selftest(_args=None):
    problems = []
    a = parse_flights(_FIXTURE_NESTED)
    if not (len(a) == 2
            and a[0]["flightNo"] == "CA1501" and a[0]["price"] == 780.0   # 按价格升序
            and a[1]["airline"] == "东方航空" and a[1]["price"] == 850.0
            and a[0]["bookingUrl"].startswith("https://")):
        problems.append("嵌套形态解析不符:%r" % (a,))
    b = parse_flights(_FIXTURE_FLAT)
    if not (len(b) == 1 and b[0]["airline"] == "海南航空" and b[0]["price"] == 720.0):
        problems.append("扁平形态解析不符:%r" % (b,))
    if problems:
        for x in problems:
            print("✗ " + x)
        sys.exit(1)
    print("✓ selftest 通过:嵌套/扁平两种返回形态解析正常,按价格升序")


def main():
    ap = argparse.ArgumentParser(description="机票价格查询(travel-plan-viz 可选调研工具,飞猪 FlyAI 直连)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest", help="解析器自检(无需 Key 与网络)")
    se = sub.add_parser("search", help="查航班候选")
    se.add_argument("origin", help="出发机场/城市码,如 PEK")
    se.add_argument("destination", help="到达机场/城市码,如 SHA")
    se.add_argument("date", help="出发日期 YYYY-MM-DD")
    se.add_argument("--top", type=int, default=5, help="取最低价前 N 条(默认 5,契约要 3-5 个候选)")
    se.add_argument("--out", type=Path, default=Path("flight-notes"), help="输出目录(默认 ./flight-notes)")
    se.add_argument("--base", default=API_BASE, help="API base(默认 %(default)s,首跑按官方文档核对)")
    se.add_argument("--path", default=SEARCH_PATH, help="搜索端点路径(默认 %(default)s)")
    se.add_argument("--key-file", help="Key 文件路径(替代 FLYAI_API_KEY 环境变量)")
    se.add_argument("--dump", action="store_true", help="保存原始返回 JSON 供排查")
    args = ap.parse_args()
    {"search": cmd_search, "selftest": cmd_selftest}[args.cmd](args)


if __name__ == "__main__":
    main()
