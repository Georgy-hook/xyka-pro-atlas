/* Trusted mobile input on the issued atlas, not a second release verifier.
 * PLAYWRIGHT_CORE=… CHROME=… node model/verify_atlas_touch.cjs /absolute/issue /existing/scratch [atlas-url]
 * Writes TOUCH_ACCEPTANCE.json and viewport JPEGs in a fresh scratch subdirectory on success. No site-side test hook.
 */
'use strict';

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs/promises');
const path = require('node:path');
const {pathToFileURL} = require('node:url');

const canvas = '#atlas-canvas';
const fit = '[data-action="fit"]';
const inspect = name => `[data-inspect="${name}"]`;
const portrait = {width: 390, height: 844};
const landscape = {width: 844, height: 390};
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const round = value => Math.round(value * 1000) / 1000;
const deg = value => value * 180 / Math.PI;
const angle = (a, b) => deg(Math.acos(Math.max(-1, Math.min(1, a.reduce((s, v, i) => s + v * b[i], 0)))));
const yaw = dir => deg(Math.atan2(dir[0], dir[2]));
const turn = (a, b) => (yaw(b.dir) - yaw(a.dir) + 540) % 360 - 180;

// As in verify_atlas_ui.cjs:installFrameObserver, use Three's AFTER-draw scene callback.
// No camera setters, fake renderer, geometry writes or per-frame pixel/mesh readbacks.
function installObserver() {
  let audit;
  window.__touchTrace = {
    begin() {
      audit = {startY: scrollY, initialPick: AtlasUI.getState().selected, excursion: 0, changedPick: false,
        trusted: true, onCanvas: true, edges: [], oneMoves: 0, twoMoves: 0};
    },
    read: () => audit,
  };
  window.addEventListener('scroll', () => {
    if (!audit) return;
    audit.excursion = Math.max(audit.excursion, Math.abs(scrollY - audit.startY));
    audit.lastScroll = performance.now();
  }, {passive: true});
  window.addEventListener('atlas:change', event => {
    if (audit && event.detail.selected !== audit.initialPick) audit.changedPick = true;
  });
  for (const type of ['touchstart', 'touchmove', 'touchend', 'touchcancel']) {
    document.addEventListener(type, event => {
      if (!audit) return;
      audit.trusted &&= event.isTrusted;
      audit.onCanvas &&= event.target.id === 'atlas-canvas';
      if (type === 'touchmove') {
        if (event.touches.length === 1) ++audit.oneMoves;
        if (event.touches.length === 2) {
          ++audit.twoMoves;
          const [a, b] = event.touches;
          audit.span = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
        }
      } else {
        audit.edges.push([type, Array.from(event.touches, t => t.identifier)]);
        if (type === 'touchend') {
          audit.endX = event.changedTouches[0].clientX;
          audit.endY = event.changedTouches[0].clientY;
        }
      }
    }, {capture: true, passive: true});
  }
  document.addEventListener('load', event => {
    if (!(event.target instanceof HTMLScriptElement) || !new URL(event.target.src).pathname.endsWith('/three-atlas.js')) return;
    const T = window.AtlasThree;
    const original = T.Scene.prototype.onAfterRender;
    const meshes = new Map();
    const pos = new T.Vector3();
    let eye;
    let dir;
    let count = 0;
    let last = 0;
    T.Scene.prototype.onAfterRender = function(renderer, scene, camera, ...args) {
      original.call(this, renderer, scene, camera, ...args);
      if (renderer.domElement.id !== 'atlas-canvas' || renderer.getRenderTarget() !== null) return;
      if (!meshes.size) {
        const ids = new Set(ATLAS_SCENE.parts.map(p => p.id));
        scene.traverse(o => {
          if (!o.isMesh || !ids.has(o.userData.id)) return;
          if (meshes.has(o.userData.id)) throw Error(`Duplicate physical CAD leaf: ${o.userData.id}`);
          meshes.set(o.userData.id, o);
        });
      }
      eye = camera;
      dir = eye.getWorldDirection(pos).toArray();
      ++count;
      last = performance.now();
    };
    const visible = mesh => mesh.visible && (!mesh.parent || visible(mesh.parent));
    window.__atlasFrame = {
      clock: () => ({count, last}),
      pose: () => ({dir, count, physicalLeaves: meshes.size}),
      // Height in CSS pixels of the real fairing vertices at the last settled pose.
      fairingHeight() {
        const mesh = meshes.get('MechUpperFairing');
        if (!mesh || !visible(mesh)) throw Error('Missing visible fairing in measured render');
        const matrix = eye.projectionMatrix.clone().multiply(eye.matrixWorldInverse).multiply(mesh.matrixWorld);
        const vertices = mesh.geometry.attributes.position;
        let min = Infinity;
        let max = -Infinity;
        for (let i = 0; i < vertices.count; ++i) {
          const y = pos.fromBufferAttribute(vertices, i).applyMatrix4(matrix).y;
          min = Math.min(min, y);
          max = Math.max(max, y);
        }
        return (max - min) * document.getElementById('atlas-canvas').getBoundingClientRect().height / 2;
      },
      startPoint({onPart, dx, dy}) {
        const surface = document.getElementById('atlas-canvas');
        const rect = surface.getBoundingClientRect();
        const candidates = [...meshes.values()].filter(visible);
        const ray = new T.Raycaster();
        const hit = (x, y) => {
          ray.setFromCamera(new T.Vector2(2 * (x - rect.left) / rect.width - 1, 1 - 2 * (y - rect.top) / rect.height), eye);
          return ray.intersectObjects(candidates, false)[0]?.object.userData.id || null;
        };
        const columns = onPart ? [.5, .42, .58, .34, .66] : [.14, .85, .25, .75, .5];
        for (const fy of [.5, .36, .64, .21, .79, .12, .88]) {
          for (const fx of columns) {
            const x = Math.round(rect.left + fx * rect.width);
            const y = Math.round(rect.top + fy * rect.height);
            if (![0, .5, 1].every(n => document.elementFromPoint(x + n * dx, y + n * dy) === surface)) continue;
            const id = hit(x, y);
            // The lit LCD is selectable through glass; avoid that purpose-built exception and triangle edges.
            if (onPart && id && id !== ATLAS_SCENE.presentation.lcd.windowId && hit(x + 1, y) === id) return {x, y, id};
            if (!onPart && !id && !hit(x + dx / 2, y + dy / 2) && !hit(x + dx, y + dy)) return {x, y, id};
          }
        }
        throw Error('No exposed, independently ray-tested contact path on the model field');
      },
    };
  }, true);
}

