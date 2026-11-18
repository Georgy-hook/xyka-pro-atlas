/* Native paint / interaction acceptance. Run with the same PLAYWRIGHT_CORE and CHROME as
 * verify_atlas_ui.cjs: node verify_atlas_motion.cjs ABS_ISSUE_ROOT EXISTING_EXTERNAL_SCRATCH [atlas URL]
 * No page styles, replayed clocks, renderer shims, image replacements or app state setters.
 * PNGs come from Chromium's compositor, not a reconstruction of the DOM or the CAD scene.
 */
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const {pathToFileURL} = require('node:url');

const full = [0, 0, 1, 1];
const bodyField = [.02, .105, .96, .84]; // excludes the sticky masthead
const partField = [.2, .16, .6, .68]; // relative to the intrinsic (not letterboxed) housing image
const round = n => Math.round(n * 1000) / 1000;
const max = a => a.length ? Math.max(...a) : 0;
const range = a => a.length ? max(a) - Math.min(...a) : 0;
const last = a => a[a.length - 1];
const unique = a => [...new Set(a)];
const chip = id => `#product-finishes [data-product-finish="${id}"]`;
const dlg = '#language-dialog';
const ready = 'html[data-ui-ready="true"][data-viewport-state="ready"]';
const frames = (page, n = 3) => page.evaluate(n => new Promise(resolve => {
  const tick = () => --n ? requestAnimationFrame(tick) : resolve();
  requestAnimationFrame(tick);
}), n);

// Playwright's convenience actions may scroll a sticky opener into the middle of the
// document! For already-visible targets dispatch a real pointer/tap at its hit-tested center.
async function hit(page, selector, touch = false) {
  const [x, y] = await page.locator(selector).evaluate(el => {
    const r = el.getBoundingClientRect();
    const x = r.left + r.width / 2;
    const y = r.top + r.height / 2;
    if (!el.contains(document.elementFromPoint(x, y))) throw Error(`Obscured target: ${el.outerHTML.slice(0, 100)}`);
    return [x, y];
  });
  if (touch) await page.touchscreen.tap(x, y);
  else await page.mouse.click(x, y);
}

// Installed before navigation: the CSS reveal can finish *before* the big scene is ready.
// Bounded observation windows, stopped before the separate browser-native idle trace.
function installSampler() {
  let rows = [];
  let input = '';
  let actions = [];
  let handle = 0;
  const q = selector => document.querySelector(selector);
  const pref = matchMedia('(prefers-reduced-motion: reduce)');
  function note(action) {
    if (!handle) return;
    input = action;
    actions.push({action, layers: document.querySelectorAll('.finish-outgoing').length});
  }
  document.addEventListener('click', e => {
    const el = e.target.closest?.('button,a');
    if (el) note(el.id || el.dataset.productFinish || el.hreflang);
  }, true);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') note('Escape'); }, true);
  function alpha(el) {
    let value = 1;
    for (; el; el = el.parentElement) {
      const style = getComputedStyle(el);
      if (style.display === 'none' || style.visibility === 'hidden') return 0;
      value *= Number(style.opacity);
    }
    return value;
  }
  function read() {
    const img = q('#product-image');
    const stage = q('.product-visual');
    if (!stage || !img) return;
    const contour = q('.product-contour');
    const matrix = new DOMMatrix(getComputedStyle(stage).transform === 'none' ? '' : getComputedStyle(stage).transform);
    const layers = stage.querySelectorAll('.finish-outgoing');
    const title = q('#language-title');
    const open = !!q('#language-dialog')?.open;
    const choice = q('#language-dialog a[hreflang]');
    const header = q('#product-title');
    const active = document.activeElement;
    rows.push({t: performance.now(), input, y: scrollY, reduced: pref.matches,
      material: +getComputedStyle(img).opacity, title: alpha(header), shift: matrix.f,
      contour: contour ? alpha(contour) : 0, count: layers.length,
      old: layers.length ? +getComputedStyle(layers[0]).opacity : 0,
      open, ink: open ? alpha(title) : 0, choice: open ? alpha(choice) : 0,
      top: open ? title.getBoundingClientRect().top : null,
      focus: active?.id || active?.getAttribute('hreflang') || ''});
  }
  function stop() {
    cancelAnimationFrame(handle);
    handle = 0;
    return rows;
  }
  function start() {
    stop();
    rows = [];
    actions = [];
    input = '';
    const end = performance.now() + 8000;
    function tick() {
      read();
      if (performance.now() < end) handle = requestAnimationFrame(tick);
    }
    handle = requestAnimationFrame(tick);
  }
  Object.defineProperty(window, '__motionWitness', {value: {start, stop, get rows() { return rows; }, get actions() { return actions; }}});
  start();
}

// A screencast has a compositor timestamp and sends only frames Chromium actually presents.
// Acknowledge immediately; decode in a private offscreen canvas only *after* the interaction.
async function filmstrip(context, page) {
  const cdp = await context.newCDPSession(page);
  let film = [];
  cdp.on('Page.screencastFrame', event => {
    cdp.send('Page.screencastFrameAck', {sessionId: event.sessionId}).catch(() => {});
    film.push({png: event.data, time: event.metadata.timestamp * 1000});
    if (film.length > 160) film.shift();
  });
  await cdp.send('Page.startScreencast', {format: 'png', maxWidth: 720, maxHeight: 640, everyNthFrame: 1});
  return {
    cdp,
    reset() { film = []; },
    take() { return film.slice(); },
    async shot() {
      const {data} = await cdp.send('Page.captureScreenshot', {format: 'png', captureBeyondViewport: false});
      return {png: data};
    },
    async stop() { await cdp.send('Page.stopScreencast'); }
  };
}

