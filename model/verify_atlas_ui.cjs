/* Offline acceptance of an issued directory (native verification, manifest, atlas and print image).
 * PLAYWRIGHT_CORE=... CHROME=... node verify_atlas_ui.cjs /absolute/issue /absolute/scratch
 * ATLAS_UI_BASELINE=1 runs only the 16 legacy scenarios and NEVER issues ATLAS_ACCEPTANCE.json.
 * Each invocation has a fresh output directory; the viewer itself has no test dependencies.
 */
'use strict';

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs/promises');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const product = require('./verify_product_page.cjs');

const baseline = process.env.ATLAS_UI_BASELINE === '1';
const report = {mode: baseline ? 'baseline' : 'release', releaseAccepted: false, scenarios: [], screenshotSHA256: {}};
const functional = ['Housing', 'LowerBody', 'Fascia', 'LightRing', 'Battery', 'Pod', 'Heater', 'MainPCB', 'DisplayPCB', 'Harness', 'Mounts'];
const zero = [0, 0, 0];
const eps = 1e-7; // World coordinates in metres (0.1 µm); not a claim about CAD accuracy.
const stateOf = page => page.evaluate(() => AtlasUI.getState());
const frames = page => page.evaluate(() => new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done))));
const sorted = xs => [...xs].sort();
const norm = value => String(value).replace(/\s+/g, ' ').trim();
const sameIDs = (actual, expected, label) => assert.deepEqual(sorted(actual), sorted(expected), label);
const near = (a, b, tolerance = eps) => Math.abs(a - b) <= tolerance;
const isVector = v => Array.isArray(v) && v.length === 3 && v.every(Number.isFinite);
const deltaFrom = (a, b) => a.map((v, i) => v - b[i]);
const checkVector = (value, target, label, tolerance = eps) => assert.ok(isVector(value) && isVector(target) &&
  value.every((v, i) => near(v, target[i], tolerance)), `${label}: [${value}] != [${target}] m`);
const partRows = page => page.locator('#part-list [data-part-id]').evaluateAll(rows => rows.map(row => row.dataset.partId));
const action = (page, name) => page.locator(`[data-action="${name}"]`);
const view = (page, name) => page.locator(`[data-view="${name}"]`);
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const verify = (name, condition) => {
  assert.ok(condition, name);
  report.scenarios.push(name);
};

const sheets = [
  {id: 'assembly', name: '01 Сборка'},
  {id: 'specs', name: '02 Размеры и материалы'},
];

async function checkSheets(page, active) {
  const nav = page.getByRole('tablist', {name: 'Листы атласа', exact: true});
  const tabs = nav.getByRole('tab');
  assert.equal(await tabs.count(), sheets.length, 'Exactly two top-level tabs in the accessible UI');
  assert.deepEqual(await nav.locator('button').allTextContents(), sheets.map(s => s.name));
  assert.deepEqual(await page.locator('#sheets > [role="tabpanel"]').evaluateAll(nodes => nodes.map(n => n.id)),
    sheets.map(s => s.id), 'No extra mounted (even hidden) top-level panels');
  const retired = [
    '#research', '#research-body', '#tab-research', '[data-page="research"]', '[data-ev-sheet="research"]',
    '[aria-controls~="research"]', '[aria-labelledby~="tab-research"]', '[href="#research"]',
    '[data-ev-list="sources"]', '[data-ev-list="observations"]',
  ];
  assert.equal(await page.locator(retired.join(',')).count(), 0, 'Removed sheet and controls must not exist in the DOM');
  assert.equal(await page.getByText('Фотоисследование', {exact: true}).count(), 0);
  for (const {id, name} of sheets) {
    const tab = nav.getByRole('tab', {name, exact: true});
    const selected = id === active;
    assert.ok(await tab.isVisible(), `Visible tab: ${name}`);
    assert.equal(await tab.getAttribute('aria-controls'), id);
    assert.equal(await tab.getAttribute('aria-selected'), String(selected));
    assert.equal(await tab.evaluate(el => el.tabIndex), selected ? 0 : -1);
    assert.equal(await page.getByRole('tabpanel', {name, exact: true}).count(), selected ? 1 : 0);
    assert.equal(await page.locator(`#${id}`).isVisible(), selected);
  }
  assert.equal(await page.evaluate(() => AtlasUI.getState().page), active);
  if (!baseline) {
    const overview = page.locator('#assembly #overview');
    assert.equal(await overview.count(), 1, 'The product is inside the assembly sheet, never a third sheet');
    assert.equal(await overview.isVisible(), active === 'assembly', 'Specs hides the entire product overview');
  }
}

async function visit(page, url, mode = 'ready') {
  await page.goto(url);
  await page.waitForSelector(`html[data-ui-ready="true"][data-viewport-state="${mode}"]`);
  await checkSheets(page, 'assembly');
}

async function turnSheet(page, target, key) {
  const tab = page.locator(`#tab-${target}`);
  if (key) {
    await page.locator('#sheets-nav [aria-selected="true"]').press(key);
    assert.ok(await tab.evaluate(el => el === document.activeElement), `Keyboard focus: ${target}`);
  } else await tab.click();
  await checkSheets(page, target);
}

async function openMaterialPassport(page) {
  const search = page.locator('#spec-body [data-ev-search="materials"]');
  if (await search.count()) await search.fill('MechHeaterPlate');
  await page.locator('#specs [data-ev-row="material"] [data-ev-part="MechHeaterPlate"]').click();
  await checkSheets(page, 'assembly');
  assert.equal(await page.locator('#passport:not([hidden]) #part-id').textContent(), 'MechHeaterPlate');
  assert.equal(await page.evaluate(() => AtlasUI.getState().group), 'Heater');
  assert.equal(await page.evaluate(() => document.activeElement.id), 'part-focus');
  const references = await page.evaluate(() => ATLAS_NOTES.observations
    .filter(o => o.parts.includes('MechHeaterPlate') && o.url).map(o => o.url));
  assert.ok(references.length, 'Real part-specific source expected');
  assert.deepEqual(await page.locator('#passport [data-ev-field="observations"] a')
    .evaluateAll(links => links.map(link => link.href)), references);
}

