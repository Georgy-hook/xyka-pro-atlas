/* Release-only offline browser checks. The historical Russian scenarios and their
 * independent native/GLB/frame oracles remain in verify_atlas_ui.cjs. */
'use strict';

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs/promises');
const path = require('node:path');
const product = require('./verify_product_page.cjs');

const languages = ['en', 'ru', 'zh-CN'];
const selfNames = {en: 'English', ru: 'Русский', 'zh-CN': '简体中文'};
const widths = [[1440, 960], [1280, 800], [768, 1024], [390, 844], [360, 740]];
const terms = {
  en: {tabs: ['01 Assembly', '02 Dimensions & materials'], title: /inside/i, battery: /batter|pack/i,
    material: /not (?:been )?(?:identified|established|determined|known)|unknown|unconfirmed/i, unavailable: /unavailable|not available/i},
  ru: {tabs: ['01 Сборка', '02 Размеры и материалы'], title: /изнутри/i, battery: /батаре|аккумулятор/i,
    material: /не установлен|неизвест/i, unavailable: /недоступ/i},
  'zh-CN': {tabs: ['01 装配模型', '02 尺寸与材料'], title: /内部/, battery: /电池/,
    material: /未[确知明]|不明|未知|无法确定/, unavailable: /无法|不可/}
};
const cleanText = s => String(s).replace(/\s+/g, ' ').trim();
const hrefs = locator => locator.evaluateAll(links => links.map(a => a.href));
const state = page => page.evaluate(() => AtlasUI.getState());
const raf = page => page.evaluate(() => new Promise(ok => requestAnimationFrame(() => requestAnimationFrame(ok))));
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');

function human(text, lang, label) {
  // Use only on prose known NOT to quote the original printed artwork, CAD IDs or source files.
  const script = {en: /[a-z]{2}/i, ru: /\p{Script=Cyrillic}/u, 'zh-CN': /\p{Script=Han}/u};
  assert.match(text, script[lang], `${lang} ${label}: missing human text`);
  if (lang !== 'ru') assert.doesNotMatch(text, /\p{Script=Cyrillic}/u, `${lang} ${label}: untranslated Russian copy`);
  if (lang !== 'zh-CN') assert.doesNotMatch(text, /\p{Script=Han}/u, `${lang} ${label}: unexpected Chinese copy`);
}

async function visit(page, url, lang, mode = 'ready') {
  await page.goto(url);
  await page.waitForSelector(`html[data-ui-ready="true"][data-viewport-state="${mode}"]`);
  assert.equal(await page.locator('html').getAttribute('lang'), lang, url);
  assert.equal(await page.evaluate(() => AtlasLocale.lang), lang);
  assert.equal(new URL(page.url()).protocol, 'file:');
}

// Independently parse the issued classic JSON assignments, not the already-running app.
// Digest the base64 payload separately so a complete GLB never crosses Playwright's wire.
async function rawDigests(root) {
  async function assignment(rel, key) {
    const source = (await fs.readFile(path.join(root, rel), 'utf8')).trimEnd();
    const prefix = new RegExp(`^(?:\\s*//[^\\n]*\\n)*\\s*window\\.${key}\\s*=\\s*`);
    const match = source.match(prefix);
    assert.ok(match && source.endsWith(';'), `${rel}: expected an issued classic JSON assignment`);
    return JSON.parse(source.slice(match[0].length, -1));
  }
  const {glbBase64, ...scene} = await assignment('atlas/data/scene.js', 'ATLAS_SCENE');
  const notes = await assignment('atlas/evidence.js', 'ATLAS_NOTES');
  return {scene: hash(JSON.stringify(scene)), notes: hash(JSON.stringify(notes)), glb: hash(Buffer.from(glbBase64, 'base64'))};
}