async function settle(page) {
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  await page.waitForFunction(() => {
    const frame = window.__atlasFrame?.clock();
    return frame?.count > 0 && performance.now() - frame.last > 180;
  }, null, {timeout: 8000, polling: 50});
}

async function sample(page, measureSize = false) {
  await settle(page);
  return page.evaluate(size => ({...__atlasFrame.pose(), y: scrollY, scale: visualViewport.scale,
    selected: AtlasUI.getState().selected, ...(size ? {height: __atlasFrame.fairingHeight()} : {})}), measureSize);
}

async function center(page, selector) {
  await page.locator(selector).evaluate(el => el.scrollIntoView({behavior: 'instant', block: 'center', inline: 'nearest'}));
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
}

// A fixed, unobstructed interior crop of the composited WebGL canvas. Hash it only at rest.
async function crop({page, cdp}) {
  const clip = await page.locator(canvas).evaluate(el => {
    const r = el.getBoundingClientRect();
    const x = Math.round(r.left + r.width / 2);
    const y = Math.round(r.top + r.height / 2);
    for (const dx of [-45, 0, 45]) {
      for (const dy of [-45, 0, 45]) {
        if (document.elementFromPoint(x + dx, y + dy) !== el) throw Error('Rendered model crop is obscured');
      }
    }
    return {x: x + scrollX - 45, y: y + scrollY - 45, width: 90, height: 90, scale: 1};
  });
  const shot = await cdp.send('Page.captureScreenshot', {format: 'png', clip});
  return sha(Buffer.from(shot.data, 'base64'));
}

function touch(cdp, type, points = []) {
  return cdp.send('Input.dispatchTouchEvent', {type,
    touchPoints: points.map(({x, y, id = 1}) => ({x, y, id, radiusX: 5, radiusY: 5, force: .65}))});
}

