#!/usr/bin/env python3
"""
Build web/finishes.js from the interior-design selection addenda PDF.

  python3 -I tools/finishes.py <addenda.pdf> web/finishes.js

* pulls the product swatch photos embedded in the addenda (pdfplumber + pdftoppm) and embeds the
  ones the 3D model uses as small JPEG data URIs
* writes the finishes catalogue (what each selection is, where it is used, what the research found)

The addenda itself is not part of the repository (it carries the client's name and address).
"""
import sys, re, json, base64, io, os, subprocess, tempfile
import pdfplumber
from PIL import Image

PICK = {   # key -> (regex on the label next to the swatch, trim white margins?)
    'brick':     (r'Hawthorn.*Brick Austral', False),
    'oak':       (r'Evo Natural Oak', False),
    'carpet':    (r'Beach Isle', False),
    'omniform':  (r'Omniform - Grey', True),
    'belga':     (r'Belga Charcoal', True),
    'omnistone': (r'Omni - Stone Charcoal', True),
    'calacatta': (r'Calacatta Signature', False),
    'buller':    (r'Buller Stone', False),
    'florentine': (r'Florentine Walnut - Woodmatt Thermolaminate', False),
    'notaio':    (r'Notaio Walnut - Matt', False),
    'glacier':   (r'Glacier', False),
    'fire':      (r'Fire Fingers', False),
    'nostalgia': (r'Nostalgia', True),
    'stain':     (r'Natural Stain - Charcoal', False),
    'silver':    (r'Matt Silver', False),
    'chifley':   (r'Chifley EM0', True),
}