async function presentation(page, lang, expected, issued) {
  const sample = await page.evaluate(async () => {
    const {data, notes} = AtlasLocale.catalogue(ATLAS_SCENE, ATLAS_NOTES);
    const {glbBase64, ...raw} = ATLAS_SCENE;
    const bytes = value => new TextEncoder().encode(JSON.stringify(value));
    const sha = async bytes => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)),
      v => v.toString(16).padStart(2, '0')).join('');
    const digests = {scene: await sha(bytes(raw)), notes: await sha(bytes(ATLAS_NOTES)),
      glb: await sha(Uint8Array.fromBase64(glbBase64))};
    const copies = data !== ATLAS_SCENE && data.parts !== ATLAS_SCENE.parts && notes !== ATLAS_NOTES;
    const intact = data.glbBase64 === glbBase64;
    return {digests, copies, intact, source: data.sourceSHA256, parts: data.parts, groups: data.groups,
      steps: data.service.steps, notes, localized: AtlasLocale.t('Русский', 'English', '简体中文')};
  });
  assert.deepEqual(sample.digests, expected, `${lang}: original scene, embedded mesh and notes match disk after localization`);
  assert.ok(sample.copies && sample.intact, `${lang}: separate presentation of the exact embedded mesh`);
  assert.equal(sample.source, issued.scene.sourceSHA256);
  assert.equal(sample.localized, selfNames[lang]);
  assert.deepEqual(sample.groups.map(g => g.id), issued.groups);
  assert.deepEqual(sample.parts.map(p => p.id), issued.ids);
  for (const p of sample.parts) {
    const raw = issued.byId[p.id];
    for (const k of ['unit', 'group', 'bbox', 'nativePath', 'explode', 'color']) {
      assert.deepEqual(p[k], raw[k], `${lang}: ${p.id}.${k}`);
    }
  }
  for (const [i, step] of sample.steps.entries()) {
    for (const k of ['id', 'moves', 'focusIds', 'view']) assert.deepEqual(step[k], issued.scene.service.steps[i][k]);
  }
  assert.equal(sample.steps.length, issued.scene.service.steps.length);
  for (const [i, finish] of sample.notes.finishes.entries()) {
    for (const k of ['id', 'swatch', 'colors', 'source']) assert.deepEqual(finish[k], issued.notes.finishes[i][k]);
  }
  assert.deepEqual(Object.keys(sample.notes.materials).sort(), Object.keys(issued.notes.materials).sort());
  assert.deepEqual(sample.notes.sources.map(s => s.url), issued.notes.sources.map(s => s.url));
  assert.deepEqual(sample.notes.observations.map(o => [o.url, o.parts]), issued.notes.observations.map(o => [o.url, o.parts]));
  sample.byId = Object.fromEntries(sample.parts.map(p => [p.id, p]));
  return sample;
}

async function sheet(page, lang, active) {
  const nav = page.locator('#sheets-nav');
  assert.equal(await nav.getByRole('tab').count(), 2);
  assert.equal(await page.getByRole('tabpanel', {name: terms[lang].tabs[active === 'assembly' ? 0 : 1], exact: true}).count(), 1);
  for (const [i, id] of ['assembly', 'specs'].entries()) {
    const tab = nav.getByRole('tab', {name: terms[lang].tabs[i], exact: true});
    assert.equal(await tab.getAttribute('aria-controls'), id);
    assert.equal(await tab.getAttribute('aria-selected'), String(id === active));
    assert.equal(await page.locator(`#${id}`).isVisible(), id === active);
  }
  assert.equal((await state(page)).page, active);
}

