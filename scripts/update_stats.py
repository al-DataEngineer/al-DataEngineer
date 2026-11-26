"""Fetch real GitHub stats via GraphQL and regenerate profile SVG cards."""

from __future__ import annotations

import html
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"

GRAPHQL_QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      nodes {
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges {
            size
            node {
              name
            }
          }
        }
      }
    }
  }
}
"""


def fetch_github_data(username: str, token: str) -> dict:
    """Query GitHub GraphQL API for contribution calendar and language sizes."""
    payload = json.dumps({"query": GRAPHQL_QUERY, "variables": {"login": username}}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "github-profile-stats-updater",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if "errors" in data:
        raise RuntimeError(f"GitHub GraphQL error: {data['errors']}")
    return data["data"]["user"]


def compute_streaks(days: list[dict]) -> tuple[int, int, int]:
    """Return (current_streak, longest_streak, contributions_last_30d)."""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    yesterday_str = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

    longest = 0
    running = 0
    for day in days:
        if day["contributionCount"] > 0:
            running += 1
            longest = max(longest, running)
        else:
            running = 0

    # Current streak: count backwards from today (or yesterday if today has 0 so far)
    current = 0
    idx = len(days) - 1
    if idx >= 0 and days[idx]["date"] == today_str and days[idx]["contributionCount"] == 0:
        idx -= 1
    while idx >= 0 and days[idx]["contributionCount"] > 0:
        current += 1
        idx -= 1

    # Last 30 days contributions
    last_30 = sum(d["contributionCount"] for d in days[-30:])
    return current, longest, last_30


def compute_top_languages(repos: list[dict]) -> list[tuple[str, int]]:
    """Aggregate language byte counts and return top 2 as (name, percentage)."""
    totals: dict[str, int] = {}
    for repo in repos:
        for edge in repo.get("languages", {}).get("edges", []):
            name = edge["node"]["name"]
            totals[name] = totals.get(name, 0) + edge["size"]

    if not totals:
        return [("Python", 100), ("Jupyter Notebook", 0)]

    sorted_langs = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:2]
    top_sum = sum(size for _, size in sorted_langs) or 1
    first_pct = round(sorted_langs[0][1] * 100 / top_sum)
    if len(sorted_langs) == 1:
        return [(sorted_langs[0][0], 100), ("Other", 0)]
    return [(sorted_langs[0][0], first_pct), (sorted_langs[1][0], 100 - first_pct)]


def render_left_col(current_streak: int, total_contrib: int, longest_streak: int, contrib_30d: int) -> str:
    return f"""<svg width="420" height="420" viewBox="0 0 420 420" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="cardBg" x1="0" y1="0" x2="420" y2="210" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#18202c"/>
      <stop offset="100%" stop-color="#11161f"/>
    </linearGradient>
    <style>
      .header {{
        font-family: "JetBrains Mono", Consolas, monospace;
        font-size: 13px;
        fill: #cbd5e1;
      }}
      .code {{
        font-family: "JetBrains Mono", "Fira Code", Consolas, monospace;
        font-size: 13px;
      }}
      .stat-title {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-size: 16px;
        font-weight: 700;
        fill: #67e8f9;
      }}
      .stat-label {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-size: 13.5px;
        fill: #cbd5e1;
      }}
      .stat-val {{
        font-family: "JetBrains Mono", Consolas, monospace;
        font-size: 14px;
        font-weight: 700;
      }}
    </style>
  </defs>

  <!-- TOP CARD: whoami.json -->
  <rect x="1" y="1" width="418" height="198" rx="12" fill="url(#cardBg)" stroke="#30363d" stroke-width="1.4"/>
  <rect x="18" y="12" width="11" height="14" rx="1.5" stroke="#8b949e" stroke-width="1.3" fill="none"/>
  <line x1="21" y1="17" x2="26" y2="17" stroke="#8b949e" stroke-width="1.2"/>
  <line x1="21" y1="21" x2="26" y2="21" stroke="#8b949e" stroke-width="1.2"/>
  <text x="37" y="23.5" class="header">whoami.json</text>
  <line x1="1" y1="38" x2="419" y2="38" stroke="#30363d" stroke-width="1"/>

  <text x="20" y="65" class="code" fill="#8b949e">{{</text>
  <text x="20" y="90" class="code">
    <tspan fill="#79c0ff">  "name"</tspan><tspan fill="#8b949e">: </tspan><tspan fill="#a5d6ff">"Ahmad Alimin"</tspan><tspan fill="#8b949e">,</tspan>
  </text>
  <text x="20" y="114" class="code">
    <tspan fill="#79c0ff">  "role"</tspan><tspan fill="#8b949e">: </tspan><tspan fill="#a5d6ff">"Data Science student"</tspan><tspan fill="#8b949e">,</tspan>
  </text>
  <text x="20" y="138" class="code">
    <tspan fill="#79c0ff">  "focus"</tspan><tspan fill="#8b949e">: </tspan><tspan fill="#a5d6ff">"Data analysis &amp; AI"</tspan><tspan fill="#8b949e">,</tspan>
  </text>
  <text x="20" y="162" class="code">
    <tspan fill="#79c0ff">  "status"</tspan><tspan fill="#8b949e">: </tspan><tspan fill="#a5d6ff">"Open to collaborate"</tspan>
  </text>
  <text x="20" y="185" class="code" fill="#8b949e">}}</text>

  <!-- BOTTOM CARD: GitHub Streak Stats -->
  <rect x="1" y="214" width="418" height="205" rx="12" fill="url(#cardBg)" stroke="#30363d" stroke-width="1.4"/>
  <text x="22" y="248" class="stat-title">GitHub Streak Stats</text>
  <line x1="22" y1="262" x2="398" y2="262" stroke="#30363d" stroke-opacity="0.6" stroke-width="1"/>

  <circle cx="29" cy="285" r="7" fill="#f97316" fill-opacity="0.18"/>
  <path d="M29 279C29 279 33 283 33 286.5C33 288.7 31.2 290.5 29 290.5C26.8 290.5 25 288.7 25 286.5C25 284.5 26.5 282.5 27.5 281.5C27.5 283 28.5 283.5 29 283.5C29.5 283.5 29 281 29 279Z" fill="#fb923c"/>
  <text x="44" y="289" class="stat-label">Current Streak</text>
  <text x="396" y="289" text-anchor="end" class="stat-val" fill="#fb923c">{current_streak}</text>

  <text x="22" y="322" class="stat-label">Total Contributions</text>
  <text x="396" y="322" text-anchor="end" class="stat-val" fill="#e6edf3">{total_contrib}</text>

  <text x="22" y="355" class="stat-label">Longest Streak</text>
  <text x="396" y="355" text-anchor="end" class="stat-val" fill="#e6edf3">{longest_streak}</text>

  <text x="22" y="388" class="stat-label">Contributions (30d)</text>
  <text x="396" y="388" text-anchor="end" class="stat-val" fill="#67e8f9">{contrib_30d}</text>
