"""
Hand-authored description of the Airlie 30 "Wright" sales sketch (V4) that cannot be read
directly from the PDF's vector walls: openings, floor finishes, fixtures, stair.

Coordinates are read from 600 dpi crops of the sketch (see tools/overlay.py). The helper
`px()` converts a pixel in one of those crops into the shared millimetre coordinate system:
    X = px * 8.4667 - 352.8
    Z = (py + offset) * 8.4667 - 352.8      offset = 0 for '*t' (top) crops, 1242 for '*b' (bottom)
X runs left->right on the plan (west->east), Z runs top->bottom (rear -> street frontage).

Vertical dimensions come from the Boutique Homes master drawing set (Airlie 30):
  ground ceiling 2,590 | first-floor level +2,909 | first-floor ceiling 2,440 above that (5,349)
  window head 2,150 | door head 2,040 | 17 risers | porch / outdoor living 172 below ground floor.
"""

ZSHIFT = 2000      # mm added to every Z so the outdoor-living posts north of the living wall stay positive
K = 8.4667
OFF = {'Gt': 0, 'Gb': 1242, 'Ft': 0, 'Fb': 1242}


def px(img, x, y):
    if img == 'mm':          # millimetres in the un-shifted plan frame
        return (x, y + ZSHIFT)
    return (round(x * K - 352.8), round((y + OFF[img]) * K - 352.8) + ZSHIFT)


def pxr(img, x0, y0, x1, y1):
    a = px(img, x0, y0)
    b = px(img, x1, y1)
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))


# ----------------------------------------------------------------------------- levels
LEVELS = {
    'G': dict(name='Ground floor', floor=0, ceil=2590, top=2909),
    'F': dict(name='First floor', floor=2909, ceil=5349, top=5349),
}
DOOR_HEAD = 2040
WIN_HEAD = 2150
RISERS = 17
RISE = 2909 / RISERS

