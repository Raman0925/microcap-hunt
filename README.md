# Project Microcap Hunt

AI-powered investment research firm for Indian microcap stocks.

## Overview

Three specialized AI agents conduct deep fundamental and technical research on Indian microcap companies, debate investment merits, and produce structured reports.

### Agents

| Agent | Focus | Framework |
|-------|-------|-----------|
| **Laxmi** | Fundamentals | Buffett, Munger, Lynch, Marks, Pabrai, Greenblatt, Graham |
| **Meera** | Technical Analysis | Price action, momentum, volume, chart patterns |
| **Tara** | Story & Risk | Nassim Taleb — antifragility, tail risk, narrative |

### Investment Frameworks

- **Warren Buffett** — Economic moats, owner-earnings, durable competitive advantage
- **Charlie Munger** — Mental models, latticework thinking, inversion
- **Peter Lynch** — PEG ratio, growth at reasonable price, local knowledge
- **Howard Marks** — Market cycles, risk asymmetry, second-level thinking
- **Mohnish Pabrai** — Dhandho investing, cloning, margin of safety
- **Joel Greenblatt** — Magic formula, ROIC, earnings yield
- **Benjamin Graham** — Net-net, margin of safety, value investing
- **Nassim Taleb** — Antifragility, black swans, optionality, via negativa

## Architecture

```
microcap/          — Python agents
  main.py          — Orchestrator
  laxmi.py         — Fundamentals agent
  meera.py         — Technical analysis agent
  tara.py          — Story/risk agent
  debate.py        — Agent debate engine
  fetcher.py       — Data fetcher (BSE/NSE)
  state_tracker.py — Research state management
  db.py            — SQLite storage
  reporter.py      — Report generation
  INVESTMENT_FRAMEWORK.md — Full framework reference

microcap-dashboard/   — Web dashboard
  api/              — FastAPI backend (port 8765)
  frontend/         — React frontend (port 3000)
```

## Setup & Run

```bash
# Install dependencies
pip install -r microcap/requirements.txt

# Run research agents
cd microcap
python3 main.py

# Start dashboard (separate terminal)
cd microcap-dashboard
./start.sh
```

Dashboard: http://localhost:3000  
API: http://localhost:8765

## Storage

SQLite database (`microcap.db`) stores all research results, agent debates, and investment recommendations locally.
