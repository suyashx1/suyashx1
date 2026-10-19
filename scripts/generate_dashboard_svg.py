#!/usr/bin/env python3
import json
import math
import os
from datetime import datetime, timezone
from html import escape
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(ROOT, "profile_config.json")


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def gh_get(url, token=None):
    headers = {"User-Agent": "suyashx1-profile-dashboard"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = Request(url, headers=headers)
    with urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_data(handle, token=None):
    try:
        user = gh_get(f"https://api.github.com/users/{handle}", token=token)
        repos = gh_get(
            f"https://api.github.com/users/{handle}/repos?per_page=100&type=owner&sort=updated",
            token=token,
        )
    except (HTTPError, URLError, TimeoutError):
        user = {
            "followers": 0,
            "created_at": "",
            "location": "",
            "bio": "",
            "name": handle,
        }
        repos = []
        api_available = False
    else:
        api_available = True

    stars = sum(repo.get("stargazers_count", 0) for repo in repos)
    forks = sum(repo.get("forks_count", 0) for repo in repos)

    lang_counts = {}
    month_activity = [0] * 12
    now = datetime.now(timezone.utc)

    for repo in repos:
        lang = repo.get("language") or "Other"
        lang_counts[lang] = lang_counts.get(lang, 0) + 1

        pushed = repo.get("pushed_at")
        if pushed:
            try:
                pushed_dt = datetime.strptime(pushed, "%Y-%m-%dT%H:%M:%SZ").replace(
                    tzinfo=timezone.utc
                )
                month_diff = (now.year - pushed_dt.year) * 12 + (now.month - pushed_dt.month)
                if 0 <= month_diff < 12:
                    month_activity[11 - month_diff] += 1
            except ValueError:
                pass

    top_langs = sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "user": user,
        "api_available": api_available,
        "repo_count": len(repos),
        "stars": stars,
        "forks": forks,
        "top_langs": top_langs,
        "activity": month_activity,
        "generated_at": now,
    }


def draw_bars(x, y, width, rows, values, colors, label_color):
    out = []
    max_v = max([v for _, v in values], default=1)
    row_h = 28
    for i, (name, value) in enumerate(values):
        top = y + i * row_h
        ratio = value / max_v if max_v else 0
        fill_w = max(8, int((width - 140) * ratio))
        color = colors[i % len(colors)]
        out.append(
            f'<text x="{x}" y="{top + 16}" fill="{label_color}" font-size="13" font-weight="600">{escape(name)}</text>'
        )
        out.append(
            f'<rect x="{x + 95}" y="{top + 5}" width="{width - 140}" height="12" rx="6" fill="rgba(127,127,127,0.25)"/>'
        )
        out.append(
            f'<rect x="{x + 95}" y="{top + 5}" width="{fill_w}" height="12" rx="6" fill="{color}"/>'
        )
        out.append(
            f'<text x="{x + width - 30}" y="{top + 16}" text-anchor="end" fill="{label_color}" font-size="12">{value}</text>'
        )
    return "\n".join(out)


def sparkline_points(x, y, width, height, values):
    if not values:
        return ""
    max_v = max(values) or 1
    step = width / (len(values) - 1)
    points = []
    for i, v in enumerate(values):
        px = x + i * step
        py = y + height - (v / max_v) * height
        points.append(f"{px:.1f},{py:.1f}")
    return " ".join(points)


