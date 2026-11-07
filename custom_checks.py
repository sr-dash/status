"""Checks of your own, called from status.config.yml with
`type: custom` and `function: <name>`. Each function takes the context dict
(helpers: check, age_check, jget, parse, hours, iso, fmt_h, now, and `shared`
for passing values between checks) and returns a check or a list of them.

These are the ones for HelioField; a copy of this repository can delete them.
"""

FIELD = "https://sr-dash.github.io/heliofield/data/"
IMG = "https://sr-dash.github.io/heliofield-imagery/"


def heliofield_product(ctx):
    """The daily PFSS product: its map time, against a nightly schedule."""
    dates = ctx["jget"](FIELD + "index.json")["dates"]
    last = dates[-1]
    ctx["shared"]["field_last"] = last
    meta = ctx["jget"](FIELD + f"{last}/meta.json")
    return ctx["age_check"]("Daily field product", ctx["parse"](meta["obstime"]), 34, 58,
                            f"Latest map {last} {meta['obstime'][11:16]} UTC, taken", FIELD + "index.json")


def imagery_latest(ctx):
    """The latest day of images: complete, and level with HelioField."""
    check, jget = ctx["check"], ctx["jget"]
    dates = jget(IMG + "index.json")["dates"]
    ctx["shared"]["img_dates"] = dates
    last = dates[-1]
    day = jget(IMG + f"days/{last}/index.json")
    ids = {p["id"] for p in day["panels"]}
    aia = sum(i.startswith("aia") for i in ids)
    field_last = ctx["shared"].get("field_last")
    lag = (ctx["parse"](field_last) - ctx["parse"](last)).days if field_last else 0
    state = "ok" if lag <= 0 else "warn" if lag == 1 else "fail"
    detail = f"Latest day {last}: {len(ids)} panels, {aia} of 8 AIA" + (f"; {lag} day(s) behind HelioField" if lag > 0 else "; level with HelioField")
    if aia == 0:
        state = "fail"
    elif (aia < 8 or "hmi" not in ids) and state == "ok":
        state = "warn"
    return check(state, "Images for the latest day", detail, IMG + f"days/{last}/index.json", kind="data")


def imagery_retries(ctx):
    """Panels lost to an archive that did not answer, waiting to be retried."""
    check, jget = ctx["check"], ctx["jget"]
    dates = ctx["shared"].get("img_dates") or jget(IMG + "index.json")["dates"]
    inc = []
    for d in dates[-7:]:
        j = jget(IMG + f"days/{d}/index.json")
        if j.get("incomplete"):
            inc.append(f"{d} ({', '.join(j['incomplete'])})")
    return check("warn" if inc else "ok", "Panels to retry", "; ".join(inc) if inc else "None in the last 7 days", IMG + "index.json", kind="data")
