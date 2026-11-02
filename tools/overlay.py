#!/usr/bin/env python3
"""
Render 600 dpi crops of the sketch with the extracted walls overlaid in red. The crops are what
tools/spec.py's pixel coordinates refer to (see px() there).

  pdftoppm -r 600 -png sketch.pdf work/x6
  python3 -I tools/overlay.py work/extracted.json work/x6-1.png work/

Writes ov_ground_top/bot.png and ov_first_top/bot.png (each half-plan is 1501 px wide).
"""
import sys, json
from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS = None
MM = 200 * 25.4 / 72
ORG = (73.0, 211.0)            # crop origin used by spec.px(): plan frame *before* spec.ZSHIFT
ZSHIFT = 2000
DX = {'ground': 0, 'first': 276.35}
d = json.load(open(sys.argv[1])); im = Image.open(sys.argv[2]).convert('RGB'); out = sys.argv[3]; k = 600 / 72
for fl in ('ground', 'first'):
    x0 = ORG[0] + DX[fl] - 5; y0 = ORG[1] - 5
    x1 = x0 + 12000 / MM + 10; y1 = y0 + 21000 / MM + 10
    c = im.crop((int(x0 * k), int(y0 * k), int(x1 * k), int(y1 * k))).convert('RGBA')
    ov = Image.new('RGBA', c.size, (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
    for a, b, e, f in d[fl]['walls']:
        px = lambda X: (ORG[0] + DX[fl] + X / MM - x0) * k
        pz = lambda Z: (ORG[1] + (Z - ZSHIFT) / MM - y0) * k
        dr.rectangle([px(a), pz(b), px(e), pz(f)], fill=(255, 0, 0, 110))
    c = Image.alpha_composite(c, ov).convert('RGB')
    W, H = c.size
    c.crop((0, 0, W, H // 2 + 40)).save(f'{out}/ov_{fl}_top.png'); c.crop((0, H // 2 - 40, W, H)).save(f'{out}/ov_{fl}_bot.png')
