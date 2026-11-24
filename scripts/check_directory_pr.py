#!/usr/bin/env python3
"""Check a pull request that adds or edits entries in directory.yml.

The workflows run this file from the main branch (never the pull request's copy), and read the
proposed directory.yml only as data. It checks that:

  - only directory.yml changes (DIRECTORY.md, the README table and the directory page are made
    from it after merging);
  - the sections themselves are unchanged and no existing entry is removed;
  - every new or edited entry has the fields its section needs, written as plain text;
  - nothing is listed twice;
  - every new or edited entry follows docs/directory-style-guide.md (plain text, sentence case,
    no full stop in table cells, no marketing words, no serial comma, no exclamation marks or emoji);
  - with --body: every required box in the pull request template is ticked;
  - with --network: the repository exists on GitHub and is not archived, and the live page answers.

    python3 scripts/check_directory_pr.py --base directory.yml --head proposed.yml \\
        --files changed-files.txt [--body pr-body.md] [--network] [--summary report.md] [--json result.json]

Exit status 0 when the pull request is ready for review, 1 when something needs fixing. The
report (Markdown) goes to standard output and, with --summary, to that file.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml

PROJECT_FIELDS = {"repo", "name", "live", "how", "watches", "note"}
PROJECT_REQUIRED = ("repo", "name", "how", "watches")
PAGE_FIELDS = {"name", "live", "about"}
PAGE_REQUIRED = ("name", "live", "about")
LIMITS = {"name": 60, "how": 120, "watches": 120, "about": 120, "note": 160}
REPO_RE = re.compile(r"^[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}$")
URL_RE = re.compile(r"^https://[A-Za-z0-9.-]+\.[A-Za-z]{2,}(:\d+)?(/[^\s<>\"'`|\[\]()]*)?$")
PLAIN_BAD = re.compile(r"[\[\]<>`|]|https?://|\]\(|\n")
UA = "sr-dash-status-directory-check"


def load(path: str) -> dict:
    text = Path(path).read_text() if path and Path(path).exists() else ""
    data = yaml.safe_load(text) if text.strip() else None
    if not isinstance(data, dict) or not isinstance(data.get("sections"), list):
        raise ValueError("directory.yml must keep its top-level `sections:` list")
    return data


def entries(data: dict) -> dict:
    """Every entry keyed by (section id, kind, identity)."""
    out = {}
    for s in data["sections"]:
        for kind in ("projects", "pages"):
            for p in s.get(kind) or []:
                if not isinstance(p, dict):
                    continue
                ident = p.get("repo") if kind == "projects" else p.get("live")
                out[(s.get("id"), kind, str(ident).lower().rstrip("/"))] = p
    return out


def shape(data: dict) -> list:
    return [(s.get("id"), s.get("title"), " ".join(str(s.get("about", "")).split()),
             "projects" in s, "pages" in s) for s in data["sections"]]


MARKETING = re.compile(r"\b(best|fastest|easiest|ultimate|powerful|amazing|awesome|revolutionary|blazing(ly)?|"
                       r"world[- ]class|seamless(ly)?|cutting[- ]edge|next[- ]gen(eration)?|game[- ]chang\w*|"
                       r"effortless(ly)?|robust|state[- ]of[- ]the[- ]art|beautiful|stunning|incredible|lightning)\b", re.I)
EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F]")
STYLE_GUIDE = "docs/directory-style-guide.md"
CELL_FIELDS = ("how", "watches", "about")   # table cells: no full stop
SENTENCE_FIELDS = ("note",)                 # a sentence: ends with a full stop


def short(item: str) -> str:
    """A checklist item as plain text, shortened."""
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", item)
    text = re.sub(r"[*`]", "", text)
    return text if len(text) <= 70 else text[:67].rstrip() + "..."


def check_text(errors: list, where: str, field: str, value, warnings: list | None = None) -> None:
    """Plain text that follows the style guide."""
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{where}: `{field}` must be a line of text")
        return
    if len(value) > LIMITS.get(field, 120):
        errors.append(f"{where}: `{field}` is {len(value)} characters; keep it under {LIMITS.get(field, 120)}")
    if PLAIN_BAD.search(value):
        errors.append(f"{where}: `{field}` should be plain text, without links, Markdown or HTML")
    if value != value.strip() or "  " in value:
        errors.append(f"{where}: `{field}` has extra spaces")
    if field == "name":
        return  # the project's own spelling is kept
    if not value[:1].isupper() and not value[:1].isdigit():
        errors.append(f"{where}: `{field}` should start with a capital letter")
    if field in CELL_FIELDS and value.rstrip().endswith((".", ";", ":", ",")):
        errors.append(f"{where}: `{field}` is a table cell, so it should not end with punctuation")
    if field in SENTENCE_FIELDS and not value.rstrip().endswith("."):
        errors.append(f"{where}: `{field}` is a sentence, so it should end with a full stop")
    if "!" in value:
        errors.append(f"{where}: `{field}` should not use exclamation marks")
    if EMOJI.search(value):
        errors.append(f"{where}: `{field}` should not use emoji")
    m = MARKETING.search(value)
    if m:
        errors.append(f"{where}: `{field}` uses a marketing word (\"{m.group(0)}\"); describe what it does instead")
    shout = [w for w in re.findall(r"\b[A-Z]{6,}\b", value)]
    if shout:
        errors.append(f"{where}: `{field}` has words in capitals ({', '.join(shout)}); keep capitals for short acronyms")
    if warnings is not None:
        if re.search(r",\s+(and|or)\s", value):
            warnings.append(f"{where}: `{field}` uses a serial comma (\", and\"); the directory writes \"A, B and C\"")
        if re.search(r"\b(e\.g\.|i\.e\.|etc\.?)", value):
            warnings.append(f"{where}: `{field}` uses an abbreviation (e.g., i.e., etc.); write it out or list the items")


def fetch(url: str, token: str | None = None, timeout: int = 25):
    headers = {"User-Agent": UA}
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(400000)
    except urllib.error.HTTPError as err:
        return err.code, b""
    except Exception as err:  # DNS, TLS, timeout
        return None, str(err).encode()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", required=True)
    ap.add_argument("--files", help="file with the changed paths, one per line")
    ap.add_argument("--network", action="store_true")
    ap.add_argument("--summary")
    ap.add_argument("--body", help="file with the pull request description, to check the template's checklist")
    ap.add_argument("--json", help="write the result as JSON (for the overview comment)")
    args = ap.parse_args(argv)
    errors, warnings, notes, previews, names = [], [], [], [], []

    if args.files:
        changed = [f.strip() for f in Path(args.files).read_text().splitlines() if f.strip()]
        others = [f for f in changed if f != "directory.yml"]
        if others:
            errors.append("Only `directory.yml` may change in a directory pull request. Please remove: "
                          + ", ".join(f"`{f}`" for f in others)
                          + ". DIRECTORY.md, the README table and the directory page are made from it after merging.")
        if "directory.yml" not in changed:
            errors.append("This pull request does not change `directory.yml`.")

    if args.body is not None:
        body = Path(args.body).read_text() if Path(args.body).exists() else ""
        boxes = re.findall(r"^\s*[-*]\s+\[( |x|X)\]\s+(.+?)\s*$", body, re.M)
        if "## Directory entry" not in body or not boxes:
            errors.append("The pull request description is not the directory template. Please replace it with "
                          "[the directory template](https://github.com/sr-dash/status/blob/main/.github/PULL_REQUEST_TEMPLATE/directory.md) "
                          "and tick each box.")
            boxes = []
        else:
            unticked = [t for mark, t in boxes if mark == " " and "(optional)" not in t.lower()]
            if unticked:
                errors.append("Please tick every box in the checklist once it is true: "
                              + "; ".join(f"\"{short(t)}\"" for t in unticked))

    try:
        base, head = load(args.base), load(args.head)
    except Exception as err:
        errors.append(f"`directory.yml` could not be read: {err}")
        return report(errors, warnings, notes, args.summary, [], args.json)

    if shape(base) != shape(head):
        errors.append("The sections (their ids, titles and descriptions) must stay as they are; only add or edit entries.")

    b, h = entries(base), entries(head)
    removed = [k for k in b if k not in h]
    if removed:
        errors.append("Existing entries cannot be removed in a contribution: "
                      + ", ".join(f"`{k[2]}`" for k in removed) + ". Open an issue if one should go.")
    changed = [k for k in h if k not in b or h[k] != b[k]]
    if not changed and not removed:
        errors.append("No directory entry was added or edited.")

    seen_repo, seen_live, seen_name = {}, {}, {}
    raw = [(s.get("id"), kind, (p.get("repo") if kind == "projects" else p.get("live")), p)
           for s in head["sections"] for kind in ("projects", "pages") for p in (s.get(kind) or []) if isinstance(p, dict)]
    for sid, kind, ident, p in raw:
        for key, store in ((p.get("repo"), seen_repo), (str(p.get("live") or "").lower().rstrip("/"), seen_live),
                           (f"{sid}:{str(p.get('name', '')).strip().lower()}", seen_name)):
            if key and key not in (":",):
                store.setdefault(str(key).lower(), []).append(ident)
    for label, store in (("repository", seen_repo), ("live page", seen_live), ("name in a section", seen_name)):
        for key, ids in store.items():
            if len(ids) > 1 and key:
                errors.append(f"The same {label} is listed more than once: `{key}`")

    token = os.environ.get("GITHUB_TOKEN")
    for key in changed:
        sid, kind, ident = key
        p = h[key]
        where = f"`{p.get('name') or ident}` ({sid})"
        allowed, required = (PROJECT_FIELDS, PROJECT_REQUIRED) if kind == "projects" else (PAGE_FIELDS, PAGE_REQUIRED)
        extra = set(p) - allowed
        if extra:
            errors.append(f"{where}: unknown field(s) " + ", ".join(f"`{x}`" for x in sorted(extra))
                          + "; use " + ", ".join(f"`{x}`" for x in sorted(allowed)))
        for f in required:
            if f not in p:
                errors.append(f"{where}: `{f}` is required")
        for f in ("name", "how", "watches", "about", "note"):
            if f in p:
                check_text(errors, where, f, p[f], warnings)
        if kind == "projects" and "repo" in p and not REPO_RE.match(str(p["repo"])):
            errors.append(f"{where}: `repo` should be `owner/name` on GitHub")
        if p.get("live") is not None and not URL_RE.match(str(p["live"])):
            errors.append(f"{where}: `live` should be one https:// address")
        notes.append(f"{'New' if key not in b else 'Edited'}: {where}")
        previews.append(preview(sid, kind, p, head))
        names.append(md(p.get("name") or ident))

        if not args.network:
            continue
        if kind == "projects" and REPO_RE.match(str(p.get("repo", ""))):
            code, body = fetch(f"https://api.github.com/repos/{p['repo']}", token)
            if code == 404:
                errors.append(f"{where}: the repository `{p['repo']}` was not found on GitHub")
            elif code == 200:
                r = json.loads(body)
                if r.get("private"):
                    errors.append(f"{where}: the repository is private")
                if r.get("archived"):
                    errors.append(f"{where}: the repository is archived")
                if r.get("fork"):
                    warnings.append(f"{where}: the repository is a fork; list the original unless the fork is the maintained one")
                if not r.get("license"):
                    warnings.append(f"{where}: the repository has no licence file, so it may not be open source")
                notes.append(f"{where}: {r.get('stargazers_count', 0)} stars, last push {str(r.get('pushed_at', ''))[:10]}, "
                             f"licence {((r.get('license') or {}).get('spdx_id')) or 'none'}")
            else:
                warnings.append(f"{where}: GitHub did not answer ({code}); the repository was not checked")
        if p.get("live") and URL_RE.match(str(p["live"])):
            code, body = fetch(str(p["live"]))
            if code is not None and 200 <= code < 400:
                notes.append(f"{where}: the live page answers ({code})")
            elif code in (404, 410) or (code is None and re.search(rb"Name or service not known|nodename nor servname|getaddrinfo", body)):
                errors.append(f"{where}: the live page is gone ({code or 'unknown host'})")
            else:
                warnings.append(f"{where}: the live page did not answer the check ({code or body.decode()[:80]}); it may block automated requests")

    return report(errors, warnings, notes, args.summary, previews, args.json, names)


def md(value) -> str:
    """Contributor text made inert for a Markdown comment (no links, images, mentions or HTML)."""
    text = " ".join(str(value if value is not None else "").split())[:200]
    text = re.sub(r"([\\`*_\[\]()<>#!|~])", r"\\\1", text)
    return text.replace("@", "@\u200b")


def preview(sid, kind, p, data) -> dict:
    """How the entry will look in DIRECTORY.md (contributor text escaped)."""
    title = next((s.get("title") for s in data["sections"] if s.get("id") == sid), sid)
    live_ok = bool(p.get("live")) and bool(URL_RE.match(str(p.get("live"))))
    if kind == "projects":
        repo = str(p.get("repo", ""))
        name = f"**[{md(p.get('name'))}](https://github.com/{repo})**" if REPO_RE.match(repo) else f"**{md(p.get('name'))}**"
        live = f"<br>[Live page]({p['live']})" if live_ok else (f"<br>Live page: {md(p.get('live'))}" if p.get("live") else "")
        return {"section": md(title), "kind": kind, "header": "| Project | How it runs | What it watches |\n|---|---|---|",
                "row": f"| {name}{live} | {md(p.get('how'))} | {md(p.get('watches'))} |"}
    name = f"**[{md(p.get('name'))}]({p['live']})**" if live_ok else f"**{md(p.get('name'))}**"
    return {"section": md(title), "kind": kind, "header": "| Status page | What it covers |\n|---|---|",
            "row": f"| {name} | {md(p.get('about'))} |"}


def report(errors, warnings, notes, summary_path, previews=(), json_path=None, names=()) -> int:
    lines = ["## Directory check", ""]
    if errors:
        lines += ["**Needs changes before review.**", ""] + [f"- ❌ {e}" for e in errors] + [""]
    else:
        lines += ["**Ready for review.** Once the maintainer approves it, it is merged and the directory is "
                  "updated automatically.", ""]
    if warnings:
        lines += ["Worth a look:", ""] + [f"- ⚠️ {w}" for w in warnings] + [""]
    if notes:
        lines += ["Checked:", ""] + [f"- {n}" for n in notes] + [""]
    text = "\n".join(lines)
    print(text)
    if summary_path:
        Path(summary_path).write_text(text)
    if json_path:
        Path(json_path).write_text(json.dumps({"ok": not errors, "errors": errors, "warnings": warnings,
                                               "notes": notes, "previews": list(previews),
                                               "names": list(names)}, indent=1))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