// Decode captured PNGs (or a local issued WebP reference) in the browser's native decoder.
// Rectangles are normalized: a rescaled screencast and a full-resolution still use the same field.
async function pixels(page, pictures, rect = full, mime = 'image/png') {
  const data = await page.evaluate(async ({pictures, rect, mime}) => {
    const canvas = new OffscreenCanvas(100, 100);
    const g = canvas.getContext('2d', {willReadFrequently: true});
    g.imageSmoothingQuality = 'high';
    const result = [];
    for (const base64 of pictures) {
      const bytes = Uint8Array.fromBase64(base64);
      const bitmap = await createImageBitmap(new Blob([bytes], {type: mime}));
      const [x, y, w, h] = rect;
      g.clearRect(0, 0, 100, 100);
      g.drawImage(bitmap, x * bitmap.width, y * bitmap.height, w * bitmap.width, h * bitmap.height, 0, 0, 100, 100);
      bitmap.close();
      result.push(new Uint8Array(g.getImageData(0, 0, 100, 100).data.buffer).toBase64());
    }
    return result;
  }, {pictures: pictures.map(p => p.png), rect, mime});
  return data.map(rgb => Buffer.from(rgb, 'base64'));
}

function thin(list, limit = 28) {
  if (list.length <= limit) return list;
  return Array.from({length: limit}, (_, i) => list[Math.round(i * (list.length - 1) / (limit - 1))]);
}

function indices(buffer, keep = () => true) {
  const result = [];
  for (let i = 0; i < buffer.length; i += 4) if (keep(i)) result.push(i);
  return result;
}

function errorRGB(a, b, i) {
  return (Math.abs(a[i] - b[i]) + Math.abs(a[i + 1] - b[i + 1]) + Math.abs(a[i + 2] - b[i + 2])) / 3;
}

function distance(a, b, mask = indices(a)) {
  return mask.reduce((n, i) => n + errorRGB(a, b, i), 0) / mask.length;
}

function contrast(a) {
  // RMS contrast of the painted field, not merely the existence of a body/heading.
  let sum = 0;
  let squares = 0;
  for (let i = 0; i < a.length; i += 4) {
    const light = .2126 * a[i] + .7152 * a[i + 1] + .0722 * a[i + 2];
    sum += light;
    squares += light * light;
  }
  const n = a.length / 4;
  return Math.sqrt(Math.max(0, squares / n - (sum / n) ** 2));
}

async function imageField(page, crop = partField) {
  const field = await page.locator('#product-image').evaluate(async (img, crop) => {
    // The reduced-motion WebGL scene may be ready before the separately fetched photo.
    // Decode it for intrinsic dimensions; the filmstrip already contains the actual first paints.
    await img.decode();
    const r = img.getBoundingClientRect();
    const scale = Math.min(r.width / img.naturalWidth, r.height / img.naturalHeight);
    const w = img.naturalWidth * scale;
    const h = img.naturalHeight * scale;
    const x = r.x + (r.width - w) / 2;
    const y = r.y + (r.height - h) / 2;
    return [(x + crop[0] * w) / innerWidth, (y + crop[1] * h) / innerHeight,
      crop[2] * w / innerWidth, crop[3] * h / innerHeight];
  }, crop);
  assert.ok(field.every(Number.isFinite) && field[0] >= 0 && field[1] >= 0 &&
    field[0] + field[2] <= 1.001 && field[1] + field[3] <= 1.001, `The housing sample must be in frame: ${field}`);
  return field;
}

const begin = page => page.evaluate(() => window.__motionWitness.start());
const end = page => page.evaluate(() => window.__motionWitness.stop());
const notReplayed = rows => rows.length > 0 && rows.every(r => r.contour < .01 && r.material > .99 && Math.abs(r.shift) < .1);
const inkMoves = (r, atRest) => r.open && r.ink > .015 && r.choice > .01 &&
  (Math.abs(r.ink - atRest.ink) > .025 || Math.abs(r.choice - atRest.choice) > .025 || Math.abs(r.top - atRest.top) > .65);

async function settled(page, selector) {
  await frames(page, 2);
  await page.waitForFunction(s => {
    const el = document.querySelector(s);
    return el && !el.getAnimations({subtree: true}).some(a => a.playState === 'running' || a.pending);
  }, selector, {timeout: 5000});
  await frames(page);
}

async function settledFinish(page, id) {
  await page.waitForFunction(id => {
    const img = document.querySelector('#product-image');
    return img?.complete && img.naturalWidth && new URL(img.currentSrc).pathname.endsWith(`/hero-${id}.webp`) &&
      !document.querySelector('.finish-outgoing');
  }, id, {timeout: 5000});
  await frames(page);
}