// r187 assigns WebGLRenderer.render on the instance. Its documented Scene callback
// runs after world updates and drawing, before the WebGL back buffer is discarded.
// Observe, never drive: no replacement renderer, setOffsets, render(), camera or geometry writes.
function installFrameObserver() {
  document.addEventListener('load', event => {
    if (!(event.target instanceof HTMLScriptElement) || !event.target.src.endsWith('/three-atlas.js')) return;
    const T = window.AtlasThree;
    const proto = T.Scene.prototype;
    const original = proto.onAfterRender;
    const copy = document.createElement('canvas');
    const ctx = copy.getContext('2d', {willReadFrequently: true});
    const models = new Map();
    const topology = {}; // Measured once, from instantiated Three meshes, not catalogue JSON.
    const visible = obj => obj.visible && (!obj.parent || visible(obj.parent));
    let camera, current;
    proto.onAfterRender = function(renderer, scene, eye, ...args) {
      original.call(this, renderer, scene, eye, ...args);
      const canvas = renderer.domElement;
      if (canvas.id !== 'atlas-canvas' || !(eye.isPerspectiveCamera || eye.isOrthographicCamera) || renderer.getRenderTarget() !== null) return;
      if (!models.size) {
        const ids = new Set(ATLAS_SCENE.parts.map(p => p.id));
        scene.traverse(o => {
          // The exporter attaches the registered CAD id to the physical glTF mesh's extras.
          if (!o.isMesh || !ids.has(o.userData.id)) return;
          if (models.has(o.userData.id)) throw Error(`Duplicate physical mesh: ${o.userData.id}`);
          models.set(o.userData.id, o);
          const ancestors = [];
          for (let parent = o.parent; parent; parent = parent.parent) {
            if (parent.userData.id) ancestors.push(parent.userData.id);
          }
          topology[o.userData.id] = {ancestors, triangles: (o.geometry.index || o.geometry.attributes.position).count / 3};
        });
      }
      camera = eye;
      const world = {}, paint = {}, shown = [];
      for (const [id, mesh] of models) {
        world[id] = mesh.matrixWorld.toArray();
        if (visible(mesh)) shown.push(id);
        paint[id] = [].concat(mesh.material).map(m =>
          [m.color?.getHex(), m.emissive?.getHex(), m.emissiveIntensity].join('/')).join(';');
      }
      if (copy.width !== canvas.width) copy.width = canvas.width;
      if (copy.height !== canvas.height) copy.height = canvas.height;
      ctx.drawImage(canvas, 0, 0); // Raw drawn pixels, NOT a DOM screenshot with captions/controls.
      current = {world, paint, shown, direction: eye.getWorldDirection(new T.Vector3()).toArray()};
    };
    window.__atlasFrame = {
      read: () => current,
      topology: () => topology,
      async pixels(region) {
        if (!current) throw Error('No observed Atlas render');
        const w = copy.width, h = copy.height;
        const rgba = ctx.getImageData(0, 0, w, h).data;
        const digest = async () => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', rgba)),
          b => b.toString(16).padStart(2, '0')).join('');
        const all = await digest();
        if (!region) return {all};
        const projectRect = points => {
          const ndc = points.map(p => p.project(camera));
          const xs = ndc.map(p => (p.x + 1) * w / 2), ys = ndc.map(p => (1 - p.y) * h / 2);
          return [Math.max(0, Math.floor(Math.min(...xs))-2), Math.max(0, Math.floor(Math.min(...ys))-2),
            Math.min(w, Math.ceil(Math.max(...xs))+2), Math.min(h, Math.ceil(Math.max(...ys))+2)];
        };
        // Peeling the film can reveal more of the dark glass field than the optical opening.
        // Colour must appear in the predicted aperture; nothing may change outside the actual carrier.
        const rect = projectRect(region.aperture.map(p => new T.Vector3(...p)));
        const rgb = region.color.slice(1).match(/../g).map(c => parseInt(c, 16));
        const hi = rgb.indexOf(Math.max(...rgb)), lo = rgb.indexOf(Math.min(...rgb));
        let ink = 0;
        for (let y = rect[1]; y < rect[3]; ++y) for (let x = rect[0]; x < rect[2]; ++x) {
          const n = (y*w+x)*4;
          ink += Math.max(0, rgba[n+hi] - rgba[n+lo]);
        }
        const {min, max} = new T.Box3().setFromObject(models.get(region.id));
        const corners = Array.from({length: 8}, (_, i) => new T.Vector3(i & 1 ? max.x : min.x,
          i & 2 ? max.y : min.y, i & 4 ? max.z : min.z));
        const [x0, y0, x1, y1] = projectRect(corners);
        if (x0 >= x1 || y0 >= y1 || (x1-x0)*(y1-y0) >= w*h/2) throw Error('LCD region not local/visible');
        for (let y = y0; y < y1; ++y) rgba.fill(0, (y*w+x0)*4, (y*w+x1)*4);
        return {all, outsideLCD: await digest(), rect, ink};
      },
      hit() {
        const canvas = document.getElementById('atlas-canvas');
        const rect = canvas.getBoundingClientRect();
        const ray = new T.Raycaster();
        const meshes = [...models.values()].filter(visible);
        // Hit-test the actual current projection. Pick a pixel not covered by DOM controls.
        for (const fy of [.5, .4, .6, .3, .7, .2, .8]) {
          for (const fx of [.5, .4, .6, .3, .7, .2, .8]) {
            const x = Math.floor(rect.left + fx * rect.width), y = Math.floor(rect.top + fy * rect.height);
            if (document.elementFromPoint(x, y) !== canvas) continue;
            ray.setFromCamera(new T.Vector2(2*(x-rect.left)/rect.width-1, 1-2*(y-rect.top)/rect.height), camera);
            const mesh = ray.intersectObjects(meshes, false)[0]?.object;
            if (mesh) return {id: mesh.userData.id, x, y};
          }
        }
        throw Error('No visible CAD triangle found for a real canvas click');
      },
    };
  }, true);
}

async function frame(page) {
  await frames(page);
  const result = await page.evaluate(() => window.__atlasFrame?.read());
  assert.ok(result && Object.keys(result.world).length, 'Observed the physical meshes in a real rendered frame');
  return result;
}

async function pixels(page, region = null) {
  await frames(page);
  return page.evaluate(corners => __atlasFrame.pixels(corners), region);
}

async function physicalPick(page) {
  await page.locator('#atlas-canvas').scrollIntoViewIfNeeded();
  await frames(page);
  const hit = await page.evaluate(() => __atlasFrame.hit());
  await page.mouse.click(hit.x, hit.y);
  assert.equal((await stateOf(page)).selected, hit.id, 'Passport must identify the triangle actually hit');
  assert.equal(await page.locator('#passport:not([hidden]) #part-id').textContent(), hit.id);
  return hit.id;
}

function checkWorld(actual, rest, offsets, label) {
  sameIDs(Object.keys(actual.world), Object.keys(rest.world), `${label}: same physical objects`);
  for (const [id, base] of Object.entries(rest.world)) {
    const matrix = actual.world[id];
    const d = offsets[id] || zero;
    // No rotation/scale disguised as an extraction; parent and local transforms counted exactly once.
    for (let j = 0; j < 16; ++j) {
      const expected = base[j] + (j >= 12 && j <= 14 ? d[j - 12] : 0);
      assert.ok(near(matrix[j], expected), `${label}: ${id}.matrixWorld[${j}] = ${matrix[j]}, expected ${expected}`);
    }
  }
}

