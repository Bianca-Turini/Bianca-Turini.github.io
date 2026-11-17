#!/usr/bin/env python3
"""Draw the "BiT" favicon (BIanca Turini) as PNGs with optically equal letter gaps.

    python3 tools/make_favicon.py [font-key]          # writes assets/favicon-*.png
    python3 tools/make_favicon.py --compare OUT.html   # side-by-side font comparison

Letters are rasterised here (not live SVG text), so the icon looks the same on
every device regardless of which fonts the visitor has installed.
"""
import base64
import io
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
SYS = "/System/Library/Fonts/"
SUP = "/System/Library/Fonts/Supplemental/"

# key: (label, font file, face name to pick inside a .ttc)
FONTS = {
    "helvetica": ("Helvetica Neue (current)", SYS + "HelveticaNeue.ttc", "Bold"),
    "georgia":   ("Georgia", SUP + "Georgia Bold.ttf", None),
    "didot":     ("Didot", SUP + "Didot.ttc", "Bold"),
    "times":     ("Times", SUP + "Times New Roman Bold.ttf", None),
    "menlo":     ("Menlo (mono)", SYS + "Menlo.ttc", "Bold"),
    "futura":    ("Futura", SUP + "Futura.ttc", "Bold"),
    "avenir":    ("Avenir Next", SYS + "Avenir Next.ttc", "Bold"),
    "baskerville": ("Baskerville italic", SUP + "Baskerville.ttc", "SemiBold Italic"),
}

INK, PAPER = (17, 19, 22, 255), (255, 255, 255, 255)
N = 512  # drawing resolution


def load(path, face, size):
    if face is None:
        return ImageFont.truetype(path, size)
    for i in range(32):
        try:
            f = ImageFont.truetype(path, size, index=i)
        except OSError:
            break
        if f.getname()[1].lower() == face.lower():
            return f
    return ImageFont.truetype(path, size)


def draw(key, i_scale=0.66, gap_frac=0.035):
    _, path, face = FONTS[key]
    big = load(path, face, int(N * 0.50))
    small = load(path, face, int(N * 0.50 * i_scale))
    glyphs = [("B", big), ("i", small), ("T", big)]
    boxes = [f.getbbox(ch, anchor="ls") for ch, f in glyphs]  # relative to baseline
    widths = [b[2] - b[0] for b in boxes]
    gap = N * gap_frac
    total = sum(widths) + gap * 2
    cap_top = min(b[1] for b in boxes)  # most negative = tallest ink
    baseline = N / 2 - cap_top / 2  # centre the ink vertically

    img = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, N - 1, N - 1], radius=N * 0.11, fill=INK)
    x = (N - total) / 2
    for (ch, f), b, w in zip(glyphs, boxes, widths):
        d.text((x - b[0], baseline), ch, font=f, fill=PAPER, anchor="ls")
        x += w + gap
    return img


def png(img, size):
    buf = io.BytesIO()
    img.resize((size, size), Image.LANCZOS).save(buf, "PNG")
    return buf.getvalue()


if __name__ == "__main__":
    if "--compare" in sys.argv:
        out = pathlib.Path(sys.argv[sys.argv.index("--compare") + 1])
        rows = ""
        for n, (key, (label, *_)) in enumerate(FONTS.items(), 1):
            img = draw(key)
            src = {s: "data:image/png;base64," + base64.b64encode(png(img, s)).decode() for s in (16, 32, 96)}
            rows += (f'<div class="r"><img src="{src[16]}" width=16><img src="{src[32]}" width=32>'
                     f'<img src="{src[96]}" width=96><span>{n} · {label}</span></div>')
        out.write_text('<body style="margin:20px;font:15px system-ui;columns:2">'
                       '<style>.r{display:flex;align-items:end;gap:14px;margin:0 0 14px;break-inside:avoid}</style>'
                       + rows + "</body>")
        print("wrote", out)
    else:
        key = sys.argv[1] if len(sys.argv) > 1 else "helvetica"
        img = draw(key)
        for size, name in [(32, "favicon-32.png"), (64, "favicon-64.png"), (180, "apple-touch-icon.png")]:
            (ROOT / "assets" / name).write_bytes(png(img, size))
        print("favicon drawn with", FONTS[key][0])