async function checkSpecs(page, sample, issued, lang) {
  await sheet(page, lang, 'specs');
  const spec = page.locator('#spec-body [data-ev-sheet]');
  assert.equal(await spec.evaluate(el => el.closest('[lang]').lang), lang);
  human(await spec.locator('h2').innerText(), lang, 'specification heading');
  const {dimensions, kit} = sample.notes;
  for (const [kind, records] of [['dimension', dimensions], ['kit', kit]]) {
    const rows = spec.locator(`[data-ev-row="${kind}"]`);
    const original = kind === 'kit' ? issued.notes.kit : issued.notes.dimensions;
    assert.equal(records.length, original.length);
    assert.equal(await rows.count(), original.length);
    for (const [i, item] of records.entries()) {
      const row = rows.nth(i);
      const raw = original[i];
      const printed = cleanText(await row.innerText());
      const title = kind === 'kit' ? item.label : item.name;
      human(title, lang, `${kind}[${i}] title`);
      for (const s of (kind === 'kit' ? [title, item.source, item.note] : [title, item.cad, item.reference, item.status])) {
        if (s) assert.ok(printed.includes(cleanText(s)), `${lang} ${kind}[${i}] missing ${s}`);
      }
      assert.deepEqual(await hrefs(row.locator('a')), raw.url ? [new URL(raw.url).href] : [], `${kind}[${i}] actual citation`);
      if (kind === 'kit') {
        assert.equal(item.quantity, raw.quantity);
        assert.match(await row.locator('.ev-kit-line > .ev-label').innerText(), new RegExp(`(?:^|\\D)${raw.quantity}(?:$|\\D)`));
      } else {
        const value = await row.locator('[data-ev-field="cad"]').innerText();
        const numbers = s => (s.replace(/(\d),(?=\d)/g, '$1.').match(/\d+(?:\.\d+)?|±|°|×/g) || []);
        assert.deepEqual(numbers(value), numbers(raw.cad), `${lang} ${title}: measurements, tolerances and decimal places`);
        if (raw.cad.includes('мм')) assert.match(value, lang === 'ru' ? /мм/ : /mm|毫米/);
      }
    }
  }
}

async function materialPassport(page, sample, issued, lang) {
  const id = 'MechHeaterPlate';
  const part = sample.byId[id];
  const search = page.locator('[data-ev-search="materials"]');
  if (await search.count()) await search.fill(id);
  const button = page.locator(`[data-ev-list="materials"] button[data-ev-part="${id}"]`);
  const row = button.locator('xpath=ancestor::li[@data-ev-row="material"]');
  const material = sample.notes.materials[id];
  assert.match(material, terms[lang].material, `${lang}: substrate/coating/layers not identified`);
  assert.ok(cleanText(await row.innerText()).includes(cleanText(material)));
  await button.click();
  await sheet(page, lang, 'assembly');
  assert.equal((await state(page)).group, 'Heater');
  const root = page.locator(`#passport [data-ev-passport="${id}"]`);
  assert.equal(await root.evaluate(el => el.closest('[lang]').lang), lang);
  assert.equal(await page.locator('#part-focus:focus').innerText(), part.label);
  assert.equal(await page.locator('#part-id').innerText(), id);
  human(part.label, lang, 'heater part name');
  const field = key => root.locator(`[data-ev-field="${key}"]`);
  for (const [key, text] of [['sub', part.sub], ['material', material], ['confidence', part.confidence], ['note', part.note]]) {
    assert.ok(cleanText(await field(key).innerText()).includes(cleanText(text)), `${lang} ${id} ${key}`);
  }
  assert.match(await field('confidence').innerText(), /EST/);
  assert.match(await field('note').innerText(), /UNKNOWN/);
  const bbox = await field('bbox').evaluate(el => el.firstChild.textContent);
  const sizes = [...bbox.matchAll(/\d+(?:[,.]\d+)?/g)].map(m => Number(m[0].replace(',', '.')));
  const box = issued.byId[id].bbox;
  const expected = box.slice(3).map((max, i) => Math.round((max - box[i]) * 1e6) / 1000);
  assert.deepEqual(sizes, expected, `${lang} ${id}: printed CAD extents in mm, rounded to 0.001 mm`);
  assert.match(bbox, lang === 'ru' ? /мм/ : /mm|毫米/);
  // This part has two plain URL citations, and a separate, genuinely linked observation.
  assert.deepEqual(await hrefs(field('evidence').locator('a')), issued.byId[id].evidence.split(/;\s*/).map(u => new URL(u).href));
  const related = issued.notes.observations.filter(o => o.parts.includes(id) && o.url);
  assert.ok(related.length);
  assert.deepEqual(await hrefs(field('observations').locator('a')), related.map(o => new URL(o.url).href));
}

