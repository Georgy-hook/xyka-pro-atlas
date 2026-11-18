/* Browser-side witnesses for the product overview. No network, UI writes or replacement renderer. */
'use strict';

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs/promises');
const path = require('node:path');

const finishes = ['graphite', 'silver', 'blue', 'pink'];
const hero = '#assembly #overview';
const productButton = id => `${hero} #product-finishes button[data-product-finish="${id}"]`;

// isVisible() alone is true even kilometres below the fold. IntersectionObserver also accounts for
// clipping by ancestors (notably the separately scrolling register); it does not scroll the target.
async function inFrame(locator, minimum, label) {
  assert.ok(await locator.isVisible(), `${label}: not visible`);
  const {ratio, exposed} = await locator.evaluate(el => new Promise(resolve => {
    const observer = new IntersectionObserver(([entry]) => {
      observer.disconnect();
      const {x, y, width, height} = entry.intersectionRect;
      const atCenter = document.elementFromPoint(x + width / 2, y + height / 2);
      resolve({ratio: entry.intersectionRatio, exposed: getComputedStyle(el).pointerEvents === 'none' || el.contains(atCenter)});
    });
    observer.observe(el);
  }));
  assert.ok(ratio >= minimum, `${label}: only ${Math.round(ratio * 100)}% in viewport`);
  assert.ok(exposed, `${label}: covered at the middle of its visible region`);
}

async function checkOptions(page, root) {
  const ids = (selector, key) => page.locator(selector).evaluateAll((nodes, key) =>
    nodes.map(el => el.dataset[key]).sort(), key);
  const expected = [...finishes].sort();
  assert.deepEqual(await ids(`${hero} #product-finishes button`, 'productFinish'), expected);
  assert.deepEqual(await ids('[data-product-finish]', 'productFinish'), expected, 'No duplicate product options');
  assert.deepEqual(await ids('#finishes button', 'finish'), expected);
  assert.equal(await page.locator('[data-finish]').count(), finishes.length, 'Only the live drawing owns data-finish');
  const digests = {};
  for (const id of finishes) {
    const bytes = await fs.readFile(path.join(root, 'atlas', 'media', `hero-${id}.webp`));
    assert.equal(bytes.toString('ascii', 0, 4), 'RIFF');
    assert.equal(bytes.toString('ascii', 8, 12), 'WEBP');
    digests[id] = crypto.createHash('sha256').update(bytes).digest('hex');
  }
  assert.equal(new Set(Object.values(digests)).size, finishes.length, 'Four different local finish assets');
  return digests;
}

async function checkFinish(page, id) {
  const {finish, viewport} = await page.evaluate(() => AtlasUI.getState());
  assert.equal(finish, id, 'Primary app finish');
  const label = await page.evaluate(id => ATLAS_NOTES.finishes.find(f => f.id === id).label, id);
  assert.equal(await page.locator('#product-finish-name').innerText(), label);
  assert.equal(await page.locator('#finish-name').textContent(), label);
  for (const [selector, attribute] of [['#product-finishes', 'data-product-finish'], ['#finishes', 'data-finish']]) {
    // The static fallback deliberately hides the WebGL drawing's controls, never the hero's.
    if (selector === '#product-finishes' || viewport === 'ready') {
      assert.equal(await page.locator(selector).getByRole('button', {name: label, exact: true}).count(), 1);
    }
    assert.equal(await page.locator(`${selector} button[aria-pressed="true"]`).getAttribute(attribute), id,
      `${selector}: one active finish, matching the actual assembly`);
  }
  const image = page.locator(`${hero} img#product-image`);
  assert.ok(await image.isVisible(), 'The product does not depend on the canvas');
  const expected = new URL(`media/hero-${id}.webp`, page.url()).href;
  const loaded = await image.evaluate(async img => {
    await img.decode();
    return {src: img.currentSrc, w: img.naturalWidth, h: img.naturalHeight, alt: img.alt.trim(), complete: img.complete};
  });
  assert.equal(loaded.src, expected, `${id}: decoded the issued file:// image`);
  assert.ok(loaded.complete && loaded.alt && loaded.w >= 256 && loaded.h >= 256, `${id}: not a product illustration`);
  assert.equal(await page.locator(`${hero} img[src*="hero-"]:visible`).count(), 1, 'Exactly one studio finish on stage');
}