async function swipe(cdp, {x, y}, dx, dy, steps = 6) {
  await touch(cdp, 'touchStart', [{x, y}]);
  for (let i = 1; i <= steps; ++i) {
    await delay(22);
    await touch(cdp, 'touchMove', [{x: x + dx * i / steps, y: y + dy * i / steps}]);
  }
  await touch(cdp, 'touchEnd');
}

async function tap(cdp, {x, y}, driftPx = 0) {
  await touch(cdp, 'touchStart', [{x, y}]);
  if (driftPx) {
    await delay(24);
    await touch(cdp, 'touchMove', [{x: x + driftPx, y}]);
  }
  await delay(55);
  await touch(cdp, 'touchEnd');
}

// Do not let test-runner autoscroll hide an inaccessible onscreen caption or clipped button.
async function tapVisible({page, cdp}, selector) {
  const pos = await page.locator(selector).evaluate(el => {
    const r = el.getBoundingClientRect();
    const x = r.left + r.width / 2;
    const y = r.top + r.height / 2;
    if (el.disabled || !el.contains(document.elementFromPoint(x, y))) throw Error(`Touch target not reachable: ${el.id || el.tagName}`);
    return {x, y};
  });
  await tap(cdp, pos);
}

const beginTrace = page => page.evaluate(() => __touchTrace.begin());
const readTrace = page => page.evaluate(() => __touchTrace.read());
const single = [['touchstart', [1]], ['touchend', []]];
function noSideEffects(trace, before, after, edges) {
  assert.deepEqual(trace.edges, edges, 'Actual Chromium contact transitions');
  assert.ok(trace.trusted && trace.onCanvas, 'Trusted touch events hit the canvas');
  assert.ok(!trace.changedPick && before.selected === after.selected, 'No spurious part selection');
  assert.ok(trace.excursion <= 2 && Math.abs(after.y - before.y) <= 2, 'Drawing gesture must not scroll the page');
  assert.ok(Math.abs(after.scale - 1) < .01, 'Drawing gesture must not page-zoom');
}

async function sweep(ui, onPart, dx, dy = 0) {
  const {page, cdp} = ui;
  const before = await sample(page);
  const image = await crop(ui);
  const start = await page.evaluate(args => __atlasFrame.startPoint(args), {onPart, dx, dy});
  await beginTrace(page);
  await swipe(cdp, start, dx, dy);
  const after = await sample(page);
  const trace = await readTrace(page);
  noSideEffects(trace, before, after, single);
  const distance = angle(before.dir, after.dir);
  const rendered = await crop(ui);
  const travel = Math.hypot(dx, dy);
  // Chromium can send a PointerEvent without a DOM touchmove below its touch slop.
  // Check the actual trusted touchend coordinate even for those fine adjustments.
  assert.ok(Math.hypot(trace.endX - start.x - dx, trace.endY - start.y - dy) < .25, 'Finger must reach the measured endpoint');
  if (travel >= 12) assert.ok(trace.oneMoves > 0, 'One finger moved on the field');
  assert.ok(after.count > before.count && rendered !== image, `Sweep (${dx}, ${dy}) must visibly redraw the physical scene`);
  const minimumDegrees = travel >= 50 ? 12 : travel >= 12 ? 2 : .6;
  assert.ok(distance > minimumDegrees && distance < 155, `Usable continuous orbit: ${round(distance)}°`);
  return {start: start.id || 'empty', dx, dy, degrees: round(distance), yaw: round(turn(before, after)),
    pitch: round(deg(Math.asin(after.dir[1]) - Math.asin(before.dir[1]))), frames: after.count - before.count,
    scrollPx: trace.excursion, selected: after.selected, beforeImage: image, afterImage: rendered};
}

async function idle(ui) {
  const a = await sample(ui.page);
  const image = await crop(ui);
  await delay(650);
  const b = await sample(ui.page);
  assert.equal(b.count, a.count, 'No GL draws requested during idle observation');
  assert.ok(angle(a.dir, b.dir) < .001, 'No camera drift at idle');
  assert.equal(await crop(ui), image, 'Same settled pose, same real model pixels');
  return {observedMs: 650, extraDraws: b.count - a.count, image};
}