// The manifest's first field is an unquoted FreeCAD Name. Respect quoted, multiline evidence fields.
function manifestIDs(csv) {
  const rows = [];
  let quoted = false;
  for (const line of csv.trimEnd().replace(/^\uFEFF/, '').split(/\r?\n/)) {
    if (!quoted) rows.push(line.split(',', 1)[0]);
    if ((line.match(/"/g) || []).length % 2) quoted = !quoted;
  }
  assert.ok(!quoted && rows.shift() === 'object_id' && rows.every(id => /^\w+$/.test(id)), 'Native manifest ID column');
  return rows;
}

async function readCatalogue(page, root) {
  const glb = await fs.readFile(path.join(root, 'atlas/data/atlas.glb'));
  assert.equal(glb.toString('ascii', 0, 4), 'glTF');
  assert.equal(glb.readUInt32LE(8), glb.length);
  const doc = JSON.parse(glb.toString('utf8', 20, 20 + glb.readUInt32LE(12)));
  const native = JSON.parse(await fs.readFile(path.join(root, 'VERIFICATION.json'), 'utf8'));
  const source = hash(await fs.readFile(path.join(root, 'XKAH_PRO_A43_rebuilt.FCStd')));
  const manifest = manifestIDs(await fs.readFile(path.join(root, 'MODEL_MANIFEST.csv'), 'utf8'));
  assert.equal(native.source_sha256, source, 'VERIFICATION.json must match this FCStd');
  assert.equal(native.valid_reopened_shapes, true, 'Native report must certify reopened geometry');
  assert.equal(doc.asset.extras.sourceSHA256, source, 'Standalone GLB must match this FCStd');
  const {scene, notes, embedded} = await page.evaluate(async () => {
    const {glbBase64, ...scene} = ATLAS_SCENE;
    const bytes = Uint8Array.fromBase64(glbBase64);
    const digest = new Uint8Array(await crypto.subtle.digest('SHA-256', bytes));
    return {scene, notes: ATLAS_NOTES, embedded: Array.from(digest, n => n.toString(16).padStart(2, '0')).join('')};
  });
  assert.equal(embedded, hash(glb), 'Browser opened exactly the verified standalone mesh bytes');
  assert.equal(scene.sourceSHA256, source);
  const ids = scene.parts.map(p => p.id);
  assert.ok(ids.length && new Set(ids).size === ids.length, 'Unique CAD leaf IDs');
  assert.equal(ids.length, native.physical_features);
  sameIDs(manifest, ids, 'One manifest record per scene leaf');
  sameIDs(doc.meshes.map(m => m.name), ids, 'No missing, duplicate or phantom GLB geometry');
  const groups = scene.groups.map(g => g.id);
  assert.ok(groups.length && new Set(groups).size === groups.length && !groups.includes('all'), 'Unique functional groups');
  if (!baseline) {
    sameIDs(groups, functional, 'Release requires exactly the eleven retail functional groups');
    sameIDs(scene.units.map(u => u.id), ['UpperUnit', 'LowerUnit'], 'Two installed units');
    for (const key of ['units', 'service', 'presentation']) {
      assert.deepEqual(doc.asset.extras[key], scene[key], `Browser and verified standalone GLB disagree: ${key}`);
    }
  }
  const groupOf = Object.fromEntries(scene.groups.map(g => [g.id, g]));
  const byId = Object.fromEntries(scene.parts.map(p => [p.id, p]));
  const memberIDs = group => scene.parts.filter(p => p.group === group).map(p => p.id);
  for (const g of scene.groups) {
    assert.ok(memberIDs(g.id).length, `Empty functional group ${g.id}`);
    if (!baseline) assert.ok(typeof g.shortLabel === 'string' && g.shortLabel.trim(), `${g.id}: shortLabel`);
  }
  // Also catch phantom instances (not just extra mesh definitions). GLTFLoader carries node.extras
  // into userData. Inspect actual ancestor order and positive triangle counts in that drawn graph.
  const topology = await page.evaluate(() => __atlasFrame.topology());
  sameIDs(Object.keys(topology), ids, 'All registered leaves instantiated exactly once');
  sameIDs(doc.nodes.filter(n => n.mesh !== undefined).map(n => n.name), ids, 'No phantom or orphan GLB instances');
  let triangles = 0;
  for (const p of scene.parts) {
    const {ancestors, triangles: count} = topology[p.id];
    assert.ok(groupOf[p.group] && ancestors.includes(p.group), `${p.id}: physical group ancestry`);
    if (!baseline) {
      assert.equal(p.unit, groupOf[p.group].unit);
      assert.ok(scene.units.some(u => u.id === p.unit) && ancestors.indexOf(p.unit) > ancestors.indexOf(p.group), `${p.id}: physical unit ancestry`);
    }
    assert.ok(Number.isInteger(count) && count > 0, `${p.id}: missing triangles`);
    triangles += count;
  }
  assert.equal(scene.triangleCount, triangles);
  Object.assign(report, {sourceSHA256: source, glbSHA256: embedded, physicalFeatures: ids.length, triangleCount: triangles,
    groupCounts: Object.fromEntries(groups.map(g => [g, memberIDs(g).length]))});
  return {scene, notes, ids, groups, groupOf, byId, memberIDs};
}

function servicePlan({scene, byId, ids}) {
  const steps = scene.service?.steps;
  assert.ok(Array.isArray(steps) && steps.length, 'Release requires an issued service plan');
  const totals = [{}]; // Pure oracle; never supplied to the UI or renderer.
  const targets = [[]];
  const names = new Set();
  for (const step of steps) {
    assert.ok(['id', 'title', 'text', 'source'].every(k => typeof step[k] === 'string' && step[k].trim()), 'Documented, named service step');
    assert.ok(!names.has(step.id), `Duplicate step ${step.id}`);
    names.add(step.id);
    const next = {...totals.at(-1)};
    assert.ok(Array.isArray(step.moves) && step.moves.length, `${step.id}: missing incremental moves`);
    const focus = step.focusIds ?? [];
    assert.ok(Array.isArray(focus) && focus.every(id => Object.hasOwn(byId, id)), `${step.id}: dangling focus ID`);
    const parts = new Set(focus);
    for (const {d, ids: moved} of step.moves) {
      assert.ok(isVector(d) && d.some(Boolean) && Array.isArray(moved) && moved.length && new Set(moved).size === moved.length,
        `${step.id}: invalid move`);
      for (const id of moved) {
        assert.ok(Object.hasOwn(byId, id), `${step.id}: phantom ${id}`);
        next[id] = (next[id] || zero).map((v, i) => v + d[i]);
        parts.add(id);
      }
    }
    assert.ok([...parts].some(id => deltaFrom(next[id] || zero, totals.at(-1)[id] || zero).some(v => Math.abs(v) > eps)),
      `${step.id}: no net movement`);
    totals.push(next);
    targets.push([...parts]);
  }
  for (const id of ids) checkVector(totals.at(-1)[id] || zero, byId[id].explode, `${id}: steps vs saved native leaf offset`, 1e-6);
  return {steps, totals, targets};
}

function checkRetailRoles(data, plan) {
  const {scene, groupOf, memberIDs, byId} = data;
  const {steps, totals} = plan;
  const at = (i, id) => totals[i][id] || zero;
  const increment = (i, id) => deltaFrom(at(i+1, id), at(i, id));
  const equal = (a, b) => a.every((v, i) => near(v, b[i]));
  const pod = ['MechRemovablePod', 'MechPodScreen', 'MechPodLid'];
  const film = ['MechServiceCover', 'MechCoverWindow'];
  const required = {
    Pod: pod, Fascia: [...film, 'MechKeyCarrier'], DisplayPCB: ['UiKeyMembrane', 'UiGlass', 'UiPlungerC'],
    LowerBody: ['MechLowerShroud', 'MechChamberInsert'], Housing: ['MechUpperFairing'],
    LightRing: ['MechLightRing', 'MechTopBridge'], Heater: ['MechHeatGuard', 'MechHeaterPlate'],
    Battery: ['MechBatteryEnvelope', 'MechPackCap', 'MechPackEndContacts', 'MechPackUsbRim', 'MechRetailBatteryRuSpecInk'],
  };
  for (const [group, leaves] of Object.entries(required)) {
    for (const id of leaves) assert.equal(byId[id]?.group, group, `${group}: missing/misfiled ${id}`);
  }
  assert.equal(groupOf.Battery.unit, 'UpperUnit');
  assert.equal(groupOf.Pod.unit, 'LowerUnit');
  const lcd = scene.presentation?.lcd;
  assert.equal(byId[lcd?.anchor]?.group, 'DisplayPCB', 'LCD must be bound to the display, not the removable film');
  assert.ok(lcd.artwork?.kind === 'presentation' && lcd.artwork.polygons?.length, 'Missing traced presentation');
  const box = byId[lcd.anchor].bbox;
  assert.ok(lcd.corners?.length === 4 && lcd.corners.every(p => isVector(p) && p.every((v, i) =>
    v >= box[i] - 0.00011 && v <= box[i+3] + 0.00011)), 'The optical aperture must be on the real anchor mesh (CAD tessellation tolerance)');

  // A role is witnessed by real, registered positive-triangle geometry *and* a distinct
  // relative movement. A text mention / focusIds entry alone is not an extracted part.
  const witnesses = {};
  function witness(name, predicate) {
    const i = steps.findIndex((_, i) => predicate(id => increment(i, id)));
    assert.ok(i >= 0, `No service step demonstrates ${name}`);
    witnesses[name] = steps[i].id;
    return i + 1;
  }
  const movesTogether = (d, ids) => !equal(d(ids[0]), zero) && ids.every(id => equal(d(id), d(ids[0])));
  const seat = 'MechPackSeatSockets';
  assert.ok(byId[seat]?.unit === 'UpperUnit' && byId[seat].group !== 'Battery', 'Fixed mating contacts in upper body');
  witness('removable pack versus fixed contacts', d => movesTogether(d, memberIDs('Battery')) && equal(d(seat), zero));
  const lower = scene.parts.filter(p => p.unit === 'LowerUnit').map(p => p.id);
  witness('lower unit with installed pod, apart from upper', d => movesTogether(d, lower) && equal(d('MechUpperFairing'), zero));
  witness('pod leaves lower receiver', d => movesTogether(d, pod) && !equal(d(pod[0]), d('MechChamberInsert')));
  assert.ok(totals.some((_, i) => pod.every((id, j) => pod.slice(j+1).every(other => !equal(at(i, id), at(i, other))))),
    'Cup, sieve and lid must occupy three distinct extraction offsets, not one translated pod');
  const filmIndex = witness('film and optical window detach from carrier and LCD', d => movesTogether(d, film) &&
    !equal(d(film[0]), d('MechKeyCarrier')) && !equal(d(film[0]), d('UiGlass')));
  witness('key membrane leaves display buttons', d => !equal(d('UiKeyMembrane'), zero) && !equal(d('UiKeyMembrane'), d('UiPlungerC')));
  const screws = data.ids.filter(id => id.startsWith('MechServiceScrew'));
  for (const station of ['TopL', 'TopR', 'SideR', 'Foot']) assert.ok(screws.includes(`MechServiceScrew${station}`), `Missing evidenced screw: ${station}`);
  witness('registered fascia fasteners distinct from film', d => screws.every(id => !equal(d(id), zero) && !equal(d(id), d(film[0]))));
  // The light catches can be integral to the crown; do not demand fictitious individual meshes for molded hooks.
  witness('snap crown and light diffuser leave their seats', d => movesTogether(d, ['MechLightRing', 'MechTopBridge']) && !equal(d('MechTopBridge'), d('MechUpperFairing')));
  const base = 'MechServiceBaseInsert'; // The base catch is molded on this registered carrier.
  assert.equal(byId[base]?.unit, 'UpperUnit');
  witness('internal base retention distinct from removable lower half', d => !equal(d(base), zero) &&
    !equal(d(base), d('MechUpperFairing')) && !equal(d(base), d('MechLowerShroud')));
  report.retail = {required, seat, screws, base, lcdAnchor: lcd.anchor, witnesses};
  return filmIndex;
}

async function groupTabs(page, data) {
  const tabs = await page.locator('#group-tabs [role="tab"]').evaluateAll(nodes => nodes.map(n => (
    {id: n.dataset.group, text: n.textContent.trim().replace(/^\d+\s*/, '')}
  )));
  assert.deepEqual(tabs.map(t => t.id), ['all', ...data.groups], 'DOM tab order must follow the issued group array');
  for (const tab of tabs.slice(1)) {
    const label = data.groupOf[tab.id].shortLabel;
    if (!baseline || label) assert.equal(tab.text, label, `Printed shortLabel for ${tab.id}`);
  }
}

async function checkGroup(page, data, id) {
  await page.locator(`[data-group="${id}"]`).click();
  assert.equal((await stateOf(page)).group, id);
  const expected = data.memberIDs(id);
  sameIDs(await partRows(page), expected, `${id}: catalogue membership`);
  assert.equal(await page.locator('#group-count').innerText(), String(expected.length), `Printed count for ${id}`);
}

async function checkSpecs(page, notes) {
  const dimensions = notes.dimensions;
  assert.ok(dimensions.some(d => /ширин|поперечн/i.test(d.name)) && dimensions.some(d => /диаметр/i.test(d.name)) &&
    dimensions.some(d => /^https:\/\//.test(d.url)), 'Separate, sourced width and diameter records');
  const sections = [['dimension', dimensions]];
  if (!baseline) sections.push(['kit', notes.kit]);
  for (const [kind, records] of sections) {
    assert.ok(Array.isArray(records) && records.length, `Missing ATLAS_NOTES ${kind} records`);
    const rows = page.locator(`#spec-body [data-ev-row="${kind}"]`);
    assert.equal(await rows.count(), records.length, `One ${kind} row per issued record`);
    for (const [i, item] of records.entries()) {
      const row = rows.nth(i);
      const text = norm(await row.innerText());
      const values = kind === 'kit' ? [item.label, item.source, ...(item.note ? [item.note] : [])] : [item.name, item.reference, item.cad];
      for (const value of values) assert.ok(value && text.includes(norm(value)), `${kind}[${i}]: ${value}`);
      if (kind === 'kit') {
        assert.ok(item.quantity != null && /^https?:\/\//.test(item.url), `kit[${i}]: documented quantity and source`);
        assert.equal(await row.getByText(`Количество: ${item.quantity}`, {exact: true}).count(), 1);
        assert.equal(await row.locator('[data-ev-part]').count(), 0, 'Kit is not an installed leaf register');
      }
      if (item.url) assert.deepEqual(await row.locator('a').evaluateAll(as => as.map(a => a.href)), [new URL(item.url).href]);
    }
    report.scenarios.push(kind === 'kit' ? 'regional kit labels, quantities, notes and source links match the issue' :
      'dimensions distinguish catalogue width and diameter and retain cited sources');
  }
}

async function checkStepOptions(page, steps) {
  assert.ok(await page.locator('#service-order').isVisible(), 'Existing assembly sheet exposes the service order');
  const select = page.locator('select#service-step');
  assert.ok(await select.isVisible() && await select.isEnabled(), 'Navigable native step select');
  const choices = await select.evaluate(s => [...s.options].map(o => ({id: o.value, title: o.textContent.trim()})));
  assert.deepEqual(choices.map(c => c.id), ['', ...steps.map(s => s.id)], 'Ordered CAD steps preceded by rest');
  assert.match(choices[0].title, /в сборе/i);
  steps.forEach((s, i) => assert.ok(choices[i+1].title.includes(s.title), `Select label: ${s.id}`));
}

async function checkPose(page, plan, i, readDetail = true) {
  const step = plan.steps[i-1];
  const state = await stateOf(page);
  assert.equal(state.serviceStep, step?.id ?? null);
  assert.equal(await page.locator('#service-step').inputValue(), step?.id || '');
  assert.equal(state.explode, 0, 'Service state and coarse explosion must not add together');
  const map = state.serviceOffsets;
  assert.ok(map && typeof map === 'object' && !Array.isArray(map), 'getState must expose a world offset map');
  const expected = plan.totals[i];
  for (const id of Object.keys(map)) {
    assert.ok(Object.hasOwn(expected, id), `${step?.id}: unexpected service offset for ${id}`);
    assert.ok(isVector(map[id]), `${id}: invalid public offset`);
  }
  for (const [id, d] of Object.entries(expected)) checkVector(map[id] || zero, d, `${step?.id}: state offset for ${id}`);
  if (!step) {
    assert.equal(await page.locator('#service-detail [data-service-part]').count(), 0, 'Rest has no stale detail buttons');
    return;
  }
  assert.equal(state.group, 'all');
  assert.equal(state.selected, null, 'Focus hint is not a passport selection');
  assert.equal(state.isolated, null);
  assert.ok(await page.locator('#passport').isHidden());
  if (!readDetail) return; // On reverse we verify the exact saved pose and rendered frame.
  assert.ok(norm(await page.locator('#service-detail').innerText()).includes(norm(step.text)), `${step.id}: annotation`);
  const source = page.locator('#service-source');
  assert.ok(await source.isVisible());
  if (/^https?:\/\/\S+$/.test(step.source)) {
    assert.deepEqual(await source.locator('a').evaluateAll(as => as.map(a => a.href)), [new URL(step.source).href]);
  } else assert.ok(norm(await source.innerText()).includes(norm(step.source)), `${step.id}: textual source`);
  const parts = page.locator('#service-parts');
  if (!await parts.evaluate(d => d.open)) await parts.locator('summary').click();
  const buttons = page.locator('#service-detail [data-service-part]');
  await buttons.first().waitFor({state: 'visible'});
  const detail = await buttons.evaluateAll(nodes => nodes.map(b => ({id: b.dataset.servicePart,
    button: b.tagName === 'BUTTON' && !b.disabled && !!b.closest('#service-parts') && !!b.getClientRects().length})));
  sameIDs(detail.map(b => b.id), plan.targets[i], `${step.id}: focus ∪ this step's moved leaves, no stale entries/duplicates`);
  assert.ok(detail.every(b => b.button), 'Each listed part is a genuine separate button');
  await parts.locator('summary').click(); // Keep layout, and thus canvas size, stable while comparing frames.
}

async function walkService(page, plan, inspectFrame) {
  await checkStepOptions(page, plan.steps);
  await checkPose(page, plan, 0);
  for (const [index, step] of plan.steps.entries()) {
    await action(page, 'service-next').click();
    await checkPose(page, plan, index + 1);
    if (inspectFrame) await inspectFrame(index + 1, step);
  }
}

async function assertScreen(page, on) {
  assert.equal((await stateOf(page)).screenOn, on);
  assert.equal(await action(page, 'screen').getAttribute('aria-pressed'), String(on));
}

async function screenCycle(page, lcd, offset) {
  const region = {id: lcd.anchor, color: lcd.artwork.color,
    aperture: lcd.corners.map(p => p.map((v, i) => v + offset[i]))};
  const button = action(page, 'screen');
  await view(page, 'front').click();
  await assertScreen(page, true);
  const lit = await pixels(page, region);
  await button.click();
  await assertScreen(page, false);
  const dark = await pixels(page, region);
  assert.notEqual(dark.all, lit.all, `${lcd.anchor}: changing real pixels on the screen`);
  assert.equal(dark.outsideLCD, lit.outsideLCD, `Screen change outside the projected ${lcd.anchor} mesh`);
  assert.ok(lit.ink > dark.ink, `No traced ink colour appeared inside the optical aperture of ${lcd.anchor}`);
  await button.click();
  await assertScreen(page, true);
  assert.deepEqual(await pixels(page, region), lit, 'Exact on frame with unchanged camera, finish and step');
  await button.click();
  await assertScreen(page, false);
  assert.deepEqual(await pixels(page, region), dark, 'Exact off frame');
  return {rect: lit.rect, onSHA256: lit.all, offSHA256: dark.all, outsideSHA256: lit.outsideLCD};
}

async function checkViews(page, restPixels) {
  const axes = {left: [1, 0, 0], right: [-1, 0, 0], bottom: [0, 1, 0]}; // camera looking INTO the model
  const hashes = [];
  for (const [name, direction] of Object.entries(axes)) {
    const control = view(page, name);
    await control.click();
    assert.equal((await stateOf(page)).view, name);
    assert.equal(await control.getAttribute('aria-pressed'), 'true');
    checkVector((await frame(page)).direction, direction, `${name}: camera direction`, 0.002);
    hashes.push((await pixels(page)).all);
  }
  assert.equal(new Set([restPixels, ...hashes]).size, hashes.length+1);
  await action(page, 'reset').click();
  verify('left, right and bottom use the corresponding world cameras; reset restores the original pixels', (await pixels(page)).all === restPixels);
}

async function releaseControls(page, data, plan, rest, initialPixels) {
  const {steps, totals} = plan;
  const select = page.locator('#service-step');
  const reset = action(page, 'reset');
  const lcd = data.scene.presentation.lcd;
  await checkViews(page, initialPixels);
  report.screen = {assembled: await screenCycle(page, lcd, zero)};
  await reset.click();
  await assertScreen(page, true);
  verify('catalogue screen starts on; on/off changes only the real optical aperture, reset returns to on', (await pixels(page)).all === initialPixels);

  // Remember forward frames under one named camera/finish. Do not compare different
  // auto-selected projections as proof of extraction. Matrix checks also cover hidden parts.
  await view(page, 'front').click();
  const forward = [{world: rest.world, image: (await pixels(page)).all}];
  await walkService(page, plan, async (i, s) => {
    if (s.view) assert.equal((await stateOf(page)).view, s.view, `${s.id}: documented preset`);
    await view(page, 'front').click();
    const actual = await frame(page);
    checkWorld(actual, rest, totals[i], s.id);
    sameIDs(actual.shown, data.ids, `${s.id}: service is an assembly, not a filtered model`);
    const changedPaint = data.ids.filter(id => actual.paint[id] !== rest.paint[id]);
    sameIDs(changedPaint, (s.focusIds || []).slice(0, 1), `${s.id}: visual hint on the requested physical leaf only`);
    const image = (await pixels(page)).all;
    if (image === forward.at(-1).image) {
      // A front projection can occlude an extracted part. Require differential pixels
      // from the same second projection, not a skipped check or just a changed camera.
      await select.selectOption(steps[i-2]?.id || '');
      await view(page, 'iso').click();
      const previous = (await pixels(page)).all;
      await select.selectOption(s.id);
      await view(page, 'iso').click();
      assert.notEqual((await pixels(page)).all, previous, `${s.id}: no visible transition in front or iso`);
    }
    forward.push({world: actual.world, image});
  });
  const independent = await page.evaluate(() => {
    const a = AtlasUI.getState().serviceOffsets, b = AtlasUI.getState().serviceOffsets;
    return a !== b && Object.keys(a).every(k => a[k] !== b[k]);
  });
  verify('independently accumulated steps match every rendered world matrix, all detail IDs and the physical focus hint', independent);
  for (let i = steps.length-1; i >= 0; --i) {
    await action(page, 'service-prev').click();
    await checkPose(page, plan, i, false);
    await view(page, 'front').click();
    assert.deepEqual((await frame(page)).world, forward[i].world, `Back to ${i}: exact world pose`);
    assert.equal((await pixels(page)).all, forward[i].image, `Back to ${i}: exact front frame`);
  }
  verify('previous 1→0 and every intermediate reverse transition restore the identical forward pose and pixels', (await stateOf(page)).serviceStep === null);

  const filmIndex = plan.filmIndex;
  const filmStep = steps[filmIndex - 1].id;
  await select.selectOption(filmStep);
  checkWorld(await frame(page), rest, totals[filmIndex], 'Direct select of peeled film');
  report.screen[filmStep] = await screenCycle(page, lcd, totals[filmIndex][lcd.anchor] || zero);
  await action(page, 'screen').click();
  // Repeat after the optical carrier itself has moved independently of the film.
  const movedLCD = totals.findLastIndex(map => map[lcd.anchor]?.some(Boolean) &&
    deltaFrom(map[lcd.anchor], map.MechCoverWindow || zero).some(v => Math.abs(v) > eps));
  assert.ok(movedLCD > 0, 'Missing stage with independently translated LCD carrier');
  await select.selectOption(steps[movedLCD-1].id);
  report.screen[steps[movedLCD-1].id] = await screenCycle(page, lcd, totals[movedLCD][lcd.anchor]);
  await reset.click();
  verify('the illuminated mark stays at the projected LCD after film removal and follows the moving LCD carrier', (await pixels(page)).all === initialPixels);

  const first = steps[0];
  async function rolledBack(label, id, group) {
    await checkPose(page, plan, 0);
    const state = await stateOf(page);
    assert.equal(state.selected, id);
    assert.equal(state.group, group);
    if (id) assert.equal(await page.locator('#passport:not([hidden]) #part-id').textContent(), id);
    const actual = await frame(page);
    checkWorld(actual, rest, {}, label);
    sameIDs(actual.shown, group === 'all' ? data.ids : data.memberIDs(group), `${label}: only correct group visible`);
  }
  await page.locator('#explode-slider [role="slider"]').press('End');
  await select.selectOption(first.id);
  await checkPose(page, plan, 1);
  checkWorld(await frame(page), rest, totals[1], 'Starting service clears full slider explosion');
  await page.locator(`[data-group="${data.groups[0]}"]`).click();
  await rolledBack('group rollback', null, data.groups[0]);
  await select.selectOption(filmStep);
  await page.locator('#service-parts > summary').click();
  const film = 'MechServiceCover';
  await page.locator(`#service-detail button[data-service-part="${film}"]`).click();
  await rolledBack('detail button rollback', film, data.byId[film].group);
  await action(page, 'isolate').click();
  await select.selectOption(first.id);
  await checkPose(page, plan, 1);
  sameIDs((await frame(page)).shown, data.ids, 'Service releases previous isolation');
  const member = 'UiKeyMembrane';
  await page.locator(`#part-list [data-part-id="${member}"]`).click();
  await rolledBack('register pick rollback', member, data.byId[member].group);
  await select.selectOption(first.id);
  const hit = await physicalPick(page);
  await rolledBack('canvas pick rollback', hit, data.byId[hit].group);
  await select.selectOption(steps.at(-1).id);
  await action(page, 'service-rest').click();
  await rolledBack('rest button', null, 'all');
  await reset.click();
  verify('group, step-detail, register and real canvas picks rollback before opening the correct physical group; rest clears all',
    (await pixels(page)).all === initialPixels);
  report.steps = steps.map((step, i) => ({id: step.id, detailCount: plan.targets[i+1].length, frontSHA256: forward[i+1].image}));
}

async function noScreen(page) {
  const screen = action(page, 'screen');
  assert.ok(await screen.count() === 0 || await screen.isHidden() || await screen.isDisabled(), 'No usable screen switch without traced WebGL art');
  const state = await stateOf(page);
  if (!baseline || 'screenOn' in state) assert.equal(state.screenOn, false);
}

async function legacyControls(page, data, rest, original, shot, productFrames) {
  const {ids, groups, byId, groupOf, memberIDs, notes} = data;
  const state = () => stateOf(page);
  const viewHash = async () => (await pixels(page)).all;
  const list = page.locator('#part-list [data-part-id]');
  console.log('=== WebGL: palettes, full explosion, catalogue, keyboard and picks');
  const colors = [];
  for (const {id: finish} of notes.finishes) {
    await page.locator(`[data-finish="${finish}"]`).click();
    assert.equal((await state()).finish, finish);
    colors.push(await viewHash());
    if (!baseline) {
      await product.checkFinish(page, finish);
      assert.equal(colors.at(-1), productFrames.get(finish), `${finish}: same rendered finish from either control`);
    }
  }
  verify('four real surface palettes render four distinct frames', colors.length === 4 && new Set(colors).size === 4);
  await action(page, 'reset').click();
  if (!baseline) await product.checkFinish(page, 'graphite');
  const before = await viewHash();
  assert.equal(before, original, 'Reset restores the initial palette and frame');
  await page.locator('#explode-slider [role="slider"]').press('End');
  const full = Object.fromEntries(ids.map(id => [id, byId[id].explode ?? groupOf[byId[id].group].explode]));
  for (const id of ids) assert.ok(isVector(full[id]), `No explode vector: ${id}`);
  checkWorld(await frame(page), rest, full, 'Full slider explosion');
  verify('keyboard operates the custom explode slider and changes geometry on screen',
    (await state()).explode === 1 && await viewHash() !== before);
  await shot('atlas-exploded');
  await action(page, 'reset').click();
  checkWorld(await frame(page), rest, {}, 'Explosion reset');
  assert.equal(await viewHash(), original, 'Explosion reset restores original pixels');
  for (const group of groups) {
    await checkGroup(page, data, group);
    sameIDs((await frame(page)).shown, memberIDs(group), `${group}: real filtered render`);
    if (group === 'MainPCB') await shot('atlas-mainboard');
  }
  verify('all issued subsystem tabs load precisely their own CAD parts', (await state()).group === groups.at(-1));
  await page.locator('[data-group="DisplayPCB"]').click();
  await page.locator('#part-search').fill('UiPerforatedLand');
  assert.equal(await list.count(), 1);
  await page.locator('#part-search').press('Enter');
  verify('keyboard search selects the actual perforated region of the display PCB',
    (await state()).selected === 'UiPerforatedLand' && await page.locator('#part-id').textContent() === 'UiPerforatedLand');
  const broad = await viewHash();
  await action(page, 'isolate').click();
  sameIDs((await frame(page)).shown, ['UiPerforatedLand'], 'Isolation hides every other physical ID');
  verify('isolation changes the view; unrelated bodies disappear', (await state()).isolated === 'UiPerforatedLand' && await viewHash() !== broad);
  await action(page, 'leave-isolation').click();
  assert.ok(!(await state()).isolated);
  await action(page, 'reset').click();
  verify('physical canvas pick opens a catalogue passport', Boolean(await physicalPick(page)));
  for (const [target, key] of [['specs', 'ArrowLeft'], ['assembly', 'ArrowRight'], ['specs', 'End'], ['assembly', 'Home']]) {
    await turnSheet(page, target, key);
  }
  report.scenarios.push('two numbered sheets share a wrapping keyboard tablist with only one tab stop');
  await turnSheet(page, 'specs');
  await checkSpecs(page, notes);
  await openMaterialPassport(page);
  report.scenarios.push('material ID returns to the linked CAD passport and its own sources');
  await action(page, 'reset').click();
  const orderedTabs = ['all', ...groups];
  await page.locator('[data-group="MainPCB"]').press('ArrowRight');
  verify('arrow keys move between subsystem tabs in issued order',
    (await state()).group === orderedTabs[(orderedTabs.indexOf('MainPCB') + 1) % orderedTabs.length]);
}

async function fallbackControls(fallback, index, root, data, plan, original, clean) {
  const {groups, byId} = data;
  await fallback.addInitScript(() => {
    if (location.search !== '?no-webgl') return;
    const nativeGet = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function(type, ...args) {
      return type.includes('webgl') ? null : nativeGet.call(this, type, ...args);
    };
  });
  const alt = await fallback.newPage();
  await visit(alt, `${index}?no-webgl`, 'fallback');
  await noScreen(alt);
  if (!baseline) {
    await product.checkFinish(alt, 'graphite');
    await product.checkLayout(alt);
    await alt.locator(product.productButton('silver')).click();
    await product.checkFinish(alt, 'silver');
  }
  await groupTabs(alt, data);
  for (const group of groups) await checkGroup(alt, data, group);
  const print = alt.locator('#print-image');
  assert.equal(await print.evaluate(img => img.currentSrc), pathToFileURL(path.join(root, 'XKAH_PRO_A43_assembly_assembled.png')).href);
  verify('explicit WebGL fallback retains all subsystem entries and a genuine CAD illustration',
    await print.isVisible() && await print.evaluate(img => img.complete && img.naturalWidth > 100));
  if (!baseline) {
    await action(alt, 'reset').click();
    await walkService(alt, plan);
    await alt.locator('#service-parts > summary').click();
    const id = plan.targets.at(-1)[0];
    await alt.locator(`#service-detail button[data-service-part="${id}"]`).click();
    await checkPose(alt, plan, 0);
    assert.equal((await stateOf(alt)).group, byId[id].group);
    verify('without WebGL all steps have the same ordered, sourced, actionable parts list', (await stateOf(alt)).selected === id);
  }
  await turnSheet(alt, 'specs', 'ArrowRight');
  await openMaterialPassport(alt);
  await visit(alt, index);
  if (!baseline) {
    await assertScreen(alt, true);
    await checkPose(alt, plan, 0);
    assert.equal((await pixels(alt)).all, original, 'Reopened WebGL renders the initial on frame');
  }
  await turnSheet(alt, 'specs');
  await turnSheet(alt, 'assembly', 'ArrowLeft');
  verify('fallback, material-to-passport navigation and reopening with WebGL expose only the two sheets', clean());
}

async function run() {
  const [input, scratch] = process.argv.slice(2);
  assert.ok(input && scratch && path.isAbsolute(input) && path.isAbsolute(scratch),
    'Usage: node verify_atlas_ui.cjs /absolute/issue /absolute/scratch (outside the issue)');
  const root = await fs.realpath(input);
  const outRoot = await fs.realpath(scratch); // The caller supplies an existing scratch, never the issue tree.
  for (const readOnly of [root, path.resolve(__dirname, '..')]) {
    assert.ok(outRoot !== readOnly && !outRoot.startsWith(readOnly + path.sep), `Refusing to write inside ${readOnly}`);
  }
  const outputs = await fs.mkdtemp(path.join(outRoot, `atlas-${report.mode}-`));
  const tmp = path.join(outputs, 'browser-tmp');
  await fs.mkdir(tmp);
  Object.assign(process.env, {TMPDIR: tmp, TMP: tmp, TEMP: tmp}); // Playwright's temp profile, downloads, crash dumps
  const {chromium} = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');
  const index = pathToFileURL(path.join(root, 'atlas/index.html')).href;
  const browser = await chromium.launch({
    headless: true,
    env: {...process.env, HOME: tmp, CFFIXED_USER_HOME: tmp, XDG_CACHE_HOME: path.join(tmp, 'cache'), XDG_CONFIG_HOME: path.join(tmp, 'config')},
    executablePath: process.env.CHROME || undefined,
    args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--disable-background-networking',
      '--disable-component-update', '--disable-crash-reporter', '--no-proxy-server', '--host-resolver-rules=MAP * ~NOTFOUND'],
  });
  console.log(`=== ${report.mode}: ${index} → ${outputs}`);
  try {
    report.browser = `Chromium ${browser.version()}`;
    const errors = [], external = [];
    async function openContext() {
      const context = await browser.newContext({offline: true, serviceWorkers: 'block', reducedMotion: 'reduce',
        viewport: {width: 1440, height: 960}, deviceScaleFactor: 1});
      context.on('request', r => { if (/^(https?|wss?):/i.test(r.url())) external.push(r.url()); });
      context.on('page', p => {
        p.on('pageerror', e => errors.push(e.message));
        p.on('websocket', ws => external.push(ws.url()));
      });
      await context.addInitScript(installFrameObserver);
      return context;
    }
    function clean() {
      assert.deepEqual(errors, [], 'No uncaught exception');
      assert.deepEqual(external, [], 'No external requests, even failed attempts');
      return true;
    }
    const context = await openContext();
    const page = await context.newPage();
    const shot = async name => {
      await page.mouse.move(2, 1);
      // Photograph the state just verified, not the top of a now much longer document.
      if (name === 'atlas-mainboard' || name === 'atlas-exploded') {
        const canvas = page.locator('#atlas-canvas');
        await canvas.evaluate(el => el.scrollIntoView({block: 'center', inline: 'nearest', behavior: 'instant'}));
        await product.inFrame(canvas, .90, `${name}: actual WebGL canvas`);
        await product.inFrame(page.locator('#drawing-title'), .95, `${name}: drawing title`);
        if (name === 'atlas-mainboard') {
          assert.equal((await stateOf(page)).group, 'MainPCB');
          await product.inFrame(page.locator('#register-title'), .95, 'MainPCB register heading');
          await product.inFrame(page.locator('#part-list [data-part-id]').first(), .90, 'MainPCB register entries');
        } else {
          assert.equal((await stateOf(page)).explode, 1);
          await product.inFrame(page.locator('#explode-value'), .95, 'Full explosion control');
        }
      } else {
        assert.ok(await page.evaluate(() => Math.abs(scrollY) <= 1), `${name}: actual first screen`);
        if (!baseline) {
          await product.checkFinish(page, 'graphite');
          await product.checkLayout(page);
        }
      }
      await frames(page);
      const bytes = await page.screenshot({path: path.join(outputs, `${name}.png`), fullPage: false, animations: 'disabled'});
      report.screenshotSHA256[name] = hash(bytes);
    };
    await visit(page, index);
    await shot('atlas-assembly'); // Untouched landing state, before any palette or viewer interaction.
    const data = await readCatalogue(page, root);
    const rest = await frame(page);
    const original = (await pixels(page)).all;
    sameIDs(rest.shown, data.ids, 'All verified physical IDs appear in the actual render');
    verify('file:// opened the matching native scene with WebGL', page.url() === index);
    sameIDs(await partRows(page), data.ids, 'No missing, duplicate or phantom rows in the catalogue');
    report.scenarios.push('one catalogue row for each independently selectable CAD leaf');
    await groupTabs(page, data);
    let plan;
    const productFrames = new Map();
    if (!baseline) {
      plan = servicePlan(data);
      plan.filmIndex = checkRetailRoles(data, plan);
      await checkPose(page, plan, 0);
      await assertScreen(page, true);
      console.log('=== Product overview: local studio finishes, real palette, navigation and service CTA');
      report.product = {imageSHA256: await product.checkOptions(page, root)};
      const studioFrames = new Set();
      for (const finish of product.finishes) {
        await page.locator(product.productButton(finish)).click();
        await product.checkFinish(page, finish);
        // Compare the visible illustration alone, excluding changed captions and swatch outlines.
        studioFrames.add(hash(await page.locator('#product-image').screenshot({animations: 'disabled'})));
        productFrames.set(finish, (await pixels(page)).all);
      }
      assert.equal(studioFrames.size, product.finishes.length, 'All four decoded studio images look different');
      await action(page, 'reset').click();
      await product.checkFinish(page, 'graphite');
      await product.checkNavigation(page, plan.steps[0].id, turnSheet, checkSheets);
      await checkPose(page, plan, 1, false);
      checkWorld(await frame(page), rest, plan.totals[1], 'Service CTA really moves the first issued parts');
      await action(page, 'reset').click();
    } else if (!data.scene.presentation?.lcd) await noScreen(page);
    await legacyControls(page, data, rest, original, shot, productFrames);
    if (!baseline) {
      console.log('=== Retail: camera axes, optical aperture, every accumulated service pose and rollback');
      await action(page, 'reset').click();
      await releaseControls(page, data, plan, rest, original);
    }
    if (!baseline) {
      for (const [width, height] of [[1280, 800], [768, 1024], [360, 740]]) {
        await page.setViewportSize({width, height});
        await page.evaluate(() => window.scrollTo({top: 0, left: 0, behavior: 'instant'}));
        await frames(page);
        await product.checkLayout(page);
      }
    }
    await page.setViewportSize({width: 390, height: 844});
    await turnSheet(page, 'specs');
    await turnSheet(page, 'assembly');
    const width = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);
    verify('mobile layout has no document-level horizontal overflow', width[0] <= width[1] + 1);
    await action(page, 'reset').click();
    await page.evaluate(() => window.scrollTo({top: 0, left: 0, behavior: 'instant'}));
    await shot('atlas-mobile');
    verify('no uncaught browser exception and no remote request', clean());
    await context.close();

    console.log('=== Forced WebGL failure: print image, ordered text, catalogue and recovery');
    const fallback = await openContext();
    await fallbackControls(fallback, index, root, data, plan, original, clean);
    await fallback.close();
    if (baseline) assert.equal(report.scenarios.length, 16, 'Preserve the sixteen baseline scenarios');
    else assert.equal(report.scenarios.length, 24, 'Preserve all 24 release scenarios');
    sameIDs(Object.keys(report.screenshotSHA256), ['atlas-assembly', 'atlas-exploded', 'atlas-mainboard', 'atlas-mobile'], 'Published screenshot keys');
    assert.equal(new Set(Object.values(report.screenshotSHA256)).size, 4, 'Four distinct viewport captures');
    report.releaseAccepted = !baseline;
    const file = baseline ? 'ATLAS_BASELINE.json' : 'ATLAS_ACCEPTANCE.json';
    await fs.writeFile(path.join(outputs, file), JSON.stringify(report, null, 2) + '\n', {flag: 'wx'});
    console.log(`${baseline ? 'BASELINE ONLY (not release acceptance)' : 'PASS release'}: ${report.scenarios.length} scenarios, ` +
      `${report.physicalFeatures} physical features, ${report.triangleCount} triangles. ${path.join(outputs, file)}`);
  } finally {
    await browser.close();
  }
}

run().catch(error => {
  console.error(`FAIL ${report.mode}:`, error);
  process.exitCode = 1;
});
