/* Classic script, including file://. The host supplies roots, localized notes,
 * scene data and onPart(id); it owns the tabs, selection and passport header.
 * materials is a dictionary keyed by CAD ID; bbox is [minXYZ, maxXYZ] in m.
 */
(() => {
  'use strict';

  const UNPAGED_LIMIT = 32;
  const PAGE_SIZE = 16;
  const t = (ru, en, zh) => window.AtlasLocale.t(ru, en, zh);
  const UNKNOWN = t('Не указано', 'Not specified', '未注明');
  const UNTITLED = t('Без названия', 'Untitled', '未命名');
  const RELATED = t('Связанные наблюдения', 'Related observations', '相关观察记录');
  const COMPARISON_NOTE = t(
    'Разборка HookahCat служит для сравнения, но не доказывает устройство ревизии A4.3.',
    'The HookahCat teardown is useful for comparison but does not establish how revision A4.3 is built.',
    'HookahCat 的拆解仅供对照，不能证明 A4.3 版本的内部构造。'
  );
  const KIT_NOTE = t(
    'Комплектация по указанным источникам; состав зависит от рынка и выпуска. Это содержимое упаковки, не число деталей в установленной модели.',
    'Package contents are taken from the cited sources and vary by market and production run. These quantities refer to what is in the box, not to the parts installed in the model.',
    '包装清单据所引来源整理，内容因市场和生产批次而异。这里的数量是包装内的件数，不是模型中已安装的零件数。'
  );
  const mentionsHookahCat = value => /(?:^|[^a-z0-9])hookah[\s._-]*cat(?:$|[^a-z0-9])/i.test(value);
  const mm = new Intl.NumberFormat(window.AtlasLocale.lang, { maximumFractionDigits: 3, useGrouping: false });
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
    link.setAttribute('aria-label', t(
      `${link.textContent} — открыть источник в новой вкладке`,
      `${link.textContent} — open source in a new tab`,
      `${link.textContent}（在新标签页打开来源）`
    ));
    return link;
  }

  function sourceLink(value, caption) {
    const raw = text(value);
    const url = safeURL(raw);
    if (!url) return el('span', 'ev-inert', caption || (raw
      ? t('Неактивный адрес', 'Inactive link', '链接不可用')
      : t('Ссылка не указана', 'No link specified', '未提供链接')));
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
    for (const match of note.matchAll(/\bhttps?:\/\/[^\s<>"'«»，。；：！？、（）【】《》“”‘’]+/gi)) {
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
    line.append(el('span', 'ev-label', t('Источник', 'Source', '来源')), ' ', sourceLink(url, caption));
    return line;
  }

  function partID(id, ctx) {
    const part = ctx.parts.get(id);
    const label = text(id) || t('ID не указан', 'ID not specified', '未注明 ID');
    if (!part) return el('span', 'ev-id', t(`${label} (нет в сцене)`, `${label} (not in scene)`, `${label}（场景中无此零件）`));
    if (typeof ctx.onPart !== 'function') return el('span', 'ev-id', label);
    const button = el('button', 'ev-id ev-part', label);
    button.type = 'button';
    button.dataset.evPart = id;
    const name = [label, text(part.label)].filter(Boolean).join(' · ');
    button.setAttribute('aria-label', t(`Открыть паспорт: ${name}`, `Open part record: ${name}`, `打开零件档案：${name}`));
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
      if (!count) fragment.append(el('li', 'ev-empty', items.length ? t('Совпадений нет.', 'No matches.', '没有匹配项。') : empty));
      list.replaceChildren(fragment);
      if (range) {
        const span = `${offset + 1}–${end}`;
        range.textContent = count
          ? t(`${span} из ${count}`, `${span} of ${count}`, `第 ${span} 条，共 ${count} 条`)
          : t('Найдено: 0', 'Found: 0', '找到 0 条');
        prev.setAttribute('aria-disabled', String(offset === 0));
        next.setAttribute('aria-disabled', String(end === count));
      }
    }

    function pageButton(direction, title, delta) {
      const button = el('button', 'ev-page', title);
      button.type = 'button';
      button.dataset.evPage = direction;
      button.setAttribute('aria-label', t(`${title} страница: ${label}`, `${title} page: ${label}`, `${label}：${title}`));
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
      search.append(el('span', 'ev-label', `${t('Поиск', 'Search', '搜索')} · ${label}`), input);
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
      prev = pageButton('prev', t('Предыдущая', 'Previous', '上一页'), -1);
      next = pageButton('next', t('Следующая', 'Next', '下一页'), 1);
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
      margin.append(el('span', 'ev-status', status
        ? t(`Статус: ${status}`, `Status: ${status}`, `状态：${status}`)
        : t('Статус не указан', 'Status not specified', '未注明状态')));
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
    const title = text(o?.title) || UNTITLED;
    const status = text(o?.status);
    const source = text(o?.source) || UNKNOWN;
    return record('observation', i, status, sourceLink(o?.url, title),
      el('p', 'ev-citation', t(`Источник: ${source}`, `Source: ${source}`, `来源：${source}`)));
  }

  function dimensionRow(d, i) {
    const comparison = el('dl', 'ev-comparison');
    comparison.append(field('cad', 'CAD', text(d?.cad)),
      field('reference', t('Ориентир', 'Reference', '参考值'), text(d?.reference)));
    const nodes = [el('h4', 'ev-title', text(d?.name) || UNTITLED), comparison];
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
    if (quantity) line.append(el('span', 'ev-label', t(`Количество: ${quantity}`, `Quantity: ${quantity}`, `数量：${quantity}`)));
    const source = text(item.source);
    if (source || text(item.url)) line.append(citation(item.url, source));
    row.append(line);
    const note = text(item.note);
    if (note) row.append(el('p', 'ev-citation', note));
    return row;
  }

  function sheet(key, title, boundary) {
    const page = el('article', 'ev-sheet');
    page.dataset.evSheet = key;
    const head = el('header', 'ev-head');
    head.append(el('p', 'ev-label', 'XYKA PRO · A4.3'), el('h2', 'ev-heading', title));
    const note = el('aside', 'ev-boundary');
    note.append(el('span', 'ev-label', t('Граница достоверности', 'Limits of the evidence', '证据适用范围')),
      el('p', 'ev-text', boundary));
    page.append(head, note);
    return page;
  }

  function section(label, config, note) {
    const block = el('section', 'ev-section');
    const head = el('div', 'ev-section-head');
    const count = config.items.length;
    head.append(el('h3', 'ev-subheading', label), el('span', 'ev-total', t(`Записей: ${count}`, `Records: ${count}`, `共 ${count} 条`)));
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
    const spec = sheet('specification', t('Размеры и материалы', 'Dimensions and materials', '尺寸与材料'), t(
      'CAD описывает модель, а не физический обмер. EST — оценка; запись о материале не подтверждает состав детали.',
      'CAD dimensions describe the model, not measurements of the physical device. EST marks an estimate. A material note does not confirm a part’s composition.',
      'CAD 尺寸描述的是模型，不是实物测量值。EST 表示估算值；材料记录不能证实零件的实际成分。'
    ));
    const materials = notes?.materials ?? {};
    spec.append(section(t('Размеры', 'Dimensions', '尺寸'), {
      key: 'dimensions', items: array(notes?.dimensions),
      empty: t('Размеры не указаны.', 'No dimensions specified.', '未提供尺寸。'),
      searchText: d => [d?.name, d?.cad, d?.reference, d?.status, d?.url].join(' '),
      row: dimensionRow
    }));
    const kit = array(notes?.kit).filter(item => typeof item?.label === 'string' && item.label.trim());
    if (kit.length) {
      spec.append(section(t('В комплекте', 'In the box', '包装清单'), {
        key: 'kit', items: kit,
        searchText: item => [item.label, item.quantity, item.note, item.source, item.url].join(' '),
        row: kitRow
      }, KIT_NOTE));
    }
    spec.append(section(t('Материалы', 'Materials', '材料'), {
      key: 'materials', items: Object.keys(materials),
      empty: t('Материалы не указаны.', 'No materials specified.', '未提供材料信息。'),
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
    if (!Array.isArray(box) || box.length !== 6) return t('Габарит не задан', 'No bounds specified', '未提供外包尺寸');
    const invalid = t('Некорректный габарит', 'Invalid bounds', '外包尺寸无效');
    const sizes = [];
    for (let axis = 0; axis < 3; axis++) {
      const min = box[axis];
      const max = box[axis + 3];
      if (!Number.isFinite(min) || !Number.isFinite(max) || max < min) return invalid;
      const size = (max - min) * 1000;
      if (!Number.isFinite(size)) return invalid;
      sizes.push(size > 0 && size < 0.001 ? `< ${mm.format(0.001)}` : mm.format(size));
    }
    return `${sizes.join(' × ')} ${t('мм', 'mm', 'mm')}`;
  }

  function renderPassport(root, part, { notes, data } = {}) {
    if (!root) return;
    if (!part) {
      root.replaceChildren(el('p', 'ev-empty', t('Выберите деталь для просмотра паспорта.',
        'Select a part to view its record.', '选择零件以查看其档案。')));
      return;
    }
    const passport = el('dl', 'ev-passport');
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
    const confidenceHint = t('EST — оценка, не физический обмер.',
      'EST marks an estimate, not a physical measurement.', 'EST 表示估算值，而非实测值。');
    passport.append(
      field('group', t('Узел', 'Assembly', '组件'), text(group?.label) || text(part.group)),
      field('sub', t('Подраздел', 'Subsection', '子类别'), text(part.sub)),
      field('bbox', t('Габарит CAD · X × Y × Z', 'CAD bounds · X × Y × Z', 'CAD 外包尺寸 · X × Y × Z'), bounds(part.bbox), t(
        'По границам модели вдоль мировых осей. Это не физический обмер детали.',
        'Model extents along the world axes, not measurements of the physical part.',
        '按模型在世界坐标轴上的边界计算，并非零件的实测尺寸。'
      )),
      field('evidence', t('Основание', 'Evidence', '依据'), linkedEvidence(part.evidence)),
      field('confidence', t('Достоверность', 'Confidence', '可信度'), text(part.confidence),
        comparison ? `${confidenceHint} ${COMPARISON_NOTE}` : confidenceHint),
      field('note', t('Примечание', 'Note', '备注'), text(part.note)),
      field('material', t('Материал', 'Material', '材料'), material || t('Материал не указан', 'Material not specified', '未注明材料')),
      field('observations', RELATED, register({
        key: 'related', label: RELATED, items: related,
        empty: t('Связанных наблюдений нет.', 'No related observations.', '没有相关观察记录。'),
        searchText: i => observationText(observations[i]),
        row: i => passportSource(observations[i], i)
      }))
    );
    root.replaceChildren(passport);
  }

  window.AtlasEvidence = { renderSpecs, renderPassport };
})();
