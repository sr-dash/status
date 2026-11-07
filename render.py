"""Render the status page as complete HTML (readable without JavaScript, so
search engines index it), from status.json and history.json.

    render(cfg, status, history, out_dir)

writes index.html, sitemap.xml, and copies web/app.js, web/style.css and
web/og.png. The browser script (app.js) only adds to it: theme, filters,
search, live times, a countdown and refreshing the page in place.
"""

from __future__ import annotations

import html
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

WEB = Path(__file__).resolve().parent / "web"
LABEL = {"ok": "Operational", "warn": "Needs a look", "fail": "Failing", "running": "Running",
         "idle": "Idle", "unknown": "Unknown"}
CHIP = {"ok": "OK", "warn": "Warning", "fail": "Failing", "running": "Running", "idle": "Idle", "unknown": "Unknown"}
KIND = {"site": "Site", "pages": "Deploy", "pulls": "Pull requests", "workflow": "Workflow", "data": "Data"}
ORDER = {"fail": 0, "warn": 1, "unknown": 2, "running": 3, "ok": 4, "idle": 5}
e = lambda s: html.escape(str(s if s is not None else ""), quote=True)


def parse(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def nice(t: str) -> str:
    return parse(t).strftime("%-d %b %Y, %H:%M UTC")


def healthy(hist, repo, least=12):
    """Share of checks in the history that found the site healthy; None until
    there are enough checks for the figure to mean something."""
    s = [h["repos"].get(repo) for h in hist if repo in h.get("repos", {})]
    return round(100 * sum(x == "ok" for x in s) / len(s)) if len(s) >= least else None


def strip_svg(hist, repo, now, days=14, bins=56):
    """The worst state in each 6-hour bin, as a row of bars with tooltips."""
    span = timedelta(days=days)
    start = now - span
    rank = {"ok": 0, "warn": 1, "fail": 2}
    cells = [None] * bins
    for h in hist:
        s = h["repos"].get(repo)
        if not s:
            continue
        i = int((parse(h["t"]) - start) / (span / bins))
        if 0 <= i < bins and (cells[i] is None or rank.get(s, 0) > rank.get(cells[i], 0)):
            cells[i] = s
    w, gap, H = 10, 2, 28
    parts = []
    for i, s in enumerate(cells):
        t0 = start + span / bins * i
        tip = f"{t0:%-d %b %H:%M}–{t0 + span / bins:%H:%M} UTC: {LABEL.get(s, 'no data') if s else 'no data'}"
        hgt = {None: 8, "ok": 16, "warn": 22, "fail": H}.get(s, 16)
        parts.append(f'<rect class="b b-{s or "none"}" x="{i * (w + gap)}" y="{H - hgt}" width="{w}" height="{hgt}" rx="2" '
                     f'data-tip="{e(tip)}"><title>{e(tip)}</title></rect>')
    vw = bins * (w + gap) - gap
    return (f'<svg class="strip" viewBox="0 0 {vw} {H}" preserveAspectRatio="none" role="img" '
            f'aria-label="Last {days} days, worst state in each 6 hours">{"".join(parts)}</svg>')


def incidents(hist, names, limit=12):
    """Changes of state per site: when something went wrong and when it recovered."""
    out, prev, since = [], {}, {}
    for h in hist:
        for repo, s in h.get("repos", {}).items():
            p = prev.get(repo)
            if p is not None and s != p:
                if s in ("warn", "fail") and p == "ok":
                    since[repo] = h["t"]
                    out.append({"t": h["t"], "repo": repo, "to": s, "from": p})
                elif s == "ok" and p in ("warn", "fail"):
                    dur = (parse(h["t"]) - parse(since.get(repo, h["t"]))).total_seconds() / 3600
                    out.append({"t": h["t"], "repo": repo, "to": s, "from": p, "dur": dur})
                elif s != p:
                    out.append({"t": h["t"], "repo": repo, "to": s, "from": p})
            prev[repo] = s
    out = out[::-1][:limit]
    if not out:
        return '<p class="quiet">No changes of state in the last 14 days.</p>'
    rows = []
    for x in out:
        dur = x.get("dur")
        what = ((f"recovered after {dur:.0f} h" if dur >= 1 else f"recovered after {max(1, round(dur * 60))} min") if dur is not None else
                f"{LABEL[x['from']].lower()} → {LABEL[x['to']].lower()}")
        rows.append(f'<li class="inc st-{x["to"]}"><time datetime="{x["t"]}">{nice(x["t"])}</time>'
                    f'<span class="chip c-{x["to"]}">{CHIP[x["to"]]}</span>'
                    f'<span><a href="#{e(x["repo"])}">{e(names.get(x["repo"], x["repo"]))}</a> <span class="quiet">{e(what)}</span></span></li>')
    return f'<ol class="incidents">{"".join(rows)}</ol>'


def check_row(c):
    kind = KIND.get(c.get("kind"), "Check")
    name = f'<a href="{e(c["link"])}">{e(c["name"])}</a>' if c.get("link") else e(c["name"])
    when = f'<time class="ago" datetime="{e(c["when"])}">{nice(c["when"])}</time>' if c.get("when") else ""
    return (f'<tr class="row" data-state="{c["state"]}" data-kind="{e(c.get("kind", ""))}">'
            f'<td class="st"><span class="chip c-{c["state"]}">{CHIP[c["state"]]}</span></td>'
            f'<th scope="row" class="nm">{name}<span class="kind">{kind}</span></th>'
            f'<td class="dt">{e(c["detail"])}</td><td class="wh">{when}</td></tr>')


def repo_section(r, hist, now):
    checks = sorted(r["checks"], key=lambda c: ORDER[c["state"]])
    bad = sum(c["state"] in ("warn", "fail") for c in checks)
    hp = healthy(hist, r["repo"])
    links = [f'<a href="{e(r["url"])}">Site</a>'] if r.get("url") else []
    links += [f'<a href="{e(r["github"])}">Repository</a>', f'<a href="{e(r["github"])}/actions">Actions</a>']
    return f"""
<section class="repo st-{r['state']}" id="{e(r['repo'])}" data-state="{r['state']}" aria-labelledby="h-{e(r['repo'])}">
  <header class="repo-head">
    <button class="fold" type="button" aria-expanded="true" aria-controls="b-{e(r['repo'])}" aria-label="Show or hide {e(r['name'])}">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg></button>
    <div class="repo-title">
      <h2 id="h-{e(r['repo'])}">{e(r['name'])}</h2>
      <p class="about">{e(r.get('about', ''))}</p>
    </div>
    <div class="repo-meta">
      <span class="chip c-{r['state']} big">{LABEL[r['state']]}</span>
      <span class="quiet">{f'{bad} to look at · ' if bad else ''}{len(checks)} checks{f' · healthy {hp}% of 14 days' if hp is not None else ''}</span>
      <nav class="links" aria-label="{e(r['name'])} links">{' '.join(links)}</nav>
    </div>
  </header>
  <div class="repo-body" id="b-{e(r['repo'])}">
    <figure class="history">{strip_svg(hist, r['repo'], now)}<figcaption><span>14 days ago</span><span>now</span></figcaption></figure>
    <div class="table-wrap"><table class="checks">
      <caption class="sr">Checks for {e(r['name'])}</caption>
      <thead><tr><th scope="col">State</th><th scope="col">Check</th><th scope="col">Detail</th><th scope="col">When</th></tr></thead>
      <tbody>{''.join(check_row(c) for c in checks)}</tbody>
    </table></div>
  </div>
</section>"""


def render(cfg, status, hist, out: Path) -> None:
    pg = cfg["page"]
    now = parse(status["checked"])
    names = {r["repo"]: r["name"] for r in status["repos"]}
    allc = [c for r in status["repos"] for c in r["checks"]]
    bad = [(r, c) for r in status["repos"] for c in r["checks"] if c["state"] in ("warn", "fail")]
    hps = [h for h in (healthy(hist, r["repo"]) for r in status["repos"]) if h is not None]
    overall = round(sum(hps) / len(hps)) if hps else None
    st = status["state"]
    headline = {"ok": "All systems operational", "warn": f"{len(bad)} {'thing needs' if len(bad) == 1 else 'things need'} a look",
                "fail": f"{sum(c['state'] == 'fail' for _, c in bad)} failing, {sum(c['state'] == 'warn' for _, c in bad)} to look at"}[st]
    nxt = now + timedelta(hours=status.get("every_h", 1))
    attention = "".join(
        f'<li class="att st-{c["state"]}"><span class="chip c-{c["state"]}">{CHIP[c["state"]]}</span>'
        f'<a href="#{e(r["repo"])}">{e(r["name"])}</a> <b>{e(c["name"])}</b> <span class="quiet">{e(c["detail"])}</span></li>'
        for r, c in sorted(bad, key=lambda x: ORDER[x[1]["state"]]))
    summary = "".join(
        f'<a class="tile st-{r["state"]}" href="#{e(r["repo"])}"><span class="dot" aria-hidden="true"></span>'
        f'<span class="tile-name">{e(r["name"])}</span><span class="tile-state">{LABEL[r["state"]]}</span></a>'
        for r in status["repos"])
    sections = "".join(repo_section(r, hist, now) for r in status["repos"])
    url = pg["url"].rstrip("/") + "/"
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
    tpl = (WEB / "template.html").read_text()
    repl = {
        "TITLE": e(title), "PAGE_TITLE": e(pg["title"]), "DESC": e(desc), "URL": e(url), "OG": e(url + "og.png"),
        "SITE_NAME": e(pg["site_name"]), "HOME": e(pg.get("home", url)), "AUTHOR": e(pg.get("author", "")),
        "AUTHOR_URL": e(pg.get("author_url", pg.get("home", url))), "ANALYTICS": analytics, "FAVICON": favicon, "TOUCH": touch,
        "TWITTER": twitter, "LD": json.dumps(ld, ensure_ascii=False).replace("</", "<\\/"),
        "ACCENT": e(pg.get("accent", "#1f4e87")), "ACCENT_DARK": e(pg.get("accent_dark", "#7aa9e3")),
        "STATE": st, "HEADLINE": e(headline), "STATE_LABEL": LABEL[st],
        "CHECKED": status["checked"], "CHECKED_NICE": nice(status["checked"]), "NEXT": nxt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "EVERY": f'{status.get("every_h", 1):g}', "EVERY_TEXT": "hour" if status.get("every_h", 1) == 1 else f'{status.get("every_h", 1):g} hours', "N_SITES": str(len(status["repos"])), "N_CHECKS": str(len(allc)),
        "N_BAD": str(len(bad)), "HEALTHY": f"{overall}%" if overall is not None else "–",
        "ATTENTION": f'<ul class="attention">{attention}</ul>' if attention else '<p class="quiet all-clear">Nothing needs a look right now.</p>',
        "SUMMARY": summary, "SECTIONS": sections, "INCIDENTS": incidents(hist, names),
        "OWNER": e(status.get("owner", "")), "YEAR": str(now.year),
        "N_RUNS": str(len(hist)),
    }
    for k, v in repl.items():
        tpl = tpl.replace("%%" + k + "%%", v)
    (out / "index.html").write_text(tpl)
    for f in ("app.js", "style.css", "og.png"):
        if (WEB / f).exists():
            shutil.copy(WEB / f, out / f)
    (out / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f' <url><loc>{e(url)}</loc><lastmod>{status["checked"][:10]}</lastmod><changefreq>hourly</changefreq></url>\n</urlset>\n')
    (out / ".nojekyll").write_text("")
