"""
Finishes layers added on top of the structural model (see tools/build_model.py):

  * wall-face panels  : skirting, wet-room tiling, splashbacks (interior) and brick / render / cladding skins (exterior),
                        generated from the room regions so they follow the real wall faces and stop at doors and windows
  * door leaves       : flush internal doors with matt black levers, Monument entry / garage doors
  * fixtures          : stone tops, basins, taps, shower screens, waterfall ends, oven front, sink
  * roof              : hip roof over the first-floor mass + flat deck over the lower parts (approximate)
"""
import numpy as np
from scipy import ndimage
import spec as S

RF = 20
GW, GH = 12500, 24500
PAD = 1000          # mm of margin so the exterior of the outermost walls exists in the masks


def rmask(rects, pad=PAD):
    m = np.zeros((GH // RF, GW // RF), bool)
    for x0, z0, x1, z1 in rects:
        a, b = max(0, int(x0 + pad) // RF), max(0, int(z0 + pad) // RF)
        c, d = -(-int(x1 + pad) // RF), -(-int(z1 + pad) // RF)
        m[b:d, a:c] = True
    return m


def _runs(edge, axis):
    """True-runs of a 2-D bool array: yields (line index, start, end). axis=1 runs along columns (x)."""
    if axis == 1:
        for i in np.where(edge.any(1))[0]:
            row = edge[i].astype(np.int8)
            d = np.diff(np.concatenate(([0], row, [0])))
            for s, e in zip(np.where(d == 1)[0], np.where(d == -1)[0]):
                yield int(i), int(s), int(e)
    else:
        for j in np.where(edge.any(0))[0]:
            col = edge[:, j].astype(np.int8)
            d = np.diff(np.concatenate(([0], col, [0])))
            for s, e in zip(np.where(d == 1)[0], np.where(d == -1)[0]):
                yield int(j), int(s), int(e)


def boundary_runs(region, solid):
    """Faces where `region` meets `solid`. Yields (d, c, a0, a1): d = normal pointing into the region ('+z','-z','+x','-x'),
    c = plane coordinate (mm, nudged 2 mm into the region), a0..a1 = extent along the face (mm)."""
    out = []
    for i, s, e in _runs(region & np.roll(solid, 1, 0), 1):
        out.append(('+z', i * RF + 2 - PAD, s * RF - PAD, e * RF - PAD))      # wall to the north of the region: face looks south
    for i, s, e in _runs(region & np.roll(solid, -1, 0), 1):
        out.append(('-z', (i + 1) * RF - 2 - PAD, s * RF - PAD, e * RF - PAD))
    for j, s, e in _runs(region & np.roll(solid, 1, 1), 0):
        out.append(('+x', j * RF + 2 - PAD, s * RF - PAD, e * RF - PAD))
    for j, s, e in _runs(region & np.roll(solid, -1, 1), 0):
        out.append(('-x', (j + 1) * RF - 2 - PAD, s * RF - PAD, e * RF - PAD))
    return out


SIDE = {'+z': 'N', '-z': 'S', '+x': 'W', '-x': 'E'}      # which side of the room the wall is on


def opening_bands(ops):
    out = []
    for g in ops:
        k = g['kind']
        if k == 'win':
            sill = g['sill'] if g['sill'] is not None else 900
            head = g['head'] or S.WIN_HEAD
        elif k in ('garage', 'entry'):
            sill, head = 0, S.WIN_HEAD
        elif k == 'slider':
            sill, head = 0, g['head'] or S.DOOR_HEAD
        else:
            sill, head = 0, S.DOOR_HEAD
        out.append((g['x0'], g['z0'], g['x1'], g['z1'], sill, head))
    return out


def clip(d, c, a0, a1, y0, y1, bands, tol=45):
    """Cut a rectangular face by the window / door openings that pierce it."""
    plane_z = d in ('+z', '-z')
    segs = [(a0, a1, y0, y1)]
    for (x0, z0, x1, z1, sill, head) in bands:
        if plane_z:
            if not (z0 - tol <= c <= z1 + tol):
                continue
            o0, o1 = x0, x1
        else:
            if not (x0 - tol <= c <= x1 + tol):
                continue
            o0, o1 = z0, z1
        new = []
        for (s0, s1, t0, t1) in segs:
            if o1 <= s0 or o0 >= s1:
                new.append((s0, s1, t0, t1)); continue
            if o0 > s0: new.append((s0, o0, t0, t1))
            if o1 < s1: new.append((o1, s1, t0, t1))
            m0, m1 = max(s0, o0), min(s1, o1)
            if sill > t0: new.append((m0, m1, t0, min(t1, sill)))
            if head < t1: new.append((m0, m1, max(t0, head), t1))
        segs = new
    return [s for s in segs if s[1] - s[0] > 10 and s[3] - s[2] > 5]


def apply(model, qa):
    model['panels'] = []
    P = model['panels']
    solid_by = {}
    for lv in ('G', 'F'):
        L = S.LEVELS[lv]
        fl = L['floor']
        H = L['ceil'] - fl                    # interior wall height (to the ceiling)
        HW = L['top'] - fl                    # structural wall height
        walls = [w for w in qa[lv]['walls'] if not _is_post(lv, w)]
        ops = qa[lv]['ops']
        bands = opening_bands(ops)
        wallm = rmask(walls)
        openm = rmask([(g['x0'], g['z0'], g['x1'], g['z1']) for g in ops])
        solid = wallm | openm
        L2raw = qa[lv]['L2']
        L2 = np.zeros_like(L2raw)
        sh = PAD // RF
        L2[sh:, sh:] = L2raw[:-sh, :-sh]
        indoor = np.zeros(L2.shape, bool)

        def emit(d, c, a0, a1, y0, y1, k, off=0):
            for (s0, s1, t0, t1) in clip(d, c, a0, a1, y0, y1, bands):
                cc = c + (off if d in ('+z', '+x') else -off)
                P.append(dict(l=lv, d=d, c=int(cc), a=[int(s0), int(s1)], y=[int(t0 + fl), int(t1 + fl)], k=k))

        for idx, f in enumerate(S.FLOORS[lv], 1):
            reg = (L2 == idx) & ~solid                       # open cells only (floors are grown under the walls)
            name, fin = f['name'], f['finish']
            if f.get('y', fl) < fl or fin == 'concrete':
                continue                                       # outdoor living, porch, garage, store: no skirting
            indoor |= (L2 == idx)
            wet = S.WET.get(name, {})
            for (d, c, a0, a1) in boundary_runs(reg, solid):
                side = SIDE[d]
                if wet.get('tile'):
                    k = wet['tile']
                    if wet.get('feature') and wet['feature'][1] == side:
                        k = wet['feature'][0]
                    emit(d, c, a0, a1, 0, H, k)
                else:
                    emit(d, c, a0, a1, 0, 100 if fin == 'tile' else 67, 'skirt_tile' if fin == 'tile' else 'skirt')
                for (k, sd, (img, p0, p1), y0, y1) in wet.get('splash', []):
                    if sd != side:
                        continue
                    if d in ('+z', '-z'):
                        r0, r1 = sorted((S.px(img, p0, 0)[0], S.px(img, p1, 0)[0]))
                    else:
                        r0, r1 = sorted((S.px(img, 0, p0)[1], S.px(img, 0, p1)[1]))
                    s0, s1 = max(a0, r0), min(a1, r1)
                    if s1 - s0 > 30:
                        emit(d, c, s0, s1, y0, y1, k, off=2)
            if name == 'Open plan' and lv == 'G':              # kitchen splashback behind the benches
                for (d, c, a0, a1) in boundary_runs(reg, solid):
                    for (sd, (img, p0, p1)) in S.KITCHEN_SPLASH:
                        if SIDE[d] != sd:
                            continue
                        if d in ('+z', '-z'):
                            r0, r1 = sorted((S.px(img, p0, 0)[0], S.px(img, p1, 0)[0]))
                        else:
                            r0, r1 = sorted((S.px(img, 0, p0)[1], S.px(img, 0, p1)[1]))
                        s0, s1 = max(a0, r0), min(a1, r1)
                        if s1 - s0 > 30:
                            emit(d, c, s0, s1, S.SPLASH_Y[0], S.SPLASH_Y[1], 'tile_nostalgia', off=2)
        # ---- exterior skins: open cells connected to the plan border
        openc = ~solid & ~indoor
        lab, n = ndimage.label(openc)
        ext = lab == lab[0, 0] if lab[0, 0] else np.zeros_like(openc)
        for (d, c, a0, a1) in boundary_runs(ext, solid):
            mid = (a0 + a1) // 2
            front = d == '+z' and c > 19000          # faces the street
            if lv == 'G':
                if front:
                    k = 'brick' if mid < 6000 else ('render' if mid < 9700 else 'cladding')
                else:
                    k = 'brick'
            else:
                k = 'render' if front else 'brick'
            emit(d, c, a0, a1, 0, HW, k)
        solid_by[lv] = solid
    _doors(model, qa)
    _fixtures(model, qa)
    _roof(model, qa)


def _is_post(lv, w):
    return S.is_post(lv, w)


def _box(model, lv, m, k, b, c='deco', **kw):
    d = dict(l=lv, m=m, c=c, k=k, b=[int(v) for v in b]); d.update(kw)
    model['boxes'].append(d)


# ------------------------------------------------------------------------------------ doors
# Doors are emitted as records (model['doors']) rather than boxes: the viewer builds them closed, and animates them
# open and shut.  Along-axis coordinates are mm on the wall's own axis ('x' or 'z'), c is the wall centre line.
LEAF_GAP = 3            # mm of shadow gap around a leaf
JAMB = 35               # width of the door-frame trim added in build_model.add_opening
FLOOR_GAP = 8           # leaf clearance above the finished floor


def _doors(model, qa):
    out = model['doors'] = []
    for lv in ('G', 'F'):
        fl = S.LEVELS[lv]['floor']
        for g in qa[lv]['ops']:
            name, kind = g['name'], g['kind']
            if kind not in ('door', 'entry', 'slider'):
                continue
            x0, z0, x1, z1 = g['x0'], g['z0'], g['x1'], g['z1']
            along_x = (x1 - x0) >= (z1 - z0)
            a0, a1 = (x0, x1) if along_x else (z0, z1)
            c = (z0 + z1) // 2 if along_x else (x0 + x1) // 2
            thk = (z1 - z0) if along_x else (x1 - x0)
            d = dict(l=lv, n=name, ax='x' if along_x else 'z', c=int(c), thk=int(thk), fl=int(fl), y0=FLOOR_GAP)
            if kind == 'slider':
                head = g['head'] or S.DOOR_HEAD
                d.update(y1=int(head - 4), lo=int(a0), hi=int(a1))
                if 'stacker' in name.lower():
                    d.update(t='stack', np=max(2, int(round((a1 - a0) / 1250.0))), k='frame')
                elif name in S.SLIDER_KEYS:
                    d.update(t='slide', np=2, k=S.SLIDER_KEYS[name])      # two overlapping robe panels
                else:
                    d.update(t='slide', np=1, k='door_white')             # cavity slider
                out.append(d)
                continue
            if kind == 'entry':
                spec = S.ENTRY_LEAF
                d.update(t='hinge', k='door_monument', entry=True, y1=int(S.WIN_HEAD - 45 - LEAF_GAP),
                         lo=int(a0 + 45 + LEAF_GAP), hi=int(a0 + 860 - LEAF_GAP))
            else:
                spec = S.LEAVES.get(name)
                if not spec:
                    continue
                k = 'door_monument' if name in S.EXT_DOORS else 'door_white'
                d.update(t='double' if spec[0] == 'both' else 'hinge', k=k, y1=int(S.DOOR_HEAD - 6),
                         lo=int(a0 + JAMB + LEAF_GAP), hi=int(a1 - JAMB - LEAF_GAP))
            d.update(hg=spec[0], sw=spec[1])
            out.append(d)


# ------------------------------------------------------------------------------------ fixtures
def _find(model, name, lv=None):
    return [b for b in model['boxes'] if b.get('n') == name and (lv is None or b['l'] == lv)]


def _fixtures(model, qa):
    fl = {'G': 0, 'F': S.LEVELS['F']['floor']}
    # --- stone tops over vanities
    for b in _find(model, 'Vanity') + _find(model, 'Double vanity'):
        x0, y0, z0, x1, y1, z1 = b['b']
        _box(model, b['l'], 'fur', 'blanco', [x0 - 10, y1, z0 - 10, x1 + 10, y1 + 20, z1 + 10], c='deco', n='Vanity top')
    # --- basins + taps
    for lv, img, bc, tp in S.BASINS:
        cx, cz = S.px(img, *bc)
        tx, tz = S.px(img, *tp)
        y = fl[lv] + 870
        _box(model, lv, 'fur', 'basin', [cx - 230, y + 20, cz - 175, cx + 230, y + 24, cz + 175], c='deco', n='Basin')
        _box(model, lv, 'fur', 'black_matt', [tx - 14, y + 20, tz - 14, tx + 14, y + 190, tz + 14], c='deco', n='Tap', sh='cyl')
    # --- showers: rail, rose, waste, screens
    for lv, img, rail, waste in S.SHOWERS:
        rx, rz = S.px(img, *rail)
        wx, wz = S.px(img, *waste)
        _box(model, lv, 'fur', 'black_matt', [rx - 12, fl[lv] + 800, rz - 12, rx + 12, fl[lv] + 1950, rz + 12], c='deco', n='Shower rail', sh='cyl')
        _box(model, lv, 'fur', 'black_matt', [rx - 120, fl[lv] + 2020, rz - 120, rx + 120, fl[lv] + 2040, rz + 120], c='deco', n='Shower rose', sh='cyl')
        _box(model, lv, 'fur', 'black_matt', [wx - 42, fl[lv], wz - 42, wx + 42, fl[lv] + 6, wz + 42], c='deco', n='Waste')
    for lv, img, ax, ay, bx, by in S.SCREENS:
        (x0, z0), (x1, z1) = S.px(img, ax, ay), S.px(img, bx, by)
        xa, xb = sorted((x0, x1)); za, zb = sorted((z0, z1))
        t = 12
        xa, xb = (xa - t, xb + t) if xb - xa < 40 else (xa, xb)
        za, zb = (za - t, zb + t) if zb - za < 40 else (za, zb)
        f0 = fl[lv]
        model['glass'].append(dict(l=lv, obscure=False, b=[xa, f0 + 40, za, xb, f0 + 2000, zb]))
        _box(model, lv, 'frame', None, [xa - 8, f0, za - 8, xb + 8, f0 + 40, zb + 8], c='solid')
        _box(model, lv, 'frame', None, [xa - 8, f0 + 1960, za - 8, xb + 8, f0 + 2000, zb + 8], c='solid')
        _box(model, lv, 'none', None, [xa - 8, f0 + 40, za - 8, xb + 8, f0 + 1960, zb + 8], c='solid')
        for (px_, pz_) in ((xa, za), (xb, zb)):
            _box(model, lv, 'frame', None, [px_ - 14, f0, pz_ - 14, px_ + 14, f0 + 2000, pz_ + 14], c='deco')
    # --- kitchen: island waterfall ends, sink, tap, oven front
    for b in _find(model, 'Island base', 'G'):
        x0, y0, z0, x1, y1, z1 = b['b']
        _box(model, 'G', 'fur', 'cala', [x0 - 5, 0, z0 - 40, x1 + 5, 920, z0], c='solid', n='Waterfall end')
        _box(model, 'G', 'fur', 'cala', [x0 - 5, 0, z1, x1 + 5, 920, z1 + 40], c='solid', n='Waterfall end')
    for b in _find(model, 'Sink', 'G'):
        x0, y0, z0, x1, y1, z1 = b['b']
        cx, cz = (x0 + x1) // 2, (z0 + z1) // 2
        b['b'] = [cx - 380, 915, cz - 220, cx + 380, 925, cz + 220]
        _box(model, 'G', 'fur', 'black_matt', [cx - 15, 925, cz - 195 - 15, cx + 15, 1260, cz - 195 + 15], c='deco', n='Tap', sh='cyl')
        _box(model, 'G', 'fur', 'black_matt', [cx - 12, 1230, cz - 190, cx + 12, 1260, cz - 60], c='deco', n='Spout')
    cook = _find(model, 'Cooktop', 'G')
    bench = _find(model, 'Kitchen bench W', 'G')
    if cook and bench:
        zc = (cook[0]['b'][2] + cook[0]['b'][5]) // 2
        xe = bench[0]['b'][3]
        _box(model, 'G', 'fur', 'oven', [xe, 280, zc - 440, xe + 30, 820, zc + 440], c='deco', n='Oven')
    # outdoor living posts / laundry cabinetry
    for b in _find(model, 'Laundry trough', 'G'):
        x0, y0, z0, x1, y1, z1 = b['b']
        _box(model, 'G', 'fur', 'cab_not', [x0 - 30, 0, z0 - 30, x1 + 10, 840, z1 + 30], c='solid', n='Laundry base')
        _box(model, 'G', 'fur', 'buller', [x0 - 35, 840, z0 - 35, x1 + 12, 873, z1 + 35], c='deco', n='Laundry top')
        b['b'] = [x0 + 5, 873, z0 + 5, x1 - 5, 878, z1 - 5]
        _box(model, 'G', 'fur', 'black_matt', [(x0 + x1) // 2 - 12, 878, z0 + 4, (x0 + x1) // 2 + 12, 1080, z0 + 28], c='deco', n='Tap', sh='cyl')


# ------------------------------------------------------------------------------------ roof
def _roof(model, qa):
    fw = qa['F']['walls']
    x0 = min(w[0] for w in fw); x1 = max(w[2] for w in fw)
    z0 = min(w[1] for w in fw); z1 = max(w[3] for w in fw)
    R = S.ROOF
    # flat deck over the ground-floor parts that sit outside the first-floor mass
    m = np.zeros((GH // RF, GW // RF), bool)
    for c in model['ceilings']:
        if c['l'] == 'G':
            a, b, cc, d = c['r']
            m[b // RF:d // RF, a // RF:cc // RF] = True
    m &= ~rmask([(x0 - 60, z0 - 60, x1 + 60, z1 + 60)])
    m = ndimage.binary_opening(m, iterations=3)
    flats = []
    H, W = m.shape; active = {}
    for y in range(H + 1):
        runs = []
        if y < H:
            d = np.diff(np.concatenate(([0], m[y].astype(np.int8), [0])))
            runs = list(zip(np.where(d == 1)[0], np.where(d == -1)[0]))
        new = {}
        for r in runs: new[r] = active.get(r, y)
        for r, ys in active.items():
            if r not in new: flats.append([int(r[0]) * RF, int(ys) * RF, int(r[1]) * RF, int(y) * RF])
        active = new
    model['roof'] = dict(hip=dict(x0=int(x0), z0=int(z0), x1=int(x1), z1=int(z1), plate=S.LEVELS['F']['top'], pitch=R['pitch_deg'], over=R['overhang']),
                         flats=flats, deck=R['deck'])
