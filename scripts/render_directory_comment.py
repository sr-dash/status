#!/usr/bin/env python3
"""Fill a directory comment template (.github/directory/*.md) from the check's JSON result.

    python3 scripts/render_directory_comment.py review result.json SHA          > comment.md
    python3 scripts/render_directory_comment.py merged AUTHOR "Name, Name"      > comment.md
    python3 scripts/render_directory_comment.py blocked "the reason"            > comment.md

Placeholders are written {{LIKE_THIS}}; the maintainer can reword the templates freely.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / ".github" / "directory"


def fill(name: str, values: dict) -> str:
    text = (TEMPLATES / f"{name}-comment.md").read_text()
    text = re.sub(r"\{\{([A-Z_]+)\}\}", lambda m: values.get(m.group(1), ""), text)
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def review(result_path: str, sha: str) -> str:
    r = json.loads(Path(result_path).read_text())
    ok = r.get("ok")
    previews = r.get("previews") or []
    if previews:
        blocks = []
        for p in previews:
            blocks.append(f"**{p['section']}**\n\n{p['header']}\n{p['row']}")
        preview = "\n\n".join(blocks)
    else:
        preview = "_No new or edited entry was found in `directory.yml`._"
    problems = ""
    if r.get("errors"):
        problems = "### To fix before review\n\n" + "\n".join(f"- [ ] {e}" for e in r["errors"]) + "\n"
    warnings = ""
    if r.get("warnings"):
        warnings = "### Worth a look\n\n" + "\n".join(f"- {w}" for w in r["warnings"]) + "\n"
    return fill("review", {
        "STATUS": "ready for review" if ok else "needs changes",
        "INTRO": ("Thanks for the contribution. The automatic checks passed; the maintainer will review it."
                  if ok else
                  "Thanks for the contribution. A few things need fixing before review; push the changes to this "
                  "branch and this comment updates."),
        "PREVIEW": preview,
        "PROBLEMS": problems,
        "WARNINGS": warnings,
        "CHECKED": "\n".join(f"- {n}" for n in r.get("notes") or ["Nothing to check."]),
        "SHA": sha[:7],
    })


def main(argv: list[str]) -> int:
    kind = argv[1] if len(argv) > 1 else ""
    if kind == "review" and len(argv) == 4:
        sys.stdout.write(review(argv[2], argv[3]))
    elif kind == "merged" and len(argv) == 4:
        sys.stdout.write(fill("merged", {"AUTHOR": re.sub(r"[^A-Za-z0-9-]", "", argv[2]), "NAMES": argv[3]}))
    elif kind == "blocked" and len(argv) == 3:
        sys.stdout.write(fill("blocked", {"REASON": argv[2]}))
    else:
        sys.exit(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
