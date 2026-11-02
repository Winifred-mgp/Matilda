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

`Tab` switches Walk ↔ Dollhouse · `C` ceilings · `M` map. The **Ground / First / Both** buttons jump
floors (Walk) or show/hide floors (Dollhouse). “Jump to room…” teleports to any room, and you can click
the mini‑map to move. Dollhouse has a **cut‑away walls** option so you can look straight into the rooms.

## What is modelled

* Walls, window and door openings at the positions drawn on the plans (windows are glazed, doors are open
  doorways with frames, sliding doors are shown half open, the garage door is closed).
* The U‑shaped stair: 17 risers (≈171 mm) and 241 mm goings, with the landing and the first‑floor stair void and balustrade.
* Floor finishes by room (timber, carpet, tile, concrete) following the shading on the plan; room names and sizes as labelled.
* Indicative furniture and fixtures from the plan symbols (beds, sofas, kitchen, vanities, cars…) for a sense of scale.
* Vertical dimensions from the master drawing set for the Airlie 30: ground ceiling 2,590 mm, first floor at +2,909 mm,
  first‑floor ceiling 2,440 mm (5,349 mm overall), window heads 2,150 mm, door heads 2,040 mm, porch and outdoor living 172 mm below the ground floor.

## Known simplifications

* Door leaves are not drawn (doorways are open) and there is no roof, cladding or site/landscaping.
* Window sill heights are typical (700–950 mm; low sills for the dining window and stacker door, high sills for bath/ensuite/stair windows) –
  the sketch only shows plan positions, not elevations.
* Furniture is drawn as simple boxes from the plan symbols and is not a fit‑out specification.

## Rebuilding the model

```bash
pip install pdfplumber pillow numpy scipy
python3 -I tools/extract_plan.py  sketch.pdf work          # walls + labels from the PDF -> work/extracted.json
python3 -I tools/build_model.py   work/extracted.json web/model.js work/qa   # openings, floors, stair, furniture (+ QA pictures)
python3 tools/bundle.py                                     # -> dist/airlie30-3d.html
```

`tools/spec.py` holds the hand‑read details (openings, finishes, furniture, stair) as pixel positions on 600 dpi
crops of the sketch; `tools/overlay.py` regenerates those crops with the extracted walls drawn on top.
The plan PDF itself is not part of this repository.

Three.js r128 (MIT) is vendored in `web/vendor/`.