# ----------------------------------------------------------------------------- openings
# kind: win | door | slider | open | garage | entry
# at: pixel on the opening; axis 'h' = wall runs along X (gap measured along X), 'v' = along Z.
# span=(a,b) in px along the axis (and at_px for the wall line) override gap auto-detection when
# the opening is bounded by hairline glazing instead of solid wall.
OPENINGS = {
    'G': [
        # ---- rear / living
        dict(img='Gt', at=(950, 62), axis='h', kind='win', sill=700, name='Living window'),
        dict(img='Gt', at=(670, 270), axis='v', kind='slider', sill=0, head=2148, name='Outdoor living stacker door'),
        dict(img='Gt', at=(540, 572), axis='h', kind='win', sill=950, name='Kitchen window'),
        dict(img='Gt', at=(318, 905), axis='v', kind='win', sill=950, name='Kitchen bench window'),
        dict(img='Gt', at=(1250, 830), axis='v', kind='win', sill=340, name='Dining window'),
        # ---- garage
        dict(img='Gb', at=(138, 195), axis='h', kind='door', name='Garage side door'),
        dict(img='Gb', at=(730, 282), axis='v', kind='door', name='Garage internal door'),
        dict(img='Gb', at=(390, 920), axis='h', kind='garage', name='Garage door'),
        # ---- entry / guest
        dict(img='Gb', at=(836, 870), axis='h', kind='entry', span=(757, 915), name='Front door + sidelight'),
        dict(img='Gb', at=(1070, 1085), axis='h', kind='win', sill=900, span=(932, 1200), thick=120, name='Guest bed window'),
        dict(img='Gb', at=(925, 1030), axis='v', kind='win', sill=900, span=(965, 1085), thick=120, name='Guest bed side window'),
        dict(img='Gb', at=(935, 700), axis='v', kind='slider', name='Guest bed door'),
        # ---- services
        dict(img='Gb', at=(1070, 320), axis='v', kind='door', name='Powder room door'),
        dict(img='Gb', at=(990, 250), axis='h', kind='door', name='Linen door'),
        dict(img='Gb', at=(905, 510), axis='v', kind='door', name="Laundry doors"),
        dict(img='Gb', at=(1135, 630), axis='h', kind='slider', name='WIR sliding door'),
        dict(img='Gt', at=(905, 1295), axis='v', kind='door', name='Store door'),
    ],
    'F': [
        dict(img='Ft', at=(520, 62), axis='h', kind='win', sill=900, name='Bed 4 window'),
        dict(img='Ft', at=(1030, 62), axis='h', kind='win', sill=900, name='Bed 3 window'),
        dict(img='Ft', at=(318, 775), axis='v', kind='win', sill=700, obscure=True, name='Bath window'),
        dict(img='Ft', at=(1245, 780), axis='v', kind='win', sill=900, name='Bed 2 window'),
        dict(img='Ft', at=(1245, 1225), axis='v', kind='win', sill=1500, name='Stair window'),
        dict(img='Ft', at=(318, 1180), axis='v', kind='win', sill=900, name='Retreat window'),
        dict(img='Ft', at=(733, 215), axis='v', kind='slider', name='Bed 4 robe doors'),
        dict(img='Ft', at=(868, 215), axis='v', kind='slider', name='Bed 3 robe doors'),
        dict(img='Ft', at=(800, 420), axis='h', kind='door', name='Linen door'),
        dict(img='Ft', at=(731, 490), axis='v', kind='door', name='Bed 4 door'),
        dict(img='Ft', at=(872, 488), axis='v', kind='door', name='Bed 3 door'),
        dict(img='Ft', at=(872, 955), axis='v', kind='door', name='Bed 2 door'),
        dict(img='Ft', at=(572, 628), axis='v', kind='door', name='Bath door'),
        dict(img='Ft', at=(630, 688), axis='h', kind='door', name='WC door'),
        dict(img='Ft', at=(1100, 1022), axis='h', kind='slider', name='Bed 2 robe doors'),
        dict(img='Fb', at=(318, 455), axis='v', kind='win', sill=900, name='WIR window'),
        dict(img='Fb', at=(318, 860), axis='v', kind='win', sill=900, name='Retreat 2 side window'),
        dict(img='Fb', at=(470, 925), axis='h', kind='win', sill=700, name='Retreat 2 window'),
        dict(img='Fb', at=(728, 1020), axis='v', kind='win', sill=900, span=(965, 1078), thick=120, name='Bed 1 side window'),
        dict(img='Fb', at=(790, 1082), axis='h', kind='win', sill=700, span=(738, 838), thick=140, name='Bed 1 window A'),
        dict(img='Fb', at=(980, 1082), axis='h', kind='win', sill=700, name='Bed 1 window B'),
        dict(img='Fb', at=(1175, 1082), axis='h', kind='win', sill=700, span=(1124, 1232), thick=140, name='Bed 1 window C'),
        dict(img='Fb', at=(1245, 1025), axis='v', kind='win', sill=900, name='Bed 1 east window'),
        dict(img='Fb', at=(1245, 180), axis='v', kind='win', sill=1500, name='Ensuite window'),
        dict(img='Fb', at=(695, 272), axis='v', kind='door', name='Walk-in linen door'),
        dict(img='Fb', at=(455, 392), axis='h', kind='open', name='WIR opening'),
        dict(img='Fb', at=(768, 392), axis='h', kind='door', name='Master suite door'),
        dict(img='Fb', at=(1050, 568), axis='h', kind='open', name='Ensuite opening'),
        dict(img='Fb', at=(978, 320), axis='v', kind='door', name='Ensuite WC door'),
    ],
}

# ----------------------------------------------------------------------------- extra wall posts
# Corner posts at glazed corners are drawn as hairline fills in the PDF, so they are re-added here.
EXTRA_WALLS = {
    'G': [],
    'F': [
        ('Fb', 313, 910, 333, 933),      # retreat 2 south-west corner
        ('Fb', 720, 1068, 740, 1088),    # bed 1 bay south-west corner
        ('Fb', 1232, 1068, 1252, 1088),  # bed 1 bay south-east corner
    ],
}

