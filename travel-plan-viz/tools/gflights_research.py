#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gflights_research.py —— 机票价格查询(travel-plan-viz 可选调研工具,Google Flights 比价)

个人调研用:经 fli 库(PyPI 包名 flights,逆向 Google Flights 接口、无需 Key)按
「出发机场 到达机场 日期」查航班候选,输出 JSON + Markdown(含查询时间戳),
供 Agent 在「调研补全」阶段填 flights.candidates。与 flight_research.py(飞猪
FlyAI 官方 API)是并列的两条机票调研渠道,本工具零 Key、即装即用。

用法:
  python3 -m pip install flights        # 依赖:fli(PyPI 名就叫 flights)
  python3 gflights_research.py search PEK SHA 2026-10-25 [--top 5]
  python3 gflights_research.py selftest        # 整理器自检(不需要网络与 fli)

⚠️ 两条边界:
  - 逆向接口:Google 改版/风控随时可能失效;失败时如实报错,别硬凑数据。
  - 需能连通 www.google.com(境内服务器不一定可达,先 curl 探测再跑)。
  - 保持低频:填一次 flights.candidates 通常 1 条航线 1 次查询足够。
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

SEAT_CHOICES = {"economy": "ECONOMY", "business": "BUSINESS", "first": "FIRST"}
STOPS_CHOICES = {"any": "ANY", "nonstop": "NON_STOP", "one": "ONE_STOP"}
SORT_CHOICES = {"cheapest": "CHEAPEST", "fastest": "FASTEST"}


# ---------- 纯整理函数(不依赖网络与 fli,可 selftest;输入鸭子类型即可) ----------

def _code(v):
    """枚举(Airport.PEK / Airline.NX)→ IATA/航司二字码字符串。"""
    return getattr(v, "name", str(v))


def _fmt_dt(v):
    s = str(v)
    return s[5:16].replace("T", " ") if len(s) >= 16 else s  # "2026-10-25 08:30" → "10-25 08:30"