async function pinch(ui) {
  const {page, cdp} = ui;
  await tapVisible(ui, fit); // Establish the fitted scale at the current freely rotated orientation.
  const before = await sample(page, true);
  const {x, y} = await page.evaluate(() => __atlasFrame.startPoint({onPart: true, dx: 0, dy: 0}));
  const a = {id: 1, x: x - 23, y};
  const b = {id: 2, x: x + 23, y};
  const startImage = await crop(ui);
  await beginTrace(page);
  await touch(cdp, 'touchStart', [a]);
  await delay(45);
  await touch(cdp, 'touchStart', [a, b]);
  for (let i = 1; i <= 6; ++i) {
    a.x = x - 23 - 14 * i / 6;
    b.x = x + 23 + 14 * i / 6;
    await delay(22);
    await touch(cdp, 'touchMove', [a, b]);
  }
  // A CDP receipt can precede delivery of the coalesced final touchmove to the page.
  // Observe the full span FIRST, then wait for its render before measuring or lifting.
  await page.waitForFunction(() => Math.abs(__touchTrace.read().span - 74) < .1);
  const spread = await sample(page, true);
  const spreadImage = await crop(ui);
  // Supply only the lifted contact. Verify actual touchend with one remaining, not a second touchstart.
  await touch(cdp, 'touchEnd', [b]);
  await delay(40);
  a.x += 1;
  await touch(cdp, 'touchMove', [a]);
  await touch(cdp, 'touchEnd');
  const released = await sample(page, true);
  const trace = await readTrace(page);
  noSideEffects(trace, before, released, [['touchstart', [1]], ['touchstart', [1, 2]], ['touchend', [1]], ['touchend', []]]);
  const ratio = spread.height / before.height;
  assert.ok(trace.twoMoves > 0 && spread.count > before.count && spreadImage !== startImage &&
    angle(before.dir, spread.dir) < 3 && ratio > 1.12,
    `Finger spread must enlarge projected CAD geometry: ${round(ratio)}×`);
  assert.ok(Math.abs(released.height / spread.height - 1) < .045 && angle(spread.dir, released.dir) < 4,
    `Single lift must not teleport, select or reset: ${round(released.height / spread.height)}×; ${round(angle(spread.dir, released.dir))}°`);
  await tapVisible(ui, fit);
  const fitted = await sample(page, true);
  assert.ok(fitted.count > spread.count && Math.abs(fitted.height / before.height - 1) < .045 &&
    angle(before.dir, fitted.dir) < 4 && fitted.height < spread.height * .94, 'Fit restores real framing, not just a button state');
  return {spanPx: [46, 74], projectedHeightsPx: [before, spread, released, fitted].map(s => round(s.height)),
    ratio: round(ratio), fitRatio: round(fitted.height / before.height), contacts: trace.edges,
    scrollPx: trace.excursion, beforeImage: startImage, spreadImage};
}

async function screenshot(ui, name) {
  const bytes = await ui.page.screenshot({type: 'jpeg', quality: 72, scale: 'css'});
  await fs.writeFile(path.join(ui.outputs, name), bytes, {flag: 'wx'});
  ui.report.screenshots[name] = sha(bytes);
}

async function selectAndReturn(ui) {
  const {page, cdp} = ui;
  const before = await sample(page);
  const hit = await page.evaluate(() => __atlasFrame.startPoint({onPart: true, dx: 0, dy: 0}));
  await beginTrace(page);
  // A tap needn't land and lift on the mathematically exact same coordinate.
  await tap(cdp, hit, 1);
  await page.waitForFunction(id => AtlasUI.getState().selected === id, hit.id);
  const selected = await sample(page);
  const trace = await readTrace(page);
  assert.deepEqual(trace.edges, single);
  const drift = trace.endX - hit.x;
  const degrees = angle(before.dir, selected.dir);
  assert.ok(Math.abs(drift - 1) < .2 && degrees < .25, 'Resting 1px fingertip drift may tap, but must not also rotate the model');
  assert.ok(trace.trusted && trace.onCanvas && trace.changedPick && trace.excursion <= 2 && Math.abs(selected.y - before.y) <= 2,
    `Physical tap must leave the model in place, not jump to register (${selected.y - before.y}px)`);
  assert.equal(await page.locator('#picked-id').textContent(), hit.id);
  assert.ok(await page.locator('#picked-caption').isVisible(), 'Reachable explicit selected-part link');
  await screenshot(ui, 'ru-model-picked.jpg');
  await tapVisible(ui, '#picked-caption');
  await page.waitForFunction(() => document.activeElement.id === 'part-focus' && !document.querySelector('#passport').hidden);
  assert.equal(await page.locator('#part-id').textContent(), hit.id);
  const opened = await page.locator('#part-focus').evaluate(el => {
    const r = el.getBoundingClientRect();
    if (!el.contains(document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2))) throw Error('Focused passport heading not on screen');
    return scrollY;
  });
  await tapVisible(ui, '#to-drawing');
  await page.waitForFunction(() => {
    const el = document.getElementById('atlas-canvas');
    const r = el.getBoundingClientRect();
    return document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2) === el;
  });
  const returned = await sample(page);
  assert.equal(returned.selected, hit.id, 'Returning to the drawing preserves inspected part');
  return {physicalPart: hit.id, fingerDriftPx: round(drift), tapDegrees: round(degrees), tapScrollPx: round(selected.y - before.y),
    openScrollPx: round(opened - selected.y), returnScrollPx: round(returned.y - opened)};
}