def render(theme, cfg, data):
    user = data["user"]
    generated = data["generated_at"].strftime("%Y-%m-%d %H:%M UTC")

    if theme == "dark":
        colors = {
            "bg1": "#0d1117",
            "bg2": "#161b22",
            "card": "#111827",
            "stroke": "#30363d",
            "text": "#c9d1d9",
            "sub": "#8b949e",
            "accent": "#58a6ff",
            "accent2": "#bc8cff",
            "bars": ["#58a6ff", "#bc8cff", "#2ea043", "#ffa657", "#f778ba"],
        }
    else:
        colors = {
            "bg1": "#f6f8fa",
            "bg2": "#ffffff",
            "card": "#ffffff",
            "stroke": "#d0d7de",
            "text": "#1f2328",
            "sub": "#57606a",
            "accent": "#0969da",
            "accent2": "#8250df",
            "bars": ["#0969da", "#8250df", "#1a7f37", "#9a6700", "#bf3989"],
        }

    name = cfg.get("display_name") or user.get("name") or cfg["handle"]
    tagline = cfg.get("tagline") or user.get("bio") or "Building cool things with code"
    location = cfg.get("location") or user.get("location") or "Unknown"
    contact = cfg.get("contact") or {}
    highlights = cfg.get("highlights") or []

    top_langs = data["top_langs"]
    if not top_langs and cfg.get("languages"):
        top_langs = [(lang, max(1, 5 - i)) for i, lang in enumerate(cfg["languages"][:5])]
    if not top_langs:
        top_langs = [("Other", 1)]
    activity = data["activity"]
    points = sparkline_points(650, 380, 540, 90, activity)

    highlights_svg = []
    for i, item in enumerate(highlights[:4]):
        highlights_svg.append(
            f'<text x="75" y="{340 + i * 28}" fill="{colors["text"]}" font-size="14">• {escape(item)}</text>'
        )

    bars = draw_bars(650, 458, 540, 5, top_langs, colors["bars"], colors["text"])

    repos_value = data["repo_count"] if data["api_available"] else "syncing..."
    followers_value = user.get("followers", 0) if data["api_available"] else "syncing..."
    stars_value = data["stars"] if data["api_available"] else "syncing..."
    forks_value = data["forks"] if data["api_available"] else "syncing..."
    created_value = (
        (user.get("created_at") or "")[:10] if data["api_available"] else "syncing..."
    )
    sync_note = (
        "Live GitHub data connected"
        if data["api_available"]
        else "Waiting for GitHub Actions refresh"
    )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720" role="img" aria-label="Dynamic GitHub dashboard for {escape(cfg['handle'])}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{colors['bg1']}"/>
      <stop offset="100%" stop-color="{colors['bg2']}"/>
    </linearGradient>
    <linearGradient id="titleGradient" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{colors['accent']}"/>
      <stop offset="100%" stop-color="{colors['accent2']}"/>
    </linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="10" stdDeviation="12" flood-opacity="0.2"/>
    </filter>
  </defs>

  <rect width="1280" height="720" rx="20" fill="url(#bg)"/>

  <rect x="40" y="40" width="1200" height="640" rx="18" fill="{colors['card']}" stroke="{colors['stroke']}" filter="url(#shadow)"/>

  <text x="75" y="105" fill="url(#titleGradient)" font-size="38" font-weight="800" font-family="Inter, Segoe UI, Arial, sans-serif">{escape(name)}</text>
  <text x="75" y="138" fill="{colors['sub']}" font-size="18" font-family="Inter, Segoe UI, Arial, sans-serif">{escape(tagline)}</text>

  <text x="75" y="188" fill="{colors['accent']}" font-size="16" font-weight="700">@{escape(cfg['handle'])}</text>
  <text x="75" y="214" fill="{colors['sub']}" font-size="14">📍 {escape(location)}</text>
  <text x="75" y="238" fill="{colors['sub']}" font-size="14">🧠 Focus: {escape(cfg.get('focus', 'Full-stack, AI, and Developer Tools'))}</text>

  <rect x="60" y="270" width="520" height="2" fill="{colors['stroke']}"/>
  <text x="75" y="305" fill="{colors['accent']}" font-size="16" font-weight="700">Highlights</text>
  {''.join(highlights_svg)}

  <text x="75" y="490" fill="{colors['accent']}" font-size="16" font-weight="700">Contact</text>
  <text x="75" y="520" fill="{colors['text']}" font-size="14">✉️ {escape(contact.get('email', ''))}</text>
  <text x="75" y="546" fill="{colors['text']}" font-size="14">🔗 {escape(contact.get('website', ''))}</text>
  <text x="75" y="572" fill="{colors['text']}" font-size="14">💼 {escape(contact.get('linkedin', ''))}</text>

  <rect x="630" y="85" width="575" height="250" rx="14" fill="rgba(127,127,127,0.08)" stroke="{colors['stroke']}"/>
  <text x="660" y="126" fill="{colors['accent']}" font-size="18" font-weight="700">GitHub Snapshot</text>
  <text x="1160" y="126" text-anchor="end" fill="{colors['sub']}" font-size="12">{sync_note}</text>

  <text x="660" y="172" fill="{colors['text']}" font-size="15">Public repos</text>
  <text x="1160" y="172" text-anchor="end" fill="{colors['text']}" font-size="15" font-weight="700">{repos_value}</text>

  <text x="660" y="205" fill="{colors['text']}" font-size="15">Followers</text>
  <text x="1160" y="205" text-anchor="end" fill="{colors['text']}" font-size="15" font-weight="700">{followers_value}</text>

  <text x="660" y="238" fill="{colors['text']}" font-size="15">Total stars</text>
  <text x="1160" y="238" text-anchor="end" fill="{colors['text']}" font-size="15" font-weight="700">{stars_value}</text>

  <text x="660" y="271" fill="{colors['text']}" font-size="15">Total forks</text>
  <text x="1160" y="271" text-anchor="end" fill="{colors['text']}" font-size="15" font-weight="700">{forks_value}</text>

  <text x="660" y="304" fill="{colors['text']}" font-size="15">Member since</text>
  <text x="1160" y="304" text-anchor="end" fill="{colors['text']}" font-size="15" font-weight="700">{escape(created_value)}</text>

  <text x="650" y="372" fill="{colors['accent']}" font-size="16" font-weight="700">12-month repo activity</text>
  <polyline points="{points}" fill="none" stroke="{colors['accent2']}" stroke-width="4" stroke-linecap="round"/>

  <text x="650" y="442" fill="{colors['accent']}" font-size="16" font-weight="700">Top languages (by repositories)</text>
  {bars}

  <text x="75" y="646" fill="{colors['sub']}" font-size="12">Auto-updated daily via GitHub Actions • Last refresh: {generated}</text>
</svg>
'''


def main():
    cfg = load_config()
    handle = cfg["handle"]
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    data = fetch_data(handle, token=token)

    outputs = {
        "dark_mode.svg": render("dark", cfg, data),
        "light_mode.svg": render("light", cfg, data),
    }

    for name, content in outputs.items():
        with open(os.path.join(ROOT, name), "w", encoding="utf-8") as f:
            f.write(content)


if __name__ == "__main__":
    main()