async function picturePair(env, key, before, during, after, field) {
  const {page, save} = env;
  const shots = thin(during);
  const [a, b, ...others] = await pixels(page, [before, after, ...shots], field);
  const d = distance(a, b);
  const trajectory = others.map(p => [round(distance(p, a)), round(distance(p, b))]);
  const best = trajectory.map(([x, y]) => Math.min(x, y));
  const index = best.indexOf(max(best));
  if (env.normal && index !== -1) await save(`${key}-middle`, shots[index]);
  await save(`${key}-settled`, after);
  return {samples: shots.length, endpointRGB: round(d), middleRGB: round(max(best)), trajectory};
}

// Scan for a narrow, bright stroke alongside the sloping left wall of the *issued CAD render*.
// The alpha channel locates that physical silhouette independently of the new outline asset.
// A mere dimming of the same photograph cannot add a ridge brighter than BOTH neighbours.
function rimInk(photo, housing) {
  const light = (x, y) => photo[(y * 100 + x) * 4 + 1];
  let total = 0;
  for (let y = 19; y < 76; y++) {
    let edge = 0;
    while (edge < 98 && housing[(y * 100 + edge) * 4 + 3] < 150) edge++;
    let ridge = 0;
    for (let x = Math.max(2, edge - 6); x < Math.min(98, edge + 7); x++) {
      ridge = Math.max(ridge, light(x, y) - Math.max(light(x - 2, y), light(x + 2, y)));
    }
    total += ridge;
  }
  return total / 57;
}

// Use the same public, passive Scene callback as the original acceptance test. Measure the
// camera actually used for screen drawing, not a requested preset or the saved return state.
function observeEye() {
  document.addEventListener('load', event => {
    if (!event.target.src?.endsWith('/three-atlas.js')) return;
    const T = window.AtlasThree;
    const proto = T.Scene.prototype;
    const original = proto.onAfterRender;
    let draws = 0;
    let anchor;
    proto.onAfterRender = function(renderer, scene, eye, ...rest) {
      original.call(this, renderer, scene, eye, ...rest);
      if (renderer.domElement.id !== 'atlas-canvas' || renderer.getRenderTarget()) return;
      if (!anchor) scene.traverse(o => { if (o.userData.id === 'MechBatteryEnvelope' && o.isMesh) anchor = o; });
      const point = new T.Vector3();
      if (anchor) anchor.getWorldPosition(point);
      const depth = Math.abs(point.applyMatrix4(eye.matrixWorldInverse).z);
      window.__motionEye = {draws: ++draws, direction: eye.getWorldDirection(new T.Vector3()).toArray(),
        // Vertical NDC units per world unit at the same physical part, including real zoom/dolly.
        magnification: eye.projectionMatrix.elements[5] / (eye.isPerspectiveCamera ? depth : 1)};
    };
  }, true);
}

async function intro(env) {
  const {page, url, film, check, metric, normal, save} = env;
  film.reset();
  await page.goto(url.href, {waitUntil: 'commit'});
  await page.waitForSelector(ready, {timeout: 30000});
  await settled(page, '.product-visual');
  // No network lookup on the first paint. Keep the embedded paths exactly registered
  // to the editable standalone vector, including when opening the offline copy.
  const master = await fs.readFile(path.join(process.argv[2], 'atlas/media/hero-contour.svg'), 'utf8');
  const registration = await page.evaluate(text => {
    const reference = new DOMParser().parseFromString(text, 'image/svg+xml').documentElement;
    const shown = document.querySelector('svg.product-contour');
    const paths = svg => [...svg.querySelectorAll('path')].map(p => p.getAttribute('d').replace(/\s+/g, ' ').trim());
    return !!shown && shown.getAttribute('viewBox') === reference.getAttribute('viewBox') &&
      JSON.stringify(paths(shown)) === JSON.stringify(paths(reference)) && paths(shown).length === 12 &&
      !performance.getEntriesByType('resource').some(r => new URL(r.name).pathname.endsWith('/media/hero-contour.svg'));
  }, master);
  check(registration, 'The HTML carries the twelve source-registered contours without a separate first-paint request');
  const rows = await end(page);
  assert.ok(rows.length, 'No animation frames observed on load');
  const origin = await page.evaluate(() => performance.timeOrigin +
    (performance.getEntriesByName('first-contentful-paint')[0]?.startTime ?? 0));
  const visibleFrames = film.take().filter(frame => frame.time >= origin - 2);
  const finish = await film.shot();
  const field = await imageField(page);
  const samples = thin(visibleFrames);
  const middle = rows.filter(r => r.contour > .025 && r.material > .05 && r.material < .98);
  const metrics = {frames: rows.length, mixed: middle.length, material: unique(rows.map(r => round(r.material))),
    contourPeak: round(max(rows.map(r => r.contour))), shiftPx: round(range(rows.map(r => r.shift)))};
  metric('intro', metrics);
  check(rows.every(r => r.title > .15), 'The title remains legible throughout entry');
  check(notReplayed(rows.slice(-3)), 'Material is fully present and at rest at the end of entry');
  // A busy JS/GLB startup can skip rAF while the compositor keeps drawing the opacity
  // animation. Require actual changing native product pixels below, not a JS frame quota.
  check(normal ? middle.length > 0 && metrics.shiftPx > .3 : notReplayed(rows),
    normal ? 'Contour, material and figure visibly progress on initial load' : 'No entry motion on any reduced-motion frame');
  check(await page.locator('html').getAttribute('data-studio-seen') === 'true', 'Once-only entry has settled');
  const fields = await pixels(page, [...samples, finish], bodyField);
  const contrasts = fields.map(contrast);
  metrics.minFieldContrast = round(Math.min(...contrasts));
  check(metrics.minFieldContrast > 2, 'No observed first-screen paint fades to an empty page');
  if (normal && samples.length > 1) {
    const start = samples[0];
    await save('hero-early', start);
    const p = await picturePair(env, 'hero', start, samples.slice(1), finish, field);
    metrics.paint = p;
    check(p.endpointRGB > 2 && p.middleRGB > .65, 'Native early, intermediate and settled product paints differ');
    const [housing] = await pixels(page, [env.refs[0]], full, 'image/webp');
    const walls = await pixels(page, [...samples, finish], await imageField(page, full));
    const ridge = walls.map(paint => rimInk(paint, housing));
    metrics.rimInk = {peak: round(max(ridge)), settled: round(last(ridge))};
    const i = ridge.indexOf(max(ridge));
    if (i < samples.length) await save('hero-contour', samples[i]);
    check(max(ridge) > last(ridge) + 3, 'Visible CAD-registered rim ink, not just a fading photograph');
  } else {
    await save('hero-settled', finish);
    check(!normal, 'Native filmstrip includes the reveal before it settles');
  }
}

