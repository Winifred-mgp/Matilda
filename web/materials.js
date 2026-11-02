/* Finishes library: every selection from the interior-design addenda as a Three.js material.
 * Textures are drawn procedurally at the product's real size (plank, tile, brick, door-module dimensions)
 * and are seeded from the swatch photos embedded in finishes.js, so colour and pattern follow the real product.
 */
(function () {
  'use strict';
  const SW = window.FINISH_SWATCHES || {};
  const imgs = {};
  const redraws = [];
  let pending = 0;

  function loadImg(key) {
    if (!SW[key]) return;
    const im = new Image();
    pending++;
    im.onload = im.onerror = () => { if (--pending === 0) redraws.forEach((f) => f()); };
    im.src = SW[key];
    imgs[key] = im;
  }
  Object.keys(SW).forEach(loadImg);
  const ok = (k) => imgs[k] && imgs[k].complete && imgs[k].naturalWidth > 0;

  function rng(seed) {
    let a = seed >>> 0;
    return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  }
  const clamp = (v) => Math.max(0, Math.min(255, v));
  const shade = (hex, f) => {
    const n = parseInt(hex.slice(1), 16);
    return `rgb(${clamp(((n >> 16) & 255) * f) | 0},${clamp(((n >> 8) & 255) * f) | 0},${clamp((n & 255) * f) | 0})`;
  };
  function speckle(g, w, h, n, a, seed, light) {
    const r = rng(seed);
    for (let i = 0; i < n; i++) {
      g.fillStyle = (light ? 'rgba(255,255,255,' : 'rgba(0,0,0,') + (r() * a).toFixed(3) + ')';
      g.fillRect(r() * w, r() * h, 1 + r() * 1.5, 1 + r() * 1.5);
    }
  }
  /** a random crop of a swatch, drawn into (x,y,w,h); rot = rotate the source 90 degrees first */
  function swatchInto(g, key, x, y, w, h, r, opts) {
    opts = opts || {};
    const im = imgs[key];
    if (!ok(key)) return false;
    const sw = im.naturalWidth, sh = im.naturalHeight;
    const cw = Math.max(8, sw * (opts.min || 0.55) + r() * sw * 0.4), ch = Math.max(8, sh * (opts.min || 0.55) + r() * sh * 0.4);
    const sx = r() * (sw - cw), sy = r() * (sh - ch);
    g.save();
    if (opts.alpha) g.globalAlpha = opts.alpha;
    if (opts.rot) {
      g.translate(x + w / 2, y + h / 2); g.rotate(Math.PI / 2);
      g.drawImage(im, sx, sy, cw, ch, -h / 2, -w / 2, h, w);
    } else g.drawImage(im, sx, sy, cw, ch, x, y, w, h);
    g.restore();
    return true;
  }

  function build(THREE, aniso) {
    const T = {};          // textures
    const M = {};          // materials
    function tex(name, w, h, tileU, tileV, draw, o) {
      o = o || {};
      const c = document.createElement('canvas'); c.width = w; c.height = h;
      const g = c.getContext('2d');
      const t = new THREE.CanvasTexture(c);
      t.wrapS = o.mirror ? THREE.MirroredRepeatWrapping : THREE.RepeatWrapping;
      t.wrapT = o.mirror ? THREE.MirroredRepeatWrapping : THREE.RepeatWrapping;
      t.anisotropy = aniso; t.userData = { tile: [tileU, tileV] };
      const run = () => { g.clearRect(0, 0, w, h); draw(g, w, h); t.needsUpdate = true; };
      run(); redraws.push(run);
      T[name] = t;
      return t;
    }
    const lam = (map, extra) => new THREE.MeshLambertMaterial(Object.assign({ map }, extra || {}));
    const col = (hex, extra) => new THREE.MeshLambertMaterial(Object.assign({ color: new THREE.Color(hex) }, extra || {}));
    const gloss = (hex, sh) => new THREE.MeshPhongMaterial({ color: new THREE.Color(hex), shininess: sh || 50, specular: 0x333333 });

    // ---------------------------------------------------------------- paint (Dulux)
    M.paint = col('#EEECE5');                    // Natural White SW1F4, LRV 85
    M.ceiling = col('#F5F5F3');                  // Ceiling White
    M.trim = gloss('#EEECE5', 40);               // Aquanamel gloss, skirting / architraves / internal doors
    M.skirt = M.trim;
    M.door_white = gloss('#EEECE5', 45);
    M.monument = col('#323233');
    M.door_monument = gloss('#323233', 60);      // Aquanamel high gloss on the front door
    M.frame = col('#1C1C1D');                    // Interpon Textura Black GN305A
    M.black_matt = col('#1C1C1D');
    M.melamine = col('#F3F3F1');                 // white melamine carcass / shelving
    M.porcelain = gloss('#FAFAFA', 90);
    M.appliance = gloss('#F0F0F0', 60);
    M.steel = new THREE.MeshPhongMaterial({ color: 0xbfc1c4, shininess: 40, specular: 0x333333 });
    M.glacier = col('#E1DACD');                  // sliding robe door, Glacier vinyl
    M.parchment = col('#E6DCC6');                // sliding robe door, Parchment vinyl
    M.blanco = col('#EDE9E0');                   // Blanco Bliss: soft warm white
    M.buller = col('#EBEBE8');                   // Polytec Buller Stone Matt

    // ---------------------------------------------------------------- floors
    // Evo Natural Oak hybrid, planks 1842 x 230 mm, running lengthways (texture u = plank length)
    tex('oak', 1024, 512, 1.842, 0.92, (g, w, h) => {
      const r = rng(11), rows = 4, ph = h / rows;
      for (let i = 0; i < rows; i++) {
        const cut = (0.25 + 0.5 * ((i * 0.37) % 1)) * w;
        [[0, cut], [cut, w]].forEach(([a, b]) => {
          const f = 0.93 + r() * 0.14;
          g.fillStyle = shade('#A08A61', f); g.fillRect(a, i * ph, b - a, ph);
          swatchInto(g, 'oak', a, i * ph, b - a, ph, r, { rot: true, alpha: 0.55, min: 0.5 });
          g.fillStyle = 'rgba(40,25,10,0.5)'; g.fillRect(a, i * ph, 1.5, ph);
        });
        g.fillStyle = 'rgba(40,25,10,0.38)'; g.fillRect(0, i * ph, w, 1.6);
      }
      speckle(g, w, h, 1800, 0.05, 5, false);
    });
    M.oak = lam(T.oak);
    M.oak_table = lam(T.oak);

    // Carpet Call "Beach Isle - St Barts": very dark charcoal speckled cut pile
    tex('carpet', 256, 256, 0.8, 0.8, (g, w, h) => {
      g.fillStyle = '#433F3C'; g.fillRect(0, 0, w, h);
      speckle(g, w, h, 5200, 0.2, 21, true); speckle(g, w, h, 4200, 0.28, 22, false);
    });
    M.carpet = lam(T.carpet);

    // grout colour: floor/wall tile grout is not specified in the addenda (about 3 mm); splashbacks use Ardex Misty Grey
    const GROUT = '#8D8D8A', MISTY = '#A9AAA7';
    function tileGrid(g, w, h, cols, rows, key, base, grout, seed, gap) {
      const r = rng(seed), tw = w / cols, th = h / rows;
      g.fillStyle = grout; g.fillRect(0, 0, w, h);
      for (let j = 0; j < rows; j++) for (let i = 0; i < cols; i++) {
        const x = i * tw + gap / 2, y = j * th + gap / 2, ww = tw - gap, hh = th - gap;
        g.fillStyle = shade(base, 0.94 + r() * 0.12); g.fillRect(x, y, ww, hh);
        swatchInto(g, key, x, y, ww, hh, r, { alpha: 0.9, min: 0.35 });
      }
    }
    // Omniform Grey Matt 450 x 450 (floor and wall)
    tex('omniform', 512, 512, 0.9, 0.9, (g, w, h) => tileGrid(g, w, h, 2, 2, 'omniform', '#C4C4C3', GROUT, 31, 2));
    M.tile_omni = lam(T.omniform);
    M.skirt_tile = col('#C4C4C3');
    // Belga Charcoal textured 300 x 600 (laid vertically) and Omni Stone Charcoal Silk 300 x 600
    tex('belga', 512, 512, 0.6, 0.6, (g, w, h) => tileGrid(g, w, h, 2, 1, 'belga', '#4B4642', '#6E6C69', 41, 2));
    M.tile_belga = lam(T.belga);
    tex('omnistone', 512, 512, 0.6, 0.6, (g, w, h) => tileGrid(g, w, h, 2, 1, 'omnistone', '#5E5F5A', '#6E6C69', 51, 2));
    M.tile_omnistone = lam(T.omnistone);
    // Nostalgia White Satin 75 x 300, brick bond horizontal, Misty Grey grout
    tex('nostalgia', 512, 256, 0.6, 0.3, (g, w, h) => {
      const r = rng(61), rows = 4, th = h / rows, tw = w / 2;
      g.fillStyle = MISTY; g.fillRect(0, 0, w, h);
      for (let j = 0; j < rows; j++) for (let i = -1; i < 3; i++) {
        const x = i * tw + (j % 2) * tw / 2;
        g.fillStyle = shade('#F4F4F2', 0.95 + r() * 0.06); g.fillRect(x + 1, j * th + 1, tw - 2, th - 2);
        g.fillStyle = 'rgba(255,255,255,0.35)'; g.fillRect(x + 1, j * th + 1, tw - 2, 2);
      }
    });
    M.tile_nostalgia = lam(T.nostalgia);
    // Fire Fingers White Gloss 293 x 296 mosaic sheet (vertical stack)
    tex('fire', 256, 256, 0.293, 0.296, (g, w, h) => {
      if (ok('fire')) g.drawImage(imgs.fire, 0, 0, w, h);
      else {
        g.fillStyle = MISTY; g.fillRect(0, 0, w, h);
        for (let i = 0; i < 12; i++) { g.fillStyle = '#F4F4F2'; g.fillRect(i * w / 12 + 2, 2, w / 12 - 4, h - 4); }
      }
    });
    M.tile_fire = new THREE.MeshPhongMaterial({ map: T.fire, shininess: 35, specular: 0x222222 });

    M.concrete = lam(tex('concrete', 256, 256, 3, 3, (g, w, h) => {
      g.fillStyle = '#A4A7A9'; g.fillRect(0, 0, w, h); speckle(g, w, h, 4200, 0.1, 71, false); speckle(g, w, h, 3000, 0.1, 72, true);
    }));

    // ---------------------------------------------------------------- stone & laminate
    // Calacatta Signature (Zenith): white with broad grey veins; 2x2 mirrored swatch so the repeat is seamless
    tex('cala', 512, 512, 2.0, 2.0, (g, w, h) => {
      g.fillStyle = '#E9E9E7'; g.fillRect(0, 0, w, h);
      if (ok('calacatta')) {
        const im = imgs.calacatta, q = w / 2;
        [[0, 0, 1, 1], [q, 0, -1, 1], [0, q, 1, -1], [q, q, -1, -1]].forEach(([x, y, sx, sy]) => {
          g.save(); g.translate(x + (sx < 0 ? q : 0), y + (sy < 0 ? q : 0)); g.scale(sx, sy); g.drawImage(im, 0, 0, q, q); g.restore();
        });
      }
    });
    M.cala = new THREE.MeshPhongMaterial({ map: T.cala, shininess: 70, specular: 0x444444 });

    // Cabinetry fronts. Module = one 600 mm wide door (or three drawers), full height of the unit.
    function cabinet(name, key, base, mode, seed) {
      tex(name, 256, 376, 0.6, 0.88, (g, w, h) => {
        const r = rng(seed);
        g.fillStyle = base; g.fillRect(0, 0, w, h);
        if (!swatchInto(g, key, 0, 0, w, h, () => 0.2 + r() * 0.5, { alpha: 0.9, min: 0.45 })) { /* fallback colour only */ }
        const kick = h * 0.15, gap = 3;
        g.fillStyle = 'rgba(15,10,8,0.82)'; g.fillRect(0, h - kick, w, kick);               // kickboard
        g.fillStyle = 'rgba(12,8,6,0.78)';
        g.fillRect(0, 0, gap, h - kick); g.fillRect(w - gap, 0, gap, h - kick); g.fillRect(0, h - kick - gap, w, gap); g.fillRect(0, 0, w, gap);
        const bevel = (x, y, ww, hh) => {                                                  // Chifley: slim rail, recessed centre
          g.strokeStyle = 'rgba(0,0,0,0.38)'; g.lineWidth = 1.5; g.strokeRect(x, y, ww, hh);
          g.strokeStyle = 'rgba(255,255,255,0.20)'; g.beginPath(); g.moveTo(x, y + hh); g.lineTo(x, y); g.lineTo(x + ww, y); g.stroke();
        };
        g.fillStyle = '#1C1C1D';
        if (mode === 'doors') {
          bevel(10, 10, w - 20, h - kick - 20);
          g.fillRect(w - 24, 18, 6, 0.16 / 0.88 * h);                                       // Livorno 160 mm, vertical, top of the cupboard
        } else {
          const dh = (h - kick) / 3;
          for (let i = 0; i < 3; i++) {
            bevel(10, i * dh + 8, w - 20, dh - 14);
            if (i > 0) { g.fillStyle = 'rgba(12,8,6,0.78)'; g.fillRect(0, i * dh - 1.5, w, 3); }
            g.fillStyle = '#1C1C1D'; g.fillRect(w / 2 - 0.256 / 0.6 * w / 2, i * dh + 0.05 / 0.88 * h, 0.256 / 0.6 * w, 6);   // Livorno D 256 mm
          }
        }
      });
    }
    cabinet('cab_flo', 'florentine', '#85644D', 'doors', 81);
    cabinet('cab_flo_dr', 'florentine', '#85644D', 'drawers', 82);
    cabinet('cab_not', 'notaio', '#8E7863', 'doors', 83);
    ['cab_flo', 'cab_flo_dr', 'cab_not'].forEach((k) => { M[k] = lam(T[k]); M[k].userData.cab = true; });
    // plain walnut for tops and ends of cabinets
    tex('walnut', 128, 128, 0.5, 0.5, (g, w, h) => { g.fillStyle = '#85644D'; g.fillRect(0, 0, w, h); swatchInto(g, 'florentine', 0, 0, w, h, rng(5), { alpha: 0.9 }); }, { mirror: true });
    M.walnut = lam(T.walnut);

    // ---------------------------------------------------------------- appliances & fixtures (decals on the box faces)
    tex('cooktop', 512, 300, 0.9, 0.53, (g, w, h) => {      // F&P CI905CTB2, 900 x 530, five zones, black glass
      g.fillStyle = '#0E0F11'; g.fillRect(0, 0, w, h);
      g.strokeStyle = 'rgba(190,190,195,0.55)'; g.lineWidth = 2;
      [[0.17, 0.3, 0.1], [0.17, 0.72, 0.1], [0.5, 0.5, 0.13], [0.83, 0.3, 0.1], [0.83, 0.72, 0.1]].forEach(([x, y, r]) => { g.beginPath(); g.arc(x * w, y * h, r * h * 1.2, 0, 7); g.stroke(); });
      g.fillStyle = 'rgba(190,190,195,0.5)'; g.fillRect(w * 0.35, h * 0.9, w * 0.3, 3);
    });
    M.cooktop = [col('#0E0F11'), col('#0E0F11'), new THREE.MeshPhongMaterial({ map: T.cooktop, shininess: 120, specular: 0x777777 }), col('#0E0F11'), col('#0E0F11'), col('#0E0F11')];
    tex('sink', 512, 290, 0.76, 0.44, (g, w, h) => {        // Franke Maris double bowl, matt black
      g.fillStyle = '#222426'; g.fillRect(0, 0, w, h);
      [[0.06, 0.1], [0.53, 0.1]].forEach(([x, y]) => { g.fillStyle = '#17181A'; g.fillRect(x * w, y * h, 0.41 * w, 0.8 * h); g.fillStyle = '#2E3033'; g.beginPath(); g.arc((x + 0.205) * w, (y + 0.4) * h, 9, 0, 7); g.fill(); });
    });
    M.sink = [col('#222426'), col('#222426'), new THREE.MeshLambertMaterial({ map: T.sink }), col('#222426'), col('#222426'), col('#222426')];
    tex('basin', 256, 190, 0.46, 0.35, (g, w, h) => {       // inset basin, white
      g.fillStyle = '#F6F6F4'; g.fillRect(0, 0, w, h);
      g.fillStyle = '#E3E4E2'; g.beginPath(); g.ellipse(w / 2, h / 2, w * 0.4, h * 0.38, 0, 0, 7); g.fill();
      g.fillStyle = '#C9CACA'; g.beginPath(); g.arc(w / 2, h / 2, 6, 0, 7); g.fill();
    });
    M.basin = [col('#F6F6F4'), col('#F6F6F4'), new THREE.MeshPhongMaterial({ map: T.basin, shininess: 80 }), col('#F6F6F4'), col('#F6F6F4'), col('#F6F6F4')];
    tex('oven', 256, 128, 0.9, 0.54, (g, w, h) => {         // F&P OB90S9LEX2: black glass, stainless handle
      g.fillStyle = '#121315'; g.fillRect(0, 0, w, h);
      g.fillStyle = '#9EA2A6'; g.fillRect(w * 0.08, h * 0.1, w * 0.84, 5);
      g.fillStyle = 'rgba(255,255,255,0.08)'; g.fillRect(w * 0.1, h * 0.3, w * 0.8, h * 0.6);
      g.fillStyle = '#9EA2A6'; [0.2, 0.32, 0.44, 0.56, 0.68, 0.8].forEach((x) => { g.beginPath(); g.arc(w * x, h * 0.08, 3, 0, 7); g.fill(); });
    });
    M.oven = [col('#121315'), col('#121315'), col('#121315'), col('#121315'), new THREE.MeshPhongMaterial({ map: T.oven, shininess: 100, specular: 0x666666 }), col('#121315')];
    // Centurion Cosmopolitan sectional garage door, Monument: three wide horizontal panels (Wright facade elevation)
    tex('garage', 512, 256, 4.8, 2.15, (g, w, h) => {
      g.fillStyle = '#323233'; g.fillRect(0, 0, w, h);
      for (let i = 1; i < 3; i++) { g.fillStyle = 'rgba(0,0,0,0.65)'; g.fillRect(0, i * h / 3 - 2, w, 4); g.fillStyle = 'rgba(255,255,255,0.10)'; g.fillRect(0, i * h / 3 + 2, w, 1.5); }
      g.strokeStyle = 'rgba(0,0,0,0.5)'; g.lineWidth = 3; g.strokeRect(1, 1, w - 2, h - 2);
    });
    M.garage_door = [col('#323233'), col('#323233'), col('#323233'), col('#323233'), new THREE.MeshLambertMaterial({ map: T.garage }), new THREE.MeshLambertMaterial({ map: T.garage })];

    // ---------------------------------------------------------------- timber (Intergrain Natural Stain, Charcoal)
    tex('stain', 256, 256, 0.6, 0.6, (g, w, h) => {
      g.fillStyle = '#514837'; g.fillRect(0, 0, w, h);
      if (ok('stain')) { const q = w / 2, im = imgs.stain; [[0, 0, 1, 1], [q, 0, -1, 1], [0, q, 1, -1], [q, q, -1, -1]].forEach(([x, y, sx, sy]) => { g.save(); g.translate(x + (sx < 0 ? q : 0), y + (sy < 0 ? q : 0)); g.scale(sx, sy); g.drawImage(im, 0, 0, q, q); g.restore(); }); }
      speckle(g, w, h, 1500, 0.07, 91, false);
    }, { mirror: true });
    M.stain = lam(T.stain); M.stain_post = M.stain; M.stain_wood = M.stain;

    // ---------------------------------------------------------------- exterior
    // Austral Bricks Melbourne "Hawthorn": 230 x 76 mm bricks, 10 mm joints, stretcher bond; natural grey mortar
    function brickPalette() {
      const p = [];
      if (ok('brick')) {
        const c = document.createElement('canvas'); c.width = 54; c.height = 54;
        const g = c.getContext('2d'); g.drawImage(imgs.brick, 0, 0, 54, 54);
        const d = g.getImageData(0, 0, 54, 54).data, r = rng(3);
        for (let tries = 0; tries < 4000 && p.length < 90; tries++) {
          const i = ((r() * 54) | 0) * 54 + ((r() * 54) | 0), R = d[i * 4], G = d[i * 4 + 1], B = d[i * 4 + 2];
          if ((R + G + B) / 3 < 150) p.push([R, G, B]);          // brick, not mortar
        }
      }
      return p.length > 20 ? p : [[138, 90, 69], [107, 74, 63], [125, 106, 82], [74, 61, 58], [150, 98, 76]];
    }
    tex('brick', 1024, 768, 0.96, 0.688, (g, w, h) => {
      const pal = brickPalette(), r = rng(7), pm = w / 0.96, bw = 0.23 * pm, bh = 0.076 * pm, j = 0.01 * pm;
      g.fillStyle = '#A8A59D'; g.fillRect(0, 0, w, h);
      for (let row = 0; row < 8; row++) {
        const y = row * (bh + j), off = (row % 2) * (bw + j) / 2;
        for (let c = -1; c < 5; c++) {
          const x = c * (bw + j) + off, p = pal[(r() * pal.length) | 0], f = 0.92 + r() * 0.16;
          g.fillStyle = `rgb(${clamp(p[0] * f) | 0},${clamp(p[1] * f) | 0},${clamp(p[2] * f) | 0})`;
          g.fillRect(x, y, bw, bh);
          for (let b = 0; b < 5; b++) {
            const q = pal[(r() * pal.length) | 0];
            g.fillStyle = `rgba(${q[0]},${q[1]},${q[2]},0.45)`;
            g.fillRect(x + r() * bw * 0.8, y + r() * bh * 0.7, 6 + r() * bw * 0.35, 4 + r() * bh * 0.4);
          }
          g.fillStyle = 'rgba(0,0,0,0.12)'; g.fillRect(x, y + bh - 3, bw, 3);
        }
      }
      speckle(g, w, h, 5000, 0.12, 8, false);
    });
    M.brick = lam(T.brick);
    // Dulux Beige Royal Half S15B1H with a fine Acratex texture
    tex('render', 256, 256, 1, 1, (g, w, h) => { g.fillStyle = '#DAD4C7'; g.fillRect(0, 0, w, h); speckle(g, w, h, 5000, 0.07, 9, false); speckle(g, w, h, 3500, 0.07, 10, true); });
    M.render = lam(T.render);
    // Innova Stratum: 300 mm planks with a 16 mm joint, painted Monument
    tex('cladding', 128, 256, 0.5, 0.632, (g, w, h) => {
      g.fillStyle = '#323233'; g.fillRect(0, 0, w, h);
      for (let i = 0; i < 2; i++) { const y = i * h / 2; g.fillStyle = 'rgba(0,0,0,0.7)'; g.fillRect(0, y, w, 16 / 632 * h); g.fillStyle = 'rgba(255,255,255,0.06)'; g.fillRect(0, y + 16 / 632 * h, w, 3); }
    });
    M.cladding = lam(T.cladding);
    // metal roof, COLORBOND Monument ("Monolith"); ribs run down the slope
    tex('roof', 128, 128, 0.25, 0.25, (g, w, h) => {
      g.fillStyle = '#323233'; g.fillRect(0, 0, w, h);
      for (let i = 0; i < 2; i++) { const x = i * w / 2; g.fillStyle = 'rgba(255,255,255,0.12)'; g.fillRect(x + 6, 0, 8, h); g.fillStyle = 'rgba(0,0,0,0.35)'; g.fillRect(x + w / 4, 0, 10, h); }
    });
    M.roof = new THREE.MeshPhongMaterial({ map: T.roof, shininess: 25, specular: 0x222222, side: THREE.DoubleSide });
    M.fascia = col('#323233');

    return { M, T, redrawAll: () => redraws.forEach((f) => f()) };
  }
  window.Finishes = { build };
})();