async function controlsLayout(page, lang, viewport) {
  await center(page, inspect('left'));
  const info = await page.evaluate(() => {
    const buttons = Array.from(document.querySelectorAll('[data-inspect], [data-action="fit"]'), el => {
      const r = el.getBoundingClientRect();
      const x = r.left + r.width / 2;
      const y = r.top + r.height / 2;
      // Midpoints of all four edges (not the transparent corners of a round button).
      const exposed = [[x, y], [r.left + 3, y], [r.right - 3, y], [x, r.top + 3], [x, r.bottom - 3]]
        .every(([cx, cy]) => el.contains(document.elementFromPoint(cx, cy)));
      return {name: el.dataset.inspect || 'fit', label: (el.getAttribute('aria-label') || el.innerText || el.title).trim(),
        width: r.width, height: r.height, exposed, enabled: el.matches('button:enabled') && el.tabIndex >= 0};
    });
    const chooser = document.querySelector('#inspect-group');
    return {buttons, lang: document.documentElement.lang, nativeGroups: chooser instanceof HTMLSelectElement ? chooser.options.length : 0,
      width: innerWidth, height: innerHeight, layoutWidth: document.documentElement.scrollWidth, scale: visualViewport.scale,
      orientation: screen.orientation.type, reduced: matchMedia('(prefers-reduced-motion: reduce)').matches,
      coarse: matchMedia('(pointer: coarse)').matches, touchPoints: navigator.maxTouchPoints};
  });
  assert.equal(info.lang, lang);
  assert.ok(info.coarse && info.touchPoints >= 2, 'Real multi-touch emulation, not just a narrow desktop viewport');
  assert.ok(Math.abs(info.width - viewport.width) <= 1 && Math.abs(info.height - viewport.height) <= 1 &&
    info.layoutWidth <= viewport.width + 1 && Math.abs(info.scale - 1) < .01, 'Phone viewport must not shrink to hide horizontal overflow');
  assert.equal(info.orientation.startsWith('landscape'), viewport.width > viewport.height, 'Physical screen orientation');
  assert.equal(info.nativeGroups, 12, 'All-assembly and eleven groups in native mobile chooser');
  assert.deepEqual(info.buttons.map(b => b.name).sort(), ['fit', 'in', 'left', 'out', 'right']);
  for (const b of info.buttons) {
    assert.ok(b.width >= 44 && b.height >= 44 && b.exposed && b.enabled,
      `${lang} ${viewport.width}×${viewport.height}: ${b.name} must be reachable, unclipped and >=44 CSS px (${b.width}×${b.height})`);
    assert.ok(({en: /[a-z]{2}/i, ru: /[а-яё]/i, 'zh-CN': /\p{Script=Han}/u})[lang].test(b.label), `Localized ${b.name} button: ${b.label}`);
  }
  return info;
}

