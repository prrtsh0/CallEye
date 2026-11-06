"""Generate the 1200x630 Open Graph preview image in the CallEye brand style
(navy background, doodle, name). Writes site/assets/og-image.png."""
from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "site" / "assets"
OUT = OUT_DIR / "og-image.png"

W, H = 1200, 630


def _font(size: int):
    import os  # noqa: PLC0415  (stdlib, used only here)
    candidates = [
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for p in candidates:
        if os.path.exists(p):
            from PIL import ImageFont  # noqa: PLC0415
            return ImageFont.truetype(p, size)
    from PIL import ImageFont  # noqa: PLC0415
    return ImageFont.load_default()


def main() -> int:
    try:
        from PIL import Image, ImageDraw  # noqa: PLC0415
    except Exception as e:  # pragma: no cover
        print("Pillow not available:", e)
        return 1

    navy = (9, 31, 64)
    blue = (31, 95, 224)
    white = (255, 255, 255)
    muted = (200, 210, 224)

    img = Image.new("RGB", (W, H), navy)
    d = ImageDraw.Draw(img)

    # corner washes
    d.ellipse([800, -300, 1500, 400], fill=(13, 43, 87))
    d.ellipse([-350, -150, 250, 450], fill=(18, 56, 110))

    # doodle: simple phone
    d.rounded_rectangle([900, 180, 1060, 470], radius=36, outline=blue, width=8)
    d.rounded_rectangle([920, 210, 1040, 360], radius=20, outline=muted, width=4)
    d.ellipse([962, 420, 998, 456], fill=white)
    for i in range(3):
        y = 235 + i * 40
        d.line([940, y, 1010, y], fill=muted, width=6)

    # text
    title_f = _font(88)
    sub_f = _font(40)
    tag_f = _font(30)

    d.text((90, 170), "CallEye", font=title_f, fill=white)
    d.text((92, 310), "Slow the scam down.", font=sub_f, fill=blue)
    d.text((92, 420), "A calm, honest pressure-call reader.", font=tag_f, fill=muted)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    img.save(OUT)
    print("Wrote", OUT, img.size)
    return 0


if __name__ == "__main__":
    sys.exit(main())
