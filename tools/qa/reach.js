// Reachability: flood-fills every spot a walker can reach, with all doors closed and then all open.
// Needs: npm i playwright   (and its Chromium).   Run: node tools/qa/reach.js
const { chromium } = require('playwright');
const path = require('path');
const APP = 'file://' + path.resolve(__dirname, '../../web/index.html');
(async () => {
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 800, height: 480 } });
  const errs = [];
  page.on('console', m => { if (['error', 'warning'].includes(m.type())) errs.push(m.type() + ': ' + m.text().slice(0, 260)); });
  page.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  await page.goto(APP + '?q=fast');
  await page.waitForTimeout(2500);
  const info = await page.evaluate(() => ({ doors: __tour.doors().length, coll: __tour.counts.coll, names: __tour.doors().map(d => d.l + ' ' + d.n) }));
  console.log('doors', info.doors, 'coll', info.coll);
  const closed = await page.evaluate(() => { const r = __tour.reach(); return { cells: r.cells, maxFeet: r.maxFeet, far: r.rooms.filter(x => x[1] > 0.9).map(x => x.join(':')) }; });
  console.log('CLOSED  cells', closed.cells, 'maxFeet', closed.maxFeet, 'unreached', closed.far.length, closed.far.join(' | '));
  await page.evaluate(() => __tour.setDoors(true));
  const open = await page.evaluate(() => { const r = __tour.reach(); return { cells: r.cells, maxFeet: r.maxFeet, far: r.rooms.filter(x => x[1] > 0.9).map(x => x.join(':')) }; });
  console.log('OPEN    cells', open.cells, 'maxFeet', open.maxFeet, 'unreached', open.far.length, open.far.join(' | '));
  await page.evaluate(() => __tour.setDoors(false));
  const back = await page.evaluate(() => __tour.reach().cells);
  console.log('CLOSED again cells', back);
  console.log('ERRORS', errs.length); errs.slice(0, 10).forEach(e => console.log(e));
  await browser.close();
})();