async function checkService(page, sample, lang, mode) {
  const select = page.locator('#service-step');
  const options = await select.evaluate(s => Array.from(s.options, o => [o.value, o.textContent]));
  assert.deepEqual(options.map(([id]) => id), ['', ...sample.steps.map(s => s.id)]);
  for (const [i, step] of sample.steps.entries()) {
    assert.ok(options[i + 1][1].includes(step.title));
    human(step.title, lang, `${step.id}: step title`);
    if (i === 0) await page.locator('[data-action="service-next"]').click();
    else await select.selectOption(step.id);
    const s = await state(page);
    assert.equal(s.serviceStep, step.id);
    assert.ok(Object.keys(s.serviceOffsets).length);
    assert.equal(await page.locator('#service-text').innerText(), step.text);
    human(step.text, lang, `${step.id}: actual step annotation`);
    const source = page.locator('#service-source');
    if (/^https?:\/\/\S+$/.test(step.source)) assert.deepEqual(await hrefs(source.locator('a')), [new URL(step.source).href]);
    else assert.ok(cleanText(await source.innerText()).includes(cleanText(step.source)));
    if (mode === 'ready') assert.equal(await page.locator('#drawing-title').innerText(), step.title);
  }
  await select.selectOption('battery');
  await page.locator('#service-parts > summary').click();
  const cap = page.locator('button[data-service-part="MechPackCap"]');
  assert.ok(cleanText(await cap.innerText()).includes(cleanText(sample.byId.MechPackCap.label)));
  await cap.click();
  assert.equal((await state(page)).serviceStep, null);
  assert.equal((await state(page)).group, 'Battery');
  assert.equal(await page.locator('#part-id').innerText(), 'MechPackCap');
}

// Compare occupied rectangles, not just document.scrollWidth. Text may wrap; a real
// overflow rail is allowed for groups/views. Static titles and buttons must never
// collide, extend past the viewport, or clip their text at a narrow breakpoint.
async function layout(page, lang, sets) {
  const defects = await page.evaluate(sets => {
    const failures = [];
    const id = el => el.id || el.dataset.action || el.className || el.tagName;
    if (document.documentElement.scrollWidth > innerWidth + 1) failures.push('horizontal document overflow');
    for (const selector of sets) {
      const elements = [...document.querySelectorAll(selector)].filter(el => el.checkVisibility());
      for (const [i, el] of elements.entries()) {
        const r = el.getBoundingClientRect();
        if (r.width < 1 || r.height < 1 || r.left < -1 || r.right > innerWidth + 1) failures.push(`clipped ${id(el)}`);
        // Include actual text lines: an unconstrained text node can spill outside an
        // otherwise perfectly sized button or heading. Native selects may ellipsize.
        if (el.matches('button, a, h1, h2, h3, .product-intro')) {
          const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
          while (walker.nextNode()) {
            const node = walker.currentNode;
            if (!node.textContent.trim() || !node.parentElement.checkVisibility() || node.parentElement.closest('.sr-only')) continue;
            const range = document.createRange();
            range.selectNodeContents(node);
            for (const ink of range.getClientRects()) {
              if (ink.width && (ink.left < r.left - 2 || ink.right > r.right + 2 || ink.left < -1 || ink.right > innerWidth + 1)) {
                failures.push(`overflowing text in ${id(el)}: ${node.textContent.trim()}`);
              }
            }
          }
        }
        for (const other of elements.slice(i + 1)) {
          const s = other.getBoundingClientRect();
          const width = Math.min(r.right, s.right) - Math.max(r.left, s.left);
          const height = Math.min(r.bottom, s.bottom) - Math.max(r.top, s.top);
          if (width > 1 && height > 1) failures.push(`${id(el)} overlaps ${id(other)}`);
        }
      }
    }
    return failures;
  }, sets);
  assert.deepEqual(defects, [], `${lang} at ${page.viewportSize().width}px: ${defects.join('; ')}`);
}