# ---------------------------------------------------------------------------- catalogue
# g = group, n = product, s = selection detail, w = where it is used in the model, r = what the research established
# sw = swatch key (photo from the addenda) or c = colour chip
CATALOGUE = [
    # ---- exterior
    dict(g='Exterior', n='Roof, gutters, fascia, downpipes', s='Metal roof "Monolith" (Standard)', c='#323233',
         w='Roof (toggle), eaves, fascia, gutters',
         r='Monolith is the trade name for COLORBOND Monument. Classic finish RGB 50,50,51 (#323233); matt would be #292E2A.'),
    dict(g='Exterior', n='Face brick: Austral Bricks Melbourne, Hawthorn (Cat. 5)', s='Natural grey mortar, rolled joints', sw='brick',
         w='Sides and rear, ground and first floor; garage frontage',
         r='Hawthorn is a red/tan/brown clay blend with dark char and black frit. Standard brick 230 x 110 x 76 mm, laid as 86 mm courses.'),
    dict(g='Exterior', n='Render: Dulux Beige Royal Half S15B1H', s='Acratex 2-coat system; facade, contrast render, mouldings', c='#DAD4C7',
         w='Front facade at entry, portal and first-floor front',
         r='Dulux lists #DAD4C7 (RGB 218,212,199), LRV 69.'),
    dict(g='Exterior', n='Cladding: Innova Stratum', s='Painted COLORBOND Monument (Dulux, LRV 8)', c='#323233',
         w='Front feature cladding beside the guest bed',
         r='Fibre-cement plank 12 mm thick, 300 mm wide with a 16 mm horizontal joint.'),
    dict(g='Exterior', n='Windows and sliding doors: Interpon Textura Black GN305A', s='Aluminium frames (Bradnam\'s), black hardware', c='#1C1C1D',
         w='All window frames, stacker door',
         r='Textured, low-gloss black powder coat; same shade as the standard black.'),
    dict(g='Exterior', n='Front entry: Hume Newington XN1', s='Colorbond Monument; translucent glazing and sidelight', c='#323233',
         w='Entry door and sidelight',
         r='Flat painted door with a single tall vertical glazing slot; solid 40 mm core, 2040 x 820 mm common size.'),
    dict(g='Exterior', n='Garage door: Centurion Cosmopolitan', s='COLORBOND Monument', c='#323233',
         w='Sectional garage door, rear garage door',
         r='No public profile sheet was found; drawn as the three wide horizontal panels shown on the Wright facade elevation.'),
    dict(g='Exterior', n='Outdoor living posts: Intergrain Natural Stain, Charcoal', s='Beams in COLORBOND Monument', sw='stain',
         w='Four posts of the outdoor living area',
         r='Semi-transparent water-based stain (a third-party reading is about RGB 82,69,59), so the timber grain shows through.'),
    # ---- floors
    dict(g='Floors', n='Evo Natural Oak Hybrid, 7 mm', s='Beaumont Tiles 1299523, quad beading', sw='oak',
         w='Ground-floor living, kitchen, dining, entry, pantry',
         r='Hybrid plank 1842 x 230 mm, 0.55 mm wear layer; mid honey oak.'),
    dict(g='Floors', n='Carpet: Beach Isle, St Barts', s='Carpet Call SC5078, 100% polyester cut pile (Cat. 4); Dunlop SuperGreen 10 mm underlay', sw='carpet',
         w='Bedrooms, retreats, passage, robes and walk-ins',
         r='A very dark charcoal speckle (about #433F3C), much darker than a typical beige carpet.'),
    dict(g='Floors', n='Floor tile: Omniform Grey Matt 450 x 450', s='Beaumont Tiles 1256618, 8.5 mm', sw='omniform',
         w='Laundry, powder room, bathroom, ensuite, WC; tile skirting',
         r='Cloudy mid-light grey concrete look. Grout about 3 mm (builder note).'),
    # ---- walls & paint
    dict(g='Walls and paint', n='Internal walls: Dulux Natural White SW1F4', s='Wash&Wear Matt (Boutique standard)', c='#EEECE5',
         w='All internal walls',
         r='Dulux lists #EEECE5 (RGB 238,236,229), LRV 85, a warm neutral white.'),
    dict(g='Walls and paint', n='Trim and doors: Natural White gloss', s='Aquanamel Gloss; skirting and architraves single bevel 67 x 12 mm (Botany Bay)', c='#EEECE5',
         w='Skirting, architraves, internal doors',
         r='Primed MDF, painted in the same Natural White as the walls.'),
    dict(g='Walls and paint', n='Ceilings: Dulux Ceiling White', s='Professional Ceiling Flat, 75 mm cove cornice', c='#F5F5F3',
         w='All ceilings', r='Flat white ceiling paint.'),
    dict(g='Walls and paint', n='Staircase: Intergrain Natural Stain, Charcoal', s='Kiln-dried hardwood treads and risers; square painted wall rail; black brackets BR01', sw='stain',
         w='Treads, risers, stair balustrade',
         r='Modernist U-shaped open-to-bottom stair; stain lets the hardwood grain show.'),
    # ---- tiles & splashbacks
    dict(g='Tiles and splashbacks', n='Wall tile: Omniform Grey Matt 450 x 450', s='Beaumont Tiles 1256618; matt black trim 116307', sw='omniform',
         w='Bathroom, ensuite and powder room walls', r='Same tile as the floor, taken up the walls.'),
    dict(g='Tiles and splashbacks', n='Feature tile: Belga Charcoal textured 300 x 600', s='Beaumont Tiles 1295141', sw='belga',
         w='Bathroom and powder room feature wall', r='Dark charcoal with a cloudy texture, 8.5 mm.'),
    dict(g='Tiles and splashbacks', n='Feature tile: Omni Stone Charcoal Silk 300 x 600', s='Beaumont Tiles 1212966, rectified', sw='omnistone',
         w='Ensuite feature wall', r='Dark grey stone look with pale veining, 10 mm.'),
    dict(g='Tiles and splashbacks', n='Kitchen splashback: Nostalgia White Satin 75 x 300', s='Beaumont Tiles 1002460; Ardex FG8 241 Misty Grey grout; brick-bond horizontal', sw='nostalgia',
         w='Wall behind the kitchen benches', r='Satin white subway tile; Misty Grey is a mid-light grey grout.'),
    dict(g='Tiles and splashbacks', n='Splashback mosaic: Fire Fingers White Gloss 293 x 296', s='Beaumont Tiles 1222049; stackbond vertical, Misty Grey grout', sw='fire',
         w='Laundry, bathroom, powder room splashbacks', r='White gloss finger mosaic on a sheet; vertical stack bond.'),
    # ---- stone, laminate, cabinetry
    dict(g='Stone and joinery', n='Benchtop: Calacatta Signature (Zenith)', s='Stone Ambassador, 40 mm Aris edge, 2 waterfall ends', sw='calacatta',
         w='Kitchen benches and island, waterfall island ends', r='Crisp white with broad grey veins; crystalline-silica-free.'),
    dict(g='Stone and joinery', n='Benchtop: Blanco Bliss (Zenith)', s='Stone Ambassador, 20 mm Aris edge', c='#EDE9E0',
         w='Bathroom, ensuite and powder room vanities', r='Soft warm tones on a white base.'),
    dict(g='Stone and joinery', n='Laundry benchtop: Polytec Buller Stone Matt', s='33 mm Tight Form edge', sw='buller',
         w='Laundry bench', r='Matt off-white stone-look laminate.'),
    dict(g='Stone and joinery', n='Cabinetry: Polytec Florentine Walnut Woodmatt', s='Thermolaminate, Chifley EM0 (Style 4) profile, white melamine carcass', sw='florentine',
         w='Kitchen base, island and overheads; vanities',
         r='Rich chocolate to mid browns with vertical grain; Chifley is a 6 mm rail around a recessed centre, 18 mm door.'),
    dict(g='Stone and joinery', n='Laundry cabinetry: Polytec Notaio Walnut Matt', s='Base and overhead', sw='notaio',
         w='Laundry cabinets', r='Caramel walnut with grey-brown grain, greyer than Florentine.'),
    dict(g='Stone and joinery', n='Handles: Dorset Livorno matt black', s='160 mm bars to base cupboards; 256 mm D to drawers; finger-pull overheads', c='#1C1C1D',
         w='Kitchen, laundry, vanities', r='Momo Livorno D handle, zinc alloy, M3163 series.'),
    dict(g='Stone and joinery', n='Sliding robe doors: Parchment and Glacier vinyl', s='Parchment (Bed 2), Glacier (Beds 3 and 4); matt silver frame', sw='glacier',
         w='Bedroom robes', r='Cat. 1 vinyl wrap; matt silver aluminium frame, polished silver rail.'),
    # ---- fixtures & appliances
    dict(g='Fixtures and appliances', n='Kitchen sink: Franke Maris MRG 620 35-35, matt black', s='Double bowl topmount; Caroma Liano II pull-out mixer, matt black', c='#222426',
         w='Kitchen bench', r='760 x 440 mm overall, bowls 345 x 400 x 200 mm.'),
    dict(g='Fixtures and appliances', n='Fisher & Paykel Series 5 cooking', s='CI905CTB2 900 mm 5-zone induction, black glass; OB90S9LEX2 900 mm oven; HP90ICSX4 insert rangehood', c='#17181A',
         w='Kitchen cooktop and oven',
         r='Cooktop 900 x 530 mm; oven 895 x 478 x 564 mm; rangehood 792 x 277 x 315 mm.'),
    dict(g='Fixtures and appliances', n='Baths: Caroma Vivas 1675 (bathroom), Urbane 1675 (ensuite)', s='Island baths, white; matt black Urbane II tapware', c='#F7F7F6',
         w='Bathroom and ensuite baths', r='1675 x 760 x 425 mm (Vivas), 270 L.'),
    dict(g='Fixtures and appliances', n='Basins: Contura II inset 530 (white), Liano II 530 Pill (matt white, x2 ensuite)', s='Matt black Caroma/Clark tapware', c='#F4F4F2',
         w='Vanities', r='Inset basins in the stone benchtops.'),
    dict(g='Fixtures and appliances', n='Toilet: Stylus Basis back-to-wall', s='BAS002, back entry', c='#FAFAFA',
         w='Powder room, bathroom, WC, ensuite', r='About 380 W x 680 D x 826 H mm.'),
    dict(g='Fixtures and appliances', n='Shower: black semi-frameless screens, KFG matt black grates', s='Clark / Caroma matt black rails and mixers', c='#1C1C1D',
         w='Showers', r='2000 mm high semi-frameless screens in black frames.'),
    dict(g='Fixtures and appliances', n='Door hardware: Lockwood Element lever, matt black', s='Satin chrome hinges and cavity-slider flush pulls', c='#1C1C1D',
         w='Internal doors, garage-to-house door', r='Lever handle on a round rose.'),
]