async function palette(env) {
  const {page, film, normal, check, metric, refs, save} = env;
  // Keep all photographs in the same viewport; never use locator.screenshot(), which can scroll.
  const field = await imageField(page);
  const actual = await pixels(page, refs, partField, 'image/webp');
  const names = ['graphite', 'pink', 'blue'];
  // Only opaque points on which these actual CAD finishes differ. UI text, swatches, focus
  // rings, the transparent background and the mobile hit link cannot manufacture a pass.
  const mask = indices(actual[0], i => actual.every(a => a[i + 3] >= 250) &&
    actual.every((a, j) => actual.slice(j + 1).every(b => errorRGB(a, b, i) > 8)));
  assert.ok(mask.length >= 100, 'Insufficient finish-distinguishing housing pixels');
  const stills = {};
  const capture = async id => {
    const photo = await film.shot();
    const [paint] = await pixels(page, [photo], field);
    const errors = actual.map(ref => round(distance(ref, paint, mask)));
    const best = errors[names.indexOf(id)];
    check(errors.every((e, i) => names[i] === id || e > best + 3), `${id}: the actual painted housing matches the issued ${id}, not another finish`);
    metric(`reference-${id}`, {opaquePixels: mask.length, RGBErrorsInGraphitePinkBlueOrder: errors});
    const state = await page.evaluate(() => ({state: AtlasUI.getState().finish,
      palette: document.querySelector('#product-finishes [aria-pressed="true"]')?.dataset.productFinish,
      src: document.querySelector('#product-image').currentSrc, visibleCount: document.querySelectorAll('#product-image').length}));
    check(state.state === id && state.palette === id && state.src.endsWith(`hero-${id}.webp`) && state.visibleCount === 1,
      `${id}: chooser, real hero and assembly agree`);
    return {photo, paint};
  };
  stills.graphite = await capture('graphite');
  let from = 'graphite';
  for (const id of ['pink', 'blue']) {
    await begin(page);
    film.reset();
    await hit(page, chip(id), env.phone);
    await settledFinish(page, id);
    const rows = await end(page);
    const shots = thin(film.take());
    stills[id] = await capture(id);
    const rgb = await pixels(page, shots, field);
    const a = stills[from].paint;
    const b = stills[id].paint;
    const delta = distance(a, b, mask);
    assert.ok(delta > 8, `${from}→${id}: final CAD paint did not change`);
    // On an old→new crossfade distances to both endpoints add up to about their separation.
    // Black/white flashes, movement of an unrelated element, or identical frames are not blends.
    const track = rgb.map(p => {
      const old = distance(a, p, mask);
      const next = distance(p, b, mask);
      return {progress: round(old / delta), remaining: round(next / delta), detour: round((old + next) / delta)};
    });
    const blends = track.map((v, i) => ({...v, i})).filter(v => v.progress > .055 && v.remaining > .055 && v.detour < 1.24);
    const best = blends.sort((x, y) => Math.abs(x.progress - .5) - Math.abs(y.progress - .5))[0];
    const fades = rows.filter(r => r.old > .01 && r.old < .99);
    metric(`${from}-to-${id}`, {deltaRGB: round(delta), samples: shots.length, mixedPaints: blends.length,
      computedMixedFrames: fades.length, peakLayers: max(rows.map(r => r.count)), track});
    check(normal ? blends.length > 0 && fades.length > 0 : !blends.length && rows.every(r => !r.count),
      normal ? `${from}→${id}: measured blended CAD pixels and a partial outgoing paint` : `${from}→${id}: no transitional paint in reduced motion`);
    check(notReplayed(rows) && rows.every(r => r.count <= 1) && !last(rows).count, `${id}: no intro replay or stale/stacked finish`);
    if (best) await save(`${from}-to-${id}-middle`, shots[best.i]);
    await save(`${id}-settled`, stills[id].photo);
    from = id;
  }

  await begin(page);
  await hit(page, chip('pink'), env.phone);
  if (normal) {
    // Race real clicks against a witnessed active fade (old releases snap instead).
    await page.waitForFunction(() => window.__motionWitness.rows.some(r => r.old > .01 && r.old < .99), null,
      {timeout: 800}).catch(() => {});
  }
  for (const id of ['graphite', 'pink', 'blue']) await hit(page, chip(id), env.phone);
  await settledFinish(page, 'blue');
  const rapid = await end(page);
  const after = await capture('blue');
  const err = distance(after.paint, stills.blue.paint, mask);
  const actions = await page.evaluate(() => window.__motionWitness.actions);
  metric('rapid-switches', {actions, peakLayers: max(rapid.map(r => r.count)), activeFrames: rapid.filter(r => r.count).length, finalBlueRGBError: round(err)});
  check(actions.some(e => e.layers > 0) === normal && rapid.every(r => r.count <= (normal ? 1 : 0)) && !last(rapid).count && notReplayed(rapid) && err < 1,
    'Rapid switches settle on the previously measured blue pixels with no orphan paint');
}

