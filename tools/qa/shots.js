// Screenshots from explicit camera positions.   node tools/qa/shots.js <quality> <w> <h> <tag> '<json [{name, js, wait}]>'
//   js runs in the page, e.g. "__tour.teleport(6468,17729,'G',0,-0.02)".   Output: ./shots/<tag>_<name>.png (create the folder first).
const { chromium } = require('playwright');
const path = require('path');
const APP = 'file://' + path.resolve(__dirname, '../../web/index.html');
(async () => {
  const q = process.argv[2], vw = +process.argv[3], vh = +process.argv[4], name = process.argv[5];
  const views = JSON.parse(process.argv[6]);
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: vw, height: vh } });
  const errs = [];
  page.on('console', m => { if (['error', 'warning'].includes(m.type())) errs.push(m.type() + ': ' + m.text().slice(0, 260)); });
  page.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  const t00 = Date.now();
  await page.goto(APP + '?q=' + q);
  await page.waitForTimeout(3000);
  console.log('state', await page.evaluate(() => __tour.FX.state.quality + '/' + __tour.FX.state.mode), (Date.now() - t00) + 'ms');
  for (const v of views) {
    await page.evaluate((js) => { eval(js); }, v.js);
    await page.waitForTimeout(v.wait || 8000);
    const t0 = Date.now();
    await page.screenshot({ path: `shots/${name}_${v.name}.png`, timeout: 280000 });
    console.log('shot', v.name, (Date.now() - t0) + 'ms', 'total', (Date.now() - t00) + 'ms');
  }
  console.log('ERRORS', errs.length); errs.slice(0, 10).forEach(e => console.log(e));
  await browser.close();
})();
