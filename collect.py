"""Collect the status of GitHub repositories, their sites and data feeds.

Reads status.config.yml; for each repository listed there it checks:

  - the site answers (its `url`);
  - the latest GitHub Pages deployment;
  - open pull requests;
  - every active workflow's latest run, and whether a scheduled one is overdue;
  - any data checks listed under `checks`:
      json_age   a timestamp (or date) in a JSON file is not too old;
      json_due   a "next update" timestamp in a JSON file has not long passed;
      custom     a function in custom_checks.py, for checks of your own.

Writes site/status.json and site/history.json (the last 14 days of checks,
read back from the published page so the state carries over between runs),
then renders the page (render.py). Alerts are decided by alert.py.

    GITHUB_TOKEN=... python collect.py --out site
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
UA = {"User-Agent": "github-status-page"}
NOW = datetime.now(timezone.utc)
RANK = {"ok": 0, "idle": 0, "running": 0, "unknown": 1, "warn": 1, "fail": 2}


# ------------------------------------------------------------ helpers
def get(url: str, token: bool = False, timeout: int = 60):
    h = dict(UA)
    tok = os.environ.get("STATUS_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token and tok:
        h["Authorization"] = "Bearer " + tok
        h["Accept"] = "application/vnd.github+json"
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
        return r.status, r.read()


def api(path: str):
    return json.loads(get("https://api.github.com/" + path, token=True)[1])


def jget(url: str):
    return json.loads(get(url + ("&" if "?" in url else "?") + f"t={int(time.time())}")[1])


def iso(t: datetime | None) -> str | None:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ") if t else None


def parse(s) -> datetime | None:
    """ISO times with or without Z or seconds, and plain dates (noon UTC)."""
    if not s:
        return None
    s = str(s).strip().replace("Z", "+00:00")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        s += "T12:00:00+00:00"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}\+00:00", s):
        s = s.replace("+00:00", ":00+00:00")
    t = datetime.fromisoformat(s)
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def hours(t: datetime | None) -> float | None:
    return round((NOW - t).total_seconds() / 3600, 1) if t else None


def pick(obj, path: str):
    """A value by dotted path with list indices: `dates[-1]`, `meta.generated`."""
    for part in re.findall(r"[^.\[\]]+|\[-?\d+\]", path):
        obj = obj[int(part[1:-1])] if part.startswith("[") else obj[part]
    return obj


def check(state: str, name: str, detail: str, link: str | None = None, when: str | None = None, kind: str = "") -> dict:
    return {"state": state, "name": name, "detail": detail, "link": link, "when": when, "kind": kind}


def fmt_h(h: float) -> str:
    return f"{h:g} h" if h < 72 else f"{h / 24:.0f} days"


def age_check(name, t, warn_h, fail_h, what, link, kind="data") -> dict:
    if t is None:
        return check("fail", name, f"{what}: not found", link, kind=kind)
    a = hours(t)
    state = "fail" if a > fail_h else "warn" if a > warn_h else "ok"
    return check(state, name, f"{what} {fmt_h(a)} ago (warning after {fmt_h(warn_h)}, alert after {fmt_h(fail_h)})", link, iso(t), kind)


# ------------------------------------------------------------ schedules
def period_h(cron: str) -> float:
    """How often a cron line fires, roughly: hourly, daily, weekly or monthly."""
    f = cron.split()
    if len(f) != 5:
        return 24.0
    minute, hour, dom, month, dow = f
    if hour == "*" or hour.startswith("*/"):
        return float(hour[2:]) if hour.startswith("*/") else 1.0
    if dom != "*":
        return 31 * 24.0
    if dow != "*":
        return 7 * 24.0
    return 24.0 / max(1, len(hour.split(",")))


def schedules(owner: str, repo: str, path: str) -> list[str]:
    try:
        text = get(f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{path}")[1].decode()
    except Exception:
        return []
    return re.findall(r"""^\s*-\s*cron:\s*["']([^"']+)["']""", text, re.M)


# ------------------------------------------------------------ standard checks
def up(url: str) -> dict:
    t0 = time.time()
    try:
        code = get(url + ("&" if "?" in url else "?") + f"t={int(t0)}", timeout=30)[0]
        ms = int((time.time() - t0) * 1000)
        c = check("ok" if code == 200 else "fail", "Site answers", f"HTTP {code} in {ms} ms", url, kind="site")
        c["ms"] = ms
        return c
    except urllib.error.HTTPError as e:
        return check("fail", "Site answers", f"HTTP {e.code}", url, kind="site")
    except Exception as e:
        return check("fail", "Site answers", f"No answer: {e}", url, kind="site")


def pages(owner: str, repo: str) -> dict:
    link = f"https://github.com/{owner}/{repo}/deployments/github-pages"
    dep = api(f"repos/{owner}/{repo}/deployments?environment=github-pages&per_page=1")
    if not dep:
        return check("idle", "Pages deployment", "No deployments", link, kind="pages")
    st = api(f"repos/{owner}/{repo}/deployments/{dep[0]['id']}/statuses?per_page=1")
    s = st[0]["state"] if st else "pending"
    t = parse(st[0]["created_at"] if st else dep[0]["created_at"])
    state = {"success": "ok", "in_progress": "running", "queued": "running", "pending": "running", "inactive": "warn"}.get(s, "fail")
    return check(state, "Pages deployment", f"{s.replace('_', ' ').capitalize()} {fmt_h(hours(t))} ago", link, iso(t), "pages")


def pulls(owner: str, repo: str) -> dict:
    link = f"https://github.com/{owner}/{repo}/pulls"
    prs = api(f"repos/{owner}/{repo}/pulls?state=open&per_page=20")
    if not prs:
        return check("ok", "Pull requests", "None open", link, kind="pulls")
    old = max(hours(parse(p["created_at"])) for p in prs)
    names = "; ".join(f"#{p['number']} {p['title'][:60]}" for p in prs[:3])
    return check("warn" if old > 48 else "ok", "Pull requests", f"{len(prs)} open, oldest {fmt_h(old)}: {names}", link, kind="pulls")


def workflows(owner: str, repo: str) -> list[dict]:
    out = []
    for w in api(f"repos/{owner}/{repo}/actions/workflows?per_page=50")["workflows"]:
        if w["path"].startswith("dynamic/") or w["state"] != "active":
            continue
        runs = api(f"repos/{owner}/{repo}/actions/workflows/{w['id']}/runs?per_page=10&exclude_pull_requests=true")["workflow_runs"]
        crons = schedules(owner, repo, w["path"])
        link = f"https://github.com/{owner}/{repo}/actions/workflows/{w['path'].rsplit('/', 1)[1]}"
        if not runs:
            out.append(check("idle", w["name"], "No runs yet" + (f" · cron {', '.join(crons)}" if crons else ""), link, kind="workflow"))
            continue
        last = runs[0]
        done = [r for r in runs if r["status"] == "completed"]
        lastdone = done[0] if done else None
        ok = next((r for r in done if r["conclusion"] == "success"), None)
        t = parse(last["created_at"])
        if last["status"] != "completed":
            state, detail = "running", f"Running for {fmt_h(hours(t))}"
        elif lastdone["conclusion"] in ("success", "skipped"):
            state, detail = "ok", "Succeeded"
        elif lastdone["conclusion"] == "cancelled":
            state, detail = ("warn" if crons else "ok"), "Last run was cancelled"
        elif lastdone["conclusion"] == "action_required":
            state, detail = "warn", "Waiting for approval to run"
        else:
            state, detail = "fail", f"Last run: {lastdone['conclusion']}"
            if ok:
                detail += f"; last success {fmt_h(hours(parse(ok['created_at'])))} ago"
        if crons:
            p = min(period_h(c) for c in crons)
            sched = [r for r in runs if r["event"] == "schedule"]
            ts = parse(sched[0]["created_at"]) if sched else None
            # GitHub starts scheduled runs late, by hours at busy times.
            if ts is None or hours(ts) > p * 1.25 + 4:
                if state == "ok":
                    state = "warn"
                detail += f"; no scheduled run for {fmt_h(hours(ts)) if ts else 'ever'} (every {fmt_h(p)})"
            detail += f" · cron {', '.join(crons)}"
        else:
            detail += " · run by hand"
        out.append(check(state, w["name"], detail, last["html_url"], iso(t), "workflow"))
    return out


# ------------------------------------------------------------ data checks
def data_check(c: dict, ctx: dict) -> list[dict]:
    kind, label = c["type"], c.get("label", "Data")
    try:
        if kind == "json_age":
            v = pick(jget(c["url"]), c["path"])
            return [age_check(label, parse(v), c.get("warn_hours", 48), c.get("fail_hours", 96), c.get("what", "Updated"), c["url"])]
        if kind == "json_due":
            j = jget(c["url"])
            due = parse(pick(j, c["path"]))
            late = (NOW - due).total_seconds() / 3600
            made = parse(pick(j, c["made_path"])) if c.get("made_path") else None
            state = "ok" if late < c.get("warn_hours", 48) else "warn" if late < c.get("fail_hours", 168) else "fail"
            detail = (f"Made {fmt_h(hours(made))} ago; " if made else "") + f"next update due {iso(due)[:10]}"
            detail += f", {fmt_h(late)} late" if late > 0 else ""
            return [check(state, label, detail, c["url"], iso(made) if made else None, "data")]
        if kind == "custom":
            mod = importlib.import_module("custom_checks")
            r = getattr(mod, c["function"])(ctx)
            return r if isinstance(r, list) else [r]
        return [check("unknown", label, f"Unknown check type {kind}", None, kind="data")]
    except Exception as e:
        return [check("fail", label if kind != "custom" else c["function"], f"Not readable: {type(e).__name__}: {e}", c.get("url"), kind="data")]


# ------------------------------------------------------------ setting itself up
def discover(owner: str, skip: str = "", limit: int = 12) -> list[dict]:
    """The owner's repositories worth watching: those with a GitHub Pages
    site, then those pushed to in the last 60 days; no forks or archives."""
    found = api(f"users/{owner}/repos?per_page=100&type=owner&sort=pushed")
    recent = NOW - timedelta(days=60)
    keep = [r for r in found if not r["fork"] and not r["archived"] and r["name"] != skip
            and (r.get("has_pages") or parse(r["pushed_at"]) > recent)]
    keep.sort(key=lambda r: (not r.get("has_pages"), -parse(r["pushed_at"]).timestamp()))
    out = []
    for r in keep[:limit]:
        url = None
        if r.get("has_pages"):
            try:
                url = api(f"repos/{owner}/{r['name']}/pages").get("html_url")
            except Exception:
                url = f"https://{owner.lower()}.github.io/{r['name']}/"
        out.append({"repo": r["name"], "name": r["name"], "url": url, "about": r.get("description") or ""})
    return out


def auto_config(cfg: dict, here: str, foreign: bool) -> dict:
    """The configuration for a copy of this repository, worked out from where
    it runs: its owner, its Pages address and the owner's repositories. In a
    copy (`foreign`), the original's page settings, analytics and own checks
    are left behind; with `repos: auto` in your own, only the list is found."""
    owner, name = here.split("/")
    try:
        url = api(f"repos/{here}/pages").get("html_url")
    except Exception:
        url = None
    url = url or f"https://{owner.lower()}.github.io/{name}/"
    cfg = dict(cfg)
    if foreign:
        cfg["page"] = {"title": "Status", "site_name": owner,
                       "description": f"Live status of {owner}'s GitHub repositories and the sites they publish: deployments, "
                                      f"scheduled workflows and pull requests, checked every hour.",
                       "url": url, "author": owner, "author_url": f"https://github.com/{owner}", "home": f"https://github.com/{owner}",
                       "accent": "#1f4e87", "accent_dark": "#7aa9e3"}
        cfg["alerts"] = {"enabled": True, "assignee": owner, "warn_after_checks": 3}
        cfg["check_every_hours"] = 1
    cfg["owner"] = owner
    cfg["repos"] = discover(owner, skip=name)
    cfg["_auto"] = True
    print(f"set up automatically for {here}: {len(cfg['repos'])} repositories, page {url}")
    return cfg


def load_config(path: Path) -> dict:
    """status.config.yml, or an automatic one when this runs in a copy of the
    repository it was written for (or when it says `repos: auto`)."""
    cfg = yaml.safe_load(path.read_text()) if path.exists() else {}
    here = os.environ.get("GITHUB_REPOSITORY", "")
    mine = (cfg.get("for_repository") or "").lower()
    foreign = bool(here and mine and here.lower() != mine) or not cfg.get("page")
    if here and (foreign or cfg.get("repos") in (None, "auto")):
        return auto_config(cfg, here, foreign)
    return cfg


def worst(checks: list[dict]) -> str:
    return ["ok", "warn", "fail"][max((RANK[c["state"]] for c in checks), default=0)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", type=Path, default=ROOT / "status.config.yml")
    ap.add_argument("--out", type=Path, default=ROOT / "site")
    ap.add_argument("--no-render", action="store_true")
    a = ap.parse_args()
    cfg = load_config(a.config)
    owner = cfg.get("owner") or os.environ.get("GITHUB_REPOSITORY_OWNER") or os.environ.get("GITHUB_REPOSITORY", "/").split("/")[0]
    page_url = cfg["page"]["url"].rstrip("/") + "/"
    sys.path.insert(0, str(ROOT))
    a.out.mkdir(parents=True, exist_ok=True)
    ctx = {"now": NOW, "check": check, "age_check": age_check, "jget": jget, "parse": parse, "hours": hours,
           "iso": iso, "fmt_h": fmt_h, "shared": {}}
    repos = []
    for r in cfg["repos"]:
        name, repo, url = r.get("name", r["repo"]), r["repo"], r.get("url")
        checks = [up(url)] if url else []
        for fn in (lambda: pages(owner, repo), lambda: pulls(owner, repo)):
            try:
                checks.append(fn())
            except Exception as e:
                checks.append(check("unknown", "GitHub", f"Not readable: {e}", f"https://github.com/{owner}/{repo}", kind="pages"))
        for c in r.get("checks", []):
            checks += data_check(c, ctx)
        try:
            checks += workflows(owner, repo)
        except Exception as e:
            checks.append(check("unknown", "Workflows", f"Not readable: {e}", f"https://github.com/{owner}/{repo}/actions", kind="workflow"))
        site = (url or "").rsplit("index.json", 1)[0] or None
        repos.append({"repo": repo, "name": name, "about": r.get("about", ""), "url": site,
                      "github": f"https://github.com/{owner}/{repo}", "state": worst(checks), "checks": checks})
    status = {"checked": iso(NOW), "every_h": cfg.get("check_every_hours", 1), "owner": owner,
              "source": os.environ.get("GITHUB_REPOSITORY") or cfg.get("for_repository"),
              "state": worst([c for r in repos for c in r["checks"]]), "repos": repos}
    (a.out / "status.json").write_text(json.dumps(status, indent=1))
    try:
        hist = jget(page_url + "history.json")
    except Exception:
        hist = []
    hist = [h for h in hist if parse(h["t"]) > NOW - timedelta(days=14)]
    ms = {r["repo"]: next((c["ms"] for c in r["checks"] if c.get("ms") is not None), None) for r in repos}
    hist.append({"t": iso(NOW), "state": status["state"], "repos": {r["repo"]: r["state"] for r in repos},
                 "ms": {k: v for k, v in ms.items() if v is not None},
                 "n": {s: sum(c["state"] == s for r in repos for c in r["checks"]) for s in ("ok", "warn", "fail")},
                 "bad": sorted(f"{r['repo']}|{c['name']}|{c['state']}" for r in repos for c in r["checks"] if c["state"] in ("warn", "fail"))})
    (a.out / "history.json").write_text(json.dumps(hist, separators=(",", ":")))
    bad = [(r["name"], c) for r in repos for c in r["checks"] if c["state"] in ("warn", "fail")]
    print(f"{status['state']}: {len(bad)} to look at")
    for n, c in bad:
        print(f"  {c['state']:4} {n}: {c['name']} — {c['detail']}")
    if not a.no_render:
        import render
        render.render(cfg, status, hist, a.out)


if __name__ == "__main__":
    sys.exit(main())
