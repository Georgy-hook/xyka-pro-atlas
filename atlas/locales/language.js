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

  function remember(next, state) {
    if (!supported(next)) return;
    write('localStorage', prefKey, next);
    if (!state || next === lang) return;
    const context = {scrollY: window.scrollY};
    for (const field of ['page', 'group', 'selected', 'isolated', 'query', 'sub', 'view', 'explode', 'finish', 'serviceStep', 'screenOn']) {
      context[field] = state[field];
    }
    context.query = typeof context.query === 'string' ? context.query.slice(0, 512) : '';
    if (state.viewport !== 'ready') delete context.screenOn;
    write('sessionStorage', returnKey, JSON.stringify({next, path: location.pathname, time: Date.now(), context}));
  }

  function takeContext() {
    try {
      const raw = read('sessionStorage', returnKey);
      if (!raw) return null;
      window.sessionStorage.removeItem(returnKey);
      const entry = JSON.parse(raw);
      const age = Date.now() - entry.time;
      return entry.path === location.pathname && entry.next === lang && age >= 0 && age < 120000 ? entry.context : null;
    } catch {
      return null;
    }
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
