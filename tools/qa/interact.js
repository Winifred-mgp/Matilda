// Door interaction: closed doors block, E / click / Open-all work, closing refuses while the leaf would sweep the player.
// Needs: npm i playwright.   Run: node tools/qa/interact.js
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
  const NAME = 'Bed 3 door';
  const st = () => page.evaluate((n) => { const d = __tour.doors().find(q => q.n === n); return { e: +d.e.toFixed(2), goal: d.goal, x: +__tour.P.x.toFixed(2), z: +__tour.P.z.toFixed(2) }; }, NAME);
  const settle = async (ms = 25000) => { const t0 = Date.now(); while (Date.now() - t0 < ms) { if (await page.evaluate(() => __tour.doors().every(d => d.e === d.goal))) return true; await page.waitForTimeout(150); } return false; };
  // hold W until x passes `xmax` (or timeout); frames are slow in software rendering so poll rather than time
  const walkUntil = async (xmax, ms = 14000) => { await page.keyboard.down('KeyW'); const t0 = Date.now(); while (Date.now() - t0 < ms) { if ((await st()).x > xmax) break; await page.waitForTimeout(150); } await page.keyboard.up('KeyW'); await page.waitForTimeout(300); };
  const ok = (name, cond, extra) => console.log((cond ? 'PASS ' : 'FAIL ') + name + (extra !== undefined ? '  ' + JSON.stringify(extra) : ''));
  const stand = (x) => page.evaluate((x) => __tour.teleport(x, 5755, 'F', x < 7000 ? -Math.PI / 2 : Math.PI / 2, -0.02), x);

  // The hallway runs between the Bed 4 door (x 5.82) and the Bed 3 door (x 7.02); Bed 3 is to the east.
  await stand(6120); await page.waitForTimeout(400);
  ok('aim sees Bed 3 door from the hall', (await page.evaluate(() => __tour.aimedDoor())) === NAME);
  await walkUntil(7.3, 9000);
  let s = await st(); ok('closed door blocks the walker (stops short of x 6.85)', s.x < 6.85, s);

  await stand(6120); await page.waitForTimeout(300);
  await page.keyboard.press('KeyE'); await settle();
  s = await st(); ok('E opens the door', s.goal === 1 && s.e === 1, s);
  await walkUntil(7.3);
  s = await st(); ok('walker passes through the open door (x > 7.3)', s.x > 7.3, s);

  // standing in the swing area: closing is refused
  await stand(7500); await page.waitForTimeout(400);
  ok('aim sees the open door from inside Bed 3', (await page.evaluate(() => __tour.aimedDoor())) === NAME);
  await page.keyboard.press('KeyE'); await page.waitForTimeout(800); await settle();
  s = await st(); ok('close refused while standing in the leaf swing', s.goal === 1 && s.e === 1, s);
  // beyond reach: nothing is targeted
  await stand(9700); await page.waitForTimeout(400);
  ok('nothing targeted from 2.7 m away', (await page.evaluate(() => __tour.aimedDoor())) !== NAME);
  // step clear: closes
  await stand(8600); await page.waitForTimeout(400);
  await page.keyboard.press('KeyE'); await settle();
  s = await st(); ok('E closes it from 1.6 m away', s.goal === 0 && s.e === 0, s);

  // the pull-down menu checkbox, with the player somewhere clear of every swing
  await page.evaluate(() => __tour.teleport(8000, 2000, 'F', 0, 0));
  await page.click('#tDoors'); await settle();
  ok('Open all doors opens every door', await page.evaluate(() => __tour.doors().every(d => d.goal === 1 && d.e === 1)));
  await page.click('#tDoors'); await settle();
  ok('and closes every door again', await page.evaluate(() => __tour.doors().every(d => d.goal === 0 && d.e === 0)), await page.evaluate(() => __tour.doors().filter(d => d.goal).map(d => d.n)));

  // mouse click on the door (clear the menu panel out of the way first, as it overlaps the crosshair at this tiny size)
  await page.evaluate(() => { document.getElementById('top').style.display = 'none'; });
  await stand(6120); await page.waitForTimeout(400);
  await page.mouse.click(400, 240); await settle();
  s = await st(); ok('click on the door opens it', s.goal === 1, s);
  await page.mouse.click(400, 240); await settle();
  s = await st(); ok('click again closes it', s.goal === 0, s);

  // line of sight: Bed 4 door is behind a wall from inside Bed 3
  await stand(7500);
  await page.evaluate(() => { __tour.P.yaw = 0; });            // face -z... toward the room's rear wall
  await page.waitForTimeout(400);
  ok('nothing targeted when facing a plain wall', (await page.evaluate(() => __tour.aimedDoor())) === null);

  // dollhouse: open all doors and look at cut-away (must not throw)
  await page.evaluate(() => { __tour.setMode('orbit'); __tour.setDoors(true); });
  await page.waitForTimeout(1500);
  console.log('ERRORS', errs.length); errs.slice(0, 10).forEach(e => console.log(e));
  console.log('finished');
  await browser.close();
})();
