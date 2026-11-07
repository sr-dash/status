"""The link-preview image (web/og.png, 1200 x 630) from status.config.yml:
the page title, the site name and the repositories it watches.

    python scripts/make_og.py
"""

from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent


def font(size, bold=False):
    names = (["IBMPlexSans-SemiBold.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"] if bold
             else ["IBMPlexSans-Regular.ttf", "Arial.ttf", "DejaVuSans.ttf"])
    for d in ["~/Library/Fonts", "/Library/Fonts", "/System/Library/Fonts/Supplemental", "/usr/share/fonts/truetype/dejavu"]:
        for n in names:
            p = Path(d).expanduser() / n
            if p.exists():
                return ImageFont.truetype(str(p), size)
    return ImageFont.load_default(size)


def main():
    cfg = yaml.safe_load((ROOT / "status.config.yml").read_text())
    pg, repos = cfg["page"], cfg["repos"]
    W, H = 1200, 630
    bg, ink, muted, rule = (23, 26, 30), (233, 234, 234), (139, 145, 152), (42, 47, 52)
    accent = tuple(int(pg.get("accent_dark", "#7aa9e3")[i:i + 2], 16) for i in (1, 3, 5))
    ok = (92, 201, 141)
    im = Image.new("RGB", (W, H), bg)
    g = ImageDraw.Draw(im)
    g.rectangle([0, 0, W, 8], fill=ok)
    g.ellipse([72, 92, 100, 120], fill=ok)
    g.ellipse([62, 82, 110, 130], outline=ok, width=3)
    g.text((128, 84), pg["site_name"].upper(), font=font(26, True), fill=muted)
    g.text((72, 150), pg["title"], font=font(84, True), fill=ink)
    g.text((72, 262), "Sites, deployments, scheduled workflows and data feeds,", font=font(32), fill=muted)
    n = cfg.get("check_every_hours", 1)
    g.text((72, 304), "checked every hour." if n == 1 else f"checked every {n:g} hours.", font=font(32), fill=muted)
    x, y = 72, 390
    for r in repos:
        name = r.get("name", r["repo"])
        w = g.textlength(name, font=font(28, True)) + 64
        if x + w > W - 72:
            x, y = 72, y + 66
        g.rounded_rectangle([x, y, x + w, y + 50], radius=25, fill=(28, 32, 37), outline=rule, width=2)
        g.ellipse([x + 20, y + 19, x + 32, y + 31], fill=ok)
        g.text((x + 44, y + 9), name, font=font(28, True), fill=ink)
        x += w + 14
    url = pg["url"].replace("https://", "").rstrip("/")
    g.text((72, H - 64), url, font=font(26), fill=accent)
    im.save(ROOT / "web" / "og.png", optimize=True)
    print("web/og.png")


if __name__ == "__main__":
    main()