async function openChooser(page, lang, opener = '#language-link') {
  const trigger = page.locator(opener);
  await trigger.press('Enter');
  const dialog = page.getByRole('dialog');
  await dialog.waitFor({state: 'visible'});
  assert.equal(await dialog.getAttribute('id'), 'language-dialog');
  assert.ok(await dialog.evaluate(el => el.matches(':modal')), 'Chooser is a real modal dialog');
  assert.equal(await trigger.getAttribute('aria-controls'), 'language-dialog');
  assert.equal(await trigger.getAttribute('aria-expanded'), 'true');
  human(await dialog.getByRole('heading').innerText(), lang, 'language chooser title');
  const rect = await dialog.boundingBox();
  const {height, width} = page.viewportSize();
  assert.ok(Math.abs(rect.y) <= 1 && rect.height >= height - 1 && rect.x >= -1 && rect.x + rect.width <= width + 1,
    'Full-height language chooser in the current viewport');
  const anchors = dialog.locator('a[data-language]');
  assert.equal(await anchors.count(), 3);
  for (const code of languages) {
    const a = dialog.getByRole('link', {name: selfNames[code], exact: true});
    assert.equal(await a.getAttribute('data-language'), code);
    assert.equal(await a.getAttribute('hreflang'), code);
    const to = new URL(await a.getAttribute('href'), page.url());
    assert.equal(to.searchParams.get('lang'), code);
    assert.equal(to.protocol, 'file:');
    assert.equal(to.pathname, new URL(page.url()).pathname);
    await product.inFrame(a, .98, `${code}: visible language choice`);
  }
  assert.equal(await dialog.locator('a[aria-current]:not([aria-current="false"])').getAttribute('data-language'), lang);
  await layout(page, lang, ['#language-close, #language-title, #language-dialog [data-language]']);
  return dialog;
}

async function closeChooser(page, opener, key = 'Escape') {
  if (key === 'Escape') await page.keyboard.press(key);
  else await page.locator('#language-close').click();
  await page.locator('#language-dialog').waitFor({state: 'hidden'});
  await page.waitForFunction(selector => document.activeElement === document.querySelector(selector), opener);
  assert.equal(await page.locator(opener).getAttribute('aria-expanded'), 'false');
}

async function layouts(page, lang) {
  for (const [width, height] of widths) {
    await page.setViewportSize({width, height});
    await page.locator('#overview-link').click();
    await page.evaluate(() => window.scrollTo({top: 0, left: 0, behavior: 'instant'}));
    await raf(page);
    await product.checkLayout(page);
    await layout(page, lang, [
      '#overview-link, #tab-assembly, #tab-specs, .mast-file, #language-nav',
      '#product-title, .product-intro, #explore-model, #explore-steps, #product-image',
      '.product-visual, .product-facts, .product-options',
      '.product-color-label, #product-finishes button',
      '#drawing-title, [data-action="reset"], #register-title',
      '#service-step, #service-controls button', '.colophon-inner > div, .colophon-inner > nav, #language-link'
    ]);
    await page.locator('#tab-specs').click();
    await sheet(page, lang, 'specs');
    await layout(page, lang, ['#spec-body h2, #spec-body h3', '#spec-body .ev-boundary, #spec-body .ev-section']);
    const opener = width <= 390 || !await page.locator('#language-nav').isVisible() ? '#language-link' : '#language-nav';
    await openChooser(page, lang, opener);
    await closeChooser(page, opener, width === 390 ? 'close' : 'Escape');
    await sheet(page, lang, 'specs');
  }
}

async function inspectAssembly(page, sample, lang) {
  await sheet(page, lang, 'assembly');
  assert.match(await page.locator('#product-title').innerText(), terms[lang].title);
  human(await page.locator('.product-intro').innerText(), lang, 'product introduction');
  const graphite = sample.notes.finishes.find(f => f.id === 'graphite');
  await product.checkFinish(page, 'graphite', graphite.label);
  human(await page.locator('#product-image').getAttribute('alt'), lang, 'product image alternative');

  await page.locator('#explore-model').click();
  assert.equal(await page.locator('#explorer:focus').count(), 1);
  const battery = page.locator('#group-tabs [data-group="Battery"]');
  await battery.click();
  const title = await page.locator('#drawing-title').innerText();
  assert.match(title, terms[lang].battery);
  assert.equal(title, sample.groups.find(g => g.id === 'Battery').shortLabel);
  const envelope = sample.byId.MechBatteryEnvelope;
  assert.match(envelope.label, terms[lang].battery);
  const search = page.locator('#part-search');
  await battery.press('/');
  assert.equal(await page.locator('#part-search:focus').count(), 1);
  await search.fill(envelope.label);
  const row = page.locator(`[data-part-id="${envelope.id}"] .part-name`);
  assert.equal(await row.innerText(), envelope.label, 'Search by the localized human name, not just a CAD ID');
  await search.press('Enter');
  assert.equal(await page.locator('#part-id').innerText(), envelope.id);
  await page.keyboard.press('Escape');
  assert.equal((await state(page)).selected, null);
  await search.fill('MechRetailBatteryRuSpecInk');
  await search.press('Enter');
  const printed = await page.locator('#passport [data-ev-field="note"]').innerText();
  for (const literal of ['XK088-B25', '3.7V', '13600mAh', '50.32Wh']) assert.ok(printed.includes(literal), `Battery inscription: ${literal}`);
  await page.locator('#explore-mainboard').click();
  assert.equal((await state(page)).group, 'MainPCB');
  for (const [id, text] of [['PcBoardID', 'GYS005-S-088-A4.3'], ['PcBoardCode', '20260204']]) {
    assert.ok((await page.locator(`#part-list [data-part-id="${id}"] .part-name`).innerText()).includes(text), 'Literal PCB silkscreen');
  }
  const front = page.locator('[data-view="front"]');
  human(await front.innerText(), lang, 'front view control');
  await front.click();
  assert.equal((await state(page)).view, 'front');
  assert.equal(await front.getAttribute('aria-pressed'), 'true');
  await page.locator('[data-action="reset"]').click();
  await page.locator('#tab-assembly').press('End');
  assert.equal(await page.locator('#tab-specs:focus').count(), 1);
}