def render_swatches(pdf_path):
    tmp = tempfile.mkdtemp()
    subprocess.run(['pdftoppm', '-r', '216', '-png', pdf_path, os.path.join(tmp, 'p')], check=True)
    pdf = pdfplumber.open(pdf_path)
    found = {}
    k = 216 / 72
    for pi, page in enumerate(pdf.pages, 1):
        words = page.extract_words()
        png = None
        for im in page.images:
            if im['x1'] - im['x0'] > 150:        # logo
                continue
            yc = (im['top'] + im['bottom']) / 2
            near = [w for w in words if abs((w['top'] + w['bottom']) / 2 - yc) < 34 and w['x0'] > im['x1'] - 2]
            near.sort(key=lambda w: (round(w['top'] / 6), w['x0']))
            label = ' '.join(w['text'] for w in near)
            for key, (rx, trim) in PICK.items():
                if key in found or not re.search(rx, label):
                    continue
                if png is None:
                    png = Image.open(os.path.join(tmp, 'p-%02d.png' % pi)).convert('RGB')
                crop = png.crop((int(im['x0'] * k) + 2, int(im['top'] * k) + 2, int(im['x1'] * k) - 2, int(im['bottom'] * k) - 2))
                if trim:
                    crop = trim_white(crop)
                found[key] = crop
    return found


def trim_white(im, thr=246):
    import numpy as np
    a = np.asarray(im.convert('L'))
    ys, xs = np.where(a < thr)
    if not len(ys):
        return im
    return im.crop((xs.min() + 1, ys.min() + 1, xs.max(), ys.max()))


def data_uri(im, maxside=128):
    im = im.copy()
    im.thumbnail((maxside, maxside), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, 'JPEG', quality=88)
    return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()


if __name__ == '__main__':
    sw = render_swatches(sys.argv[1])
    missing = [k for k in PICK if k not in sw]
    print('swatches', len(sw), 'missing', missing)
    out = {k: data_uri(v) for k, v in sw.items()}
    with open(sys.argv[2], 'w') as fh:
        fh.write('window.FINISH_SWATCHES = ' + json.dumps(out) + ';\n')
        fh.write('window.FINISH_CATALOGUE = ' + json.dumps(CATALOGUE, indent=0) + ';\n')
    print(sys.argv[2], os.path.getsize(sys.argv[2]) // 1024, 'KB')
