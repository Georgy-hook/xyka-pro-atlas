/* Acceptance of the issued atlas, not a mock scene. Run in Node with playwright-core.
 * PLAYWRIGHT_CORE=/path/to/playwright-core CHROME=/path/to/chrome node model/verify_atlas_ui.cjs OUTPUT_ROOT SCRATCH
 * The viewer itself needs neither Node nor Playwright. Browser is offline throughout.
 */
'use strict';

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs/promises');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {chromium} = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');

const root = path.resolve(process.argv[2] || '.');
const outputs = path.resolve(process.argv[3] || require('node:os').tmpdir(), 'atlas-acceptance');
const report = {scenarios: [], screenshotSHA256: {}};
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const verify = (name, condition) => {
  assert.ok(condition, name);
  report.scenarios.push(name);
};

async function run() {
  await fs.mkdir(outputs, {recursive: true});
  const index = path.join(root, 'atlas', 'index.html');
  const sourceHash = hash(await fs.readFile(path.join(root, 'XKAH_PRO_A43_rebuilt.FCStd')));
  const glb = await fs.readFile(path.join(root, 'atlas/data/atlas.glb'));
  report.glbSHA256 = hash(glb);
  const native = JSON.parse(await fs.readFile(path.join(root, 'VERIFICATION.json'), 'utf8'));
  assert.equal(native.source_sha256, sourceHash);
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROME || undefined,
    args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--disable-background-networking'],
  });
  try {
    report.browser = `Chromium ${browser.version()}`;
    const context = await browser.newContext({offline: true, viewport: {width: 1440, height: 960}, deviceScaleFactor: 1});
    const page = await context.newPage();
    const errors = [];
    const external = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('request', request => { if (/^https?:/i.test(request.url())) external.push(request.url()); });
    page.setDefaultTimeout(30000);
    const state = () => page.evaluate(() => window.AtlasUI.getState());
    const frames = () => page.evaluate(() => new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done))));
    const viewHash = async () => {
      await frames();
      return hash(await page.locator('#atlas-canvas').screenshot());
    };
    const shot = async name => {
      await page.mouse.move(2, 1);
      await page.evaluate(() => window.scrollTo(0, 0));
      await frames();
      const bytes = await page.screenshot({path: path.join(outputs, `${name}.png`), animations: 'disabled'});
      report.screenshotSHA256[name] = hash(bytes);
    };
    await page.goto(pathToFileURL(index).href);
    await page.waitForSelector('html[data-ui-ready="true"][data-viewport-state="ready"]');
    const scene = await page.evaluate(() => ({
      sha: ATLAS_SCENE.sourceSHA256,
      n: ATLAS_SCENE.parts.length,
      triangles: ATLAS_SCENE.triangleCount,
      groups: ATLAS_SCENE.groups.map(group => group.id),
      catalog: ATLAS_NOTES.finishes.map(f => f.id),
      classes: Object.fromEntries(ATLAS_SCENE.groups.map(g => [g.id, ATLAS_SCENE.parts.filter(p => p.group === g.id).length])),
    }));
    verify('file:// opened the matching native scene with WebGL', scene.sha === sourceHash && scene.n === native.physical_features);
    report.sourceSHA256 = sourceHash;
    report.physicalFeatures = scene.n;
    report.triangleCount = scene.triangles;
    report.groupCounts = scene.classes;
    const list = page.locator('#part-list [data-part-id]');
    verify('one catalogue row for each independently selectable CAD leaf', await list.count() === scene.n);
    const colors = [];
    for (const finish of scene.catalog) {
      await page.locator(`[data-finish="${finish}"]`).click();
      assert.equal((await state()).finish, finish);
      colors.push(await viewHash());
      if (finish === 'blue') await shot('atlas-assembly');
    }
    verify('four real surface palettes render four distinct frames', new Set(colors).size === 4);
    await page.locator('[data-action="reset"]').click();
    const before = await viewHash();
    await page.locator('#explode-slider [role="slider"]').focus();
    await page.keyboard.press('End');
    verify('keyboard operates the custom explode slider and changes geometry on screen',
      (await state()).explode === 1 && await viewHash() !== before);
    await shot('atlas-exploded');
    for (const grp of scene.groups) {
      await page.locator(`[data-group="${grp}"]`).click();
      assert.equal(await list.count(), scene.classes[grp]);
      assert.equal((await state()).group, grp);
      if (grp === 'MainPCB') await shot('atlas-mainboard');
    }
    verify('all seven subsystem tabs load their own CAD parts', scene.groups.length === 7 && scene.classes.Harness === 14);
    await page.locator('[data-group="DisplayPCB"]').click();
    await page.locator('#part-search').fill('UiPerforatedLand');
    assert.equal(await list.count(), 1);
    await page.locator('#part-search').press('Enter');
    verify('keyboard search selects the actual perforated region of the display PCB',
      (await state()).selected === 'UiPerforatedLand' && await page.locator('#part-id').textContent() === 'UiPerforatedLand');
    const broad = await viewHash();
    await page.locator('[data-action="isolate"]').click();
    verify('isolation changes the view; unrelated bodies disappear', (await state()).isolated === 'UiPerforatedLand' && await viewHash() !== broad);
    await page.locator('[data-action="leave-isolation"]').click();
    assert.ok(!(await state()).isolated);
    await page.locator('[data-action="reset"]').click();
    const box = await page.locator('#atlas-canvas').boundingBox();
    for (const [x, y] of [[.5, .5], [.48, .4], [.53, .62]]) {
      await page.mouse.click(box.x + x * box.width, box.y + y * box.height);
      if ((await state()).selected) break;
    }
    verify('physical canvas pick opens a catalogue passport', Boolean((await state()).selected));
    await page.locator('[data-page="research"]').click();
    verify('research cites actual external sources without network fetches', await page.locator('#research a[href^="https://"]').count() >= 4);
    await page.locator('#research [data-ev-part="MechHeaterPlate"]').first().click();
    verify('evidence opens the linked heater feature', (await state()).selected === 'MechHeaterPlate');
    await page.locator('[data-page="specs"]').click();
    const content = await page.locator('#spec-body').innerText();
    verify('catalogue widths are distinct from photo-derived dimensions', /75 мм/.test(content) && /70 мм/.test(content));
    await page.locator('[data-page="assembly"]').click();
    await page.locator('[data-action="reset"]').click();
    await page.locator('[data-group="MainPCB"]').focus();
    await page.keyboard.press('ArrowRight');
    verify('arrow keys move between subsystem tabs', (await state()).group === 'DisplayPCB');
    await page.setViewportSize({width: 390, height: 844});
    const width = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);
    verify('mobile layout has no document-level horizontal overflow', width[0] <= width[1] + 1);
    await page.locator('[data-action="reset"]').click();
    await shot('atlas-mobile');
    verify('no uncaught browser exception and no remote request', !errors.length && !external.length);
    await context.close();
    const fallback = await browser.newContext({offline: true});
    await fallback.addInitScript(() => {
      const nativeGet = HTMLCanvasElement.prototype.getContext;
      HTMLCanvasElement.prototype.getContext = function(type, ...args) {
        return type.includes('webgl') ? null : nativeGet.call(this, type, ...args);
      };
    });
    const alt = await fallback.newPage();
    await alt.goto(pathToFileURL(index).href);
    await alt.waitForSelector('html[data-viewport-state="fallback"]');
    await alt.locator('[data-group="Harness"]').click();
    verify('explicit WebGL fallback retains all 14 harness entries and a genuine CAD illustration',
      await alt.locator('#part-list [data-part-id]').count() === 14 &&
      await alt.locator('#print-image').evaluate(img => img.complete && img.naturalWidth > 100));
    await fallback.close();
    await fs.writeFile(path.join(outputs, 'ATLAS_ACCEPTANCE.json'), JSON.stringify(report, null, 2) + '\n');
    console.log(`PASS ${report.scenarios.length} acceptance scenarios, ${scene.n} physical features, ${scene.triangles} triangles. Outputs: ${outputs}`);
  } finally {
    await browser.close();
  }
}

run().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
