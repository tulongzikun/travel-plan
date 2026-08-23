<div align="center">

<!-- Hero: Migo the migratory navigator (mascot). Image lives at docs/banner.png -->
<img src="docs/banner.png" alt="travel-plan-viz · Migo the navigator bird" width="300">

<sub>👋 I'm <strong>Migo</strong> · your travel navigator — migratory birds are born to plan routes and time them right</sub>

# 🗺️ Migo · Travel Navigator

<sub><code>travel-plan-viz</code></sub>

**Turn a trip into a polished, offline-readable, mobile-first single-file HTML page**

Interactive map · Daily timeline · Booking reminders · Pre-trip essentials · Candidate flights · Hotels by area & price

A [Claude Code](https://claude.com/claude-code) / Codex Skill (portable to other agents)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)
[![output: single-file HTML](https://img.shields.io/badge/output-single--file%20HTML-ff7a59?style=flat-square)](#-samples)
[![offline readable](https://img.shields.io/badge/offline-readable-22c55e?style=flat-square)](#-features)
[![Claude Code · Codex](https://img.shields.io/badge/Claude%20Code-%C2%B7%20Codex-8b5cf6?style=flat-square)](#-install-cross-agent)
[![no API key](https://img.shields.io/badge/map-no%20API%20key-0ea5e9?style=flat-square)](#-features)
[![tests](https://img.shields.io/badge/tests-passing-brightgreen?style=flat-square)](#-tests)

<sub>🎬 More hands-on AI workflows from the author (Chinese short videos): <strong>@泽轩604</strong> on Douyin</sub>

<sub><a href="#-features">✨ Features</a> · <a href="#-install-cross-agent">🚀 Install</a> · <a href="#-faq">❓ FAQ</a> · <a href="#-how-it-works">🏗️ How it works</a> · <a href="#-star-history">⭐ Star</a></sub>

<sub><a href="README.md">简体中文</a> · <strong>English</strong></sub>

</div>

---

## ⭐ Star History

<p align="center">
  <a href="https://github.com/zexuanw958-svg/travel-plan-viz/stargazers">
    <img src="https://raw.githubusercontent.com/zexuanw958-svg/travel-plan-viz/star-history/star-history.svg" alt="travel-plan-viz Star History" width="68%">
  </a>
</p>

<p align="center">
  <sub>Chart is redrawn daily by this repo's GitHub Action from GitHub stargazer data (not real-time) — see the count at the top of the page for the live number.</sub>
</p>

---

### What is this

`travel-plan-viz` is a [Claude Code](https://claude.com/claude-code) / Codex Skill (and portable to other agents). Just say *"plan me a 4-day Hong Kong trip"* and it will **research online, build the itinerary, and generate a polished single-file HTML page** — mobile-first, text readable offline, screenshot-friendly.

Inspired by the community "vibe-coding travel guide" trick, turned into a proper, reusable Skill that hard-codes the error-prone bits.

### ✨ Features

| | Feature |
|---|---|
| 🧭 | **Two modes**: give only a destination + days and let it plan; or hand it an existing plan and it just renders the page |
| 🗺️ | **Interactive map**: Leaflet + free tiles (no API key), numbered stops + ordered dashed route + tap-to-navigate links (Apple Maps on iOS, geo: on Android, plus key-free Amap links for mainland-China stops and Google Maps links elsewhere); GCJ-02 coords from Amap/Tencent are auto-converted to WGS-84 so pins don't drift; for mainland-China trips each day's header also gets an "📍 open this day in Amap" link (official multi-marker URI carrying all of that day's stops at once, auto-split past the 10-point limit — honestly noted: Amap roadbooks have no public creation API, saving one requires manual steps inside Amap) |
| 📅 | **Daily timeline**: morning/noon/evening, each stop with a real photo, rating, and one-line review |
| ⏰ | **Pre-trip reminders**: deadlines back-calculated from the departure date — a top checklist + ⚠️ badges on the timeline |
| 🌦️ | **Pre-trip essentials**: season-aware weather/packing/typhoon notes, payment, must-have apps, ticket timing |
| ✈️ | **Candidate flights**: 3–5 real options when nothing is booked, so there's a fallback |
| 🚗 | **Point-to-point transport chain**: every leg (hotel → first stop → between stops → last stop → hotel) with mode + duration (distance estimates for driving, fares for transit) plus a rough visit length at each sight (drive time + visit time together show what a day really holds), each day's chain ending with the leg to that night's lodging, scheduled against local sunset so no mountain road is driven after dark |
| 🏨 | **Hotels by area & price + nightly lodging label**: staying areas based on the itinerary, budget/mid/premium options — chain brands first at each tier (H World / Home Inn / Jin Jiang etc.), honestly labeled local picks where no chain operates; each day's timeline header shows that night's lodging area, and the map marks lodging areas with 🏨 anchors; realtime prices via official channels once dates are locked (timestamped, book-page prevails) |
| 🍜 | **Daily food**: per-meal picks with signature dishes and reference prices |
| 📄 | **Single file, responsive, offline-readable**: one `.html`, adapts to phone & desktop (single column on mobile, multi-column on desktop); the text itinerary reads offline, while map tiles & photos need a connection and degrade gracefully (no broken-image icons) |
| ✅ | **Post-generation validation**: `validate.js` mechanically checks missing fields, out-of-range/outlier coordinates (catches swapped lat/lng or wrong-city lookups), and required blocks — no relying on "the model probably did it right" |
| 🔁 | **Iterable output**: the full trip data is embedded as JSON inside the page; hand the HTML back and say "move X from Day 3 to Day 4" — it edits the data and re-renders, no fields lost |
| 💡 | **Not just conversion — advice too**: hand it an existing plan and it offers a few optional improvements against a "complete-itinerary" checklist (restrained, never pushy) — the agent's edge over a plain prompt-to-HTML trick |
| 🔌 | **Optional adapter for official travel skills**: if you also install official skills like Fliggy / Amap / Tencent Maps / DiDi, it calls them for realtime flights, hotels, route planning, and weather, plus "book / navigate / hail a ride" links; **without them it falls back to web research — nothing missing**. Realtime accuracy of that data is owned by those official skills |
| ⚠️ | **Full disclaimer**: states all info is AI-compiled and may be outdated; points users to official apps |

### 🏗️ How it works

A hybrid architecture — **error-prone mechanics are baked into reusable engines, while the visual design is regenerated each time by a "design step"**:

- `assets/map.js` — Leaflet engine (numbered markers, route, iOS/Android navigation links, GCJ-02→WGS-84 conversion)
- `assets/reminders.js` — reminder engine (deadline math, checklist/badge rendering)
- `assets/validate.js` — contract validation engine (mechanical post-generation checks on fields/coordinates/required blocks; errors must be fixed)
- `assets/page-contract.md` — content contract telling the design step what each block needs
- `assets/page-template.html` — page template: a skeleton distilled from the published samples; inject trip data & engines, re-theme, and ship
- `references/research-guide.md` — web-research guide (coords/photos/hours/weather/transport…; images must be verified loadable; flight candidates and realtime-pricing channel rules)
- `references/design-guidelines.md` — built-in aesthetic guidelines (fallback when no external design skill is present)

> **The design step is pluggable, with no hard dependency**: if you have a design skill like `frontend-design` or `huashu-design`, it's used automatically for better results; without any, the built-in guidelines still produce a presentable page. So this skill installs standalone — no need to install anything else first.

> **Optional adaptation to official travel skills (also a soft dependency)**: if you separately install official travel skills like Fliggy, Amap, Tencent Maps, or DiDi, this skill calls them to enrich realtime data (flights / hotels / route planning / weather / precise coordinates) and adds "book / navigate / hail a ride" links on the page; without them it falls back to web research and no block is missing. The realtime accuracy of that data is owned by those official skills — this skill only adapts and presents it, without endorsement.

### 🚀 Install (cross-agent)

> **New to all this?** There's a zero-basics, step-by-step install guide (in Chinese, covers Windows & Mac): [INSTALL.md](INSTALL.md).

Link the skill into your agent's skills directory:

```bash
# Claude Code
ln -sfn "$(pwd)/travel-plan-viz" ~/.claude/skills/travel-plan-viz
# OpenAI Codex
ln -sfn "$(pwd)/travel-plan-viz" ~/.codex/skills/travel-plan-viz
```

**Using another agent?** This skill is platform-agnostic — it's just an instruction file plus three vanilla-JS engines. For agents without a skills mechanism, feed `travel-plan-viz/SKILL.md` as instructions. Full porting steps and a ready-to-paste adaptation prompt: [`travel-plan-viz/references/porting-to-other-agents.md`](travel-plan-viz/references/porting-to-other-agents.md).

### 💬 Usage

In Claude Code or Codex, just say:

```
Plan me a 4-day, 3-night trip to Hong Kong       # Mode A: plan from scratch
```
```
Here is my itinerary <paste text/HTML>, make a page   # Mode B: existing plan
```

After it's generated, hand the HTML back to Claude to keep editing, e.g. *"Day 3 is too packed, move X to Day 4."* The full trip data is embedded as JSON in the page, so edits change the data and re-render — nothing gets lost.

### 🖼️ Samples

Ready-made outputs in `samples/`, open them in a browser:

- `changzhi-jincheng-7d6n-real.html` — Changzhi & Jincheng, 7D6N (Mode A: fly + rental-car loop from Shanghai; national-heritage temples + Taihang canyons; leg-by-leg drive chain, no-mountain-roads-after-dark scheduling, chain-hotel-first picks, Gaoping heritage deep-dive (Chongming Temple's 971 hall, Kaihua Temple murals, Ji residence, Tiefo Temple, Lianghu village), rail-via-Zhengzhou fallback, National-Day-week (Oct 1–7) crowd-aware scheduling)
- `wuhan-xiangyang-6d5n-real.html` — Wuhan, Xiangyang & Zhongxiang, 6D5N (Mode A: HSR from Shanghai, dates TBD; a bianzhong-bronze-bells pilgrimage loop — Hubei Provincial Museum → the Zenghouyi tomb pit at Suizhou, an HSR ring with no backtracking; Zhiyin cruise / Tang-dynasty night shows, three zero-move nights inside Xiangyang's old city, UNESCO Ming Xianling tomb on the way home, leg-by-leg transit chain and 9 booking reminders; all 29 points carry dual-sourced WGS-84 coordinates, zero guesswork)
- `taiyuan-pingyao-jiexiu-fenyang-6d5n-real.html` — Taiyuan, Pingyao, Jiexiu & Fenyang, 6D5N (Mode A: flight + downtown car rental from Shanghai, dates TBD, National-Day week; a Shanxi-merchant heritage line — Jinci's 984 Song-dynasty hall and statues, UNESCO Shuanglin/Zhenguo temples' sculptures, Houtu Temple's glazed rooftops, the one-of-a-kind XianShen Lou, Taifu Guan's Ming suspended sculptures; crowd-aware scheduling for the holiday (a Monday-closure-proof day, first-entry-at-opening strategy), leg-by-leg drive chain, 9 booking reminders, and shows kept out of the main line by rule; every point carries WGS-84 coordinates, zero guesswork)
- `barcelona-granada-sevilla-cordoba-madrid-10d9n-real.html` — Barcelona, Granada, Seville, Córdoba & Madrid, 10D9N (Mode A: nonstop flight in + AVE rail spine from Shanghai, dates TBD anchored to the Chinese New Year 2027 red-eye window; a Gaudí & Andalusia UNESCO line — Sagrada Família, the Alhambra's Court of the Lions, the Mezquita's forest of arches; winter-sunset scheduling (viewpoints re-timed for February's early dark), a Monday-closure-proof weekday matrix (Seville Cathedral on a full-hours Thursday, Sofía's Friday evening slot, Toledo on a full-hours Saturday, Prado's Saturday free evening), leg-by-leg transit chain and 10 booking reminders, with the Barça–Atlético home fixture noted as an optional tip rather than a stop; first international sample — mainland-only Amap day links are auto-omitted abroad, 37 dual-sourced WGS-84 points including rail stations and airports, 19 Commons photos all 200-verified)

### ❓ FAQ

**Q: How is this different from just asking a chatbot to "write me an itinerary"?**

A plain chat gives you a wall of text or a one-off page. This skill bakes the error-prone parts into a reusable pipeline: an itinerary health-check with restrained optional suggestions (Mode B), a single offline-readable HTML file, tap-to-navigate map pins, booking reminders back-calculated from your departure date, mechanical post-generation validation, and embedded JSON data so the page stays editable without losing fields.

**Q: "AI travel guides are pointless — you have to verify everything yourself anyway."**

Half agreed. Time-sensitive info (prices, opening hours, schedules) must be verified through official channels — which is exactly why every page ships with a full-coverage disclaimer pointing to official apps. The value here is **organizing and reminding** — laying scattered info out as a usable itinerary page and back-calculating what to book by when — not verifying or booking for you. That last step is honestly left to you.

**Q: Does it work for cities outside China?**

Yes. The map uses global OpenStreetMap tiles; overseas coordinates are already WGS-84 and need no conversion (GCJ-02 correction only applies to coordinates coming from Amap/Tencent).

### 📁 Structure

```
travel-plan-viz/
  SKILL.md              # workflow: detect mode → research → generate
  assets/
    map.js              # Leaflet engine: markers/route/nav links/coord conversion (unit-tested)
    reminders.js        # reminder engine (unit-tested)
    validate.js         # contract validation engine: post-generation checks (unit-tested, has CLI)
    page-contract.md    # content contract for the design step
    page-template.html  # page skeleton template: inject trip data & engines, re-theme, ship
  references/
    research-guide.md   # web-research guide
    design-guidelines.md # built-in aesthetics (fallback w/o external design skill)
    porting-to-other-agents.md # cross-agent porting guide + adaptation prompt
samples/                # generated example pages
test/                   # engine unit tests (node --test)
docs/                   # static assets (banner.png)
```

### 🧪 Tests

```bash
node --test test/*.test.js
```

### ⚠️ Disclaimer

All information on the page (weather, flights, hotels, restaurants, tickets, prices, opening hours, ratings, events, etc.) is AI-compiled from public sources, **for reference only** — it may be inaccurate or outdated. **Always verify on official channels before booking or going.**

### 📄 License

[MIT](LICENSE) — use, modify, and ship it freely; just keep the copyright notice. Issues and PRs welcome.
