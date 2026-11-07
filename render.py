"""Render the status page as complete HTML (readable without JavaScript, so
search engines index it), from status.json and history.json.

    render(cfg, status, history, out_dir)

writes index.html, sitemap.xml, status badges (badge.svg and badges/<repo>.svg)
and copies web/app.js, web/style.css and web/og.png. The browser script only
adds to the page: theme, views, filters, search, live times, a countdown,
tooltips, copying and refreshing in place.
"""

from __future__ import annotations

import html
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

WEB = Path(__file__).resolve().parent / "web"
LABEL = {"ok": "Operational", "warn": "Needs a look", "fail": "Failing", "running": "Running",
         "idle": "Idle", "unknown": "Unknown"}
CHIP = {"ok": "OK", "warn": "Warning", "fail": "Failing", "running": "Running", "idle": "Idle", "unknown": "Unknown"}
KIND = {"site": "Site", "pages": "Deploy", "pulls": "Pull requests", "workflow": "Workflow", "data": "Data"}
ORDER = {"fail": 0, "warn": 1, "unknown": 2, "running": 3, "ok": 4, "idle": 5}
e = lambda s: html.escape(str(s if s is not None else ""), quote=True)

# Line icons, one per kind of check, drawn once and used by reference.
ICONS = {
    "site": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.7 3.8 5.7 3.8 9s-1.3 6.3-3.8 9c-2.5-2.7-3.8-5.7-3.8-9S9.5 5.7 12 3z"/>',
    "pages": '<path d="M5 15c-1.5 1.5-2 5-2 5s3.5-.5 5-2M9 13l-2-2c1.5-4 4.5-7 11-8-1 6.5-4 9.5-8 11l-2-2zM14 7.5a1.5 1.5 0 1 0 3 0 1.5 1.5 0 0 0-3 0"/>',
    "pulls": '<circle cx="6" cy="6" r="2.5"/><circle cx="6" cy="18" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="M6 8.5v7M18 15.5V9a3 3 0 0 0-3-3h-4M13 4l-2 2 2 2"/>',
    "workflow": '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.9 4.9 7 7M17 17l2.1 2.1M2 12h3M19 12h3M4.9 19.1 7 17M17 7l2.1-2.1"/>',
    "data": '<ellipse cx="12" cy="5.5" rx="7.5" ry="2.8"/><path d="M4.5 5.5v6c0 1.6 3.4 2.8 7.5 2.8s7.5-1.2 7.5-2.8v-6M4.5 11.5v6c0 1.6 3.4 2.8 7.5 2.8s7.5-1.2 7.5-2.8v-6"/>',
}


def icon(kind: str) -> str:
    return f'<svg class="ic" viewBox="0 0 24 24" aria-hidden="true"><use href="#i-{kind if kind in ICONS else "data"}"/></svg>'


def sprite() -> str:
    return ('<svg width="0" height="0" style="position:absolute" aria-hidden="true">'
            + "".join(f'<symbol id="i-{k}" viewBox="0 0 24 24">{v}</symbol>' for k, v in ICONS.items()) + "</svg>")


