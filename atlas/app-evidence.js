/* Classic script, including file://. The host supplies roots, ATLAS_NOTES,
 * ATLAS_SCENE and onPart(id); it owns the tabs, selection and passport header.
 * materials is a dictionary keyed by CAD ID; bbox is [minXYZ, maxXYZ] in m.
 */
(() => {
  'use strict';

  const UNPAGED_LIMIT = 32;
  const PAGE_SIZE = 16;
  const UNKNOWN = 'Не указано';
  const COMPARISON_NOTE = 'Разборка HookahCat служит для сравнения, но не доказывает устройство ревизии A4.3.';
  const KIT_NOTE = 'Комплектация по указанным источникам; состав зависит от рынка и выпуска. Это содержимое упаковки, не число деталей в установленной модели.';
  const mentionsHookahCat = value => /(?:^|[^a-z0-9])hookah[\s._-]*cat(?:$|[^a-z0-9])/i.test(value);
  const mm = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 3, useGrouping: false });
  const array = value => Array.isArray(value) ? value : [];
  const text = value => typeof value === 'string' ? value.trim() : Number.isFinite(value) ? String(value) : '';
  const fold = value => text(value).toLowerCase().replace(/ё/g, 'е');

  function el(tag, className, content) {
    const node = document.createElement(tag);
    node.className = className;
    if (content !== undefined) node.textContent = content;
    return node;
  }

  function safeURL(raw) {
    if (!/^https?:\/\//i.test(raw) || /[\\\u0000-\u001f\u007f]/.test(raw)) return null;
    try {
      const url = new URL(raw);
      if (!url.hostname || url.username || url.password) return null;
      return url;
    } catch {
      return null;
    }
  }

  function anchor(url, caption) {
    const link = el('a', 'ev-link', caption);
    link.href = url.href;
    link.title = url.href;
    link.target = '_blank';
    link.rel = 'external noopener noreferrer';
    link.setAttribute('aria-label', `${link.textContent} — открыть источник в новой вкладке`);
    return link;
  }

  function sourceLink(value, caption) {
    const raw = text(value);
    const url = safeURL(raw);
    if (!url) return el('span', 'ev-inert', caption || (raw ? 'Неактивный адрес' : 'Ссылка не указана'));
    return anchor(url, caption && caption !== raw ? caption : url.host);
  }

  // Preserve the evidence verbatim, including punctuation around each URL.
  // Bare IMG identifiers have no file mapping in ATLAS_NOTES; never guess one.
  function linkedEvidence(value) {
    const note = text(value);
    if (!note) return UNKNOWN;
    const fragment = document.createDocumentFragment();
    const openers = { ')': '(', ']': '[', '}': '{' };
    let cursor = 0;
    for (const match of note.matchAll(/\bhttps?:\/\/[^\s<>"'«»]+/gi)) {
      let token = match[0].replace(/[.,;:!?…]+$/, '');
      const closing = token.slice(-1);
      const opening = openers[closing];
      if (opening && token.split(closing).length > token.split(opening).length) token = token.slice(0, -1);
      const url = safeURL(token);
      if (!url) continue;
      fragment.append(note.slice(cursor, match.index), anchor(url, token));
      cursor = match.index + token.length;
    }
    fragment.append(note.slice(cursor));
    return fragment;
  }

  function citation(url, caption) {
    const line = el('p', 'ev-citation');
    line.append(el('span', 'ev-label', 'Источник'), ' ', sourceLink(url, caption));
    return line;
  }

  function partID(id, ctx) {
    const part = ctx.parts.get(id);
    const label = text(id) || 'ID не указан';
    if (!part) return el('span', 'ev-id', `${label} (нет в сцене)`);
    if (typeof ctx.onPart !== 'function') return el('span', 'ev-id', label);
    const button = el('button', 'ev-id ev-part', label);
    button.type = 'button';
    button.dataset.evPart = id;
    button.setAttribute('aria-label', `Открыть паспорт: ${[label, text(part.label)].filter(Boolean).join(' · ')}`);
    button.addEventListener('click', () => ctx.onPart(id));
    return button;
  }

  // Only one page has DOM nodes. The text index is built on first search;
  // paging or filtering never detaches the active search field / pager button.
  function register({ key, label, items, empty, row, searchText }) {
    const box = el('div', 'ev-register');
    box.dataset.evList = key;
    const list = el('ol', 'ev-list');
    list.setAttribute('role', 'list');
    const paged = items.length > UNPAGED_LIMIT;
    const size = paged ? PAGE_SIZE : items.length;
    let offset = 0;
    let matches = null;
    let index, range, prev, next;

    function draw() {
      const count = matches === null ? items.length : matches.length;
      const end = Math.min(offset + size, count);
      const fragment = document.createDocumentFragment();
      for (let pos = offset; pos < end; pos++) {
        const i = matches === null ? pos : matches[pos];
        fragment.append(row(items[i], i));
      }
      if (!count) fragment.append(el('li', 'ev-empty', items.length ? 'Совпадений нет.' : empty));
      list.replaceChildren(fragment);
      if (range) {
        range.textContent = count ? `${offset + 1}–${end} из ${count}` : 'Найдено: 0';
        prev.setAttribute('aria-disabled', String(offset === 0));
        next.setAttribute('aria-disabled', String(end === count));
      }
    }

    function pageButton(direction, title, delta) {
      const button = el('button', 'ev-page', title);
      button.type = 'button';
      button.dataset.evPage = direction;
      button.setAttribute('aria-label', `${title} страница: ${label}`);
      button.addEventListener('click', () => {
        if (button.getAttribute('aria-disabled') === 'true') return;
        offset += delta * PAGE_SIZE;
        draw();
      });
      return button;
    }

    if (paged) {
      const tools = el('div', 'ev-tools');
      const search = el('label', 'ev-search');
      const input = el('input', 'ev-input');
      input.type = 'search';
      input.autocomplete = 'off';
      input.spellcheck = false;
      input.dataset.evSearch = key;
      search.append(el('span', 'ev-label', `Поиск · ${label}`), input);
      input.addEventListener('input', () => {
        const words = fold(input.value).split(/\s+/).filter(Boolean);
        matches = null;
        if (words.length) {
          if (!index) index = items.map(item => fold(searchText(item)));
          matches = [];
          index.forEach((entry, i) => {
            if (words.every(word => entry.includes(word))) matches.push(i);
          });
        }
        offset = 0;
        draw();
      });
      range = el('span', 'ev-range');
      range.setAttribute('role', 'status');
      range.setAttribute('aria-atomic', 'true');
      prev = pageButton('prev', 'Предыдущая', -1);
      next = pageButton('next', 'Следующая', 1);
      const pager = el('div', 'ev-pager');
      pager.append(prev, range, next);
      tools.append(search, pager);
      box.append(tools);
    }
    box.append(list);
    draw();
    return box;
  }

  function record(kind, i, status, ...nodes) {
    const item = el('li', 'ev-record');
    item.dataset.evRow = kind;
    item.dataset.evIndex = String(i);
    const margin = el('div', 'ev-margin');
    const number = el('span', 'ev-number', String(i + 1).padStart(2, '0'));
    number.setAttribute('aria-hidden', 'true');
    margin.append(number);
    if (status !== null) {
      item.dataset.evStatus = status;
      margin.append(el('span', 'ev-status', status ? `Статус: ${status}` : 'Статус не указан'));
    }
    const body = el('div', 'ev-entry');
    body.append(...nodes);
    item.append(margin, body);
    return item;
  }

  function field(key, label, value, hint) {
    const pair = el('div', 'ev-pair');
    const dd = el('dd', 'ev-value');
    dd.dataset.evField = key;
    dd.append(typeof value === 'string' ? value || UNKNOWN : value);
    if (hint) dd.append(el('small', 'ev-hint', hint));
    pair.append(el('dt', 'ev-label', label), dd);
    return pair;
  }

  function observationText(o) {
    return [o?.title, o?.status, o?.text, o?.source, o?.url, ...array(o?.parts)].join(' ');
  }

  function passportSource(o, i) {
    const title = text(o?.title) || 'Без названия';
    const status = text(o?.status);
    return record('observation', i, status, sourceLink(o?.url, title),
      el('p', 'ev-citation', `Источник: ${text(o?.source) || UNKNOWN}`));
  }

  function dimensionRow(d, i) {
    const comparison = el('dl', 'ev-comparison');
    comparison.append(field('cad', 'CAD', text(d?.cad)), field('reference', 'Ориентир', text(d?.reference)));
    const nodes = [el('h4', 'ev-title', text(d?.name) || 'Без названия'), comparison];
    if (text(d?.url)) nodes.push(citation(d.url));
    return record('dimension', i, text(d?.status), ...nodes);
  }

  function kitRow(item, i) {
    const row = el('li', 'ev-kit-row');
    row.dataset.evRow = 'kit';
    row.dataset.evIndex = String(i);
    const line = el('div', 'ev-kit-line');
    line.append(el('h4', 'ev-title', text(item.label)));
    const quantity = text(item.quantity);
    if (quantity) line.append(el('span', 'ev-label', `Количество: ${quantity}`));
    const source = text(item.source);
    if (source || text(item.url)) line.append(citation(item.url, source));
    row.append(line);
    const note = text(item.note);
    if (note) row.append(el('p', 'ev-citation', note));
    return row;
  }

  function sheet(key, title, boundary) {
    const page = el('article', 'ev-sheet');
    page.lang = 'ru';
    page.dataset.evSheet = key;
    const head = el('header', 'ev-head');
    head.append(el('p', 'ev-label', 'Атлас разборки / XKAH PRO'), el('h2', 'ev-heading', title));
    const note = el('aside', 'ev-boundary');
    note.append(el('span', 'ev-label', 'Граница достоверности'), el('p', 'ev-text', boundary));
    page.append(head, note);
    return page;
  }

  function section(label, config, note) {
    const block = el('section', 'ev-section');
    const head = el('div', 'ev-section-head');
    head.append(el('h3', 'ev-subheading', label), el('span', 'ev-total', `Записей: ${config.items.length}`));
    block.append(head);
    if (note) block.append(el('p', 'ev-citation ev-section-note', note));
    block.append(register({ ...config, label }));
    return block;
  }

  function renderSpecs(root, { notes, data, onPart } = {}) {
    const ctx = { parts: new Map(), onPart };
    for (const part of array(data?.parts)) {
      if (text(part?.id)) ctx.parts.set(part.id, part);
    }
    const spec = sheet('specification', 'Размеры и материалы',
      'CAD описывает модель, а не физический обмер. EST — оценка; запись о материале не подтверждает состав детали.');
    const materials = notes?.materials ?? {};
    spec.append(section('Размеры', {
      key: 'dimensions', items: array(notes?.dimensions), empty: 'Размеры не указаны.',
      searchText: d => [d?.name, d?.cad, d?.reference, d?.status, d?.url].join(' '),
      row: dimensionRow
    }));
    const kit = array(notes?.kit).filter(item => typeof item?.label === 'string' && item.label.trim());
    if (kit.length) {
      spec.append(section('В комплекте', {
        key: 'kit', items: kit,
        searchText: item => [item.label, item.quantity, item.note, item.source, item.url].join(' '),
        row: kitRow
      }, KIT_NOTE));
    }
    spec.append(section('Материалы', {
      key: 'materials', items: Object.keys(materials), empty: 'Материалы не указаны.',
      searchText: id => [id, ctx.parts.get(id)?.label, ctx.parts.get(id)?.sub, materials[id]].join(' '),
      row(id, i) {
        const title = el('p', 'ev-material-title');
        title.append(partID(id, ctx), ' ', text(ctx.parts.get(id)?.label));
        return record('material', i, null, title, el('p', 'ev-text', text(materials[id]) || UNKNOWN));
      }
    }));
    root.replaceChildren(spec);
  }

  function bounds(box) {
    if (!Array.isArray(box) || box.length !== 6) return 'Габарит не задан';
    const sizes = [];
    for (let axis = 0; axis < 3; axis++) {
      const min = box[axis];
      const max = box[axis + 3];
      if (!Number.isFinite(min) || !Number.isFinite(max) || max < min) return 'Некорректный габарит';
      const size = (max - min) * 1000;
      if (!Number.isFinite(size)) return 'Некорректный габарит';
      sizes.push(size > 0 && size < 0.001 ? '< 0,001' : mm.format(size));
    }
    return `${sizes.join(' × ')} мм`;
  }

  function renderPassport(root, part, { notes, data } = {}) {
    if (!root) return;
    if (!part) {
      root.replaceChildren(el('p', 'ev-empty', 'Выберите деталь для просмотра паспорта.'));
      return;
    }
    const passport = el('dl', 'ev-passport');
    passport.lang = 'ru';
    passport.dataset.evPassport = text(part.id);
    const group = array(data?.groups).find(g => g?.id === part.group);
    const materials = notes?.materials ?? {};
    const material = Object.prototype.hasOwnProperty.call(materials, part.id) ? text(materials[part.id]) : '';
    const observations = array(notes?.observations);
    const related = [];
    observations.forEach((o, i) => {
      if (array(o?.parts).includes(part.id)) related.push(i);
    });
    const comparison = mentionsHookahCat([part.evidence, part.note, part.confidence, material].join(' ')) ||
      related.some(i => {
        const o = observations[i];
        return mentionsHookahCat([o.title, o.status, o.text, o.source, o.url].join(' '));
      });
    const confidenceHint = 'EST — оценка, не физический обмер.';
    passport.append(
      field('group', 'Узел', text(group?.label) || text(part.group)),
      field('sub', 'Подраздел', text(part.sub)),
      field('bbox', 'Габарит CAD · X × Y × Z', bounds(part.bbox),
        'По границам модели вдоль мировых осей. Это не физический обмер детали.'),
      field('evidence', 'Основание', linkedEvidence(part.evidence)),
      field('confidence', 'Достоверность', text(part.confidence), comparison ? `${confidenceHint} ${COMPARISON_NOTE}` : confidenceHint),
      field('note', 'Примечание', text(part.note)),
      field('material', 'Материал', material || 'Материал не указан'),
      field('observations', 'Связанные наблюдения', register({
        key: 'related', label: 'Связанные наблюдения', items: related, empty: 'Связанных наблюдений нет.',
        searchText: i => observationText(observations[i]),
        row: i => passportSource(observations[i], i)
      }))
    );
    root.replaceChildren(passport);
  }

  window.AtlasEvidence = { renderSpecs, renderPassport };
})();