async function checkLayout(page) {
  const overview = page.locator(hero);
  const title = overview.getByRole('heading').first();
  const intro = overview.locator('.product-intro');
  const image = overview.locator('#product-image');
  const {width, height} = page.viewportSize();
  const label = `${width}×${height} product overview`;
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${label}: horizontal overflow`);
  for (const [name, locator] of [['title', title], ['intro', intro], ['illustration', image], ['finishes', overview.locator('#product-finishes')],
    ['viewer CTA', overview.locator('#explore-model')], ['service CTA', overview.locator('#explore-steps')]]) {
    const box = await locator.boundingBox();
    assert.ok(box && Object.values(box).every(Number.isFinite) && box.width > 1 && box.height > 1, `${label}: collapsed ${name}`);
    if (name === 'illustration') {
      assert.ok(box.width >= Math.min(width / 3, 200) && box.height >= height / 5, `${label}: thumbnail instead of a hero`);
    } else assert.ok(box.x >= -1 && box.x + box.width <= width + 1, `${label}: clipped ${name}`);
  }
  for (const [locator, px] of [[title, 24], [intro, 14]]) {
    assert.ok(await locator.evaluate((el, px) => el.innerText.trim() && parseFloat(getComputedStyle(el).fontSize) >= px, px),
      `${label}: absent or illegible copy`);
    await inFrame(locator, 0.9, label + ' copy');
  }
  await inFrame(image, .60, label + ' image');
  await inFrame(overview.locator('#explore-model'), .95, label + ' viewer CTA');
  const visual = await overview.evaluate(el => {
    const rgb = color => color.match(/[\d.]+/g)?.map(Number) || [];
    const background = rgb(getComputedStyle(el).backgroundColor);
    const luminance = color => color.slice(0, 3).map(c => c / 255).map(c => c <= .04045 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4)
      .reduce((sum, c, i) => sum + c * [.2126, .7152, .0722][i], 0);
    const readable = [...el.querySelectorAll('#product-title, #product-title span, .product-intro')].every(copy => {
      const foreground = rgb(getComputedStyle(copy).color);
      const alpha = (foreground[3] ?? 1) * Number(getComputedStyle(copy).opacity);
      const visible = foreground.slice(0, 3).map((c, i) => c * alpha + background[i] * (1 - alpha));
      return (luminance(visible) + .05) / (luminance(background) + .05) >= (copy.matches('.product-intro') ? 4.5 : 3);
    });
    return {dark: background.length >= 3 && (background[3] ?? 1) >= .9 && Math.max(...background.slice(0, 3)) < 100, readable,
      reduced: matchMedia('(prefers-reduced-motion: reduce)').matches && getComputedStyle(document.documentElement).scrollBehavior !== 'smooth',
      moving: el.getAnimations({subtree: true}).some(animation => animation.playState === 'running' &&
        animation.effect.getComputedTiming().activeDuration > 100 && animation.effect.getKeyframes().some(k =>
          'transform' in k || 'translate' in k || 'rotate' in k || 'scale' in k))};
  });
  assert.ok(visual.dark, `${label}: expected dark studio surface`);
  assert.ok(visual.readable, `${label}: insufficient title or description contrast against the studio surface`);
  assert.ok(visual.reduced && !visual.moving, `${label}: respect reduced motion`);
}

async function checkNavigation(page, firstStep, turnSheet, checkSheets) {
  const viewerLink = page.locator(`${hero} a#explore-model`);
  assert.equal(await viewerLink.getAttribute('href'), '#explorer');
  await viewerLink.click();
  const heading = page.locator('#assembly #explorer');
  assert.ok(await heading.evaluate(el => el.matches('h1,h2,h3,h4,h5,h6,[role="heading"]') && el === document.activeElement),
    'Model CTA transfers keyboard focus to the explorer heading');
  await inFrame(heading, .95, 'Model CTA reveals its focus target');
  await turnSheet(page, 'specs');
  const brand = page.locator('header a#overview-link');
  assert.equal(await brand.getAttribute('href'), '#overview');
  await brand.click();
  await checkSheets(page, 'assembly');
  await inFrame(page.locator(`${hero} #product-title`), .95, 'Brand returns to the visible product overview');
  const board = page.locator(`${hero} #explore-mainboard`);
  const pdf = page.locator(`${hero} a[href$="drawings.pdf"]`);
  assert.equal(await pdf.getAttribute('href'), '../XKAH_PRO_A43_drawings.pdf');
  await board.click();
  assert.equal(await page.evaluate(() => AtlasUI.getState().group), 'MainPCB');
  await page.locator('[data-view="front"]').click();
  await page.locator('#part-list [data-part-id]').first().click();
  await brand.click();
  await board.click();
  const reopened = await page.evaluate(() => AtlasUI.getState());
  assert.equal(reopened.selected, null, 'Board link opens the board, not its previous passport');
  assert.equal(reopened.view, 'iso', 'Board link restores the component-side camera');
  await brand.click();
  await page.locator(`${hero} #explore-steps`).click();
  assert.equal(await page.locator('#service-step').inputValue(), firstStep, 'Service CTA selects the first issued step');
  assert.equal(await page.evaluate(() => AtlasUI.getState().serviceStep), firstStep);
  await inFrame(page.locator('#atlas-canvas'), .25, 'Service CTA navigates to the working drawing, not just a new state');
}

module.exports = {finishes, productButton, inFrame, checkOptions, checkFinish, checkLayout, checkNavigation};