// Simulate only the absence of the browser API, not a substitute viewer, scene or translated UI.
function unavailableWebGL() {
  if (!new URL(location.href).searchParams.has('no-webgl')) return;
  const nativeGet = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function(type, ...args) {
    return type.includes('webgl') ? null : nativeGet.call(this, type, ...args);
  };
}

async function fallback(page, index, lang, sample, issued) {
  await visit(page, `${index}?lang=${lang}&no-webgl`, lang, 'fallback');
  await sheet(page, lang, 'assembly');
  const note = page.locator('#print-note');
  assert.match(await note.innerText(), terms[lang].unavailable);
  human(await note.innerText(), lang, 'no-WebGL explanation');
  const image = page.locator('#print-image');
  assert.ok(await image.isVisible());
  assert.equal(await image.evaluate(async img => { await img.decode(); return img.currentSrc; }),
    new URL('../XKAH_PRO_A43_assembly_assembled.png', index).href);
  assert.equal(await page.locator('#atlas-canvas').isVisible(), false);
  assert.equal((await state(page)).screenOn, false);
  await page.locator('#tab-assembly').press('ArrowRight');
  await materialPassport(page, sample, issued, lang);
  await checkService(page, sample, lang, 'fallback');
}

async function preferences({openContext, index}) {
  const context = await openContext('zh-CN', false);
  try {
    const page = await context.newPage();
    await visit(page, index, 'zh-CN');
    await page.locator('[data-group="Battery"]').click();
    await page.locator('#part-list [data-part-id="MechBatteryEnvelope"]').click();
    const before = await state(page);
    const opener = '#language-link';
    const first = await openChooser(page, 'zh-CN', opener);
    // Explicitly cross both ends, not merely Tab once between two safe links.
    await first.locator('a').last().focus();
    await page.keyboard.press('Tab');
    assert.equal(await page.locator('#language-close:focus').count(), 1);
    await page.keyboard.press('Shift+Tab');
    assert.ok(await first.locator('a').last().evaluate(el => el === document.activeElement));
    await closeChooser(page, opener);
    assert.equal((await state(page)).selected, before.selected, 'Dialog Escape must not close the passport underneath');

    // Closing and reopening within one turn queues a native 'close' from the old opening.
    // Deliver it before checking that both launchers still describe the actual, open dialog.
    await page.evaluate(() => {
      const trigger = document.getElementById('language-nav');
      trigger.click();
      document.getElementById('language-close').click();
      trigger.click();
    });
    await raf(page);
    assert.ok(await page.locator('#language-dialog').evaluate(el => el.matches(':modal')));
    for (const trigger of ['#language-link', '#language-nav']) {
      assert.equal(await page.locator(trigger).getAttribute('aria-expanded'), 'true');
    }
    await closeChooser(page, '#language-nav');

    const dialog = await openChooser(page, 'zh-CN', opener);
    const ru = dialog.getByRole('link', {name: 'Русский', exact: true});
    await Promise.all([page.waitForURL(url => url.searchParams.get('lang') === 'ru'), ru.press('Enter')]);
    await page.waitForSelector('html[lang="ru"][data-viewport-state="ready"]');
    const after = await state(page);
    assert.equal(after.group, before.group);
    assert.equal(after.selected, before.selected);
    assert.equal(await page.locator('#passport:not([hidden]) #part-id').innerText(), before.selected);
    assert.match(await page.locator('#part-focus').innerText(), terms.ru.battery);
    await visit(page, index, 'ru'); // Saved choice wins over Chromium's zh-CN.
    await visit(page, `${index}?lang=en`, 'en'); // Explicit URL wins, but does NOT save a choice.
    await visit(page, index, 'ru');
    await openChooser(page, 'ru', opener);
    await Promise.all([page.waitForURL(url => url.searchParams.get('lang') === 'en'), page.locator('[data-language="en"]').click()]);
    await page.waitForSelector('html[lang="en"][data-viewport-state="ready"]');
    await visit(page, index, 'en');
  } finally {
    await context.close();
  }
  // A privacy context with no usable storage or WebGL and an unsupported browser
  // language must still work, including an explicit URL override and both sheets.
  const restricted = await openContext('fr-FR', false);
  try {
    await restricted.addInitScript(unavailableWebGL);
    await restricted.addInitScript(() => {
      for (const area of ['localStorage', 'sessionStorage']) {
        Object.defineProperty(window, area, {get() { throw new DOMException('Storage unavailable', 'SecurityError'); }});
      }
    });
    const page = await restricted.newPage();
    await visit(page, `${index}?no-webgl&lang=unsupported`, 'en', 'fallback');
    await openChooser(page, 'en');
    await Promise.all([page.waitForURL(url => url.searchParams.get('lang') === 'zh-CN'),
      page.locator('[data-language="zh-CN"]').click()]);
    await page.waitForSelector('html[lang="zh-CN"][data-viewport-state="fallback"]');
    await page.locator('#tab-assembly').press('End');
    await sheet(page, 'zh-CN', 'specs');
  } finally {
    await restricted.close();
  }
}

