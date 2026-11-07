"""The directory of status pages, from directory.yml.

    python directory.py --markdown     # DIRECTORY.md and the README's comparison table
    python directory.py --out site     # the /directory/ page and directory.json (the hourly build calls build())

For each project it reads the stars, licence and last push from GitHub, and
checks that its live page answers (and how fast). The Markdown uses
shields.io badges for stars, last commit and whether the page is up, so it
stays current without being rewritten; the web page is rebuilt every hour.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import yaml

from collect import api, get, parse

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
NOW = datetime.now(timezone.utc)
e = lambda s: html.escape(str(s if s is not None else ""), quote=True)


def probe(url: str | None) -> dict:
    if not url:
        return {"code": None, "ms": None}
    t0 = time.time()
    try:
        code = get(url, timeout=20)[0]
    except Exception as err:
        code = getattr(err, "code", 0) or 0
    return {"code": code, "ms": int((time.time() - t0) * 1000)}


def gather(path: Path = ROOT / "directory.yml") -> dict:
    d = yaml.safe_load(path.read_text())
    projects = [p for s in d["sections"] for p in s.get("projects", [])]
    pages = [p for s in d["sections"] for p in s.get("pages", [])]

    def repo(p):
        try:
            r = api(f"repos/{p['repo']}")
            p.update(stars=r["stargazers_count"], licence=(r.get("license") or {}).get("spdx_id") or "–",
                     pushed=r["pushed_at"], archived=r["archived"], description=r.get("description") or "",
                     github=r["html_url"], name=p.get("name") or r["name"])
        except Exception as err:
            p.update(stars=None, licence="–", pushed=None, archived=False, description="", github=f"https://github.com/{p['repo']}",
                     name=p.get("name") or p["repo"].split("/")[1], error=str(err))
        return p

    with ThreadPoolExecutor(8) as pool:
        list(pool.map(repo, projects))
        for p, r in zip(projects + pages, pool.map(lambda p: probe(p.get("live")), projects + pages)):
            p["probe"] = r
    for s in d["sections"]:
        if s.get("projects"):
            first = [p for p in s["projects"] if p["repo"] == "sr-dash/status"]
            rest = sorted((p for p in s["projects"] if p["repo"] != "sr-dash/status"), key=lambda p: -(p.get("stars") or 0))
            s["projects"] = first + rest
    d["checked"] = NOW.strftime("%Y-%m-%dT%H:%M:%SZ")
    return d


def ago(t: str | None) -> str:
    if not t:
        return "–"
    days = (NOW - parse(t)).days
    return "today" if days < 1 else f"{days} days ago" if days < 60 else f"{days // 30} months ago" if days < 730 else f"{days // 365} years ago"


def fmt_stars(n) -> str:
    return "–" if n is None else f"{n / 1000:.1f}k" if n >= 1000 else str(n)


# ------------------------------------------------------------ Markdown
def badges(p) -> str:
    r = p["repo"]
    out = f"![Stars](https://img.shields.io/github/stars/{r}?style=flat&label=%E2%98%85) ![Last commit](https://img.shields.io/github/last-commit/{r}?style=flat&label=updated)"
    if p.get("live"):
        out += f" [![Live page](https://img.shields.io/website?url={p['live']}&label=live&up_message=up&down_message=down&style=flat)]({p['live']})"
    return out


def markdown(d: dict) -> str:
    lines = ["# Status pages", "",
             "Open-source status pages, sorted by how they run, with a live page for each where there is one, and the "
             "status pages of services that research software relies on. Stars, last commit and whether each live page is up "
             "come from [shields.io](https://shields.io), so they are always current; "
             "[the web version](https://sr-dash.github.io/status/directory/) also checks each page every hour.", "",
             "This list belongs to [sr-dash/status](https://github.com/sr-dash/status), a status page that runs on GitHub "
             "alone and sets itself up in a copy. Know one that is missing? "
             "[Suggest it](https://github.com/sr-dash/status/issues/new?template=directory.yml) or open a pull request "
             "that adds it to [`directory.yml`](directory.yml).", ""]
    lines += [f"- [{s['title']}](#{re.sub(r'[^a-z0-9 -]', '', s['title'].lower()).replace(' ', '-')})" for s in d["sections"]] + [""]
    for s in d["sections"]:
        lines += [f"## {s['title']}", "", " ".join(s["about"].split()), ""]
        if s.get("projects"):
            lines += ["| Project | How it runs | What it watches | |", "|---|---|---|---|"]
            for p in s["projects"]:
                name = f"**[{p['name']}]({p['github']})**" + (" (this project)" if p["repo"] == "sr-dash/status" else "")
                live = f"<br>[Live page]({p['live']})" if p.get("live") else ""
                lines.append(f"| {name}{live} | {p['how']} | {p['watches']} | {badges(p)} |")
        else:
            lines += ["| Service | What it covers | |", "|---|---|---|"]
            for p in s["pages"]:
                lines.append(f"| **[{p['name']}]({p['live']})** | {p['about']} | "
                             f"![Live page](https://img.shields.io/website?url={p['live']}&label=status%20page&up_message=up&down_message=down&style=flat) |")
        lines.append("")
    lines += ["---", "", "See also the much longer [awesome-status-pages](https://github.com/ivbeg/awesome-status-pages), "
              "which also lists hosted services and the status pages of major companies.", ""]
    return "\n".join(lines)


def readme_table(d: dict) -> str:
    s = next(s for s in d["sections"] if s["id"] == "github")
    rows = ["| | How it runs | What it watches | |", "|---|---|---|---|"]
    for p in s["projects"]:
        name = f"**[{p['name']}]({p['github']})**" + (" (this one)" if p["repo"] == "sr-dash/status" else "")
        rows.append(f"| {name} | {p['how']} | {p['watches']} | {badges(p)} |")
    return "\n".join(rows)


def write_markdown(d: dict) -> None:
    (ROOT / "DIRECTORY.md").write_text(markdown(d))
    readme = (ROOT / "README.md").read_text()
    new = re.sub(r"<!-- directory:start -->.*?<!-- directory:end -->",
                 lambda m: "<!-- directory:start -->\n" + readme_table(d) + "\n<!-- directory:end -->", readme, flags=re.S)
    (ROOT / "README.md").write_text(new)
    print("DIRECTORY.md and the README table written")


# ------------------------------------------------------------ web page
def live_cell(p) -> str:
    pr = p.get("probe") or {}
    if not p.get("live"):
        return '<span class="quiet">no live page</span>'
    ok = pr.get("code") == 200
    state = "Up" if ok else ("HTTP %s" % pr["code"] if pr.get("code") else "No answer")
    host = re.sub(r"^https?://", "", p["live"]).rstrip("/")
    return (f'<a href="{e(p["live"])}" class="live-link">{e(host)}</a>'
            f'<span class="chip c-{"ok" if ok else "fail"}">{state}</span>'
            + (f'<span class="ms">{pr["ms"]} ms</span>' if ok and pr.get("ms") is not None else ""))


def page(d: dict, cfg: dict) -> str:
    sections = []
    for s in d["sections"]:
        if s.get("projects"):
            rows = "".join(
                f'<tr class="dir-row{" ours" if p["repo"] == "sr-dash/status" else ""}" data-name="{e(p["name"].lower())}">'
                f'<th scope="row"><a href="{e(p["github"])}">{e(p["name"])}</a>'
                + ('<span class="tag">this project</span>' if p["repo"] == "sr-dash/status" else "")
                + (f'<span class="tag warnt">archived</span>' if p.get("archived") else "")
                + f'<span class="repo-path">{e(p["repo"])}</span></th>'
                f'<td>{e(p["how"])}<span class="watch">{e(p["watches"])}</span></td>'
                f'<td class="num" data-v="{p.get("stars") or 0}">★ {fmt_stars(p.get("stars"))}</td>'
                f'<td>{e(p.get("licence"))}</td>'
                f'<td class="num" data-v="{parse(p["pushed"]).timestamp() if p.get("pushed") else 0:.0f}">{ago(p.get("pushed"))}</td>'
                f'<td class="lv">{live_cell(p)}</td></tr>'
                for p in s["projects"])
            table = (f'<div class="table-wrap"><table class="checks dir"><caption class="sr">{e(s["title"])}</caption>'
                     f'<thead><tr><th scope="col">Project</th><th scope="col">How it runs · what it watches</th>'
                     f'<th scope="col"><button class="sort" type="button" data-col="2">Stars</button></th><th scope="col">Licence</th>'
                     f'<th scope="col"><button class="sort" type="button" data-col="4">Last push</button></th><th scope="col">Live page</th></tr></thead>'
                     f'<tbody>{rows}</tbody></table></div>')
        else:
            table = '<ul class="svc">' + "".join(
                f'<li class="svc-item" data-name="{e(p["name"].lower())}"><a href="{e(p["live"])}"><b>{e(p["name"])}</b></a>'
                f'<span class="quiet">{e(p["about"])}</span>{live_cell(p)}</li>' for p in s["pages"]) + "</ul>"
        up = sum(1 for p in s.get("projects", s.get("pages", [])) if (p.get("probe") or {}).get("code") == 200)
        n_live = sum(1 for p in s.get("projects", s.get("pages", [])) if p.get("live"))
        sections.append(f'<section class="panel dir-sec" id="{e(s["id"])}" aria-labelledby="h-{e(s["id"])}">'
                        f'<div class="panel-head"><h2 id="h-{e(s["id"])}" class="section-title">{e(s["title"])}</h2>'
                        f'<span class="quiet small">{up} of {n_live} live pages up</span></div>'
                        f'<p class="lead-in">{e(" ".join(s["about"].split()))}</p>{table}</section>')
    url = cfg["page"]["url"].rstrip("/") + "/directory/"
    n = sum(len(s.get("projects", [])) for s in d["sections"])
    ld = {"@context": "https://schema.org", "@type": "CollectionPage", "name": "Status pages: open-source projects and live examples",
          "url": url, "dateModified": d["checked"],
          "mainEntity": {"@type": "ItemList", "itemListElement": [
              {"@type": "ListItem", "position": i + 1, "item": {"@type": "SoftwareSourceCode", "name": p["name"],
                                                                  "codeRepository": p["github"], "description": p.get("description", "")}}
              for i, p in enumerate(p for s in d["sections"] for p in s.get("projects", []))]}}
    tpl = (WEB / "directory.html").read_text()
    for k, v in {"URL": e(url), "HOME": e(cfg["page"].get("home", "/")), "SITE_NAME": e(cfg["page"]["site_name"]),
                 "STATUS": e(cfg["page"]["url"]), "CHECKED": d["checked"], "N": str(n),
                 "ANALYTICS": (f'<script async src="https://www.googletagmanager.com/gtag/js?id={e(cfg["page"]["analytics"])}"></script>'
                               f"<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());"
                               f"gtag('config','{e(cfg['page']['analytics'])}');</script>") if cfg["page"].get("analytics") else "",
                 "FAVICON": f'<link rel="icon" type="image/png" sizes="32x32" href="{e(cfg["page"]["favicon"])}">' if cfg["page"].get("favicon") else "",
                 "LD": json.dumps(ld, ensure_ascii=False).replace("</", "<\\/"), "SECTIONS": "".join(sections),
                 "TOC": "".join(f'<a class="filter" href="#{e(s["id"])}">{e(s["title"])}</a>' for s in d["sections"]),
                 "OG": e(cfg["page"]["url"].rstrip("/") + "/og.png")}.items():
        tpl = tpl.replace("%%" + k + "%%", v)
    return tpl


def build(cfg: dict, out: Path) -> None:
    """The /directory/ page, for the hourly build."""
    d = gather()
    (out / "directory").mkdir(parents=True, exist_ok=True)
    (out / "directory" / "index.html").write_text(page(d, cfg))
    (out / "directory.json").write_text(json.dumps(d, indent=1, default=str))
    sm = out / "sitemap.xml"
    if sm.exists() and "/directory/" not in sm.read_text():
        url = cfg["page"]["url"].rstrip("/") + "/directory/"
        sm.write_text(sm.read_text().replace("</urlset>", f" <url><loc>{e(url)}</loc><lastmod>{d['checked'][:10]}</lastmod>"
                                                          f"<changefreq>daily</changefreq></url>\n</urlset>"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    if a.markdown:
        write_markdown(gather())
    if a.out:
        from collect import load_config
        build(load_config(ROOT / "status.config.yml"), a.out)


if __name__ == "__main__":
    main()