async function alternatives(ui) {
  const {page} = ui;
  await center(page, inspect('left'));
  const start = await sample(page);
  await tapVisible(ui, inspect('left'));
  const left = await sample(page);
  await tapVisible(ui, inspect('right'));
  const right = await sample(page, true);
  const l = turn(start, left);
  const r = turn(left, right);
  assert.ok(l < -2 && r > 2 && left.count > start.count && right.count > left.count,
    'Left/right orbit buttons turn the rendered camera in opposite directions');
  await tapVisible(ui, inspect('in'));
  const zoom = await sample(page, true);
  await tapVisible(ui, inspect('out'));
  const out = await sample(page, true);
  assert.ok(zoom.height > 1.05 * right.height && out.height < .96 * zoom.height, 'In/out buttons change actual projected geometry');
  await page.locator(inspect('right')).focus();
  await page.keyboard.press('Enter');
  const keyboard = await sample(page);
  assert.ok(turn(out, keyboard) > 2 && keyboard.count > out.count, 'Native keyboard activation changes the physical view');
  return {leftYaw: round(l), rightYaw: round(r), zoomIn: round(zoom.height / right.height),
    zoomOut: round(out.height / zoom.height), keyboardYaw: round(turn(out, keyboard))};
}

async function outsideScroll({page, cdp}) {
  await center(page, '#service-title');
  const {x, y, before} = await page.locator('#service-title').evaluate(el => {
    const r = el.getBoundingClientRect();
    const x = r.left + r.width / 2;
    const y = r.top + r.height / 2;
    if (!el.contains(document.elementFromPoint(x, y))) throw Error('Outside swipe must start on exposed page content');
    return {x, y, before: scrollY};
  });
  await beginTrace(page);
  await swipe(cdp, {x, y}, 0, -120, 8);
  await page.waitForFunction(from => scrollY > from + 45, before);
  // Do not spend the next locale tap merely stopping the browser's native fling.
  await page.waitForFunction(() => performance.now() - __touchTrace.read().lastScroll > 150);
  const trace = await readTrace(page);
  assert.ok(trace.trusted && !trace.onCanvas && !trace.changedPick, 'Ordinary trusted page swipe outside the field');
  return {strokePx: 120, pageDeltaPx: round(await page.evaluate(() => scrollY) - before)};
}

async function ready(page, mode = 'ready') {
  await page.waitForSelector(`html[data-ui-ready="true"][data-viewport-state="${mode}"]`, {timeout: 60000});
  if (mode === 'ready') await settle(page);
}

async function chooseLanguage(ui, lang) {
  const {page} = ui;
  // The sticky masthead stays available even when the phone is down in the drawing.
  await tapVisible(ui, '#language-nav');
  const choice = `#language-dialog [data-language="${lang}"]`;
  await page.locator(choice).waitFor({state: 'visible'});
  // Locator.tap waits for the animated link to be stable and hit-testable; its input is trusted touch too.
  await page.locator(choice).tap();
  await page.waitForSelector(`html[lang="${lang}"][data-ui-ready="true"]`);
  await ready(page);
}

async function fallback(browserPage, href) {
  const {page, context} = browserPage;
  try {
    await page.addInitScript(() => {
      const original = HTMLCanvasElement.prototype.getContext;
      HTMLCanvasElement.prototype.getContext = function(kind, ...args) {
        return /webgl/i.test(kind) ? null : original.call(this, kind, ...args);
      };
    });
    await page.goto(href);
    await ready(page, 'fallback');
    await page.waitForFunction(() => {
      const image = document.getElementById('print-image');
      return image.complete && image.naturalWidth > 0 && image.getBoundingClientRect().height > 0;
    });
    const live = await page.locator('[data-inspect], [data-action="fit"]').evaluateAll(els =>
      els.filter(el => !el.disabled && el.getClientRects().length).length);
    assert.equal(live, 0, 'No actionable orbit/zoom buttons over an unavailable renderer');
    const row = page.locator('#part-list [data-part-id]').first();
    const id = await row.getAttribute('data-part-id');
    await row.tap();
    assert.equal(await page.locator('#passport:not([hidden]) #part-id').textContent(), id, 'Fallback still supports real touch selection in the register');
    return {decodedPrint: true, activeCameraButtons: live, registerPick: id};
  } finally {
    await context.close();
  }
}