</svg>
"""


def render_languages(top_langs: list[tuple[str, int]]) -> str:
    (l1_name, l1_pct), (l2_name, l2_pct) = top_langs
    w1 = max(8, round(378 * l1_pct / 100)) if l1_pct > 0 else 0
    w2 = max(8, round(378 * l2_pct / 100)) if l2_pct > 0 else 0
    return f"""<svg width="420" height="120" viewBox="0 0 420 120" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="cardBg" x1="0" y1="0" x2="420" y2="120" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#18202c"/>
      <stop offset="100%" stop-color="#11161f"/>
    </linearGradient>
    <style>
      .lang-name {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-size: 13px;
        fill: #e6edf3;
      }}
      .lang-pct {{
        font-family: "JetBrains Mono", Consolas, monospace;
        font-size: 13px;
        fill: #cbd5e1;
      }}
    </style>
  </defs>

  <rect x="1" y="1" width="418" height="118" rx="12" fill="url(#cardBg)" stroke="#30363d" stroke-width="1.4"/>

  <text x="20" y="34" class="lang-name">{html.escape(l1_name)}</text>
  <text x="398" y="34" text-anchor="end" class="lang-pct">{l1_pct}%</text>
  <rect x="20" y="43" width="378" height="8" rx="4" fill="#21262d"/>
  <rect x="20" y="43" width="{w1}" height="8" rx="4" fill="#f97316"/>

  <text x="20" y="80" class="lang-name">{html.escape(l2_name)}</text>
  <text x="398" y="80" text-anchor="end" class="lang-pct">{l2_pct}%</text>
  <rect x="20" y="89" width="378" height="8" rx="4" fill="#21262d"/>
  <rect x="20" y="89" width="{w2}" height="8" rx="4" fill="#38bdf8"/>
</svg>
"""


def render_activity_graph(days: list[dict]) -> str:
    recent = days[-21:]
    max_count = max((d["contributionCount"] for d in recent), default=1) or 1
    bars = []
    for i, day in enumerate(recent):
        count = day["contributionCount"]
        height = max(6, round((count / max_count) * 70)) if count > 0 else 4
        y = 98 - height
        x = 26 + i * 18
        color = "#fb923c" if count >= max_count * 0.7 and count > 0 else "#67e8f9"
        bars.append(f'    <rect x="{x}" y="{y}" width="6" height="{height}" rx="3" fill="{color}"/>')

    bars_svg = "\n".join(bars)
    return f"""<svg width="420" height="120" viewBox="0 0 420 120" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="cardBg" x1="0" y1="0" x2="420" y2="120" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#18202c"/>
      <stop offset="100%" stop-color="#11161f"/>
    </linearGradient>
    <filter id="barGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="2.5" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <rect x="1" y="1" width="418" height="118" rx="12" fill="url(#cardBg)" stroke="#30363d" stroke-width="1.4"/>
  <line x1="20" y1="98" x2="400" y2="98" stroke="#30363d" stroke-width="1"/>
  <g filter="url(#barGlow)">
{bars_svg}
  </g>
</svg>
"""


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN")
    username = os.environ.get("GITHUB_REPOSITORY_OWNER")
    if not token or not username:
        raise SystemExit("GITHUB_TOKEN and GITHUB_REPOSITORY_OWNER environment variables are required.")

    user = fetch_github_data(username, token)
    cal = user["contributionsCollection"]["contributionCalendar"]
    days = [d for week in cal["weeks"] for d in week["contributionDays"]]

    current_streak, longest_streak, contrib_30d = compute_streaks(days)
    total_contrib = cal["totalContributions"]
    top_langs = compute_top_languages(user["repositories"]["nodes"])

    (ASSETS_DIR / "left-col.svg").write_text(
        render_left_col(current_streak, total_contrib, longest_streak, contrib_30d),
        encoding="utf-8",
    )
    (ASSETS_DIR / "languages.svg").write_text(
        render_languages(top_langs),
        encoding="utf-8",
    )
    (ASSETS_DIR / "activity-graph.svg").write_text(
        render_activity_graph(days),
        encoding="utf-8",
    )
    print(f"Updated SVGs for {username}: streak={current_streak}, total={total_contrib}, langs={top_langs}")


if __name__ == "__main__":
    main()
