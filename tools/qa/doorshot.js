// usage: node doorshot.js <quality> <w> <h> <tag> '<json [{door, open, dist, wait}]>'
// Screenshots of named doors, closed or open.   node tools/qa/doorshot.js <photo|balanced|fast> <w> <h> <tag> '<json>'
//   json = [{door, open?, dist?, flip?, wait?}]   Screenshots are written to ./shots/<tag>_NN.png (create the folder first).
//   The camera stands dist metres in front of the door (on the side it swings away from; flip:true = the swing side) and faces it.
const { chromium } = require('playwright');
const path = require('path');
const APP = 'file://' + path.resolve(__dirname, '../../web/index.html');
(async () => {
  const [q, vw, vh, tag, spec] = [process.argv[2], +process.argv[3], +process.argv[4], process.argv[5], JSON.parse(process.argv[6])];
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: vw, height: vh } });
  const errs = [];
  page.on('console', m => { if (['error', 'warning'].includes(m.type())) errs.push(m.type() + ': ' + m.text().slice(0, 260)); });
  page.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  await page.goto(APP + '?q=' + q);
  await page.waitForTimeout(2500);
  await page.evaluate(() => { document.getElementById('help').classList.add('hide'); document.getElementById('top').style.display = 'none'; document.getElementById('mini').style.display = 'none'; });
  let i = 0;
  for (const s of spec) {
    const info = await page.evaluate((s) => {
      const d = window.HOUSE_MODEL.doors.find(x => x.n === s.door);
      if (!d) return null;
      const sw = d.sw || 1, dist = (s.dist || 1.6) * 1000;
      const mid = (d.lo + d.hi) / 2;
      const along = s.along || 0;
      let x, z, yaw;
      if (d.ax === 'x') { x = mid + along; z = d.c - sw * dist; yaw = sw > 0 ? Math.PI : 0; }
      else { x = d.c - sw * dist; z = mid + along; yaw = sw > 0 ? -Math.PI / 2 : Math.PI / 2; }
      if (s.flip) { if (d.ax === 'x') { z = d.c + sw * dist; yaw = sw > 0 ? 0 : Math.PI; } else { x = d.c + sw * dist; yaw = sw > 0 ? Math.PI / 2 : -Math.PI / 2; } }
      __tour.setMode('walk');
      if (s.all !== undefined) __tour.setDoors(s.all);
      __tour.toggleDoor && 0;
      if (s.open !== undefined) { const cur = __tour.doors().find(q => q.n === s.door); if (!!cur.goal !== !!s.open) __tour.toggleDoor(s.door); }
      __tour.teleport(x, z, d.l, yaw + (s.dyaw || 0), s.pitch === undefined ? -0.02 : s.pitch);
      return { x, z, aim: null };
    }, s);
    if (!info) { console.log('missing door', s.door); continue; }
    await page.waitForTimeout(s.wait || 4500);
    const aim = await page.evaluate(() => __tour.aimedDoor());
    const f = `shots/${tag}_${String(i++).padStart(2, '0')}.png`;
    await page.screenshot({ path: f, timeout: 280000 });
    console.log('shot', f, s.door, 'aim=', aim);
  }
  console.log('ERRORS', errs.length); errs.slice(0, 10).forEach(e => console.log(e));
  await browser.close();
})();