async function sheetAndScroll(env) {
  const {page, phone, normal, check, metric} = env;
  await begin(page);
  await page.locator('#tab-assembly').press('ArrowRight');
  await page.waitForSelector('#specs:visible');
  await page.keyboard.press('ArrowLeft');
  await page.waitForSelector('#overview:visible');
  await frames(page, 7);
  check(notReplayed(await end(page)), 'Switching sheets does not replay the product entrance');
  const link = page.locator(phone ? '.hero-inspect-link' : '#explore-model');
  assert.ok(await link.isVisible(), 'Reachable hero inspect link');
  const start = await page.evaluate(() => scrollY);
  await begin(page);
  if (phone) {
    const {x, y} = await page.locator('#product-image').evaluate(el => {
      const r = el.getBoundingClientRect();
      return {x: r.left + r.width / 2, y: r.top + r.height / 2};
    });
    check(await page.evaluate(({x, y}) => !!document.elementFromPoint(x, y)?.closest('.hero-inspect-link'), {x, y}),
      'The visible housing itself is a hit target on a touch viewport');
    await page.touchscreen.tap(x, y);
  } else await link.press('Enter');
  await page.waitForFunction(() => ['explorer', 'drawing'].includes(document.activeElement?.id) &&
    document.activeElement.getBoundingClientRect().top < innerHeight * .45 &&
    window.__motionWitness.rows.length >= 5 && new Set(window.__motionWitness.rows.slice(-4).map(r => r.y)).size === 1);
  const rows = await end(page);
  const ys = rows.map(r => r.y);
  const target = last(ys);
  const between = unique(ys.filter(y => y > start + 2 && y < target - 2));
  const landing = await page.evaluate(() => {
    const el = document.activeElement;
    const r = el.getBoundingClientRect();
    const canvas = document.querySelector('#atlas-canvas').getBoundingClientRect();
    return {id: el.id, top: r.top, canvasPx: Math.min(innerHeight, canvas.bottom) - Math.max(0, canvas.top)};
  });
  metric('hero-navigation', {start, target, between, ...landing});
  check(target > start + 150 && landing.top >= -4 && landing.canvasPx > 50 && (phone ? landing.id === 'drawing' : landing.id === 'explorer'),
    'Hero activation lands with focus on the real, visible 3D workspace');
  check(normal ? between.length >= 2 && ys.every((y, i) => !i || y >= ys[i - 1] - 2) : !between.length,
    normal ? 'Scroll passes through multiple intermediate offsets without a jump back' : 'Reduced-motion navigation snaps without intermediate offsets');
}