def parse(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def nice(t: str) -> str:
    return parse(t).strftime("%-d %b %Y, %H:%M UTC")


def healthy(hist, repo, least=12):
    """Share of checks in the history that found the site healthy; None until
    there are enough checks for the figure to mean something."""
    s = [h["repos"].get(repo) for h in hist if repo in h.get("repos", {})]
    return round(100 * sum(x == "ok" for x in s) / len(s)) if len(s) >= least else None


def bins_of(hist, key, now, days, bins):
    """The worst state in each bin of the last `days`, for one site."""
    span = timedelta(days=days)
    start = now - span
    rank = {"ok": 0, "warn": 1, "fail": 2}
    cells = [None] * bins
    for h in hist:
        s = h["repos"].get(key)
        if not s:
            continue
        i = int((parse(h["t"]) - start) / (span / bins))
        if 0 <= i < bins and (cells[i] is None or rank.get(s, 0) > rank.get(cells[i], 0)):
            cells[i] = s
    return start, span, cells


def strip_svg(hist, repo, now, days=14, bins=56, cls="strip", h=28):
    start, span, cells = bins_of(hist, repo, now, days, bins)
    w, gap = 10, 2
    parts = []
    for i, s in enumerate(cells):
        t0 = start + span / bins * i
        tip = f"{t0:%-d %b %H:%M}–{t0 + span / bins:%H:%M} UTC · {LABEL.get(s, 'no data') if s else 'no data'}"
        hgt = {None: h * .3, "ok": h * .6, "warn": h * .8, "fail": h}.get(s, h * .6)
        parts.append(f'<rect class="b b-{s or "none"}" x="{i * (w + gap)}" y="{h - hgt:.1f}" width="{w}" height="{hgt:.1f}" rx="2" '
                     f'data-tip="{e(tip)}"/>')
    vw = bins * (w + gap) - gap
    return (f'<svg class="{cls}" viewBox="0 0 {vw} {h}" preserveAspectRatio="none" role="img" '
            f'aria-label="Last {days} days, worst state in each {24 * days // bins} hours">{"".join(parts)}</svg>')


def spark_ms(hist, repo, now, days=14):
    """Response time of the site over the last days, as a line with an area."""
    pts = [(parse(h["t"]), h.get("ms", {}).get(repo)) for h in hist]
    pts = [(t, v) for t, v in pts if v is not None and t > now - timedelta(days=days)]
    if len(pts) < 2:
        return '<p class="spark-empty quiet">Response times appear after a few checks.</p>'
    W, H, pad = 300, 44, 3
    t0, t1 = now - timedelta(days=days), now
    vmax = max(v for _, v in pts) * 1.15
    X = lambda t: pad + (W - 2 * pad) * (t - t0) / (t1 - t0)
    Y = lambda v: H - pad - (H - 2 * pad) * v / vmax
    line = " ".join(f"{X(t):.1f},{Y(v):.1f}" for t, v in pts)
    area = f"M{X(pts[0][0]):.1f},{H - pad} L" + " L".join(f"{X(t):.1f},{Y(v):.1f}" for t, v in pts) + f" L{X(pts[-1][0]):.1f},{H - pad} Z"
    last = pts[-1]
    med = sorted(v for _, v in pts)[len(pts) // 2]
    hits = "".join(f'<circle class="hit" cx="{X(t):.1f}" cy="{Y(v):.1f}" r="5" data-tip="{e(f"{t:%-d %b %H:%M} UTC · {v} ms")}"/>' for t, v in pts)
    return (f'<figure class="spark"><svg viewBox="0 0 {W} {H}" preserveAspectRatio="none" role="img" aria-label="Response time, last {days} days: median {med} ms, latest {last[1]} ms">'
            f'<path class="area" d="{area}"/><polyline class="line" points="{line}"/>'
            f'<circle class="end" cx="{X(last[0]):.1f}" cy="{Y(last[1]):.1f}" r="3.2"/>{hits}</svg>'
            f'<figcaption><span>Response time</span><b>{last[1]} ms</b><span class="quiet">median {med} ms</span></figcaption></figure>')


def ring(counts: dict) -> str:
    """The share of checks in each state, as a ring with the healthy share inside."""
    total = sum(counts.values()) or 1
    r, C = 52, 2 * 3.14159265 * 52
    off, arcs = 0.0, []
    names = {"ok": "healthy", "warn": "warnings", "fail": "failing", "other": "running or idle"}
    for s in ("ok", "warn", "fail", "other"):
        n = counts.get(s, 0)
        if not n:
            continue
        L = C * n / total
        arcs.append(f'<circle class="arc a-{s}" r="{r}" cx="60" cy="60" stroke-dasharray="{L:.2f} {C - L:.2f}" '
                    f'stroke-dashoffset="{-off:.2f}" data-tip="{n} {names[s]}"/>')
        off += L
    pct = round(100 * counts.get("ok", 0) / total)
    return (f'<svg class="ring" viewBox="0 0 120 120" role="img" aria-label="{pct}% of checks are healthy">'
            f'<circle class="track" r="{r}" cx="60" cy="60"/>{"".join(arcs)}'
            f'<text x="60" y="61" class="ring-big">{pct}%</text><text x="60" y="80" class="ring-small">healthy</text></svg>')


def problems_chart(hist, now, days=14) -> str:
    """Warnings and failures at each check over the last days, stacked."""
    def count(h, s):
        if h.get("n"):
            return h["n"].get(s, 0)
        return sum(1 for k in h.get("bad", []) if k.endswith("|" + s))
    pts = [(parse(h["t"]), count(h, "warn"), count(h, "fail")) for h in hist if parse(h["t"]) > now - timedelta(days=days)]
    if not pts:
        return ""
    W, H, pad = 640, 90, 4
    t0 = now - timedelta(days=days)
    X = lambda t: pad + (W - 2 * pad) * (t - t0) / (now - t0)
    vmax = max([w + f for _, w, f in pts] + [3])
    Y = lambda v: H - pad - (H - 2 * pad) * v / vmax

    def area(vals):
        xs = [(X(t), Y(v)) for (t, _, _), v in zip(pts, vals)]
        return f"M{xs[0][0]:.1f},{H - pad} " + " ".join(f"L{x:.1f},{y:.1f}" for x, y in xs) + f" L{xs[-1][0]:.1f},{H - pad} Z"
    tot = area([w + f for _, w, f in pts])
    fail = area([f for _, _, f in pts])
    hits = "".join(f'<rect class="hit" x="{X(t) - 3:.1f}" y="0" width="6" height="{H}" '
                   f'data-tip="{e(f"{t:%-d %b %H:%M} UTC · {f} failing, {w} warnings")}"/>' for t, w, f in pts)
    ticks = "".join(f'<line class="tick" x1="{X(now - timedelta(days=d)):.1f}" x2="{X(now - timedelta(days=d)):.1f}" y1="{H - pad}" y2="{H}"/>'
                    for d in range(days, 0, -1))
    return (f'<svg class="problems" viewBox="0 0 {W} {H}" preserveAspectRatio="none" role="img" '
            f'aria-label="Warnings and failures at each check over the last {days} days">'
            f'<line class="base" x1="{pad}" x2="{W - pad}" y1="{H - pad}" y2="{H - pad}"/>{ticks}'
            f'<path class="p-warn" d="{tot}"/><path class="p-fail" d="{fail}"/>{hits}</svg>')


def badge(label: str, state: str) -> str:
    """A small status badge, in the style READMEs use, for embedding."""
    text = {"ok": "operational", "warn": "needs a look", "fail": "failing"}.get(state, state)
    col = {"ok": "#2f9e5d", "warn": "#c48a00", "fail": "#cf3a2e"}.get(state, "#8b9198")
    lw, rw = 7 * len(label) + 12, 7 * len(text) + 12
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{lw + rw}" height="20" role="img" aria-label="{e(label)}: {text}">'
            f'<title>{e(label)}: {text}</title><linearGradient id="g" x2="0" y2="100%"><stop offset="0" stop-color="#fff" stop-opacity=".1"/>'
            f'<stop offset="1" stop-opacity=".1"/></linearGradient><clipPath id="r"><rect width="{lw + rw}" height="20" rx="3"/></clipPath>'
            f'<g clip-path="url(#r)"><rect width="{lw}" height="20" fill="#3c4148"/><rect x="{lw}" width="{rw}" height="20" fill="{col}"/>'
            f'<rect width="{lw + rw}" height="20" fill="url(#g)"/></g><g fill="#fff" text-anchor="middle" font-family="Verdana,DejaVu Sans,sans-serif" font-size="11">'
            f'<text x="{lw / 2}" y="14">{e(label)}</text><text x="{lw + rw / 2}" y="14">{text}</text></g></svg>')


def incidents(hist, names, limit=14):
    """Changes of state per site: when something went wrong and when it recovered."""
    out, prev, since = [], {}, {}
    for h in hist:
        for repo, s in h.get("repos", {}).items():
            p = prev.get(repo)
            if p is not None and s != p:
                x = {"t": h["t"], "repo": repo, "to": s, "from": p}
                if s in ("warn", "fail") and p == "ok":
                    since[repo] = h["t"]
                elif s == "ok" and p in ("warn", "fail"):
                    x["dur"] = (parse(h["t"]) - parse(since.get(repo, h["t"]))).total_seconds() / 3600
                out.append(x)
            prev[repo] = s
    out = out[::-1][:limit]
    if not out:
        return '<p class="quiet">No changes of state in the last 14 days.</p>'
    rows = []
    for x in out:
        dur = x.get("dur")
        what = ((f"recovered after {dur:.0f} h" if dur >= 1 else f"recovered after {max(1, round(dur * 60))} min") if dur is not None else
                f"{LABEL[x['from']].lower()} → {LABEL[x['to']].lower()}")
        rows.append(f'<li class="inc st-{x["to"]}"><span class="inc-dot" aria-hidden="true"></span>'
                    f'<time datetime="{x["t"]}">{nice(x["t"])}</time>'
                    f'<span><a href="#{e(x["repo"])}">{e(names.get(x["repo"], x["repo"]))}</a> <span class="quiet">{e(what)}</span></span>'
                    f'<span class="chip c-{x["to"]}">{CHIP[x["to"]]}</span></li>')
    return f'<ol class="incidents">{"".join(rows)}</ol>'


def check_row(c):
    kind = KIND.get(c.get("kind"), "Check")
    name = f'<a href="{e(c["link"])}">{e(c["name"])}</a>' if c.get("link") else e(c["name"])
    when = f'<time class="ago" datetime="{e(c["when"])}">{nice(c["when"])}</time>' if c.get("when") else ""
    return (f'<tr class="row" data-state="{c["state"]}" data-kind="{e(c.get("kind", ""))}">'
            f'<td class="st"><span class="chip c-{c["state"]}">{CHIP[c["state"]]}</span></td>'
            f'<th scope="row" class="nm"><span class="nm-in">{icon(c.get("kind", ""))}<span>{name}<span class="kind">{kind}</span></span></span></th>'
            f'<td class="dt">{e(c["detail"])}</td><td class="wh">{when}</td></tr>')


def repo_section(r, hist, now, page_url):
    checks = sorted(r["checks"], key=lambda c: ORDER[c["state"]])
    bad = sum(c["state"] in ("warn", "fail") for c in checks)
    hp = healthy(hist, r["repo"])
    links = [f'<a href="{e(r["url"])}">Site</a>'] if r.get("url") else []
    links += [f'<a href="{e(r["github"])}">Repository</a>', f'<a href="{e(r["github"])}/actions">Actions</a>']
    kinds = {}
    for c in checks:
        kinds.setdefault(c.get("kind", "data"), []).append(c["state"])
    pills = "".join(
        f'<span class="kpill k-{min(v, key=lambda s: ORDER[s])}" title="{e(KIND.get(k, k))}: {len(v)} {"check" if len(v) == 1 else "checks"}">{icon(k)}{len(v)}</span>'
        for k, v in kinds.items())
    md = f"[![{r['name']} status]({page_url}badges/{r['repo']}.svg)]({page_url}#{r['repo']})"
    return f"""
<section class="repo st-{r['state']}" id="{e(r['repo'])}" data-state="{r['state']}" aria-labelledby="h-{e(r['repo'])}">
  <header class="repo-head">
    <button class="fold" type="button" aria-expanded="true" aria-controls="b-{e(r['repo'])}" aria-label="Show or hide {e(r['name'])}">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg></button>
    <div class="repo-title">
      <h2 id="h-{e(r['repo'])}">{e(r['name'])} <a class="anchor" href="#{e(r['repo'])}" aria-label="Link to {e(r['name'])}">#</a></h2>
      <p class="about">{e(r.get('about', ''))}</p>
      <div class="kpills">{pills}</div>
    </div>
    <div class="repo-meta">
      <span class="chip c-{r['state']} big">{LABEL[r['state']]}</span>
      <span class="quiet">{f'{bad} to look at · ' if bad else ''}{len(checks)} checks{f' · healthy {hp}% of 14 days' if hp is not None else ''}</span>
      <nav class="links" aria-label="{e(r['name'])} links">{' '.join(links)}
        <button class="copy" type="button" data-copy="{e(md)}" title="Copy a Markdown status badge for {e(r['name'])}">Copy badge</button></nav>
    </div>
  </header>
  <div class="repo-body" id="b-{e(r['repo'])}">
    <div class="viz">
      <figure class="history">{strip_svg(hist, r['repo'], now)}<figcaption><span>14 days ago</span><span>State, every 6 hours</span><span>now</span></figcaption></figure>
      {spark_ms(hist, r['repo'], now)}
    </div>
    <div class="table-wrap"><table class="checks">
      <caption class="sr">Checks for {e(r['name'])}</caption>
      <thead><tr><th scope="col">State</th><th scope="col">Check</th><th scope="col">Detail</th><th scope="col">When</th></tr></thead>
      <tbody>{''.join(check_row(c) for c in checks)}</tbody>
    </table></div>
  </div>
</section>"""


def tile(r, hist, now):
    ms = next((c.get("ms") for c in r["checks"] if c.get("ms") is not None), None)
    bad = sum(c["state"] in ("warn", "fail") for c in r["checks"])
    return (f'<a class="tile st-{r["state"]}" href="#{e(r["repo"])}">'
            f'<span class="tile-top"><span class="dot" aria-hidden="true"></span><span class="tile-name">{e(r["name"])}</span></span>'
            f'<span class="tile-state">{LABEL[r["state"]]}{f" · {bad} to look at" if bad else ""}</span>'
            f'{strip_svg(hist, r["repo"], now, days=1, bins=24, cls="mini", h=18)}'
            f'<span class="tile-foot"><span>{len(r["checks"])} checks · 24 h</span><span>{f"{ms} ms" if ms is not None else ""}</span></span></a>')


def render(cfg, status, hist, out: Path) -> None:
    pg = cfg["page"]
    now = parse(status["checked"])
    names = {r["repo"]: r["name"] for r in status["repos"]}
    allc = [c for r in status["repos"] for c in r["checks"]]
    bad = [(r, c) for r in status["repos"] for c in r["checks"] if c["state"] in ("warn", "fail")]
    counts = {"ok": sum(c["state"] == "ok" for c in allc), "warn": sum(c["state"] == "warn" for c in allc),
              "fail": sum(c["state"] == "fail" for c in allc)}
    counts["other"] = len(allc) - sum(counts.values())
    hps = [h for h in (healthy(hist, r["repo"]) for r in status["repos"]) if h is not None]
    overall = round(sum(hps) / len(hps)) if hps else None
    st = status["state"]
    nfail, nwarn = counts["fail"], counts["warn"]
    headline = {"ok": "All systems operational",
                "warn": f"{len(bad)} {'thing needs' if len(bad) == 1 else 'things need'} a look",
                "fail": f"{nfail} failing" + (f", {nwarn} to look at" if nwarn else "")}[st]
    nxt = now + timedelta(hours=status.get("every_h", 1))
    url = pg["url"].rstrip("/") + "/"
    attention = "".join(
        f'<li class="att st-{c["state"]}">{icon(c.get("kind", ""))}<span class="chip c-{c["state"]}">{CHIP[c["state"]]}</span>'
        f'<span class="att-text"><a href="#{e(r["repo"])}">{e(r["name"])}</a> · <b>{e(c["name"])}</b><br><span class="quiet">{e(c["detail"])}</span></span>'
        + (f'<a class="att-go" href="{e(c["link"])}">Open</a>' if c.get("link") else "") + "</li>"
        for r, c in sorted(bad, key=lambda x: ORDER[x[1]["state"]]))
    summary = "".join(tile(r, hist, now) for r in status["repos"])
    sections = "".join(repo_section(r, hist, now, url) for r in status["repos"])
    title = f'{pg["title"]} · {pg["site_name"]}'
    ld = {"@context": "https://schema.org", "@type": "WebPage", "name": title, "url": url,
          "description": " ".join(pg["description"].split()), "dateModified": status["checked"],
          "author": {"@type": "Person", "name": pg.get("author"), "url": pg.get("author_url")},
          "isPartOf": {"@type": "WebSite", "url": pg.get("home", url)},
          "mainEntity": {"@type": "ItemList", "itemListElement": [
              {"@type": "ListItem", "position": i + 1, "item": {"@type": "WebSite", "name": r["name"], "url": r.get("url") or r["github"],
                                                                  "description": r.get("about", "")}}
              for i, r in enumerate(status["repos"])]}}
    ga = pg.get("analytics")
    analytics = (f'<script async src="https://www.googletagmanager.com/gtag/js?id={e(ga)}"></script>\n'
                 f"<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}"
                 f"gtag('js',new Date());gtag('config','{e(ga)}');</script>") if ga else ""
    dot = {"ok": "%231f7a4a", "warn": "%23b07a00", "fail": "%23b3261e"}[st]
    favicon = (f'<link rel="icon" type="image/png" sizes="32x32" href="{e(pg["favicon"])}">' if pg.get("favicon") else
               f'<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 16 16%22%3E%3Ccircle cx=%228%22 cy=%228%22 r=%227%22 fill=%22{dot}%22/%3E%3C/svg%3E">')
    touch = f'<link rel="apple-touch-icon" href="{e(pg["apple_touch_icon"])}">' if pg.get("apple_touch_icon") else ""
    twitter = f'<meta name="twitter:site" content="{e(pg["twitter"])}"><meta name="twitter:creator" content="{e(pg["twitter"])}">' if pg.get("twitter") else ""
    desc = " ".join(pg["description"].split())
    every = status.get("every_h", 1)
    md_all = f"[![{pg['title']}]({url}badge.svg)]({url})"
    tpl = (WEB / "template.html").read_text()
    repl = {
        "TITLE": e(title), "PAGE_TITLE": e(pg["title"]), "DESC": e(desc), "URL": e(url), "OG": e(url + "og.png"),
        "SITE_NAME": e(pg["site_name"]), "HOME": e(pg.get("home", url)), "AUTHOR": e(pg.get("author", "")),
        "AUTHOR_URL": e(pg.get("author_url", pg.get("home", url))), "ANALYTICS": analytics, "FAVICON": favicon, "TOUCH": touch,
        "TWITTER": twitter, "LD": json.dumps(ld, ensure_ascii=False).replace("</", "<\\/"),
        "ACCENT": e(pg.get("accent", "#1f4e87")), "ACCENT_DARK": e(pg.get("accent_dark", "#7aa9e3")),
        "STATE": st, "HEADLINE": e(headline), "STATE_LABEL": LABEL[st], "SPRITE": sprite(),
        "CHECKED": status["checked"], "CHECKED_NICE": nice(status["checked"]), "NEXT": nxt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "EVERY": f"{every:g}", "EVERY_TEXT": "hour" if every == 1 else f"{every:g} hours",
        "N_SITES": str(len(status["repos"])), "N_CHECKS": str(len(allc)),
        "N_OK": str(counts["ok"]), "N_WARN": str(counts["warn"]), "N_FAIL": str(counts["fail"]),
        "L_OK": f'{counts["ok"]} healthy', "L_WARN": f'{counts["warn"]} {"warning" if counts["warn"] == 1 else "warnings"}',
        "L_FAIL": f'{counts["fail"]} failing',
        "N_BAD": str(len(bad)), "HEALTHY": f"{overall}%" if overall is not None else "–",
        "RING": ring(counts), "PROBLEMS": problems_chart(hist, now),
        "ATTENTION": f'<ul class="attention">{attention}</ul>' if attention else
                     '<p class="all-clear"><svg class="ic" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>Nothing needs a look right now.</p>',
        "SUMMARY": summary, "SECTIONS": sections, "INCIDENTS": incidents(hist, names),
        "OWNER": e(status.get("owner", "")), "YEAR": str(now.year), "N_RUNS": str(len(hist)),
        "BADGE_MD": e(md_all), "BADGE_URL": e(url + "badge.svg"),
    }
    for k, v in repl.items():
        tpl = tpl.replace("%%" + k + "%%", v)
    (out / "index.html").write_text(tpl)
    for f in ("app.js", "style.css", "og.png"):
        if (WEB / f).exists():
            shutil.copy(WEB / f, out / f)
    (out / "badges").mkdir(exist_ok=True)
    (out / "badge.svg").write_text(badge(pg["title"].lower(), st))
    for r in status["repos"]:
        (out / "badges" / f"{r['repo']}.svg").write_text(badge(r["name"], r["state"]))
    (out / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f' <url><loc>{e(url)}</loc><lastmod>{status["checked"][:10]}</lastmod><changefreq>hourly</changefreq></url>\n</urlset>\n')
    (out / ".nojekyll").write_text("")
