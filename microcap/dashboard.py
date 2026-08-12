"""
dashboard.py — Live web dashboard for Project Microcap Hunt.

Serves a single-page dashboard that auto-refreshes every 10 seconds.
Shows agent activity, company verdicts, and detailed reports.

Run with: python dashboard.py
Accessible at: http://localhost:7842
"""

import json
import time
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer

STATE_FILE = Path(__file__).parent / "dashboard_data.json"
PORT = 7842


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return None


def fmt_time(ts) -> str:
    if not ts:
        return "—"
    import datetime
    return datetime.datetime.fromtimestamp(ts).strftime("%H:%M:%S")


def fmt_ago(ts) -> str:
    if not ts:
        return "—"
    delta = int(time.time() - ts)
    if delta < 60:
        return f"{delta}s ago"
    elif delta < 3600:
        return f"{delta // 60}m ago"
    else:
        return f"{delta // 3600}h ago"


def verdict_badge(verdict: str) -> str:
    classes = {"shortlist": "badge-green", "borderline": "badge-yellow", "reject": "badge-red"}
    labels = {"shortlist": "✅ SHORTLISTED", "borderline": "⚠️ BORDERLINE", "reject": "❌ REJECTED"}
    cls = classes.get(verdict, "badge-grey")
    label = labels.get(verdict, verdict.upper())
    return f'<span class="{cls}">{label}</span>'


def agent_status_html(agent: dict, name: str) -> str:
    status = agent.get("status", "idle")
    last = agent.get("last_company") or "—"
    verdict = agent.get("last_verdict") or "—"
    count = agent.get("count", 0)
    dot_class = "dot-green" if status == "analysing" else "dot-grey"
    status_label = "Analysing..." if status == "analysing" else "Idle"
    return f"""
    <div class="agent-card">
      <div class="agent-header">
        <span class="dot {dot_class}"></span>
        <strong>{name}</strong>
        <span class="agent-status">{status_label}</span>
      </div>
      <div class="agent-detail">Last: <b>{last}</b></div>
      <div class="agent-detail">Last verdict: <b>{verdict}</b> &nbsp;|&nbsp; Total: <b>{count}</b></div>
    </div>"""