async function chooser(env) {
  const {page, film, phone, normal, tap, check, metric} = env;
  const opener = phone ? '#language-link' : '#language-nav';
  if (phone) await page.locator(opener).scrollIntoViewIfNeeded();
  async function open() {
    if (phone) return hit(page, opener, true);
    await page.locator(opener).evaluate(el => el.focus({preventScroll: true}));
    await page.keyboard.press('Enter');
  }
  const dialog = page.locator(dlg);
  const closed = await film.shot();
  await begin(page);
  film.reset();
  await open();
  await dialog.waitFor({state: 'visible'});
  await settled(page, dlg);
  const entry = await end(page);
  const unfolded = last(entry);
  assert.ok(unfolded?.open && unfolded.ink > .95 && unfolded.choice > .95, 'Language choices fully materialize');
  const entering = entry.filter(r => inkMoves(r, unfolded));
  const opened = await film.shot();
  const inPaint = await picturePair(env, 'picker-open', closed, film.take(), opened, bodyField);
  metric('picker-open', {partial: entering.length, frames: entry.length, ...inPaint});
  check(normal ? entering.length > 1 && inPaint.middleRGB > .9 : !entering.length, 'Language picker enters natively as requested by the motion preference');
  if (!normal) check(entry.filter(r => r.input === opener.slice(1)).every(r => r.open && r.ink > .98 && r.choice > .98),
    'Reduced opening exposes the complete sheet on the first post-activation frame');
  check(unfolded.focus === env.lang, 'The current language is focused on entry');
  await page.keyboard.press('Tab');
  check(await dialog.evaluate(d => d.contains(document.activeElement)), 'Keyboard traversal remains inside the native dialog');
  await begin(page);
  film.reset();
  await page.keyboard.press('Escape');
  await dialog.waitFor({state: 'hidden'});
  await frames(page);
  const exit = await end(page);
  const leaving = exit.filter(r => inkMoves(r, unfolded));
  const outPaint = await picturePair(env, 'picker-close', opened, film.take(), await film.shot(), bodyField);
  metric('picker-close', {partial: leaving.length, frames: exit.length, ...outPaint});
  check(normal ? leaving.length > 1 && outPaint.middleRGB > .9 : !leaving.length, 'Escape dismisses with real intermediate paper/ink only in normal motion');
  if (!normal) check(exit.some(r => r.input === 'Escape') && exit.filter(r => r.input === 'Escape').every(r => !r.open),
    'Reduced Escape does not leave a motionless sheet up on a hidden timer');
  check(await page.locator(`${opener}:focus`).count() === 1, 'Escape restores focus to the actual opener');

  // In a native modal an outside pointer hit is inert. Exercise the public launcher during a
  // witnessed closing frame as a separate reentrancy test, not as evidence of a physical click.
  await open();
  await settled(page, dlg);
  await begin(page);
  await hit(page, '#language-close', phone);
  const reversed = await page.evaluate(async ({rest, opener}) => {
    for (let i = 0; i < 40; i++) {
      const d = document.querySelector('#language-dialog');
      const r = window.__motionWitness.rows.at(-1);
      if (!d.open || r?.open && (r.ink < .97 || Math.abs(r.top - rest.top) > .65)) {
        const inFlight = d.open;
        document.querySelector(opener).click();
        return inFlight;
      }
      await new Promise(resolve => requestAnimationFrame(resolve));
    }
    throw Error('Closing did not progress');
  }, {rest: unfolded, opener});
  await settled(page, dlg);
  const after = last(await end(page));
  check(reversed === normal && after.open && after.ink > .98 && after.focus === env.lang &&
    await page.locator(opener).getAttribute('aria-expanded') === 'true', 'Quick close→open does not run a stale close or lose focus');
  if (normal) {
    // Turn the preference on with an already open sheet; then again while a real exit is in flight.
    await page.emulateMedia({reducedMotion: 'reduce'});
    await page.keyboard.press('Escape');
    await frames(page, 2);
    check(!await dialog.isVisible(), 'Changing to reduced motion while open makes dismissal immediate');
    await page.emulateMedia({reducedMotion: 'no-preference'});
    await open();
    await settled(page, dlg);
    await begin(page);
    await page.keyboard.press('Escape');
    const activeExit = await page.waitForFunction(() => {
      const r = window.__motionWitness.rows.at(-1);
      return !!r?.open && r.ink < .97 && r.ink > .015;
    }, null, {timeout: 650}).then(() => true, () => false);
    await page.emulateMedia({reducedMotion: 'reduce'});
    await frames(page, 3);
    const changed = (await end(page)).filter(r => r.reduced);
    check(activeExit && changed.length > 0 && changed.slice(1).every(r => !r.open) && !await dialog.isVisible(),
      'Switching preference mid-exit cancels the outstanding motion by the next painted frames');
    await page.emulateMedia({reducedMotion: 'no-preference'});
  } else {
    await page.keyboard.press('Escape');
    await frames(page, 2);
    check(!await dialog.isVisible(), 'Rapid reduced-motion reopen still dismisses immediately');
  }
}

const eye = page => page.evaluate(() => window.__motionEye);
const directionError = (a, b) => Math.hypot(...a.direction.map((v, i) => v - b.direction[i]));

async function selectEvidence(env) {
  const {page, phone, tap, check, metric} = env;
  if (phone) {
    const step = page.locator('#service-step');
    await step.scrollIntoViewIfNeeded();
    await step.selectOption('battery');
    check(await step.inputValue() === 'battery', 'A real service stage is active before changing language');
    return;
  }
  await tap('#node-Battery');
  await tap('#part-list [data-part-id="MechBatteryEnvelope"]');
  const canvas = page.locator('#atlas-canvas');
  // Begin *in* the workspace; merely revealing an edge may leave the hero on screen.
  await canvas.evaluate(el => el.scrollIntoView({block: 'center', behavior: 'instant'}));
  await frames(page);
  const box = await canvas.boundingBox();
  const x = box.x + box.width * .43;
  const y = Math.max(90, box.y + box.height * .45);
  check(await page.evaluate(({x, y}) => document.elementFromPoint(x, y)?.id === 'atlas-canvas', {x, y}), 'Real canvas receives the orbit and dolly');
  await frames(page);
  const preset = await eye(page);
  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.mouse.move(x + 68, y + 24, {steps: 7});
  await page.mouse.up();
  await frames(page, 4);
  const orbit = await eye(page);
  await page.mouse.wheel(0, -120);
  await frames(page, 6);
  const dolly = await eye(page);
  metric('camera-input', {preset, orbit, dolly});
  check(directionError(preset, orbit) > .035 && Math.abs(dolly.magnification / orbit.magnification - 1) > .015,
    'Real drag and wheel changed rendered world direction and magnification');
}

// Fingerprint the distinct product on the dark studio ground, not just a dark page. The locale
// mark can itself be dark. Small vertical registration changes accommodate translated copy.
function matchesHero(frame, reference) {
  const mask = indices(reference, i => reference[i] > 68 && reference[i] < 218 && i < reference.length * .88);
  if (mask.length < 70) return false;
  for (const dy of [-6, -3, 0, 3, 6]) {
    let matched = 0;
    for (const i of mask) {
      const j = i + 400 * dy;
      if (j >= 0 && j < frame.length && Math.abs(reference[i] - frame[j]) < 14 &&
        Math.abs(reference[i + 2] - frame[j + 2]) < 14) matched++;
    }
    if (matched > mask.length * .70) return true;
  }
  return false;
}