# ----------------------------------------------------------------------------- floors
# finish: timber | carpet | tile | concrete.  clip = px box limiting the fill (open-air spaces)
# y = floor height override (mm), default = level floor.
FLOORS = {
    'G': [
        dict(img='Gt', at=(900, 700), finish='timber', name='Open plan'),
        dict(img='Gb', at=(400, 500), finish='concrete', name='Garage'),
        dict(img='Gb', at=(1200, 400), finish='tile', name='Powder room'),
        dict(img='Gb', at=(970, 560), finish='tile', name="Laundry"),
        dict(img='Gb', at=(1180, 600), finish='carpet', name='Walk-in robe'),
        dict(img='Gb', at=(1150, 720), finish='carpet', name='Guest bed'),
        dict(img='Gb', at=(990, 215), finish='timber', name='Linen'),
        dict(img='Gt', at=(960, 1290), finish='concrete', name='Store'),
        dict(img='Gt', at=(500, 450), finish='concrete', clip=('Gt', 305, -190, 655, 572), y=-172, name='Outdoor living'),
        dict(img='Gb', at=(830, 960), finish='concrete', clip=('Gb', 745, 880, 935, 1100), y=-172, name='Porch'),
    ],
    'F': [
        dict(img='Ft', at=(480, 150), finish='carpet', name='Bed 4'),
        dict(img='Ft', at=(1080, 140), finish='carpet', name='Bed 3'),
        dict(img='Ft', at=(1050, 650), finish='carpet', name='Bed 2'),
        dict(img='Ft', at=(765, 200), finish='carpet', name='Robe 4'),
        dict(img='Ft', at=(835, 200), finish='carpet', name='Robe 3'),
        dict(img='Ft', at=(800, 383), finish='carpet', name='Linen'),
        dict(img='Ft', at=(500, 720), finish='tile', name='Bath'),
        dict(img='Ft', at=(630, 780), finish='tile', name='WC'),
        dict(img='Ft', at=(800, 600), finish='carpet', name='Passage'),
        dict(img='Ft', at=(450, 1100), finish='carpet', name='Retreat'),
        dict(img='Ft', at=(1100, 1060), finish='carpet', name='Bed 2 robe'),
        dict(img='Fb', at=(800, 700), finish='carpet', name='Bed 1'),
        dict(img='Fb', at=(450, 700), finish='carpet', name='Retreat 2'),
        dict(img='Fb', at=(1100, 320), finish='tile', name='Ensuite'),
        dict(img='Fb', at=(910, 250), finish='tile', name='Ensuite WC'),
        dict(img='Fb', at=(910, 480), finish='tile', name='Ensuite shower'),
        dict(img='Fb', at=(1100, 180), finish='tile', name='Ensuite bath'),
        dict(img='Fb', at=(450, 330), finish='carpet', name='Walk-in robe'),
        dict(img='Fb', at=(665, 270), finish='carpet', name='Walk-in linen'),
        dict(img='Fb', at=(450, 540), finish='carpet', name='Robe'),
    ],
}

# ----------------------------------------------------------------------------- labels
# (level, text, size text, px img, x, y)
LABELS = [
    ('G', 'Outdoor living', '3.0 x 5.9', 'Gt', 480, 175),
    ('G', 'Living', '4.7 x 4.6', 'Gt', 1000, 340),
    ('G', 'Dining', '4.1 x 4.0', 'Gt', 980, 890),
    ('G', 'Kitchen', '', 'Gt', 590, 1170),
    ('G', 'WIP (pantry)', '', 'Gb', 470, 135),
    ('G', 'Garage', '5.5 x 6.0', 'Gb', 400, 600),
    ('G', 'Store', '', 'Gt', 975, 1297),
    ('G', 'Linen', '', 'Gb', 990, 218),
    ('G', 'Powder room', '', 'Gb', 1195, 320),
    ("G", "Laundry", '', 'Gb', 960, 505),
    ('G', 'Walk-in robe', '', 'Gb', 1190, 562),
    ('G', 'Guest bed', '3.2 x 3.7', 'Gb', 1130, 840),
    ('G', 'Entry', '', 'Gb', 830, 700),
    ('G', 'Stairs', '', 'mm', 8700, 10040),
    ('F', 'Stairs', '', 'mm', 8700, 10040),
    ('F', 'Bed 4', '3.3 x 4.0', 'Ft', 470, 310),
    ('F', 'Bed 3', '3.0 x 3.9', 'Ft', 1100, 320),
    ('F', 'Bed 2', '3.0 x 3.9', 'Ft', 1050, 740),
    ('F', 'Bath', '', 'Ft', 500, 745),
    ('F', 'WC', '', 'Ft', 628, 722),
    ('F', 'Passage', '', 'Ft', 800, 640),
    ('F', 'Retreat', '3.4 x 4.6', 'Ft', 575, 1160),
    ('F', 'Walk-in robe', '', 'Fb', 455, 400),
    ('F', 'Walk-in linen', '', 'Fb', 680, 280),
    ('F', 'Ensuite', '', 'Fb', 1090, 350),
    ('F', 'Retreat 2', '3.4 x 2.9', 'Fb', 525, 710),
    ('F', 'Bed 1', '4.2 x 4.2', 'Fb', 1085, 790),
]