def build_html(state: dict) -> str:
    if state is None:
        return """<html><body style="font-family:sans-serif;padding:40px;background:#0d1117;color:#cdd9e5">
        <h2>No data yet</h2><p>Start the hunt: <code>python main.py</code></p>
        <meta http-equiv="refresh" content="5"></body></html>"""

    agents = state.get("agent_activity", {})
    companies = state.get("companies", [])
    shortlisted = [c for c in companies if c.get("verdict") == "shortlist"]
    borderline = [c for c in companies if c.get("verdict") == "borderline"]
    rejected = [c for c in companies if c.get("verdict") == "reject"]

    run_started = state.get("run_started")
    last_updated = state.get("last_updated")
    total = state.get("total_companies", 0)
    analysed = state.get("analysed", 0)
    progress_pct = int(analysed / total * 100) if total > 0 else 0

    agent_html = ""
    agent_names = {"laxmi": "Laxmi (Fundamentals)", "meera": "Meera (Technical)", "tara": "Tara (Story)"}
    for key, display in agent_names.items():
        agent_html += agent_status_html(agents.get(key, {}), display)

    def company_rows(clist, show_detail=False):
        rows = ""
        for c in reversed(clist):
            v = c.get("verdict", "")
            ts = fmt_ago(c.get("timestamp"))
            conf = f"{int(c.get('confidence', 0) * 100)}%"
            lv = c.get("laxmi_verdict", "—") or "—"
            mv = c.get("meera_verdict", "—") or "—"
            tv = c.get("tara_verdict", "—") or "—"
            sym = c.get("symbol", "")
            name = c.get("name", sym)
            url = c.get("screener_url", f"https://www.screener.in/company/{sym}/")
            thesis = c.get("investment_thesis", "") or ""

            row = f"""<tr>
              <td><a href="{url}" target="_blank" class="sym-link">{sym}</a></td>
              <td>{name}</td>
              <td>{verdict_badge(v)}</td>
              <td>{conf}</td>
              <td><span class="sub">{lv}</span> / <span class="sub">{mv}</span> / <span class="sub">{tv}</span></td>
              <td class="ts">{ts}</td>
            </tr>"""
            if show_detail and thesis:
                row += f'<tr class="thesis-row"><td colspan="6"><i>{thesis}</i></td></tr>'
            rows += row
        return rows or '<tr><td colspan="6" class="empty">None yet</td></tr>'

    shortlist_rows = company_rows(shortlisted, show_detail=True)
    borderline_rows = company_rows(borderline)
    reject_rows = company_rows(rejected[-30:])  # show last 30 rejects only

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="10">
<title>Microcap Hunt Dashboard</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          background: #0d1117; color: #cdd9e5; min-height: 100vh; }}
  .header {{ background: #161b22; border-bottom: 1px solid #30363d; padding: 16px 24px;
             display: flex; align-items: center; justify-content: space-between; }}
  .header h1 {{ font-size: 18px; font-weight: 700; color: #58a6ff; }}
  .header .meta {{ font-size: 12px; color: #8b949e; }}
  .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; padding: 20px 24px; }}
  .stat-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px;
                padding: 16px; text-align: center; }}
  .stat-card .num {{ font-size: 32px; font-weight: 700; margin-bottom: 4px; }}
  .stat-card .label {{ font-size: 12px; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; }}
  .num-green {{ color: #3fb950; }}
  .num-yellow {{ color: #d29922; }}
  .num-red {{ color: #f85149; }}
  .num-blue {{ color: #58a6ff; }}
  .progress-bar {{ height: 4px; background: #21262d; margin: 0 24px 4px; border-radius: 2px; }}
  .progress-fill {{ height: 100%; background: #58a6ff; border-radius: 2px;
                    transition: width 0.5s; width: {progress_pct}%; }}
  .progress-label {{ font-size: 11px; color: #8b949e; padding: 0 24px 16px; }}
  .agents {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; padding: 0 24px 20px; }}
  .agent-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 14px; }}
  .agent-header {{ display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }}
  .agent-status {{ font-size: 11px; color: #8b949e; margin-left: auto; }}
  .agent-detail {{ font-size: 12px; color: #8b949e; margin-top: 4px; }}
  .dot {{ width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }}
  .dot-green {{ background: #3fb950; box-shadow: 0 0 6px #3fb950; animation: pulse 1.5s infinite; }}
  .dot-grey {{ background: #484f58; }}
  @keyframes pulse {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:0.4; }} }}
  .section {{ padding: 0 24px 24px; }}
  .section h2 {{ font-size: 14px; font-weight: 600; color: #8b949e; text-transform: uppercase;
                 letter-spacing: 0.5px; margin-bottom: 12px; padding-bottom: 8px;
                 border-bottom: 1px solid #21262d; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ text-align: left; padding: 8px 10px; color: #8b949e; font-weight: 500;
        font-size: 11px; text-transform: uppercase; letter-spacing: 0.3px;
        border-bottom: 1px solid #21262d; }}
  td {{ padding: 8px 10px; border-bottom: 1px solid #161b22; vertical-align: top; }}
  tr:hover td {{ background: #161b22; }}
  .thesis-row td {{ color: #8b949e; font-size: 12px; padding-top: 0; border-bottom: 1px solid #21262d; }}
  .badge-green {{ background: #0d4a1e; color: #3fb950; padding: 2px 8px; border-radius: 12px;
                   font-size: 11px; font-weight: 600; white-space: nowrap; }}
  .badge-yellow {{ background: #3a2a00; color: #d29922; padding: 2px 8px; border-radius: 12px;
                    font-size: 11px; font-weight: 600; white-space: nowrap; }}
  .badge-red {{ background: #3a0d0d; color: #f85149; padding: 2px 8px; border-radius: 12px;
                 font-size: 11px; font-weight: 600; white-space: nowrap; }}
  .sym-link {{ color: #58a6ff; text-decoration: none; font-weight: 600; }}
  .sym-link:hover {{ text-decoration: underline; }}
  .sub {{ color: #8b949e; font-size: 11px; }}
  .ts {{ color: #8b949e; font-size: 11px; white-space: nowrap; }}
  .empty {{ color: #484f58; text-align: center; padding: 20px; }}
</style>
</head>
<body>
<div class="header">
  <h1>🔍 Project Microcap Hunt</h1>
  <div class="meta">Started {fmt_time(run_started)} &nbsp;|&nbsp; Last update: {fmt_ago(last_updated)} &nbsp;|&nbsp; Auto-refresh: 10s</div>
</div>

<div class="stats">
  <div class="stat-card">
    <div class="num num-blue">{analysed}<span style="font-size:18px;color:#8b949e">/{total}</span></div>
    <div class="label">Analysed</div>
  </div>
  <div class="stat-card">
    <div class="num num-green">{state.get('shortlisted', 0)}</div>
    <div class="label">Shortlisted</div>
  </div>
  <div class="stat-card">
    <div class="num num-yellow">{state.get('borderline', 0)}</div>
    <div class="label">Borderline</div>
  </div>
  <div class="stat-card">
    <div class="num num-red">{state.get('rejected', 0)}</div>
    <div class="label">Rejected</div>
  </div>
</div>

<div class="progress-bar"><div class="progress-fill"></div></div>
<div class="progress-label">{progress_pct}% complete — {analysed} of {total} companies processed</div>

<div class="agents">
  {agent_html}
</div>

<div class="section">
  <h2>✅ Shortlisted ({len(shortlisted)})</h2>
  <table>
    <thead><tr><th>Symbol</th><th>Name</th><th>Verdict</th><th>Confidence</th><th>L/M/T</th><th>When</th></tr></thead>
    <tbody>{shortlist_rows}</tbody>
  </table>
</div>

<div class="section">
  <h2>⚠️ Borderline ({len(borderline)})</h2>
  <table>
    <thead><tr><th>Symbol</th><th>Name</th><th>Verdict</th><th>Confidence</th><th>L/M/T</th><th>When</th></tr></thead>
    <tbody>{borderline_rows}</tbody>
  </table>
</div>

<div class="section">
  <h2>❌ Rejected (last 30 of {len(rejected)})</h2>
  <table>
    <thead><tr><th>Symbol</th><th>Name</th><th>Verdict</th><th>Confidence</th><th>L/M/T</th><th>When</th></tr></thead>
    <tbody>{reject_rows}</tbody>
  </table>
</div>

</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        state = load_state()
        html = build_html(state)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, fmt, *args):
        pass  # suppress access logs


if __name__ == "__main__":
    print(f"Dashboard running at http://localhost:{PORT}")
    print("Start the hunt in another terminal: python main.py")
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    server.serve_forever()
