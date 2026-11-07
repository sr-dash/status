"""Email alerts through one GitHub issue, from site/status.json and history.json.

A failure alerts at once; a warning once it has held for three checks in a
row, so a brief lag does not. While anything is wrong one issue labelled
`status-alert` stays open and assigned to the owner: it is opened with the
list, each new problem adds a comment, and it is closed with a comment when
all is clear. GitHub emails the owner each time (new issue, comment, close).
Needs the gh CLI and GH_TOKEN.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

CFG = yaml.safe_load((Path(__file__).resolve().parent / "status.config.yml").read_text())
REPO = os.environ.get("GITHUB_REPOSITORY", "")               # the repository this runs in
OWNER = CFG.get("alerts", {}).get("assignee") or CFG.get("owner") or REPO.split("/")[0]
DASH = CFG["page"]["url"].rstrip("/") + "/"
LABEL = "status-alert"
HOLD = int(CFG.get("alerts", {}).get("warn_after_checks", 3))


def gh(*args, input=None):
    return subprocess.run(["gh", *args], input=input, capture_output=True, text=True, check=True).stdout


def main(site: Path = Path("site")) -> None:
    if not CFG.get("alerts", {}).get("enabled", True):
        print("alerts are off in status.config.yml")
        return
    # The label, made once; harmless if it is already there.
    subprocess.run(["gh", "label", "create", LABEL, "-R", REPO, "--color", "b3261e",
                    "--description", "Something in the sites or pipelines needs a look"], capture_output=True)
    status = json.loads((site / "status.json").read_text())
    hist = json.loads((site / "history.json").read_text())
    recent = [set(h.get("bad", [])) for h in hist[-HOLD:]]
    held = set.intersection(*recent) if len(recent) == HOLD else set()
    problems = {}
    for r in status["repos"]:
        for c in r["checks"]:
            key = f"{r['repo']}|{c['name']}|{c['state']}"
            if c["state"] == "fail" or (c["state"] == "warn" and key in held):
                problems[key] = (r["name"], c)
    issues = json.loads(gh("issue", "list", "-R", REPO, "--label", LABEL, "--state", "open", "--json", "number,body"))
    issue = issues[0] if issues else None

    def lines(keys):
        out = []
        for k in sorted(keys):
            name, c = problems[k]
            mark = "🔴" if c["state"] == "fail" else "🟡"
            link = f" ([link]({c['link']}))" if c.get("link") else ""
            out.append(f"- {mark} **{name}**: {c['name']}: {c['detail']}{link}")
        return "\n".join(out)

    marker = lambda keys: "<!-- keys: " + json.dumps(sorted(keys)) + " -->"
    if problems and not issue:
        body = (f"Checked {status['checked']}. [Open the dashboard]({DASH}).\n\n{lines(problems)}\n\n"
                f"This issue closes itself when all is clear.\n\n{marker(problems)}")
        gh("issue", "create", "-R", REPO, "--title", f"Status: {len(problems)} to look at", "--label", LABEL,
           "--assignee", OWNER, "--body-file", "-", input=body)
        print(f"opened an alert with {len(problems)} problems")
    elif problems and issue:
        m = re.search(r"<!-- keys: (.*?) -->", issue["body"] or "")
        known = set(json.loads(m.group(1))) if m else set()
        new = set(problems) - known
        if new:
            gh("issue", "comment", str(issue["number"]), "-R", REPO, "--body-file", "-",
               input=f"New since the last alert ({status['checked']}):\n\n{lines(new)}\n\n[Dashboard]({DASH})")
        body = (f"Checked {status['checked']}. [Open the dashboard]({DASH}).\n\n{lines(problems)}\n\n"
                f"This issue closes itself when all is clear.\n\n{marker(problems)}")
        gh("issue", "edit", str(issue["number"]), "-R", REPO, "--title", f"Status: {len(problems)} to look at", "--body-file", "-", input=body)
        print(f"alert #{issue['number']} updated; {len(new)} new")
    elif issue:
        gh("issue", "close", str(issue["number"]), "-R", REPO, "--comment", f"All clear at {status['checked']}. [Dashboard]({DASH})")
        print(f"alert #{issue['number']} closed: all clear")
    else:
        print("all clear; no alert open")


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("site")))