async function run({openContext, index, root, data, report, captureEnglish, clean}) {
  const expected = await rawDigests(root);
  assert.equal(expected.glb, report.glbSHA256);
  report.locales = {rawSHA256: expected, cases: {}};
  for (const lang of languages) {
    console.log(`=== Locale ${lang}: real file URL, sheets, register, service, responsive chooser, no-WebGL`);
    // A different browser language makes a broken URL override observable in every case.
    const context = await openContext(lang === 'ru' ? 'en-US' : 'ru-RU', lang === 'en');
    try {
      await context.addInitScript(unavailableWebGL);
      const page = await context.newPage();
      await visit(page, `${index}?lang=${lang}`, lang);
      const sample = await presentation(page, lang, expected, data);
      if (lang === 'en') {
        await captureEnglish(page);
        await page.setViewportSize({width: 1440, height: 960});
      }
      await inspectAssembly(page, sample, lang);
      await checkSpecs(page, sample, data, lang);
      await materialPassport(page, sample, data, lang);
      await checkService(page, sample, lang, 'ready');
      await layouts(page, lang);
      await fallback(page, index, lang, sample, data);
      clean();
      report.locales.cases[lang] = {page: `atlas/index.html?lang=${lang}`, steps: sample.steps.length,
        parts: sample.parts.length, dimensions: sample.notes.dimensions.length, kit: sample.notes.kit.length,
        materialPassport: 'MechHeaterPlate', widths: widths.map(([width]) => width), noWebGL: true};
    } finally {
      await context.close();
    }
  }
  console.log('=== Browser language, saved preference, explicit override, real selections, Escape and denied storage');
  await preferences({openContext, index});
  clean();
  report.locales.chooser = {browser: true, persisted: true, explicitOverride: true, contextRestored: true,
    keyboard: true, unavailableStorage: true, remoteRequests: 0};
}

module.exports = {run, rawDigests, presentation, inspectAssembly, checkSpecs, materialPassport, checkService,
  layouts, preferences, fallback, visit, unavailableWebGL};
