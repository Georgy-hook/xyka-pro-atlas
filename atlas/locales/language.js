/* One scene, three presentations. No locale request or storage access is required to open the file. */
(() => {
  'use strict';

  const names = Object.freeze({en: 'English', ru: 'Русский', 'zh-CN': '简体中文'});
  const locales = Object.keys(names);
  const prefKey = 'xyka-atlas:language';
  const returnKey = 'xyka-atlas:return';
  const supported = value => locales.includes(value);
  const read = (area, key) => {
    try {
      return window[area].getItem(key);
    } catch {
      return null;
    }
  };
  const write = (area, key, value) => {
    try {
      window[area].setItem(key, value);
    } catch { /* A local file or privacy mode may deny storage. The URL still works. */ }
  };
  const explicit = new URL(location.href).searchParams.get('lang');
  const preference = read('localStorage', prefKey);
  function browserLanguage() {
    for (const item of navigator.languages || [navigator.language]) {
      const language = String(item).toLowerCase().split('-')[0];
      if (language === 'zh') return 'zh-CN';
      if (supported(language)) return language;
    }
    return 'en';
  }
  const lang = supported(explicit) ? explicit : supported(preference) ? preference : browserLanguage();
  document.documentElement.lang = lang;
  const t = (ru, en, zh) => lang === 'en' ? en : lang === 'zh-CN' ? zh : ru;

  function remember(next, state, handoff) {
    if (!supported(next)) return;
    write('localStorage', prefKey, next);
    if (next === lang || !handoff) return;
    const {href, trigger, scrollY} = handoff;
    const context = {scrollY};
    for (const field of ['page', 'group', 'selected', 'isolated', 'query', 'sub', 'view', 'explode', 'finish', 'serviceStep', 'screenOn']) {
      context[field] = state?.[field];
    }
    context.query = typeof context.query === 'string' ? context.query.slice(0, 512) : '';
    if (state?.viewport !== 'ready') delete context.screenOn;
    // The renderer owns this small numeric pose and its validation on restore.
    const orbit = window.AtlasUI?.getOrbit?.();
    if (orbit) context.orbit = orbit;
    write('sessionStorage', returnKey, JSON.stringify({from: lang, next, href, trigger, time: Date.now(), context}));
  }

  function readArrival() {
    try {
      const raw = read('sessionStorage', returnKey);
      if (!raw) return null;
      window.sessionStorage.removeItem(returnKey);
      const entry = JSON.parse(raw);
      const age = Date.now() - entry.time;
      const sameChoice = supported(entry.from) && entry.from !== lang && entry.next === lang && lang === explicit;
      return sameChoice && entry.href === location.href && age >= 0 && age < 120000 && entry.context ? entry : null;
    } catch {
      return null;
    }
  }

  // Parser-blocking by design: only our one-shot same-tab selection stamps the first paint.
  const arrival = readArrival();
  let context = arrival?.context || null;
  function takeContext() {
    const saved = context;
    context = null;
    return saved;
  }

  if (arrival) {
    const root = document.documentElement;
    root.dataset.localeHandoff = 'true';
    if (window.matchMedia?.('(prefers-reduced-motion: no-preference)').matches) root.dataset.localeStamp = names[lang];
    const release = () => {
      if (!root.dataset.localeStamp || root.classList.contains('language-arrived')) return;
      root.classList.add('language-arrived');
      setTimeout(() => {
        delete root.dataset.localeStamp;
        root.classList.remove('language-arrived');
      }, 240);
    };
    // This is a visual bridge, never a loading gate. Slow or missing deferred scripts
    // cannot leave it over the page. Real input takes precedence over restoring position.
    setTimeout(release, 600);
    let interrupted = false;
    const interrupt = () => {
      interrupted = true;
      delete root.dataset.localeStamp;
    };
    const inputs = ['pointerdown', 'keydown', 'wheel', 'touchstart'];
    for (const type of inputs) window.addEventListener(type, interrupt, {passive: true, capture: true});
    window.addEventListener('atlas:ready', () => {
      for (const type of inputs) window.removeEventListener(type, interrupt, true);
      if (!interrupted) {
        if (['language-nav', 'language-link'].includes(arrival.trigger)) {
          document.getElementById(arrival.trigger)?.focus({preventScroll: true});
        }
        // Restore as soon as the localized sheet exists, not after a potentially slow GLB.
        const top = arrival.context.scrollY;
        if (Number.isFinite(top) && top >= 0) window.scrollTo({top, behavior: 'instant'});
      }
      requestAnimationFrame(release);
    }, {once: true});
  }

  function catalogue(scene, notes) {
    const vocabulary = window.AtlasPartNames;
    const partDocs = window.AtlasPartEvidence;
    const reference = window.AtlasNotesLocale;
    const byGroup = new Map();
    const groups = (scene.groups || []).map(group => {
      const titles = locales.map(code => vocabulary.group(group, code));
      byGroup.set(group.id, titles.map(label => `${label.label} ${label.shortLabel}`));
      return {...group, ...titles[locales.indexOf(lang)]};
    });
    const parts = (scene.parts || []).map(part => {
      const titles = locales.map(code => vocabulary.part(part, code));
      const searchAliases = [...titles.map(item => `${item.label} ${item.sub || ''}`), ...(byGroup.get(part.group) || [])].join(' ');
      return {...part, ...titles[locales.indexOf(lang)], ...partDocs.part(part, lang), subKey: part.sub || '', searchAliases};
    });
    const data = {...scene, groups, parts,
      units: (scene.units || []).map(unit => ({...unit, ...vocabulary.unit(unit, lang)}))};
    if (scene.service) {
      data.service = {...scene.service, steps: (scene.service.steps || []).map(step => ({...step, ...reference.step(step, lang)}))};
    }
    return {data, notes: reference.notes(notes, lang)};
  }

  window.AtlasLocale = Object.freeze({lang, names, t, catalogue, remember, takeContext});
})();
