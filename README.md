# Matilda – Airlie 30 “Wright” 3D walkthrough

An interactive 3D model of the **ground floor and first floor** plans from the Boutique Homes sales sketch
(Airlie 30 “Wright”, V4) that you can walk through in a browser. It was built directly from the vector
geometry in the plan PDF, so wall positions and room sizes follow the drawing (first-floor outer width
8,070 mm vs 8,050 mm printed; length 19,324 mm vs 19,330 mm printed).

## Open it

* **Easiest:** open [`dist/airlie30-3d.html`](dist/airlie30-3d.html) in any modern browser (single file, works offline).
* Or serve the `web/` folder (`python3 -m http.server -d web`) and open `http://localhost:8000`.

## Controls

| | Walk | Dollhouse |
|---|---|---|
| Move | `W A S D` (hold `Shift` to hurry) · on touch: left thumb = joystick | drag = orbit |
| Look | drag the mouse (or click once to capture it) · `← →` turn · touch: right thumb | right‑drag / two fingers = pan |
| Zoom | scroll = lens zoom | scroll / pinch |
| Stairs | just walk up the U‑shaped stair – the first floor is reached the same way as in the house | |
| Doors | all doors start **closed**: face one and press `E` (or click / tap it, or tap the prompt) to open or close it | **Open all doors** in the menu |

`Tab` switches Walk ↔ Dollhouse · `C` ceilings · `M` map. The **Ground / First / Both** buttons jump
floors (Walk) or show/hide floors (Dollhouse). “Jump to room…” teleports to any room, and you can click
the mini‑map to move. Dollhouse has a **cut‑away walls** option so you can look straight into the rooms.

## Photoreal rendering

The walkthrough renders with a physically based pipeline (`web/render.js`):

* a physical sky and sun, with the sun slider sweeping all the way around the house, from low rear light through the street-side midday to the other side;
* image-based lighting from that sky, indoor / outdoor exposure adaptation like a camera, and soft room fill lights that follow you;
* a shadow-mapped sun (4096 px) so sunlight only enters through the windows, with the roof, walls and slab casting real shadows;
* screen-space ambient occlusion, a touch of bloom, ACES filmic tone mapping with sRGB output and FXAA;
* PBR materials: roughness / metalness, clearcoat on polished stone and porcelain, bump relief on grout, brick joints and carpet pile, reflective glass;
* rounded soft furniture, dressed beds and rugs, a textured lawn, driveway and path.

Use the **Quality** menu: *Photoreal* (default on desktop), *Balanced* (shadows only, default on phones) or *Fast*. If the frame rate drops, the page
steps down by itself. `?q=photo|balanced|fast` and `?t=0..100` (sun) set them from the address bar. Ambient occlusion is switched off in the
cut-away dollhouse view, where the clipped walls would confuse it.

## Finishes (from the interior design addenda)

The model carries the selections from the job's interior design addenda: 34 products across roof, brick, render,
cladding, flooring, paint, tiles, stone, joinery, fixtures and appliances. Press **Finishes** (or `F`) for the legend with
each swatch, the selection, where it is used and what the research found. Highlights:

* **Floors:** Evo Natural Oak hybrid (1842 x 230 mm planks), a very dark charcoal Beach Isle carpet, Omniform Grey 450 x 450 tiles in wet areas.
* **Walls:** Dulux Natural White `#EEECE5` with gloss skirting and doors, Ceiling White ceilings; wet rooms tiled in Omniform Grey with
  Belga Charcoal (bathroom, powder) and Omni Stone Charcoal (ensuite) feature walls, Fire Fingers mosaic and Nostalgia subway splashbacks.
* **Joinery:** Florentine Walnut cabinets with the Chifley profile and matt black Livorno handles, Calacatta Signature stone with waterfall ends,
  Notaio Walnut and Buller Stone in the laundry, Franke black sink, F&P induction cooktop and oven front.
* **Exterior:** Hawthorn brick (sides, rear, garage frontage), Beige Royal Half render, Monument cladding, Textura Black frames, Monument
  garage and entry doors, charcoal-stained timber posts and stair, and an approximate **roof** (toggle) in Monument ("Monolith").

How it was built: `tools/finishes.py` lifts the swatch photos out of the addenda PDF, `web/materials.js` redraws each product procedurally at its
real size (plank, tile, brick, door module), `tools/finish_layers.py` generates wall-face panels (skirting, tiles, splashbacks, brick/render skins)
from the room regions so they stop at doors and windows. Where the addenda gives no placement (for example which wet-room wall gets the feature tile)
the choice is an assumption. Garage, porch and outdoor-living floors are not specified, so they stay neutral concrete.

## What is modelled

* Walls, window and door openings at the positions drawn on the plans (windows are glazed). **Every door is drawn closed**: hinged
  leaves with lever handles (laundry double doors, Newington front door with its glazing slot), two‑panel sliding robe doors, the
  cavity sliders to the guest bedroom and walk‑in robe, the glass stacker door and the garage door. Open the hinged and sliding
  doors with `E` / click / tap; a door only blocks you while it is shut, and it will not close on top of you. Open
  doorways without a leaf (the walk‑in robe and ensuite openings) stay open.
* The U‑shaped stair: 17 risers (≈171 mm) and 241 mm goings, with the landing and the first‑floor stair void and balustrade.
* Floor finishes by room (timber, carpet, tile, concrete) following the shading on the plan; room names and sizes as labelled.
* Indicative furniture and fixtures from the plan symbols (beds, sofas, kitchen, vanities, cars…) for a sense of scale.
* Vertical dimensions from the master drawing set for the Airlie 30: ground ceiling 2,590 mm, first floor at +2,909 mm,
  first‑floor ceiling 2,440 mm (5,349 mm overall), window heads 2,150 mm, door heads 2,040 mm, porch and outdoor living 172 mm below the ground floor.

## Known simplifications

* Door swings and hinge sides are read from the plan arcs and are indicative; the garage door is fixed shut. The roof is an approximate hip (22.5°) with flat decks, not the engineered roof plan.
* Not placed: dishwasher, microwave, rangehood, towel rails, mirrors, flyscreens, stair wall rail. No landscaping.
* Window sill heights are typical (700–950 mm; low sills for the dining window and stacker door, high sills for bath/ensuite/stair windows) –
  the sketch only shows plan positions, not elevations.
* Furniture is drawn as simple boxes from the plan symbols and is not a fit‑out specification.

## Rebuilding the model

```bash
pip install pdfplumber pillow numpy scipy
python3 -I tools/finishes.py      addenda.pdf web/finishes.js  # swatches + catalogue from the selection addenda
python3 -I tools/extract_plan.py  sketch.pdf work          # walls + labels from the PDF -> work/extracted.json
python3 -I tools/build_model.py   work/extracted.json web/model.js work/qa   # openings, floors, stair, furniture (+ QA pictures)
python3 tools/bundle.py                                     # -> dist/airlie30-3d.html
```

`tools/spec.py` holds the hand‑read details (openings, door swings, finishes, furniture, stair) as pixel positions on 600 dpi
crops of the sketch; `tools/overlay.py` regenerates those crops with the extracted walls drawn on top.
The plan and addenda PDFs are not part of this repository (they carry the client's details).

Three.js r128 and its example post-processing passes (MIT) are vendored in `web/vendor/`.
