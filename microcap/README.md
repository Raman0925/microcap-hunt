# Project Microcap Hunt

A rule-based Indian microcap stock analysis system. Three analysts — Laxmi, Meera, and Tara — score each company from different angles and shortlist the best ones. Reports go to Telegram.

**No AI API key required.** All analysis is deterministic and rule-based.

## Analysts

| Analyst | Focus | Method |
|---------|-------|--------|
| **Laxmi** | Fundamentals — FCF consistency, D/E, ROCE, promoter holding | Rule-based scoring 0–4 |
| **Meera** | Technical — 52w range position, revenue trend | Rule-based signals 0–3 |
| **Tara** | Story — news sentiment, sector risk, governance red flags | Google News RSS + rules |

Laxmi is the **primary filter**: a hard rejection from her (confidence ≥ 85%) skips Meera and Tara.

## Scoring Rules

### Laxmi (Fundamentals — score 0–4)
- FCF positive for 3+ of last 5 years → +1
- Debt/Equity < 1 → +1
- ROCE > 12% → +1
- Promoter holding > 35% → +1

Score 3–4 = pass, 1–2 = borderline, 0 = reject

### Meera (Technical — score 0–3)
- Current price within 30% of 52w high → +1
- Revenue growing YoY → +1
- Price above 52w midpoint → +1

Score 2–3 = pass, 1 = borderline, 0 = reject

### Tara (Story — red flag counting)
- Promoter pledging > 30% → reject
- Risky sector (PSU bank, chit fund, etc.) → red flag
- Shell-like description (< 80 chars) → red flag
- Negative news keywords → red flag
- Positive news signals → positive catalyst

2+ red flags = reject, 1 = borderline, 0 = pass

## Output Format

- **Rejected**: one line — `COMPANY_NAME — rejected: [reason]`
- **Borderline**: one paragraph summary
- **Shortlisted**: full report with all three analysts' findings

Rejected companies are logged only (not sent to Telegram — too noisy). Borderline and shortlisted go to Telegram.

## Setup

### 1. Install dependencies

```bash
cd microcap/
pip install -r requirements.txt
```

### 2. Set environment variables

```bash
export TELEGRAM_BOT_TOKEN="123456:ABC..."
```

Only `TELEGRAM_BOT_TOKEN` is needed. Without it, reports print to stdout only.
Reports go to Telegram chat ID `8495865824`.

### 3. Run

#### Full hunt (default: 100 companies, batches of 10)
```bash
python main.py
```

#### Custom limits
```bash
python main.py --max 50 --batch-size 5
```

#### Analyse a single company by symbol
```bash
python main.py --single TATAPOWER
python main.py --single IRFC
```

#### Fresh start (ignore saved progress)
```bash
python main.py --no-resume
```

## How It Works

```
Screener.in microcap list
        ↓
fetcher.py — scrapes company list + financial data (requests + BeautifulSoup)
        ↓
For each company:
  Laxmi (fundamentals rules) ──┐
  Meera (technical rules)    ───┼──→ debate.py → weighted score → final verdict
  Tara (news + rules)        ──┘
        ↓
reporter.py → Telegram
```

### Rate Limiting
- Screener.in: 2.5 seconds between requests
- Google News RSS: 2.0 seconds between requests
- If Laxmi rejects with ≥85% confidence, Meera and Tara are skipped
- Progress is saved to `progress.json` — interrupted runs resume where they left off

### Debate / Weighting
The final verdict uses a weighted score: Laxmi ×2.0, Tara ×1.5, Meera ×1.0 (fundamentals-first).

Normalised score ≥ 0.35 → shortlist  
Normalised score ≥ -0.1 → borderline  
Below → reject

## Files

```
microcap/
├── main.py           # Orchestrator — run this
├── fetcher.py        # Screener.in scraper
├── laxmi.py          # Fundamental analysis (rule-based)
├── meera.py          # Technical analysis (rule-based)
├── tara.py           # Story/news analysis (Google News RSS + rules)
├── debate.py         # Weighted voting logic
├── reporter.py       # Telegram formatting and sending
├── requirements.txt  # requests, beautifulsoup4, lxml
├── progress.json     # Auto-created: resume checkpoint
└── microcap_hunt.log # Auto-created: run logs
```

## Limitations & Notes

- Screener.in's public pages sometimes use JavaScript rendering — if financial tables are empty, the company gets an incomplete analysis (flagged as borderline)
- Google News RSS may be rate-limited — Tara will skip news gracefully if it fails
- The system is for research only, not real-time trading — data is as of scrape time
- Always do your own due diligence before investing