def extract_itineraries(results):
    """fli FlightResult 列表 → 统一航班列表,按价格升序。

    输入只要求属性鸭子类型(legs/price/currency/duration/stops/primary_airline_name),
    selftest 用 SimpleNamespace 仿造,不 import fli。
    """
    out = []
    for r in results:
        try:
            price = float(r.price)
        except (TypeError, ValueError):
            continue
        segments = []
        for l in getattr(r, "legs", []):
            segments.append({
                "airline": _code(l.airline),
                "flightNo": "%s%s" % (_code(l.airline), l.flight_number),  # fli 里号可能是 int 或 str
                "from": _code(l.departure_airport),
                "to": _code(l.arrival_airport),
                "depart": _fmt_dt(l.departure_datetime),
                "arrive": _fmt_dt(l.arrival_datetime),
            })
        if not segments:
            continue
        dur = int(getattr(r, "duration", 0) or 0)
        out.append({
            "airline": getattr(r, "primary_airline_name", None) or
                       (segments[0]["airline"] if segments else ""),
            "flightNo": "+".join(s["flightNo"] for s in segments),
            "depart": segments[0]["depart"],
            "arrive": segments[-1]["arrive"],
            "price": price,
            "currency": str(getattr(r, "currency", "") or ""),
            "duration": "%dh%02dm" % (dur // 60, dur % 60),
            "stops": int(getattr(r, "stops", 0) or 0),
            "bookingUrl": getattr(r, "booking_url", None) or "",
            "segments": segments,
        })
    out.sort(key=lambda x: x["price"])
    return out


def _markdown(r):
    lines = [
        "# 航班候选:%s %s" % (r["route"], r["date"]),
        "",
        "- 查询时间:**%s**;来源:%s" % (r["queriedAt"], r["source"]),
        "- %s" % r["disclaimer"],
        "",
        "| 航司 | 航班 | 起飞→到达 | 中转 | 价格 | 链接 |",
        "|---|---|---|---|---|---|",
    ]
    for f in r["flights"]:
        price = ("%.0f %s" % (f["price"], f["currency"])) if f["price"] is not None else "—"
        link = ("[比价](%s)" % f["bookingUrl"]) if f["bookingUrl"] else "—"
        lines.append("| %s | %s | %s → %s | %d | %s | %s |"
                     % (f["airline"] or "—", f["flightNo"] or "—",
                        f["depart"] or "—", f["arrive"] or "—",
                        f["stops"], price, link))
    # 分段明细放表格之后(直飞与表行重复,只列中转),免得插在表格行间打断渲染
    multi = [f for f in r["flights"] if len(f["segments"]) > 1]
    if multi:
        lines += ["", "**中转分段明细**", ""]
        for f in multi:
            lines.append("- %s(%s)" % (f["flightNo"], f["airline"] or ""))
            for s in f["segments"]:
                lines.append("  - %s %s→%s %s~%s" % (s["flightNo"], s["from"], s["to"],
                                                     s["depart"], s["arrive"]))
    return "\n".join(lines) + "\n"


# ---------- 请求侧(依赖 fli,search 才 import) ----------

def cmd_search(args):
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", args.date):
        sys.exit("日期须为 YYYY-MM-DD,当前: " + args.date)
    try:
        from fli.models import (Airport, FlightSearchFilters, FlightSegment,
                                MaxStops, PassengerInfo, SeatType, SortBy)
        from fli.search import SearchFlights
    except ImportError:
        sys.exit("缺依赖:python3 -m pip install flights(fli,逆向 Google Flights)")

    origin, dest = args.origin.upper(), args.destination.upper()
    missing = [a for a in (origin, dest) if not hasattr(Airport, a)]
    if missing:
        sys.exit("未知机场码 %s——fli 的 Airport 枚举里没有(用 IATA 三字码,如 PEK/SHA/PVG/BCN)"
                 % "/".join(missing))

    filters = FlightSearchFilters(
        passenger_info=PassengerInfo(adults=1),
        flight_segments=[FlightSegment(
            departure_airport=[[getattr(Airport, origin), 0]],
            arrival_airport=[[getattr(Airport, dest), 0]],
            travel_date=args.date)],
        seat_type=getattr(SeatType, SEAT_CHOICES[args.seat]),
        stops=getattr(MaxStops, STOPS_CHOICES[args.stops]),
        sort_by=getattr(SortBy, SORT_CHOICES[args.sort]),
    )
    sf = SearchFlights()
    try:
        results = sf.search(filters, top_n=max(args.top * 4, 20),
                            currency=args.currency, language="zh-CN", country="CN")
    except Exception as e:  # fli 抛的形态不稳定,统一如实转述
        sys.exit("查询失败:%s: %s\n(逆向接口可能改版失效,或本机连不通 www.google.com——先 "
                 "curl -sI --max-time 8 https://www.google.com 探测)" % (type(e).__name__, e))

    rows = extract_itineraries(results or [])
    if not rows:
        sys.exit("未取到航班:fli 返回空(接口改版或该航线当日无班)——如实留空,别硬凑")

    # fli 的 FlightResult 不直接带 URL,由航班要素确定性生成 tfs 深链(无额外网络请求)
    objs = sorted([r for r in (results or []) if getattr(r, "price", None) is not None],
                  key=lambda o: float(o.price))
    for row, obj in zip(rows, objs):
        try:
            row["bookingUrl"] = sf.build_flight_booking_url(obj, currency=args.currency)
        except Exception:
            row["bookingUrl"] = ""

    rows = rows[: args.top]
    result = {
        "route": "%s-%s" % (origin, dest),
        "date": args.date,
        "queriedAt": datetime.now().isoformat(timespec="seconds"),
        "source": "Google Flights(fli 逆向接口,tools/gflights_research.py),货币 %s" % args.currency,
        "disclaimer": "Google Flights 聚合报价,随订位实时变动、与出票渠道可能有差,以订票页为准;本结果仅供调研参考。",
        "flights": rows,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    slug = "%s-%s-%s" % (origin, dest, args.date)
    jpath = args.out / ("gflights-%s.json" % slug)
    mpath = args.out / ("gflights-%s.md" % slug)
    jpath.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    mpath.write_text(_markdown(result), encoding="utf-8")
    print("已写出:\n  %s\n  %s" % (jpath, mpath))


# ---------- selftest(整理器纯函数,SimpleNamespace 仿造 fli 返回) ----------

def _selftest():
    from types import SimpleNamespace as NS

    def leg(al, no, dep, arr, frm, to):
        return NS(airline=type("A", (), {"name": al}), flight_number=no,
                  departure_airport=type("P", (), {"name": frm}), arrival_airport=type("P", (), {"name": to}),
                  departure_datetime=dep, arrival_datetime=arr)

    cheap = NS(price=1805.0, currency="CNY", duration=780, stops=1,
               primary_airline_name="澳门航空",
               legs=[leg("NX", 1, "2026-10-25 08:30:00", "2026-10-25 12:15:00", "PEK", "MFM"),
                     leg("NX", 120, "2026-10-25 19:10:00", "2026-10-25 21:30:00", "MFM", "SHA")],
               booking_url="https://www.google.com/travel/flights/booking?tfs=x")
    dear = NS(price=2600.0, currency="CNY", duration=135, stops=0,
              primary_airline_name="中国国航",
              legs=[leg("CA", 1501, "2026-10-25 09:00:00", "2026-10-25 11:15:00", "PEK", "SHA")],
              booking_url="")
    bad = NS(price=None, currency="CNY", duration=0, stops=0, legs=[], booking_url="")

    rows = extract_itineraries([dear, cheap, bad])
    problems = []
    if len(rows) != 2:
        problems.append("应滤掉无价/无段的条目,实得 %d 条" % len(rows))
    if rows and rows[0]["price"] != 1805.0:
        problems.append("应按价格升序:%r" % [r["price"] for r in rows])
    if rows and rows[0]["flightNo"] != "NX1+NX120":
        problems.append("中转航班号应拼接:%r" % rows[0]["flightNo"])
    if rows and rows[0]["duration"] != "13h00m":
        problems.append("时长格式:%r" % rows[0]["duration"])
    if rows and rows[0]["depart"] != "10-25 08:30" or rows[0]["arrive"] != "10-25 21:30":
        problems.append("首段起飞/末段到达:%r→%r" % (rows[0]["depart"], rows[0]["arrive"]))
    md = _markdown({"route": "PEK-SHA", "date": "2026-10-25",
                    "queriedAt": "2026-08-24T12:00:00", "source": "s", "disclaimer": "d",
                    "flights": rows})
    if "澳门航空" not in md or "NX1+NX120" not in md or "比价" not in md:
        problems.append("Markdown 缺关键字段")
    if problems:
        for x in problems:
            print("✗ " + x)
        sys.exit(1)
    print("✓ selftest 通过:价格升序/中转拼接/时长与时刻格式/Markdown 表格正常")


def main():
    ap = argparse.ArgumentParser(description="机票价格查询(travel-plan-viz 可选调研工具,Google Flights 比价,零 Key)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest", help="整理器自检(无需网络与 fli)")
    se = sub.add_parser("search", help="查航班候选")
    se.add_argument("origin", help="出发机场 IATA 码,如 PEK")
    se.add_argument("destination", help="到达机场 IATA 码,如 SHA")
    se.add_argument("date", help="出发日期 YYYY-MM-DD")
    se.add_argument("--top", type=int, default=5, help="取最低价前 N 条(默认 5,契约要 3-5 个候选)")
    se.add_argument("--seat", choices=sorted(SEAT_CHOICES), default="economy", help="舱等(默认 economy)")
    se.add_argument("--stops", choices=sorted(STOPS_CHOICES), default="any", help="中转限制(默认 any)")
    se.add_argument("--sort", choices=sorted(SORT_CHOICES), default="cheapest", help="排序(默认 cheapest)")
    se.add_argument("--currency", default="CNY", help="计价货币 ISO 4217(默认 CNY)")
    se.add_argument("--out", type=Path, default=Path("gflights-notes"), help="输出目录(默认 ./gflights-notes)")
    args = ap.parse_args()
    {"search": cmd_search, "selftest": lambda _a: _selftest()}[args.cmd](args)


if __name__ == "__main__":
    main()
