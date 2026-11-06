"""Status of the sites and their pipelines, for the dashboard and the alerts.

For each repository: every workflow's latest run and whether a scheduled one
is overdue, the latest GitHub Pages deployment, and whether the site answers.
For each data feed: how fresh it is against what its schedule promises.

    GITHUB_TOKEN=... python collect.py --out site

writes site/status.json (the dashboard's data) and site/history.json (the
overall state of the last 14 days of runs). The previous files are read back
from the published site, so the state carries over without a database.
Exit code 0 always; alerts are decided from status.json by alert.py.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

OWNER = "sr-dash"
SITE = "https://sr-dash.github.io/status/"
UA = {"User-Agent": "sr-dash-status"}
NOW = datetime.now(timezone.utc)

# The repositories with a live site or a scheduled pipeline, in the order shown.
REPOS = [
    ("heliofield", "HelioField", "https://sr-dash.github.io/heliofield/"),
    ("heliofield-imagery", "HelioField imagery", "https://sr-dash.github.io/heliofield-imagery/index.json"),
    ("heliofield-movies", "HelioField movies", "https://sr-dash.github.io/heliofield-movies/"),
    ("heliofleet", "HelioFleet", "https://sr-dash.github.io/heliofleet/"),
    ("cryonirsp-viewer", "CryoNIRSP Viewer", "https://sr-dash.github.io/cryonirsp-viewer/"),
    ("sr-dash.github.io", "Homepage", "https://sr-dash.github.io/"),
]


def get(url: str, token: bool = False, timeout: int = 60):
    h = dict(UA)
    if token and os.environ.get("GITHUB_TOKEN"):
        h["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
        h["Accept"] = "application/vnd.github+json"
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
        return r.status, r.read()


def api(path: str):
    return json.loads(get("https://api.github.com/" + path, token=True)[1])


def jget(url: str):
    return json.loads(get(url + ("&" if "?" in url else "?") + f"t={int(time.time())}")[1])


def iso(t: datetime | None) -> str | None:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ") if t else None


def parse(s: str | None) -> datetime | None:
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def hours(t: datetime | None) -> float | None:
    return round((NOW - t).total_seconds() / 3600, 1) if t else None


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


def schedules(repo: str, path: str) -> list[str]:
    try:
        text = get(f"https://raw.githubusercontent.com/{OWNER}/{repo}/HEAD/{path}")[1].decode()
    except Exception:
        return []
    return re.findall(r"""^\s*-\s*cron:\s*["']([^"']+)["']""", text, re.M)


# ------------------------------------------------------------ checks
def check(state: str, name: str, detail: str, link: str | None = None, when: str | None = None, kind: str = "") -> dict:
    return {"state": state, "name": name, "detail": detail, "link": link, "when": when, "kind": kind}


def workflows(repo: str) -> list[dict]:
    out = []
    for w in api(f"repos/{OWNER}/{repo}/actions/workflows?per_page=50")["workflows"]:
        if w["path"].startswith("dynamic/") or w["state"] != "active":
            continue
        runs = api(f"repos/{OWNER}/{repo}/actions/workflows/{w['id']}/runs?per_page=10&exclude_pull_requests=true")["workflow_runs"]
        crons = schedules(repo, w["path"])
        link = f"https://github.com/{OWNER}/{repo}/actions/workflows/{w['path'].rsplit('/', 1)[1]}"
        if not runs:
            out.append(check("idle", w["name"], "No runs yet" + (f"; scheduled {', '.join(crons)}" if crons else ""), link, kind="workflow"))
            continue
        last = runs[0]
        done = [r for r in runs if r["status"] == "completed"]
        lastdone = done[0] if done else None
        ok = next((r for r in done if r["conclusion"] == "success"), None)
        t = parse(last["created_at"])
        if last["status"] != "completed":
            state, detail = "running", f"Running since {hours(t)} h ago"
        elif lastdone["conclusion"] in ("success", "skipped"):
            state, detail = "ok", "Succeeded"
        elif lastdone["conclusion"] == "cancelled":
            state, detail = ("warn" if crons else "ok"), "Last run was cancelled"
        elif lastdone["conclusion"] == "action_required":
            state, detail = "warn", "Waiting for your approval to run"
        else:
            state, detail = "fail", f"Last run {lastdone['conclusion']}"
            if ok:
                detail += f"; last success {hours(parse(ok['created_at']))} h ago"
        if crons:
            p = min(period_h(c) for c in crons)
            sched = [r for r in runs if r["event"] == "schedule"]
            ts = parse(sched[0]["created_at"]) if sched else None
            # GitHub starts scheduled runs late, by hours at busy times.
            if ts is None or hours(ts) > p * 1.25 + 4:
                if state == "ok":
                    state = "warn"
                detail += f"; no scheduled run for {hours(ts) if ts else 'ever'} h (every {p:g} h)"
            detail += f" · {', '.join(crons)}"
        else:
            detail += " · run by hand"
        out.append(check(state, w["name"], detail, last["html_url"], iso(t), "workflow"))
    return out


def pulls(repo: str) -> dict:
    """Open pull requests, such as a monthly data update waiting to be merged."""
    link = f"https://github.com/{OWNER}/{repo}/pulls"
    prs = api(f"repos/{OWNER}/{repo}/pulls?state=open&per_page=20")
    if not prs:
        return check("ok", "Pull requests", "None open", link, kind="pulls")
    old = max(hours(parse(p["created_at"])) for p in prs)
    names = "; ".join(f"#{p['number']} {p['title'][:60]}" for p in prs[:3])
    return check("warn" if old > 48 else "ok", "Pull requests", f"{len(prs)} open, oldest {old:g} h: {names}", link, kind="pulls")


def pages(repo: str) -> dict:
    link = f"https://github.com/{OWNER}/{repo}/deployments/github-pages"
    try:
        dep = api(f"repos/{OWNER}/{repo}/deployments?environment=github-pages&per_page=1")
    except Exception as e:
        return check("unknown", "Pages deployment", f"Not readable: {e}", link, kind="pages")
    if not dep:
        return check("unknown", "Pages deployment", "No deployments", link, kind="pages")
    st = api(f"repos/{OWNER}/{repo}/deployments/{dep[0]['id']}/statuses?per_page=1")
    s = st[0]["state"] if st else "pending"
    t = parse(st[0]["created_at"] if st else dep[0]["created_at"])
    state = {"success": "ok", "in_progress": "running", "queued": "running", "pending": "running"}.get(s, "fail")
    if state == "fail":
        # A later successful deployment of an older commit still serves the site.
        state = "warn" if s in ("inactive",) else "fail"
    return check(state, "Pages deployment", f"{s} {hours(t)} h ago", link, iso(t), "pages")


def up(url: str) -> dict:
    t0 = time.time()
    try:
        code = get(url + ("&" if "?" in url else "?") + f"t={int(t0)}", timeout=30)[0]
        ms = int((time.time() - t0) * 1000)
        return check("ok" if code == 200 else "fail", "Site answers", f"HTTP {code} in {ms} ms", url, kind="site")
    except urllib.error.HTTPError as e:
        return check("fail", "Site answers", f"HTTP {e.code}", url, kind="site")
    except Exception as e:
        return check("fail", "Site answers", f"No answer: {e}", url, kind="site")


def age_check(name, t: datetime | None, warn_h, fail_h, what, link) -> dict:
    if t is None:
        return check("fail", name, f"{what}: not found", link, kind="data")
    a = hours(t)
    state = "fail" if a > fail_h else "warn" if a > warn_h else "ok"
    return check(state, name, f"{what} {a:g} h old (warn {warn_h:g} h, alert {fail_h:g} h)", link, iso(t), "data")


def data_checks() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {r[0]: [] for r in REPOS}
    hf = "https://sr-dash.github.io/heliofield/data/"
    img = "https://sr-dash.github.io/heliofield-imagery/"
    field_last = None
    try:
        dates = jget(hf + "index.json")["dates"]
        field_last = dates[-1]
        meta = jget(hf + f"{field_last}/meta.json")
        t = parse(meta["obstime"])
        out["heliofield"].append(age_check("Daily field product", t, 34, 58, f"Latest map {field_last} {meta['obstime'][11:16]} UTC", hf + "index.json"))
    except Exception as e:
        out["heliofield"].append(check("fail", "Daily field product", f"Not readable: {e}", hf + "index.json", kind="data"))
    try:
        idates = jget(img + "index.json")["dates"]
        last = idates[-1]
        day = jget(img + f"days/{last}/index.json")
        ids = {p["id"] for p in day["panels"]}
        aia = sum(i.startswith("aia") for i in ids)
        lag = (datetime.fromisoformat(field_last) - datetime.fromisoformat(last)).days if field_last else 0
        state = "ok" if lag <= 0 else "warn"
        if lag > 1:
            state = "fail"
        detail = f"Latest day {last}: {len(ids)} panels, {aia} of 8 AIA" + (f"; {lag} day(s) behind HelioField" if lag > 0 else "; level with HelioField")
        if aia < 8 or "hmi" not in ids:
            state = "fail" if aia == 0 else max(state, "warn", key=["ok", "warn", "fail"].index)
        out["heliofield-imagery"].append(check(state, "Images for the latest day", detail, img + f"days/{last}/index.json", kind="data"))
        inc = []
        for d in idates[-7:]:
            j = jget(img + f"days/{d}/index.json")
            if j.get("incomplete"):
                inc.append(f"{d} ({', '.join(j['incomplete'])})")
        out["heliofield-imagery"].append(check("warn" if inc else "ok", "Panels to retry",
                                               "; ".join(inc) if inc else "None in the last 7 days", img + "index.json", kind="data"))
    except Exception as e:
        out["heliofield-imagery"].append(check("fail", "Images for the latest day", f"Not readable: {e}", img + "index.json", kind="data"))
    try:
        m = jget("https://sr-dash.github.io/heliofield-movies/movies.json")
        t = parse(m["made"].replace("Z", ":00Z") if len(m["made"]) == 17 else m["made"])
        out["heliofield-movies"].append(age_check("Movies", t, 40 * 24, 70 * 24, f"Through CR {m['rotations'][1]}, made", "https://sr-dash.github.io/heliofield-movies/"))
    except Exception as e:
        out["heliofield-movies"].append(check("fail", "Movies", f"Not readable: {e}", "https://sr-dash.github.io/heliofield-movies/", kind="data"))
    try:
        man = jget("https://sr-dash.github.io/heliofleet/data/manifest.json")
        nxt = parse(man["next_update"])
        a = hours(parse(man["generated"]))
        late = (NOW - nxt).total_seconds() / 3600
        state = "ok" if late < 48 else "warn" if late < 24 * 7 else "fail"
        out["heliofleet"].append(check(state, "Ephemerides", f"Made {a:g} h ago; next update due {man['next_update'][:10]}" + (f", {late:.0f} h late" if late > 0 else ""),
                                       "https://sr-dash.github.io/heliofleet/data/manifest.json", man["generated"], "data"))
        obs = jget("https://sr-dash.github.io/heliofleet/data/obs/index.json")
        out["heliofleet"].append(age_check("Observation lists", parse(obs["generated"]), 35 * 24, 60 * 24, "Made", "https://sr-dash.github.io/heliofleet/data/obs/index.json"))
    except Exception as e:
        out["heliofleet"].append(check("fail", "Ephemerides", f"Not readable: {e}", "https://sr-dash.github.io/heliofleet/", kind="data"))
    try:
        inv = jget("https://sr-dash.github.io/cryonirsp-viewer/data/cryonirsp_dataset_details.json")
        c = age_check("Dataset inventory", parse(inv["generated_at"]), 35 * 24, 65 * 24, f"Media through {inv.get('media_through')}; made",
                      "https://sr-dash.github.io/cryonirsp-viewer/data/cryonirsp_dataset_details.json")
        out["cryonirsp-viewer"].append(c)
    except Exception as e:
        out["cryonirsp-viewer"].append(check("fail", "Dataset inventory", f"Not readable: {e}", "https://sr-dash.github.io/cryonirsp-viewer/", kind="data"))
    return out


RANK = {"ok": 0, "idle": 0, "running": 0, "unknown": 1, "warn": 1, "fail": 2}


def worst(checks: list[dict]) -> str:
    r = max((RANK[c["state"]] for c in checks), default=0)
    return ["ok", "warn", "fail"][r]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=Path("site"))
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    data = data_checks()
    repos = []
    for repo, name, url in REPOS:
        checks = [up(url), pages(repo)] + data.get(repo, [])
        try:
            checks.append(pulls(repo))
        except Exception as e:
            checks.append(check("unknown", "Pull requests", f"Not readable: {e}", f"https://github.com/{OWNER}/{repo}/pulls", kind="pulls"))
        try:
            checks += workflows(repo)
        except Exception as e:
            checks.append(check("unknown", "Workflows", f"Not readable: {e}", f"https://github.com/{OWNER}/{repo}/actions", kind="workflow"))
        repos.append({"repo": repo, "name": name, "url": url.rsplit("index.json", 1)[0],
                      "github": f"https://github.com/{OWNER}/{repo}", "state": worst(checks), "checks": checks})
    status = {"checked": iso(NOW), "state": worst([c for r in repos for c in r["checks"]]), "repos": repos}
    (a.out / "status.json").write_text(json.dumps(status, indent=1))
    try:
        hist = jget(SITE + "history.json")
    except Exception:
        hist = []
    hist = [h for h in hist if parse(h["t"]) > NOW - timedelta(days=14)]
    hist.append({"t": iso(NOW), "state": status["state"],
                 "repos": {r["repo"]: r["state"] for r in repos},
                 "bad": sorted(f"{r['repo']}|{c['name']}|{c['state']}" for r in repos for c in r["checks"] if c["state"] in ("warn", "fail"))})
    (a.out / "history.json").write_text(json.dumps(hist, separators=(",", ":")))
    bad = [(r["name"], c) for r in repos for c in r["checks"] if c["state"] in ("warn", "fail")]
    print(f"{status['state']}: {len(bad)} to look at")
    for n, c in bad:
        print(f"  {c['state']:4} {n}: {c['name']} — {c['detail']}")


if __name__ == "__main__":
    sys.exit(main())
