"""Builds profile SVGs (activity graph, followers badge, stars badge) from the GitHub API.

Runs inside the GitHub Action. Needs only the Python standard library.
Env: GH_USER (profile owner), GH_TOKEN (the built-in GITHUB_TOKEN).
Use --demo to render with fake data for a local preview.
"""
import html
import json
import os
import random
import sys
import urllib.request

OUT = "dist"
QUERY = """
query($login:String!){
  user(login:$login){
    followers{totalCount}
    repositories(first:100, ownerAffiliations:OWNER, privacy:PUBLIC){nodes{stargazerCount}}
    contributionsCollection{contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}
  }
}
"""


def fetch(user, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": user}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "profile-assets"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data or not data.get("data", {}).get("user"):
        raise RuntimeError(f"GitHub API error: {data.get('errors') or 'user not found'}")
    u = data["data"]["user"]
    cal = u["contributionsCollection"]["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    stars = sum(n["stargazerCount"] for n in u["repositories"]["nodes"])
    return days, cal["totalContributions"], u["followers"]["totalCount"], stars


def demo():
    random.seed(7)
    days = [{"date": f"d{i}", "contributionCount": max(0, int(random.gauss(2, 3)))} for i in range(365)]
    return days, sum(d["contributionCount"] for d in days), 12, 5


def badge(name, label, value, color):
    fs, h, pad = 11, 22, 10
    lw = int(len(label) * 6.6 + pad * 2)
    vw = int(len(str(value)) * 7.2 + pad * 2)
    W = lw + vw
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}">'
        f'<clipPath id="r"><rect width="{W}" height="{h}" rx="3"/></clipPath><g clip-path="url(#r)">'
        f'<rect width="{lw}" height="{h}" fill="#1e1b4b"/><rect x="{lw}" width="{vw}" height="{h}" fill="{color}"/></g>'
        f'<g fill="#fff" font-family="Verdana,DejaVu Sans,Segoe UI,Arial,sans-serif" font-size="{fs}" font-weight="700">'
        f'<text x="{pad}" y="15">{html.escape(label)}</text><text x="{lw + pad}" y="15">{html.escape(str(value))}</text></g></svg>'
    )
    open(f"{OUT}/{name}.svg", "w").write(svg)


def smooth(vals, k=3):
    out = []
    for i in range(len(vals)):
        seg = vals[max(0, i - k + 1): i + 1]
        out.append(sum(seg) / len(seg))
    return out


def graph(days, total):
    recent = days[-90:]
    raw = [d["contributionCount"] for d in recent]
    vals = smooth(raw)
    W, H = 900, 270
    L, R, T, B = 50, 30, 78, 40
    pw, ph = W - L - R, H - T - B
    top = max(max(vals), 4)
    pts = [(L + i * pw / (len(vals) - 1), T + ph - (v / top) * ph) for i, v in enumerate(vals)]
    line = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    area = line + f" L{pts[-1][0]:.1f} {T + ph} L{pts[0][0]:.1f} {T + ph} Z"
    active = sum(1 for c in raw if c > 0)
    best = max(raw)
    bi = vals.index(max(vals))
    bx, by = pts[bi]
    grid = "".join(
        f'<line x1="{L}" x2="{W - R}" y1="{T + ph * g / 3:.1f}" y2="{T + ph * g / 3:.1f}" stroke="#312e81" stroke-opacity=".5" stroke-dasharray="3 5"/>'
        for g in range(4)
    )
    chips = [(str(total), "contributions in the last year"), (str(active), "active days (90d)"), (str(best), "best day (90d)")]
    chip_svg = ""
    for i, (n, lbl) in enumerate(chips):
        x = L + i * 270
        chip_svg += f'<text x="{x}" y="46" class="n">{n}</text><text x="{x}" y="64" class="s">{html.escape(lbl)}</text>'
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0d1117"/><stop offset="1" stop-color="#14122b"/></linearGradient>
<linearGradient id="fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8b5cf6" stop-opacity=".55"/><stop offset="1" stop-color="#8b5cf6" stop-opacity="0"/></linearGradient>
<linearGradient id="ln" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#a78bfa"/><stop offset="1" stop-color="#38bdf8"/></linearGradient>
<filter id="glow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>
<style>
text{{font-family:"Fira Code","DejaVu Sans Mono",Menlo,Consolas,monospace}}
.n{{font-size:30px;font-weight:700;fill:#e0e7ff}}.s{{font-size:11px;fill:#8b8fc7}}
.ln{{stroke-dasharray:1;stroke-dashoffset:1;animation:d 3s ease-out forwards}}@keyframes d{{to{{stroke-dashoffset:0}}}}
.ar{{opacity:0;animation:f 1.2s ease-out 2.2s forwards}}@keyframes f{{to{{opacity:1}}}}
.pk{{transform-box:fill-box;transform-origin:center;opacity:0;animation:p 1.6s ease-in-out 3s infinite}}@keyframes p{{0%{{opacity:.9;transform:scale(1)}}100%{{opacity:0;transform:scale(3.2)}}}}
</style>
<rect width="{W}" height="{H}" rx="14" fill="url(#bg)" stroke="#312e81" stroke-width="1.5"/>
{chip_svg}{grid}
<path class="ar" d="{area}" fill="url(#fill)"/>
<path class="ln" pathLength="1" d="{line}" fill="none" stroke="url(#ln)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" filter="url(#glow)"/>
<circle class="pk" cx="{bx:.1f}" cy="{by:.1f}" r="5" fill="#38bdf8"/><circle cx="{bx:.1f}" cy="{by:.1f}" r="4" fill="#e0e7ff" opacity="0"><animate attributeName="opacity" from="0" to="1" begin="3s" dur=".3s" fill="freeze"/></circle>
<text x="{L}" y="{H - 14}" class="s">last 90 days</text><text x="{W - R}" y="{H - 14}" text-anchor="end" class="s">today</text>
</svg>'''
    open(f"{OUT}/activity-graph.svg", "w").write(svg)


def main():
    os.makedirs(OUT, exist_ok=True)
    if "--demo" in sys.argv:
        days, total, followers, stars = demo()
    else:
        days, total, followers, stars = fetch(os.environ["GH_USER"], os.environ["GH_TOKEN"])
    graph(days, total)
    badge("followers", "Followers", followers, "#4338ca")
    badge("stars", "Stars", stars, "#7c3aed")
    print("wrote activity-graph.svg, followers.svg, stars.svg")


if __name__ == "__main__":
    main()