async function handoff(env) {
  const {page, context, film, phone, tap, check, metric, save, heroRefs} = env;
  await selectEvidence(env);
  const next = phone ? 'zh-CN' : 'ru';
  const id = phone ? 'battery' : 'MechBatteryEnvelope';
  const selection = () => phone ? page.locator('#service-step').inputValue() : page.locator('#part-id').innerText();
  const position = () => page.evaluate(() => ({y: scrollY, chapter: document.querySelector('#overview').getBoundingClientRect().bottom}));
  const before = await position();
  assert.ok(before.chapter < 0 && await selection() === id, 'Start locale handoff in the working atlas, not at the hero');
  const readState = () => page.evaluate(() => {
    const {page, group, selected, serviceStep, view, finish, screenOn, isolated} = AtlasUI.getState();
    return {page, group, selected, serviceStep, view, finish, screenOn, isolated};
  });
  const state = await readState();
  const original = await eye(page);
  await hit(page, '#language-nav', phone);
  await settled(page, dlg);
  const link = page.locator(`${dlg} a[hreflang="${next}"]`);
  const href = new URL(await link.getAttribute('href'), page.url());
  const expected = new URL(page.url());
  expected.searchParams.set('lang', next);
  assert.equal(href.href, expected.href, 'A real link to the other edition, same resource');
  const oldTime = await page.evaluate(() => performance.timeOrigin);
  film.reset();
  await Promise.all([page.waitForURL(href.href, {waitUntil: 'commit'}), hit(page, `${dlg} a[hreflang="${next}"]`, phone)]);
  await page.waitForSelector(ready, {timeout: 30000});
  await page.waitForFunction(() => window.__motionEye?.draws > 0);
  await settled(page, 'html');
  const rows = await end(page);
  const after = await position();
  const current = await eye(page);
  const arrived = await readState();
  const paints = [...film.take(), await film.shot()];
  const flashes = [];
  let minContrast = Infinity;
  for (let n = 0; n < paints.length; n += 12) {
    const rgb = await pixels(page, paints.slice(n, n + 12), bodyField);
    rgb.forEach((p, i) => {
      minContrast = Math.min(minContrast, contrast(p));
      if (heroRefs.some(ref => matchesHero(p, ref))) flashes.push(i + n);
    });
  }
  if (flashes.length) await save('unexpected-hero-flash', paints[flashes[0]]);
  await save('localized-workspace', last(paints));
  metric('locale-handoff', {next, id, before, after, state, arrived, frames: paints.length,
    minFieldContrast: round(minContrast), heroLikePaints: flashes, eyeBefore: original, eyeAfter: current});
  check(context.pages().length === 1 && await page.evaluate(() => performance.timeOrigin) !== oldTime &&
    await page.locator('html').getAttribute('lang') === next, 'Language selection navigates a real new document in the same tab');
  check(JSON.stringify(state) === JSON.stringify(arrived) && await selection() === id, 'The actual selected CAD record or service stage and finish survive translation');
  check(after.chapter < 0 && Math.abs(after.y - before.y) < page.viewportSize().height * .18 &&
    notReplayed(rows) && paints.length > 2 && !flashes.length && minContrast > 2,
    'Handoff keeps the working place with no painted hero, restart or empty frame');
  if (!phone) check(directionError(original, current) < .015 && Math.abs(current.magnification / original.magnification - 1) < .04,
    'Restored actual camera matches both world direction and independent projected scale');
}

async function idle(env) {
  const {page, film, check, metric} = env;
  await end(page);
  await film.stop();
  await settled(page, 'html');
  const first = await film.shot();
  const start = await eye(page);
  // The interval merely bounds observation: pass requires zero *rendered* frames AND stable paint.
  await new Promise(resolve => setTimeout(resolve, 700));
  const next = await eye(page);
  const second = await film.shot();
  const [a, b] = await pixels(page, [first, second]);
  const residue = await page.evaluate(() => ({layers: document.querySelectorAll('.finish-outgoing').length,
    running: document.getAnimations().filter(a => a.playState === 'running').length}));
  metric('idle', {actualDraws: next.draws - start.draws, RGBError: round(distance(a, b)), ...residue});
  check(start.draws === next.draws && distance(a, b) < .2 && !residue.layers && !residue.running,
    'At idle: no recurring WebGL draws, changing page paint, live animations or old finish');
}