async function run() {
  const args = process.argv.slice(2);
  assert.ok((args.length === 2 || args.length === 3) && path.isAbsolute(args[0]) && path.isAbsolute(args[1]),
    'Usage: node model/verify_atlas_touch.cjs /absolute/issue /existing/external/outdir [http(s)://…/atlas/]');
  const root = await fs.realpath(args[0]);
  const out = await fs.realpath(args[1]);
  for (const immutable of [root, await fs.realpath(path.resolve(__dirname, '..'))]) {
    assert.ok(out !== immutable && !out.startsWith(immutable + path.sep), 'Output must be outside both the issue and this verifier’s project');
  }
  const native = JSON.parse(await fs.readFile(path.join(root, 'VERIFICATION.json'), 'utf8'));
  const online = args.length === 3;
  const index = online ? new URL(args[2]) : pathToFileURL(path.join(root, 'atlas/index.html'));
  if (online) assert.ok(/^https?:$/.test(index.protocol) && !index.username && !index.password, 'Supply a public or localhost atlas URL');
  index.searchParams.set('lang', 'ru');
  const outputs = await fs.mkdtemp(path.join(out, 'touch-'));
  const tmp = await fs.mkdtemp(path.join(outputs, 'chrome-'));
  Object.assign(process.env, {TMPDIR: tmp, TMP: tmp, TEMP: tmp});
  const {chromium} = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');
  const report = {accepted: false, input: 'Chromium CDP trusted touch; emulated phone (not physical hardware)',
    transport: online ? 'explicit URL, same-origin HTTP(S)' : 'file, network disabled',
    verifierSHA256: sha(await fs.readFile(__filename)), screenshots: {}};
  let browser;
  let phase;
  function stage(label) {
    phase = label;
    console.log(`=== Touch: ${label}`);
  }
  try {
    stage('launch and verify issued scene');
    browser = await chromium.launch({headless: true, executablePath: process.env.CHROME || undefined,
      env: {...process.env, HOME: tmp, CFFIXED_USER_HOME: tmp, XDG_CACHE_HOME: path.join(tmp, 'cache'), XDG_CONFIG_HOME: path.join(tmp, 'config')},
      args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--disable-background-networking', '--disable-component-update',
        '--disable-crash-reporter', ...(online ? [] : ['--no-proxy-server', '--host-resolver-rules=MAP * ~NOTFOUND'])]});
    report.browser = `Chromium ${browser.version()}`;
    const network = {forbiddenRequests: 0, sockets: 0, pageErrors: 0};
    async function phone(observe = true) {
      const context = await browser.newContext({viewport: portrait, hasTouch: true, isMobile: true, deviceScaleFactor: 1,
        reducedMotion: 'reduce', locale: 'ru-RU', offline: !online, serviceWorkers: 'block'});
      const allowed = url => online && new URL(url).origin === index.origin;
      await context.route(/^https?:/i, route => allowed(route.request().url()) ? route.continue() : route.abort());
      context.on('request', req => {
        if (/^https?:/i.test(req.url()) && !allowed(req.url())) ++network.forbiddenRequests;
      });
      await context.routeWebSocket(/.*/, socket => {
        ++network.sockets;
        socket.close();
      });
      if (observe) await context.addInitScript(installObserver);
      const page = await context.newPage();
      page.on('pageerror', () => ++network.pageErrors);
      page.setDefaultTimeout(12000);
      const cdp = await context.newCDPSession(page);
      await cdp.send('Emulation.setTouchEmulationEnabled', {enabled: true, maxTouchPoints: 5});
      return {page, context, cdp, outputs, report};
    }
    const ui = await phone();
    const {page} = ui;
    await page.goto(index.href);
    await ready(page);
    const opened = new URL(page.url());
    assert.ok(opened.protocol === index.protocol && opened.origin === index.origin, 'Visit the supplied origin, not a local fixture');
    const scene = await page.evaluate(() => ({source: ATLAS_SCENE.sourceSHA256, meshes: __atlasFrame.pose().physicalLeaves,
      stages: ATLAS_SCENE.service.steps.length, sheets: document.querySelectorAll('#sheets > [role="tabpanel"]').length}));
    assert.deepEqual(scene, {source: native.source_sha256, meshes: 660, stages: 13, sheets: 2}, 'Expected physical issued scene and both sheets');
    report.scene = scene;

    stage('Russian portrait: short and deliberate sweeps on part and empty field');
    await center(page, canvas);
    report.initialTouchHelp = (await page.locator('#gesture-hint .touch-hint').innerText()).trim();
    assert.ok(report.initialTouchHelp && await page.locator('#gesture-hint .touch-hint').isVisible(), 'Visible first-use touch instructions');
    report.sweeps = [];
    for (const [onPart, dx] of [[true, 18], [false, 68], [true, -68], [false, -18]]) {
      report.sweeps.push(await sweep(ui, onPart, dx));
    }
    const signs = report.sweeps.map(s => Math.sign(s.yaw / s.dx));
    assert.ok(signs[0] && signs.every(sign => sign === signs[0]), 'Consistent signed yaw through successive poses, reversible on both kinds of contact');
    assert.ok(report.sweeps[1].degrees > 1.45 * report.sweeps[0].degrees && report.sweeps[2].degrees > 1.45 * report.sweeps[3].degrees,
      'Deliberate strokes rotate further than short ones, not repeated preset poses');
    // v1.1.0 rotated AND opened the register for this particular fine adjustment.
    report.fineSweep = await sweep(ui, true, 5);
    report.fineReverse = await sweep(ui, false, -5);
    report.idle = await idle(ui);
    stage('spread, lift just one finger, fit and explicit passport round trip');
    report.pinch = await pinch(ui);
    report.pick = await selectAndReturn(ui);

    stage('three locales, two orientations, touch/keyboard alternatives and native page scrolling');
    report.locales = {};
    for (const lang of ['ru', 'en', 'zh-CN']) {
      const reduce = lang !== 'en';
      await page.emulateMedia({reducedMotion: reduce ? 'reduce' : 'no-preference'});
      if (lang !== 'ru') await chooseLanguage(ui, lang);
      const size = lang === 'zh-CN' ? {width: 360, height: 740} : portrait;
      await page.setViewportSize(size);
      const layouts = {portrait: await controlsLayout(page, lang, size)};
      assert.equal(layouts.portrait.reduced, reduce);
      if (lang === 'ru') report.alternatives = await alternatives(ui);
      await page.setViewportSize(landscape);
      layouts.landscape = await controlsLayout(page, lang, landscape);
      if (lang === 'en') {
        await center(page, canvas);
        layouts.diagonal = await sweep(ui, true, 29, -22);
        assert.ok(Math.abs(layouts.diagonal.pitch) > 2 && Math.abs(layouts.diagonal.yaw) > 2, 'Landscape diagonal gesture turns both axes');
        layouts.idle = await idle(ui);
        await screenshot(ui, 'en-landscape-model.jpg');
      } else if (lang === 'zh-CN') {
        await center(page, canvas);
        layouts.vertical = await sweep(ui, false, 0, 24);
        assert.ok(Math.abs(layouts.vertical.pitch) > 2, 'Vertical empty-field gesture tilts the model');
        await page.setViewportSize(size);
        await center(page, '#drawing');
        await screenshot(ui, 'zh-portrait-controls.jpg');
      }
      layouts.outsideSwipe = await outsideScroll(ui);
      report.locales[lang] = layouts;
    }
    await ui.context.close();
    stage('WebGL unavailable: static drawing and touch-accessible CAD register');
    report.fallback = await fallback(await phone(false), index.href);
    assert.deepEqual(network, {forbiddenRequests: 0, sockets: 0, pageErrors: 0}, 'No disallowed network activity or uncaught page errors');
    report.network = network;
    report.accepted = true;
    await fs.writeFile(path.join(outputs, 'TOUCH_ACCEPTANCE.json'), JSON.stringify(report, null, 2) + '\n', {flag: 'wx'});
    console.log(`PASS ${report.transport}: ${path.basename(outputs)}/TOUCH_ACCEPTANCE.json`);
  } catch (error) {
    await fs.writeFile(path.join(outputs, 'TOUCH_DIAGNOSTIC.json'), JSON.stringify({...report, accepted: false, failedPhase: phase}, null, 2) + '\n', {flag: 'wx'});
    console.error(`NOT accepted (${phase}): ${path.basename(outputs)}/TOUCH_DIAGNOSTIC.json`);
    throw error;
  } finally {
    await browser?.close();
    if (path.dirname(await fs.realpath(tmp)) === outputs) await fs.rm(tmp, {recursive: true, force: true});
  }
}

run().catch(error => {
  console.error(error.message);
  process.exitCode = 1;
});
