#!/usr/bin/env python3
"""
Generate an animated ASCII dollar-sign wordmark SVG for SUYASH.
The card renders in a terminal window (860x220) and animates in an LCD
sliding ticker fashion: the name displays, slides to the left so the
first part disappears and the remaining part reveals, then loops smoothly.
"""
import html
import os
import sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "suyash-wordmark.svg")

CANVAS_W = 860
CANVAS_H = 220
PAD = 24
TITLEBAR_H = 30
STATUS_H = 28
VIEWPORT_W = CANVAS_W - PAD * 2   # 812px
VIEWPORT_H = CANVAS_H - TITLEBAR_H - STATUS_H  # 162px

BG = "#0d1117"
BG2 = "#111722"
FRAME = "#30363d"
TITLE_TEXT = "#7d8590"
GREEN = "#39d353"
ACCENT = "#22d3ee"
INK = "#c9d1d9"

# ---- 1. Render ASCII banner of 'SUYASH' using $ glyphs -------------------
im = Image.new("L", (1000, 100), 0)
draw = ImageDraw.Draw(im)

try:
    font = ImageFont.truetype("arialbd.ttf", 72)
except Exception:
    font = ImageFont.load_default()

draw.text((15, 5), "SUYASH", fill=255, font=font)
bbox = im.getbbox()
im_cropped = im.crop((0, bbox[1], bbox[2] + 20, bbox[3]))
cw, ch = im_cropped.size

TARGET_ROWS = 10
TARGET_COLS = int(cw * (TARGET_ROWS / ch) * 1.85)
small = im_cropped.resize((TARGET_COLS, TARGET_ROWS), Image.Resampling.LANCZOS)
px = small.load()

RAMP = " .:-=+*sS#%$@"
lines = []
for y in range(TARGET_ROWS):
    row_chars = []
    for x in range(TARGET_COLS):
        lum = px[x, y] / 255.0
        if lum <= 0.14:
            row_chars.append(" ")
        elif lum >= 0.60:
            row_chars.append("$")
        else:
            idx = int(lum * (len(RAMP) - 1) + 0.5)
            row_chars.append(RAMP[idx])
    lines.append("".join(row_chars))

# ---- 2. Calculate dimensions & slide distance -----------------------------
CELL_H = 14.5
# 113 cols at ~9.3px per char = ~1050px total text width
CELL_W = 9.3
ART_W = TARGET_COLS * CELL_W
SLIDE_DIST = max(100.0, ART_W - VIEWPORT_W + 50.0)

# ---- 3. Assemble SVG ------------------------------------------------------
css = f"""
@keyframes lcd-slide {{
  0%, 25%   {{ transform: translateX(0px); }}
  55%, 80%  {{ transform: translateX(-{SLIDE_DIST:.1f}px); }}
  95%, 100% {{ transform: translateX(0px); }}
}}
.lcd-ticker {{
  animation: lcd-slide 9s cubic-bezier(0.45, 0.05, 0.55, 0.95) infinite;
}}
""".strip()

parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}" height="{CANVAS_H}" '
    f'viewBox="0 0 {CANVAS_W} {CANVAS_H}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">',
    f'<style>{css}</style>',
    '<defs>',
    f'<linearGradient id="wbg" x1="0" y1="0" x2="0" y2="1">'
    f'<stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/></linearGradient>',
    f'<clipPath id="lcd-screen"><rect x="{PAD}" y="{TITLEBAR_H + 6}" width="{VIEWPORT_W}" height="{VIEWPORT_H - 10}" rx="6"/></clipPath>',
    '</defs>',
    f'<rect width="{CANVAS_W}" height="{CANVAS_H}" rx="12" fill="url(#wbg)"/>',
    f'<rect x="0.5" y="0.5" width="{CANVAS_W-1}" height="{CANVAS_H-1}" rx="12" fill="none" stroke="{FRAME}" stroke-width="1"/>',
    f'<line x1="0" y1="{TITLEBAR_H}" x2="{CANVAS_W}" y2="{TITLEBAR_H}" stroke="{FRAME}"/>',
]

# Title bar colored dots
for i, dotcol in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
    parts.append(f'<circle cx="{PAD + i*16}" cy="{TITLEBAR_H/2}" r="5" fill="{dotcol}"/>')
parts.append(
    f'<text x="{CANVAS_W/2}" y="{TITLEBAR_H/2 + 4}" fill="{TITLE_TEXT}" font-size="12" '
    f'text-anchor="middle">suyashx1@github: ~$ ./wordmark.sh --ticker &quot;SUYASH&quot;</text>'
)

# Viewport with LCD sliding text
parts.append('<g clip-path="url(#lcd-screen)">')
parts.append('<g class="lcd-ticker">')
# Include SMIL fallback for full SVG compatibility
parts.append(
    f'<animateTransform attributeName="transform" type="translate" '
    f'values="0 0; 0 0; -{SLIDE_DIST:.1f} 0; -{SLIDE_DIST:.1f} 0; 0 0" '
    f'keyTimes="0; 0.25; 0.55; 0.80; 1" '
    f'dur="9s" repeatCount="indefinite" />'
)

start_y = TITLEBAR_H + 20
font_size = 15.5
for ry, line in enumerate(lines):
    y = start_y + ry * CELL_H + CELL_H * 0.75
    safe = html.escape(line)
    parts.append(
        f'<text xml:space="preserve" x="{PAD}" y="{y:.1f}" fill="{INK}" '
        f'font-size="{font_size:.1f}" font-weight="600">{safe}</text>'
    )

parts.append('</g>')
parts.append('</g>')

# Status bar divider & text
status_y = CANVAS_H - 12
parts.append(f'<line x1="0" y1="{CANVAS_H - STATUS_H}" x2="{CANVAS_W}" y2="{CANVAS_H - STATUS_H}" stroke="{FRAME}" stroke-opacity="0.5"/>')
parts.append(
    f'<text x="{PAD}" y="{status_y}" fill="{TITLE_TEXT}" font-size="11.5">'
    f'suyashx1@github:~$ <tspan fill="{GREEN}">[LCD MARQUEE]</tspan> <tspan fill="{ACCENT}">SUYASH</tspan></text>'
)
parts.append(
    f'<rect x="{PAD+230}" y="{status_y-9}" width="7" height="12" fill="{INK}">'
    f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.51;1" dur="1s" repeatCount="indefinite"/>'
    f'</rect>'
)

parts.append("</svg>")
svg = "".join(parts)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(svg)
print(f"wrote {OUT} ({len(svg)} bytes; {CANVAS_W}x{CANVAS_H}, cols={TARGET_COLS}, slide={SLIDE_DIST:.1f}px)")