# ----------------------------------------------------------------------------- furniture & fixtures
# (level, img, x0, y0, x1, y1, y0mm, y1mm, colour, solid, name)   px box on the crop
W_ = '#f2f1ee'; TIM = '#b58a5b'; DK = '#34383d'; GR = '#8c9299'; FAB = '#7d8590'; BED = '#e7e3dc'
CAB = '#e3ded4'; BENCH = '#cfcac0'; PORC = '#fbfbfb'; CAR = '#aeb4bb'


def B(l, img, x0, y0, x1, y1, h0, h1, col, name='', solid=True):
    return dict(l=l, img=img, p=(x0, y0, x1, y1), y0=h0, y1=h1, col=col, name=name, solid=solid)


def chairs_row(l, img, xs, y_top, y_bot, face):
    """Chairs on both long sides of a table. face is unused (chairs drawn as seat+back)."""
    out = []
    for x in xs:
        out.append(B(l, img, x - 20, y_top - 22, x + 20, y_top, 0, 450, FAB, 'chair', False))
        out.append(B(l, img, x - 20, y_bot, x + 20, y_bot + 22, 0, 450, FAB, 'chair', False))
    return out


FURNITURE = [
    # ---- ground: living
    B('G', 'Gt', 782, 85, 965, 185, 0, 420, FAB, 'Sofa (L) A'),
    B('G', 'Gt', 782, 185, 885, 450, 0, 420, FAB, 'Sofa (L) B'),
    B('G', 'Gt', 782, 85, 800, 185, 420, 850, FAB, 'Sofa back', False),
    B('G', 'Gt', 782, 85, 965, 100, 420, 850, FAB, 'Sofa back N', False),
    B('G', 'Gt', 782, 185, 800, 450, 420, 850, FAB, 'Sofa back W', False),
    B('G', 'Gt', 961, 235, 1043, 425, 0, 380, TIM, 'Coffee table', False),
    B('G', 'Gt', 1178, 178, 1225, 402, 0, 520, DK, 'TV unit / fireplace'),
    B('G', 'Gt', 941, 474, 1020, 557, 0, 420, FAB, 'Armchair'),
    B('G', 'Gt', 1039, 474, 1117, 557, 0, 420, FAB, 'Armchair'),
    # ---- ground: dining
    B('G', 'Gt', 838, 835, 1122, 940, 700, 750, TIM, 'Dining table top', False),
    B('G', 'Gt', 850, 850, 870, 870, 0, 700, TIM, 'leg', False),
    B('G', 'Gt', 1090, 850, 1110, 870, 0, 700, TIM, 'leg', False),
    B('G', 'Gt', 850, 905, 870, 925, 0, 700, TIM, 'leg', False),
    B('G', 'Gt', 1090, 905, 1110, 925, 0, 700, TIM, 'leg', False),
    # ---- ground: outdoor living
    B('G', 'Gt', 440, 235, 545, 400, 700, 750, TIM, 'Outdoor table top', False),
    B('G', 'Gt', 455, 250, 470, 265, -172, 700, TIM, 'leg', False),
    B('G', 'Gt', 515, 370, 530, 385, -172, 700, TIM, 'leg', False),
    # ---- ground: kitchen
    B('G', 'Gt', 555, 795, 720, 1090, 0, 880, CAB, 'Island base'),
    B('G', 'Gt', 550, 790, 725, 1095, 880, 920, BENCH, 'Island top', False),
    B('G', 'Gt', 330, 590, 405, 1225, 0, 880, CAB, 'Kitchen bench W'),
    B('G', 'Gt', 325, 585, 410, 1230, 880, 920, BENCH, 'Bench top W', False),
    B('G', 'Gt', 405, 590, 680, 660, 0, 880, CAB, 'Kitchen bench N'),
    B('G', 'Gt', 405, 585, 685, 665, 880, 920, BENCH, 'Bench top N', False),
    B('G', 'Gt', 338, 848, 400, 955, 920, 935, DK, 'Cooktop', False),
    B('G', 'Gt', 460, 598, 590, 650, 900, 925, GR, 'Sink', False),
    B('G', 'Gt', 590, 1262, 705, 1330, 0, 1800, GR, 'Fridge'),
    # ---- ground: garage (cars)
    B('G', 'Gb', 175, 345, 350, 870, 150, 650, CAR, 'Car 1 body'),
    B('G', 'Gb', 195, 480, 330, 770, 650, 1100, '#6b7480', 'Car 1 cabin'),
    B('G', 'Gb', 455, 345, 630, 870, 150, 650, CAR, 'Car 2 body'),
    B('G', 'Gb', 475, 480, 610, 770, 650, 1100, '#6b7480', 'Car 2 cabin'),
    # ---- ground: services
    B('G', 'Gb', 915, 195, 1062, 242, 0, 1900, W_, 'Linen shelves'),
    B('G', 'Gb', 1125, 135, 1170, 205, 0, 400, PORC, 'Toilet', False),
    B('G', 'Gb', 1128, 135, 1168, 160, 400, 900, PORC, 'Cistern', False),
    B('G', 'Gb', 1258, 340, 1320, 455, 0, 850, CAB, 'Vanity'),
    B('G', 'Gb', 965, 535, 1025, 615, 0, 900, GR, 'Laundry trough'),
    B('G', 'Gb', 950, 430, 985, 505, 0, 850, PORC, 'Washing machine'),
    B('G', 'Gb', 990, 430, 1022, 505, 0, 850, PORC, 'Dryer'),
    B('G', 'Gb', 1048, 470, 1092, 620, 0, 2000, W_, 'WIR shelves W'),
    B('G', 'Gb', 1268, 470, 1318, 620, 0, 2000, W_, 'WIR shelves E'),
    # ---- ground: guest bed
    B('G', 'Gb', 1090, 770, 1255, 935, 0, 480, BED, 'Guest bed'),
    B('G', 'Gb', 1255, 770, 1308, 935, 0, 1000, TIM, 'Bed head'),
    B('G', 'Gb', 1265, 708, 1310, 760, 0, 500, TIM, 'Bedside'),
    B('G', 'Gb', 1265, 945, 1310, 1000, 0, 500, TIM, 'Bedside'),
    # ---- first: bed 4
    B('F', 'Ft', 340, 222, 557, 388, 0, 480, BED, 'Bed 4'),
    B('F', 'Ft', 340, 222, 390, 388, 0, 1000, TIM, 'Bed head', False),
    B('F', 'Ft', 338, 158, 387, 212, 0, 500, TIM, 'Bedside'),
    B('F', 'Ft', 338, 395, 387, 450, 0, 500, TIM, 'Bedside'),
    # ---- first: bed 3
    B('F', 'Ft', 1008, 228, 1225, 393, 0, 480, BED, 'Bed 3'),
    B('F', 'Ft', 1178, 228, 1225, 393, 0, 1000, TIM, 'Bed head', False),
    B('F', 'Ft', 1178, 165, 1225, 218, 0, 500, TIM, 'Bedside'),
    B('F', 'Ft', 1178, 402, 1225, 455, 0, 500, TIM, 'Bedside'),
    # ---- first: bed 2
    B('F', 'Ft', 958, 560, 1125, 780, 0, 480, BED, 'Bed 2'),
    B('F', 'Ft', 958, 560, 1125, 610, 0, 1000, TIM, 'Bed head', False),
    B('F', 'Ft', 897, 560, 948, 607, 0, 500, TIM, 'Bedside'),
    B('F', 'Ft', 1135, 560, 1185, 607, 0, 500, TIM, 'Bedside'),
    # ---- first: bath + wc
    B('F', 'Ft', 340, 680, 422, 880, 0, 550, PORC, 'Bath'),
    B('F', 'Ft', 452, 828, 562, 890, 0, 850, CAB, 'Vanity'),
    B('F', 'Ft', 608, 815, 652, 890, 0, 400, PORC, 'Toilet', False),
    B('F', 'Ft', 610, 855, 650, 890, 400, 900, PORC, 'Cistern', False),
    # ---- first: retreat
    B('F', 'Ft', 420, 910, 680, 962, 0, 600, CAB, 'Media unit'),
    B('F', 'Ft', 338, 1165, 440, 1330, 0, 420, FAB, 'Sofa (L) A'),
    B('F', 'Fb', 338, 88, 620, 172, 0, 420, FAB, 'Sofa (L) B'),
    B('F', 'Ft', 490, 1170, 660, 1270, 0, 380, TIM, 'Coffee table', False),
    # ---- first: WIR / WIL
    B('F', 'Fb', 385, 262, 535, 385, 0, 1000, W_, 'WIR island'),
    B('F', 'Fb', 330, 510, 590, 565, 0, 2000, W_, 'Robe unit'),
    B('F', 'Fb', 640, 208, 688, 328, 0, 1900, W_, 'WIL shelves'),
    # ---- first: ensuite
    B('F', 'Fb', 885, 135, 935, 210, 0, 400, PORC, 'Toilet', False),
    B('F', 'Fb', 887, 135, 933, 160, 400, 900, PORC, 'Cistern', False),
    B('F', 'Fb', 1015, 140, 1205, 225, 0, 550, PORC, 'Bath'),
    B('F', 'Fb', 1172, 278, 1235, 520, 0, 850, CAB, 'Double vanity'),
    # ---- first: bed 1 / retreat 2
    B('F', 'Fb', 983, 716, 1170, 897, 0, 480, BED, 'Bed 1'),
    B('F', 'Fb', 1170, 716, 1225, 897, 0, 1000, TIM, 'Bed head', False),
    B('F', 'Fb', 1185, 630, 1225, 700, 0, 500, TIM, 'Bedside'),
    B('F', 'Fb', 1185, 912, 1225, 985, 0, 500, TIM, 'Bedside'),
    B('F', 'Fb', 933, 717, 975, 897, 0, 450, FAB, 'Bed bench'),
    B('F', 'Fb', 338, 697, 440, 778, 0, 420, FAB, 'Armchair'),
    B('F', 'Fb', 385, 805, 440, 860, 0, 450, TIM, 'Side table'),
    B('F', 'Fb', 465, 805, 665, 905, 0, 420, FAB, 'Sofa'),
    B('F', 'Fb', 465, 805, 665, 822, 420, 800, FAB, 'Sofa back', False),
]
# dining + outdoor chairs
FURNITURE += chairs_row('G', 'Gt', [870, 940, 1010, 1080], 835, 940, None)
FURNITURE += [B('G', 'Gt', 818, 868, 838, 908, 0, 450, FAB, 'chair', False),
              B('G', 'Gt', 1122, 868, 1142, 908, 0, 450, FAB, 'chair', False)]
for yy in (258, 310, 362):
    FURNITURE += [B('G', 'Gt', 420, yy, 440, yy + 38, -172, 278, FAB, 'chair', False),
                  B('G', 'Gt', 545, yy, 565, yy + 38, -172, 278, FAB, 'chair', False)]
FURNITURE += [B('G', 'Gt', 470, 400, 510, 440, -172, 278, FAB, 'chair', False),
              B('G', 'Gt', 470, 215, 510, 235, -172, 278, FAB, 'chair', False)]

# ----------------------------------------------------------------------------- stair (mm)
STAIR = dict(
    x_first=7340,      # riser 1 face (flight A starts here, west end)
    going=241,
    x_east=10090,      # inside face of the east wall
    zA=(8917 + ZSHIFT, 9997 + ZSHIFT),   # flight A (rear half, rises toward +X)
    zB=(10089 + ZSHIFT, 11168 + ZSHIFT),  # flight B (street half, rises toward -X, arrives at first floor)
    tread_t=50,
    void_A=(7340, 8917 + ZSHIFT, 10090, 9997 + ZSHIFT),
    void_B=(7099, 10089 + ZSHIFT, 10090, 11168 + ZSHIFT),
    guard_h=1050,
)
