#!/usr/bin/env python3
"""
Extract wall geometry + text labels from the Airlie 30 sales-sketch PDF (vector, ARCHICAD export).

  python3 -I tools/extract_plan.py <sketch.pdf> <out_dir>

Writes <out_dir>/extracted.json containing, for each floor ('ground', 'first'):
  walls : merged axis-aligned wall rectangles [x0, z0, x1, z1] in millimetres,
          in ONE shared coordinate system (first floor is registered onto the ground floor)
  words : text labels with their position (mm)
The drawing is 1:200 on A4, so 1 pt = 70.556 mm.
"""
import sys, json, os
import numpy as np
import pdfplumber
from PIL import Image, ImageDraw, ImageFilter

MM = 200 * 25.4 / 72            # mm per PDF point at 1:200
# Page regions (pt) that contain each floor drawing
SC = 72 / 110
REGION = {'ground': (100*SC, 150.0, 400*SC, 760*SC), 'first': (525*SC, 320*SC, 800*SC, 785*SC)}   # ground starts above the living wall: outdoor-living posts
# First-floor drawing -> ground-floor drawing offset (pt). Stud lines of the two floors align at
# dx = 276.35 pt; the stair's north wall has identical y on both sheets (dy = 0).
FF_DX, FF_DY = 276.35, 0.0
# Shared origin (pt) so all coordinates are positive millimetres. The outdoor-living posts sit
# ~1.5 m north of the living-room wall, so the origin is 2,000 mm north of that wall (see spec.ZSHIFT).
ORG = (73.0, 211.0 - 2000 / MM)
RES = 0.1                        # raster resolution, pt per pixel (~7 mm)
MIN_THICK_PT = 0.9               # ignore hairline fills (< ~64 mm): frames, hatching, fixtures

def isblack(c):
    if c is None: return False
    try: return all(abs(float(v)) < 0.01 for v in (c if isinstance(c, (tuple, list)) else (c,)))
    except Exception: return False

def decompose(mask):
    """Greedy decomposition of a boolean raster into rectangles (x0,y0,x1,y1 in px)."""
    H, W = mask.shape; rects = []; active = {}
    for y in range(H + 1):
        runs = []
        if y < H:
            row = mask[y]; x = 0
            while x < W:
                if row[x]:
                    s = x
                    while x < W and row[x]: x += 1
                    runs.append((s, x))
                else: x += 1
        new = {}
        for r in runs: new[r] = active.get(r, y)
        for r, ys in active.items():
            if r not in new: rects.append((r[0], ys, r[1], y))
        active = new
    return rects

def main(pdf, out):
    os.makedirs(out, exist_ok=True)
    page = pdfplumber.open(pdf).pages[0]
    res = {}
    for fl, (rx0, ry0, rx1, ry1) in REGION.items():
        sh = []
        for o in list(page.rects) + list(page.curves):
            if not (o.get('fill') and isblack(o.get('non_stroking_color'))): continue
            if o['x0'] >= rx0 and o['x1'] <= rx1 and o['top'] >= ry0 and o['bottom'] <= ry1:
                sh.append(o)
        x0 = min(o['x0'] for o in sh); y0 = min(o['top'] for o in sh)
        x1 = max(o['x1'] for o in sh); y1 = max(o['bottom'] for o in sh)
        W = int((x1 - x0) / RES) + 8; H = int((y1 - y0) / RES) + 8
        im = Image.new('L', (W, H), 0); d = ImageDraw.Draw(im)
        for o in sh:
            if min(o['x1'] - o['x0'], o['bottom'] - o['top']) < MIN_THICK_PT: continue
            pts = o.get('pts') or []
            if len(pts) > 5:
                d.polygon([((x - x0) / RES + 3, (y - y0) / RES + 3) for x, y in pts], fill=255)
            else:
                d.rectangle([(o['x0'] - x0) / RES + 3, (o['top'] - y0) / RES + 3,
                             (o['x1'] - x0) / RES + 3 - 1, (o['bottom'] - y0) / RES + 3 - 1], fill=255)
        # close the ~28 mm gap between the two drawn bands of an external wall
        im = im.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.MinFilter(7))
        rects = decompose(np.array(im) > 0)
        dx, dy = (FF_DX, FF_DY) if fl == 'first' else (0, 0)
        walls = []
        for a, b, c, e in rects:
            X0 = (x0 + (a - 3) * RES - dx - ORG[0]) * MM; X1 = (x0 + (c - 3) * RES - dx - ORG[0]) * MM
            Z0 = (y0 + (b - 3) * RES - dy - ORG[1]) * MM; Z1 = (y0 + (e - 3) * RES - dy - ORG[1]) * MM
            walls.append([round(X0), round(Z0), round(X1), round(Z1)])
        words = []
        for w in page.extract_words():
            if rx0 <= w['x0'] and w['x1'] <= rx1 and ry0 <= w['top'] and w['bottom'] <= ry1:
                words.append({'t': w['text'], 'x': round(((w['x0'] + w['x1']) / 2 - dx - ORG[0]) * MM),
                              'z': round(((w['top'] + w['bottom']) / 2 - dy - ORG[1]) * MM)})
        res[fl] = {'walls': walls, 'words': words}
        print(fl, len(walls), 'wall rects', len(words), 'words')
    json.dump(res, open(os.path.join(out, 'extracted.json'), 'w'))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
