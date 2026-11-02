#!/usr/bin/env python3
"""
Build web/model.js from tools/extracted.json (walls, from the PDF) + tools/spec.py (hand-read details).

  python3 -I tools/extract_plan.py  <sketch.pdf> <work_dir>
  python3 -I tools/build_model.py   <work_dir>/extracted.json  web/model.js  [qa_dir]

Everything is in millimetres. X = west->east, Z = rear->street, Y = up.
"""
import sys, json, os
import numpy as np
from scipy import ndimage
import spec as S

R = 10          # opening-snapping raster, mm / px
RF = 20         # floor flood-fill raster, mm / px
GW, GH = 12500, 24500


def rect_mask(rects, res, pad=0):
    m = np.zeros((GH // res, GW // res), bool)
    for x0, z0, x1, z1 in rects:
        a, b = max(0, (x0 - pad) // res), max(0, (z0 - pad) // res)
        c, d = (x1 + pad + res - 1) // res, (z1 + pad + res - 1) // res
        m[int(b):int(d), int(a):int(c)] = True
    return m


# ------------------------------------------------------------------ opening snapping
def run_len(mask, i, j, di, dj, want, limit):
    n = 0
    while 0 <= i < mask.shape[0] and 0 <= j < mask.shape[1] and mask[i, j] == want and n < limit:
        i += di; j += dj; n += 1
    return n


def snap_opening(mask, o):
    """Return dict(x0,z0,x1,z1) of the opening in mm."""
    X, Z = S.px(o['img'], *o['at'])
    axis = o['axis']
    if 'span' in o:
        a = S.px(o['img'], o['span'][0], o['at'][1])[0] if axis == 'h' else S.px(o['img'], o['at'][0], o['span'][0])[1]
        b = S.px(o['img'], o['span'][1], o['at'][1])[0] if axis == 'h' else S.px(o['img'], o['at'][0], o['span'][1])[1]
        a, b = min(a, b), max(a, b)
        t = o.get('thick', 140)
        ci, cj = Z // R, X // R
        def reach(i, j, di, dj):      # distance (mm) to the next wall cell within 200 mm, else 0
            for n in range(0, 21):
                ii, jj = i + di * n, j + dj * n
                if 0 <= ii < mask.shape[0] and 0 <= jj < mask.shape[1] and mask[ii, jj]:
                    return n * R
            return 0
        if axis == 'h':
            a -= reach(ci, a // R, 0, -1); b += reach(ci, b // R, 0, 1)
            return dict(x0=a, x1=b, z0=Z - t // 2, z1=Z + t // 2)
        a -= reach(a // R, cj, -1, 0); b += reach(b // R, cj, 1, 0)
        return dict(x0=X - t // 2, x1=X + t // 2, z0=a, z1=b)
    ci, cj = Z // R, X // R           # row (z), col (x)
    if mask[ci, cj]:                  # nudge onto free cell along the gap axis
        for d in range(1, 90):
            for s in (-1, 1):
                ii, jj = (ci, cj + s * d) if axis == 'h' else (ci + s * d, cj)
                if not mask[ii, jj]:
                    ci, cj = ii, jj; break
            else:
                continue
            break
        else:
            raise RuntimeError('no free cell near %s' % o.get('name'))
    if axis == 'h':
        l = run_len(mask, ci, cj, 0, -1, False, 500); r = run_len(mask, ci, cj + 1, 0, 1, False, 500)
        j0, j1 = cj - l + 1, cj + r          # free run [j0, j1] inclusive
        thick = []
        for jj in (j0 - 1, j1 + 1):
            up = run_len(mask, ci, jj, -1, 0, True, 60); dn = run_len(mask, ci + 1, jj, 1, 0, True, 60)
            thick.append((ci - up + 1, ci + dn))
        ok = [p for p in thick if (p[1] - p[0] + 1) * R <= 300]
        if ok:
            t = min(ok, key=lambda p: p[1] - p[0])
            return dict(x0=j0 * R, x1=(j1 + 1) * R, z0=t[0] * R, z1=(t[1] + 1) * R)
        return dict(x0=j0 * R, x1=(j1 + 1) * R, z0=Z - 50, z1=Z + 50)
    u = run_len(mask, ci, cj, -1, 0, False, 500); d = run_len(mask, ci + 1, cj, 1, 0, False, 500)
    i0, i1 = ci - u + 1, ci + d
    thick = []
    for ii in (i0 - 1, i1 + 1):
        lf = run_len(mask, ii, cj, 0, -1, True, 60); rt = run_len(mask, ii, cj + 1, 0, 1, True, 60)
        thick.append((cj - lf + 1, cj + rt))
    t = min(thick, key=lambda p: p[1] - p[0])
    return dict(x0=t[0] * R, x1=(t[1] + 1) * R, z0=i0 * R, z1=(i1 + 1) * R)


def decompose(mask):
    """Boolean raster -> list of (c0, r0, c1, r1) rectangles."""
    H, W = mask.shape; rects = []; active = {}
    for y in range(H + 1):
        runs = []
        if y < H:
            row = mask[y]
            d = np.diff(np.concatenate(([0], row.astype(np.int8), [0])))
            runs = list(zip(np.where(d == 1)[0], np.where(d == -1)[0]))
        new = {}
        for r in runs: new[r] = active.get(r, y)
        for r, ys in active.items():
            if r not in new: rects.append((r[0], ys, r[1], y))
        active = new
    return rects


def build(extracted_path, out_js, qa_dir=None):
    ex = json.load(open(extracted_path))
    model = dict(meta=dict(name='Airlie 30 Wright', source='Boutique Homes sales sketch V4 (ground + first floor plans)'),
                 levels=S.LEVELS, boxes=[], floors=[], ceilings=[], glass=[], labels=[], walk=[], spawn=None, stair=S.STAIR)
    qa = {}
    for lv in ('G', 'F'):
        L = S.LEVELS[lv]
        fl_y, top = L['floor'], L['top']
        walls = list(ex['ground' if lv == 'G' else 'first']['walls'])
        for img, a, b, c, d in S.EXTRA_WALLS[lv]:
            walls.append(list(S.pxr(img, a, b, c, d)))
        mask = rect_mask(walls, R)
        # --- walls
        for x0, z0, x1, z1 in walls:
            if x1 - x0 < 20 or z1 - z0 < 20: continue
            model['boxes'].append(dict(l=lv, m='wall', c='wall', b=[x0, fl_y, z0, x1, top, z1]))
        # --- openings
        ops = []
        for o in S.OPENINGS[lv]:
            try:
                g = snap_opening(mask, o)
            except Exception as e:
                print('!! opening failed', lv, o['name'], e); continue
            g.update(kind=o['kind'], name=o['name'], sill=o.get('sill'), head=o.get('head'), obscure=o.get('obscure', False))
            ops.append(g)
            add_opening(model, lv, g, fl_y, top)
        qa[lv] = dict(walls=walls, ops=ops)
        # --- floors (flood fill)
        barrier = rect_mask(walls, RF)
        for g in ops:
            barrier |= rect_mask([(g['x0'], g['z0'], g['x1'], g['z1'])], RF)
        if lv == 'F':                       # stair void
            for v in (S.STAIR['void_A'], S.STAIR['void_B']):
                barrier |= rect_mask([v], RF)
        free = ~barrier
        lab, n = ndimage.label(free)
        L2 = np.zeros(free.shape, np.int32)
        seeds = []
        for i, f in enumerate(S.FLOORS[lv], 1):
            X, Z = S.px(f['at'] and f['img'], *f['at'])
            ci, cj = Z // RF, X // RF
            if 'clip' in f:
                cx0, cz0, cx1, cz1 = S.pxr(*f['clip'])
                cm = np.zeros(free.shape, bool); cm[cz0 // RF:cz1 // RF, cx0 // RF:cx1 // RF] = True
                lab2, _ = ndimage.label(free & cm)
                reg = lab2 == lab2[ci, cj] if lab2[ci, cj] else np.zeros(free.shape, bool)
            else:
                if not lab[ci, cj]:
                    print('!! floor seed on barrier', lv, f['name']); continue
                reg = lab == lab[ci, cj]
            reg &= (L2 == 0)
            ys_, xs_ = np.where(reg)
            if len(ys_) and (ys_.min() == 0 or xs_.min() == 0 or ys_.max() == reg.shape[0] - 1 or xs_.max() == reg.shape[1] - 1):
                print('!! floor region leaks outside the building:', lv, f['name'])
            L2[reg] = i
            seeds.append(f)
        # let door / opening thresholds and wall footprints take the neighbouring finish
        grow = np.zeros(free.shape, bool)
        for g in ops:
            if g['kind'] in ('door', 'open', 'slider', 'entry'):
                grow |= rect_mask([(g['x0'], g['z0'], g['x1'], g['z1'])], RF)
        grow |= rect_mask(walls, RF)
        for it in range(14):
            for dz, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                sh = np.roll(L2, (dz, dx), (0, 1))
                m = grow & (L2 == 0) & (sh > 0)
                L2[m] = sh[m]
        # floors under walls only matter where a finish exists: restrict walls-growth to 2 cells
        holes = free & (L2 == 0)
        # drop tiny specks
        holes = ndimage.binary_opening(holes, iterations=2)
        lab3, n3 = ndimage.label(holes)
        for k in range(1, n3 + 1):
            ys, xs = np.where(lab3 == k)
            if ys.min() == 0 or xs.min() == 0 or ys.max() == holes.shape[0] - 1 or xs.max() == holes.shape[1] - 1:
                continue                      # exterior
            if len(ys) > 400:
                print('!! unfilled interior', lv, 'around', int(xs.mean() * RF), int(ys.mean() * RF), 'cells', len(ys))
        for i, f in enumerate(seeds, 1):
            idx = S.FLOORS[lv].index(f) + 1
            m = L2 == idx
            for c0, r0, c1, r1 in decompose(m):
                model['floors'].append(dict(l=lv, f=f['finish'], y=f.get('y', fl_y), r=[int(c0) * RF, int(r0) * RF, int(c1) * RF, int(r1) * RF]))
        qa[lv]['L2'] = L2; qa[lv]['seeds'] = seeds
        # --- ceilings
        solid = np.zeros(free.shape, bool)
        for i, f in enumerate(S.FLOORS[lv], 1):
            solid |= (L2 == i)          # covered outdoor areas (outdoor living, porch) get a ceiling too
        if lv == 'F':
            for v in (S.STAIR['void_A'], S.STAIR['void_B']):
                solid |= rect_mask([v], RF)
        solid = ndimage.binary_closing(solid, iterations=1)
        for c0, r0, c1, r1 in decompose(solid):
            model['ceilings'].append(dict(l=lv, y=L['ceil'], r=[int(c0) * RF, int(r0) * RF, int(c1) * RF, int(r1) * RF]))
    # --- labels
    for lv, text, size, img, x, y in S.LABELS:
        X, Z = S.px(img, x, y)
        model['labels'].append(dict(l=lv, t=text, s=size, x=X, z=Z))
    # --- furniture
    for f in S.FURNITURE:
        x0, z0, x1, z1 = S.pxr(f['img'], *f['p'])
        fy = S.LEVELS[f['l']]['floor']
        model['boxes'].append(dict(l=f['l'], m='fur', c='solid' if f['solid'] else 'deco', col=f['col'], n=f['name'],
                                   b=[x0, fy + f['y0'], z0, x1, fy + f['y1'], z1]))
    add_stair(model)
    # --- spawn: front door hall
    gx, gz = S.px('Gb', 835, 760)
    fx, fz = S.px('Ft', 800, 640)
    model['spawns'] = dict(G=dict(x=gx, z=gz, yaw=0), F=dict(x=fx, z=fz, yaw=0))   # yaw 0 = facing the rear (-Z)
    del model['spawn']
    # centre of the plan for orbit camera
    model['center'] = dict(x=5500, z=12200)
    os.makedirs(os.path.dirname(out_js) or '.', exist_ok=True)
    with open(out_js, 'w') as fh:
        fh.write('window.HOUSE_MODEL = ' + json.dumps(model, separators=(',', ':')) + ';\n')
    print('model:', len(model['boxes']), 'boxes', len(model['floors']), 'floor rects', len(model['ceilings']), 'ceilings',
          len(model['glass']), 'glass', os.path.getsize(out_js) // 1024, 'KB')
    if qa_dir:
        os.makedirs(qa_dir, exist_ok=True)
        draw_qa(model, qa, qa_dir)


# ------------------------------------------------------------------ openings -> boxes
def add_opening(model, lv, g, fl_y, top):
    x0, z0, x1, z1 = g['x0'], g['z0'], g['x1'], g['z1']
    k = g['kind']
    along_x = (x1 - x0) >= (z1 - z0)
    def box(m, c, a, b, y0, y1, col=None):   # a,b along-axis extents; y relative to floor
        bx = [a, fl_y + y0, z0, b, fl_y + y1, z1] if along_x else [x0, fl_y + y0, a, x1, fl_y + y1, b]
        d = dict(l=lv, m=m, c=c, b=bx)
        if col: d['col'] = col
        model['boxes'].append(d)
    def thin(m, c, a, b, y0, y1, col=None, t=40):
        if along_x:
            cz = (z0 + z1) // 2
            bx = [a, fl_y + y0, cz - t // 2, b, fl_y + y1, cz + t // 2]
        else:
            cx = (x0 + x1) // 2
            bx = [cx - t // 2, fl_y + y0, a, cx + t // 2, fl_y + y1, b]
        d = dict(l=lv, m=m, c=c, b=bx)
        if col: d['col'] = col
        model['boxes'].append(d)
    a0, a1 = (x0, x1) if along_x else (z0, z1)
    wtop = top - fl_y
    if k == 'win':
        sill = g['sill'] if g['sill'] is not None else 900
        head = g['head'] or S.WIN_HEAD
        box('wall', 'wall', a0, a1, 0, sill)
        box('wall', 'wall', a0, a1, head, wtop)
        # frame
        ft = 45
        thin('frame', 'frame', a0, a1, sill, sill + ft); thin('frame', 'frame', a0, a1, head - ft, head)
        thin('frame', 'frame', a0, a0 + ft, sill, head); thin('frame', 'frame', a1 - ft, a1, sill, head)
        n = max(1, round((a1 - a0) / 1100))
        for i in range(1, n):
            p = a0 + (a1 - a0) * i // n
            thin('frame', 'frame', p - 20, p + 20, sill, head)
        gl = dict(l=lv, obscure=g['obscure'], b=None)
        if along_x:
            cz = (z0 + z1) // 2; gl['b'] = [a0, fl_y + sill, cz - 6, a1, fl_y + head, cz + 6]
        else:
            cx = (x0 + x1) // 2; gl['b'] = [cx - 6, fl_y + sill, a0, cx + 6, fl_y + head, a1]
        model['glass'].append(gl)
        model['boxes'].append(dict(l=lv, m='none', c='solid', invisible=True, b=[x0, fl_y + 0, z0, x1, fl_y + head, z1]))
    elif k in ('door', 'open'):
        head = S.DOOR_HEAD
        box('wall', 'wall', a0, a1, head, wtop)
        # door frame (jambs + head)
        ft = 35
        thin('frame', 'deco', a0, a0 + ft, 0, head, '#e9e6df', t=max(90, (z1 - z0) if along_x else (x1 - x0)))
        thin('frame', 'deco', a1 - ft, a1, 0, head, '#e9e6df', t=max(90, (z1 - z0) if along_x else (x1 - x0)))
    elif k == 'slider':
        head = g['head'] or S.DOOR_HEAD
        box('wall', 'wall', a0, a1, head, wtop)
        # half-open sliding panels
        glassy = g['name'].lower().find('stacker') >= 0
        mid = a0 + int((a1 - a0) * (0.45 if glassy else 0.35))
        if glassy:
            gl = dict(l=lv, obscure=False, b=None)
            cx = (x0 + x1) // 2; cz = (z0 + z1) // 2
            gl['b'] = [a0, fl_y, cz - 6, mid, fl_y + head, cz + 6] if along_x else [cx - 6, fl_y, a0, cx + 6, fl_y + head, mid]
            model['glass'].append(gl)
            thin('frame', 'solid', a0, a0 + 45, 0, head); thin('frame', 'solid', mid - 45, mid, 0, head)
            thin('frame', 'solid', a0, mid, 0, 45); thin('frame', 'solid', a0, mid, head - 45, head)
        else:
            thin('door', 'solid', a0, mid, 0, head - 30, '#ece9e3', t=45)
    elif k == 'garage':
        head = g['head'] or S.WIN_HEAD
        box('wall', 'wall', a0, a1, head, wtop)
        thin('door', 'solid', a0, a1, 0, head, '#d8d9dc', t=60)
        for i in range(1, 5):
            thin('frame', 'deco', a0, a1, i * head // 5 - 8, i * head // 5 + 8, '#9a9da1', t=70)
    elif k == 'entry':
        box('wall', 'wall', a0, a1, S.WIN_HEAD, wtop)
        door_w = 860
        thin('frame', 'deco', a0, a0 + 45, 0, S.WIN_HEAD, '#3a2d25', t=120)
        thin('frame', 'deco', a0 + door_w, a0 + door_w + 45, 0, S.WIN_HEAD, '#3a2d25', t=120)
        thin('frame', 'deco', a0, a0 + door_w + 45, S.WIN_HEAD - 45, S.WIN_HEAD, '#3a2d25', t=120)
        # sidelight
        cx = (x0 + x1) // 2; cz = (z0 + z1) // 2
        gl = dict(l=lv, obscure=False, b=None)
        gl['b'] = [a0 + door_w + 45, fl_y, cz - 6, a1, fl_y + S.WIN_HEAD, cz + 6] if along_x else [cx - 6, fl_y, a0 + door_w + 45, cx + 6, fl_y + S.WIN_HEAD, a1]
        model['glass'].append(gl)
        model['boxes'].append(dict(l=lv, m='none', c='solid', invisible=True,
                                   b=[a0 + door_w + 45, fl_y, z0, a1, fl_y + S.WIN_HEAD, z1] if along_x else [x0, fl_y, a0 + door_w + 45, x1, fl_y + S.WIN_HEAD, a1]))


# ------------------------------------------------------------------ stair
def add_stair(model):
    st = S.STAIR; h = S.RISE; g = st['going']
    zA0, zA1 = st['zA']; zB0, zB1 = st['zB']
    L = lambda k: st['x_first'] + (k - 1) * g
    def tread(x0, x1, z0, z1, k):
        top = round(k * h); bot = round((k - 1) * h)
        model['boxes'].append(dict(l='G', m='stair', c='tread', b=[x0, bot, z0, x1, top, z1]))
        model['walk'].append(dict(r=[x0, z0, x1, z1], y=top))
    for k in range(1, 8):                       # flight A: treads 1..7
        tread(L(k), L(k + 1), zA0, zA1, k)
    landing_x = L(8)
    top = round(8 * h)
    model['boxes'].append(dict(l='G', m='stair', c='tread', b=[landing_x, top - 170, zA0, st['x_east'], top, zB1]))
    model['walk'].append(dict(r=[landing_x, zA0, st['x_east'], zB1], y=top))
    M = lambda k: landing_x - (k - 9) * g
    for k in range(9, 17):                      # flight B: treads 9..16 (heading west)
        tread(M(k + 1), M(k), zB0, zB1, k)
    # first-floor guards around the stair void
    f = S.LEVELS['F']['floor']; gh = st['guard_h']
    model['boxes'].append(dict(l='F', m='guard', c='solid', b=[L(1) - 25, f, zA0, L(1) + 25, f + gh, zA1 - 0]))
    model['boxes'].append(dict(l='F', m='guard', c='solid', b=[L(1) - 25, f, zA1, landing_x, f + gh, zB0]))


# ------------------------------------------------------------------ QA picture
def draw_qa(model, qa, qa_dir):
    from PIL import Image, ImageDraw
    K = 0.09
    cols = dict(timber=(226, 196, 150), carpet=(190, 200, 215), tile=(170, 200, 190), concrete=(215, 215, 215))
    for lv in ('G', 'F'):
        im = Image.new('RGB', (int(GW * K), int(GH * K)), (255, 255, 255)); d = ImageDraw.Draw(im)
        for f in model['floors']:
            if f['l'] != lv: continue
            x0, z0, x1, z1 = f['r']
            d.rectangle([x0 * K, z0 * K, x1 * K - 1, z1 * K - 1], fill=cols[f['f']])
        for b in model['boxes']:
            if b['l'] != lv: continue
            x0, y0, z0, x1, y1, z1 = b['b']
            if b['m'] == 'wall' and b['c'] == 'wall' and y0 == S.LEVELS[lv]['floor'] and y1 == S.LEVELS[lv]['top']:
                d.rectangle([x0 * K, z0 * K, max(x0 * K + 1, x1 * K - 1), max(z0 * K + 1, z1 * K - 1)], fill=(40, 40, 40))
            elif b['m'] == 'fur':
                d.rectangle([x0 * K, z0 * K, x1 * K - 1, z1 * K - 1], outline=(120, 90, 60))
            elif b['m'] in ('stair', 'guard'):
                d.rectangle([x0 * K, z0 * K, x1 * K - 1, z1 * K - 1], outline=(200, 0, 200))
        for g in qa[lv]['ops']:
            c = {'win': (0, 150, 255), 'door': (255, 120, 0), 'open': (0, 190, 90), 'slider': (190, 0, 190),
                 'garage': (120, 120, 120), 'entry': (220, 0, 0)}[g['kind']]
            d.rectangle([g['x0'] * K, g['z0'] * K, g['x1'] * K, g['z1'] * K], outline=c, width=2)
        for l in model['labels']:
            if l['l'] == lv:
                d.text((l['x'] * K - 25, l['z'] * K - 5), l['t'], fill=(200, 0, 0))
        im.save(os.path.join(qa_dir, 'qa_%s.png' % lv))


if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