async function exercise(browser, suite, phone, normal) {
  const {index, output, refs, cases} = suite;
  const lang = phone ? 'ru' : 'en';
  const viewport = phone ? {width: 390, height: 844} : {width: 1280, height: 900};
  const reducedMotion = normal ? 'no-preference' : 'reduce';
  const label = `${viewport.width}-${reducedMotion}`;
  const record = {label, viewport, reducedMotion, lang, passed: [], failures: [], metrics: {}};
  cases.push(record);
  const url = new URL(index);
  url.searchParams.set('lang', lang);
  const offline = url.protocol === 'file:';
  const context = await browser.newContext({viewport, reducedMotion, locale: lang, isMobile: phone, hasTouch: phone,
    deviceScaleFactor: 1, offline, serviceWorkers: 'block'});
  context.setDefaultTimeout(5500);
  context.setDefaultNavigationTimeout(30000);
  const forbidden = urlString => /^(?:https?|wss?):/.test(urlString) && (offline || new URL(urlString).origin !== url.origin);
  const external = [];
  const errors = [];
  context.on('request', req => { if (forbidden(req.url())) external.push(req.url()); });
  await context.route(/^https?:/, route => forbidden(route.request().url()) ? route.abort() : route.continue());
  try {
    await context.addInitScript(installSampler);
    await context.addInitScript(observeEye);
    const page = await context.newPage();
    page.on('pageerror', error => errors.push(error.message));
    page.on('websocket', socket => external.push(socket.url()));
    const film = await filmstrip(context, page);
    const env = {page, context, film, phone, normal, lang, url, refs, heroRefs: [],
      tap: selector => phone ? page.locator(selector).tap() : page.locator(selector).click(),
      check: (pass, name) => record[pass ? 'passed' : 'failures'].push(name),
      metric: (name, value) => { record.metrics[name] = value; },
      save: (name, photo) => fs.writeFile(path.join(output, `${label}-${name}.png`), Buffer.from(photo.png, 'base64'))};
    for (const test of [intro, palette, sheetAndScroll, chooser, handoff, idle]) {
      console.log(`=== ${label}: ${test.name}`);
      try {
        await test(env);
        if (test === intro || test === palette) {
          const [ref] = await pixels(page, [await film.shot()], bodyField);
          assert.ok(matchesHero(ref, ref), 'The flash detector must recognize the known first-screen product');
          env.heroRefs.push(ref);
        }
      } catch (e) {
        record.failures.push(`${test.name}: ${e.message}`);
      }
    }
    env.check(!errors.length, `No uncaught page errors${errors.length ? ': ' + errors.join('; ') : ''}`);
    env.check(!external.length, `No unapproved runtime requests${external.length ? ': ' + external.join('; ') : ''}`);
  } finally {
    await context.close();
  }
  for (const failure of record.failures) console.error(`FAIL ${label}: ${failure}`);
}

async function main() {
  const [input, scratch, given, ...extra] = process.argv.slice(2);
  assert.ok(path.isAbsolute(input || '.') && path.isAbsolute(scratch || '.') && !extra.length,
    'Usage: node verify_atlas_motion.cjs ABS_ISSUE_ROOT EXISTING_EXTERNAL_SCRATCH [absolute atlas URL]');
  const root = await fs.realpath(input);
  const outRoot = await fs.realpath(scratch);
  for (const release of [root, await fs.realpath(path.resolve(__dirname, '..'))]) {
    assert.ok(outRoot !== release && !outRoot.startsWith(release + path.sep), `Refusing to write inside ${release}`);
  }
  const index = given ? new URL(given) : pathToFileURL(path.join(root, 'atlas/index.html'));
  assert.ok(['file:', 'https:', 'http:'].includes(index.protocol), 'Expected file:// or an explicit web atlas URL');
  const output = await fs.mkdtemp(path.join(outRoot, 'atlas-motion-'));
  const tmp = path.join(output, 'browser-tmp');
  await fs.mkdir(tmp);
  Object.assign(process.env, {TMPDIR: tmp, TMP: tmp, TEMP: tmp});
  const reportPath = path.join(output, 'motion-report.json');
  const report = {root, index: index.href, browser: null, offline: index.protocol === 'file:', cases: [], ok: false};
  let browser;
  console.log(`=== Motion report: ${reportPath}`);
  try {
    const {chromium} = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');
    const refs = await Promise.all(['graphite', 'pink', 'blue'].map(async id =>
      ({png: await fs.readFile(path.join(root, 'atlas/media', `hero-${id}.webp`), 'base64')})));
    // Prefer the platform GPU for *timing* measurements; SwiftShader remains available on
    // headless machines without a graphics adapter. The real renderer runs in either case.
    const args = ['--enable-unsafe-swiftshader', '--disable-background-networking',
      '--disable-component-update', '--disable-crash-reporter', '--no-proxy-server'];
    if (report.offline) args.push('--host-resolver-rules=MAP * ~NOTFOUND');
    browser = await chromium.launch({headless: true, executablePath: process.env.CHROME || undefined, args,
      env: {...process.env, HOME: tmp, CFFIXED_USER_HOME: tmp, XDG_CACHE_HOME: path.join(tmp, 'cache'), XDG_CONFIG_HOME: path.join(tmp, 'config')}});
    report.browser = `Chromium ${browser.version()}`;
    for (const phone of [false, true]) {
      for (const normal of [true, false]) await exercise(browser, {index, output, refs, cases: report.cases}, phone, normal);
    }
    report.ok = report.cases.length === 4 && report.cases.every(c => !c.failures.length);
  } catch (e) {
    report.error = e.stack || e.message;
  } finally {
    await browser?.close();
    await fs.writeFile(reportPath, JSON.stringify(report, null, 2) + '\n');
    if (await fs.realpath(tmp) === tmp) await fs.rm(tmp, {recursive: true});
  }
  if (!report.ok) process.exitCode = 1;
  console.log(`${report.ok ? 'PASS' : 'FAIL'}: ${reportPath}`);
  if (report.error) console.error(report.error);
}

main().catch(error => { console.error(error); process.exitCode = 1; });
