/* Presentation copies of the published notes. The tables in notes-spec.js and
 * notes-research.js match whole source strings, not array positions: a revised
 * observation or measurement must never pick up an older record's translation.
 */
(() => {
  'use strict';

  const dictionaries = new Map([
    ['en', new Map()],
    ['zh-CN', new Map()]
  ]);

  function register(entries) {
    for (const [ru, en, zh] of entries) {
      dictionaries.get('en').set(ru, en);
      dictionaries.get('zh-CN').set(ru, zh);
    }
  }

  // Only these fields carry translatable prose. IDs, swatches, material-to-part
  // assignments, quantities, source URLs, and any unknown metadata stay as read.
  const fields = {
    finishes: ['label'],
    dimensions: ['name', 'cad', 'reference', 'status'],
    kit: ['label', 'note', 'source'],
    observations: ['title', 'status', 'text', 'source'],
    sources: ['title']
  };

  function copy(value) {
    if (Array.isArray(value)) return value.map(copy);
    if (value === null || typeof value !== 'object') return value;
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, copy(item)]));
  }

  function notes(rawNotes, lang) {
    const result = copy(rawNotes || {});
    const dictionary = dictionaries.get(lang);
    if (!dictionary) return result;

    for (const [section, keys] of Object.entries(fields)) {
      if (!Array.isArray(result[section])) continue;
      for (const row of result[section]) {
        if (!row) continue;
        for (const key of keys) {
          if (dictionary.has(row[key])) row[key] = dictionary.get(row[key]);
        }
      }
    }
    for (const [id, material] of Object.entries(result.materials || {})) {
      if (dictionary.has(material)) result.materials[id] = dictionary.get(material);
    }
    return result;
  }

  // The caller overlays only these three fields on its service step. Do not
  // reinterpret a source string as a URL or turn a source object into a string.
  function step(rawStep, lang) {
    const dictionary = dictionaries.get(lang);
    return {
      title: dictionary?.get(rawStep.title) ?? rawStep.title,
      text: dictionary?.get(rawStep.text) ?? rawStep.text,
      source: copy(rawStep.source)
    };
  }

  window.AtlasNotesLocale = Object.freeze({ register, notes, step });
})();
