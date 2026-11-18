/* Indexed once per CAD file. Positions are stable across searches and node tabs. */
(() => {
  'use strict';

  function normalize(value) {
    return String(value || '').normalize('NFKC').toLocaleLowerCase('ru').replace(/ё/g, 'е');
  }

  function element(tag, className, text) {
    const result = document.createElement(tag);
    result.className = className;
    if (text !== undefined) result.textContent = text;
    return result;
  }

  function create({parts, groups, onSelect, onFilter}) {
    const {t} = window.AtlasLocale;
    const root = document.getElementById('part-list');
    const search = document.getElementById('part-search');
    const select = document.getElementById('subsection');
    const count = document.getElementById('group-count');
    const summary = document.getElementById('result-count');
    const sections = groups.filter(g => g.id !== 'all');
    const index = new Map();
    const rows = new Map();
    const ordered = [];
    let groupID = null;
    let matches = [];
    let currentRow = null;

    for (const group of sections) {
      for (const part of parts.filter(p => p.group === group.id)) {
        const item = {
          part,
          group,
          // Subsection captions change language; option values and restored filters must not.
          subKey: part.subKey ?? part.sub ?? '',
          number: String(ordered.length + 1).padStart(3, '0'),
          haystack: normalize([part.id, part.label, part.sub, group.id, group.label, part.searchAliases].join(' '))
        };
        ordered.push(item);
        index.set(part.id, item);
      }
    }

    function buildRow(item) {
      const {id, label} = item.part;
      const row = element('button', 'part-row');
      row.type = 'button';
      row.tabIndex = -1;
      row.dataset.partId = id;
      row.dataset.position = item.number;
      const number = element('span', 'part-pos', item.number);
      number.setAttribute('aria-hidden', 'true');
      const name = element('span', 'part-copy');
      name.append(element('span', 'part-name', label || id), element('span', 'part-code', id));
      const arrow = document.createElement('img');
      arrow.src = 'icons/chevron-right.svg';
      arrow.alt = '';
      arrow.width = arrow.height = 13;
      row.append(number, name, arrow);
      return row;
    }

    function setCurrent(id, focus) {
      const row = rows.get(id);
      if (!row || !root.contains(row)) return false;
      if (currentRow) currentRow.tabIndex = -1;
      currentRow = row;
      row.tabIndex = 0;
      if (focus) {
        row.focus({preventScroll: true});
        row.scrollIntoView({block: 'nearest', inline: 'nearest'});
      }
      return true;
    }

    function updateOptions(scope) {
      const seen = new Set();
      const options = document.createDocumentFragment();
      options.append(new Option(t('Все подразделы', 'All sections', '全部分类'), ''));
      for (const {part, subKey} of scope) {
        if (subKey && !seen.has(subKey)) {
          options.append(new Option(part.sub, subKey));
          seen.add(subKey);
        }
      }
      select.replaceChildren(options);
      select.disabled = seen.size === 0;
    }

    function render({group, query, sub}) {
      const scope = group === 'all' ? ordered : ordered.filter(entry => entry.group.id === group);
      if (groupID !== group) updateOptions(scope);
      groupID = group;
      count.textContent = String(scope.length);
      if (search.value !== query) search.value = query;
      select.value = sub;
      const tokens = normalize(query).trim().split(/\s+/).filter(Boolean);
      matches = scope.filter(({subKey, haystack}) => (!sub || subKey === sub) && tokens.every(token => haystack.includes(token)));
      const n = matches.length;
      summary.textContent = tokens.length || sub
        ? t(`Найдено: ${n}`, `Matches: ${n}`, `找到 ${n} 项`)
        : t(`${n} поз.`, n === 1 ? '1 item' : `${n} items`, `共 ${n} 项`);
      root.dataset.resultCount = String(matches.length);

      const fragment = document.createDocumentFragment();
      let lastGroup = null;
      for (const entry of matches) {
        if (entry.group !== lastGroup) {
          const band = element('h3', 'part-band');
          band.append(element('span', '', entry.group.no), element('span', '', entry.group.label));
          fragment.append(band);
          lastGroup = entry.group;
        }
        const id = entry.part.id;
        if (!rows.has(id)) rows.set(id, buildRow(entry));
        fragment.append(rows.get(id));
      }
      if (!matches.length) {
        const empty = element('div', 'no-results', scope.length
          ? t('Совпадений нет. Попробуйте часть названия или CAD ID.',
            'No matches. Try part of a name or CAD ID.', '未找到匹配项。请尝试输入名称或 CAD ID 的一部分。')
          : t('В этом узле нет данных о деталях.', 'There are no part records for this group.', '此组件没有零件记录。'));
        if (query || sub) {
          const clear = element('button', '', t('Снять фильтры', 'Clear filters', '清除筛选'));
          clear.type = 'button';
          clear.dataset.action = 'clear-filters';
          empty.append(clear);
        }
        fragment.append(empty);
      }
      root.replaceChildren(fragment);
      root.scrollTop = 0;
      if (currentRow) currentRow.tabIndex = -1;
      currentRow = null;
      if (matches.length) setCurrent(matches[0].part.id, false);
    }

    function focusPart(id) {
      if (!setCurrent(id, true)) search.focus();
    }

    search.addEventListener('input', () => onFilter(search.value, select.value));
    select.addEventListener('change', () => onFilter(search.value, select.value));
    search.addEventListener('keydown', event => {
      if (event.isComposing || !matches.length) return;
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        focusPart(matches[0].part.id);
      } else if (event.key === 'Enter') {
        event.preventDefault();
        onSelect(matches[0].part.id);
      }
    });
    root.addEventListener('click', event => {
      const button = event.target.closest('button');
      if (!button) return;
      if (button.dataset.partId) onSelect(button.dataset.partId);
      if (button.dataset.action === 'clear-filters') {
        onFilter('', '');
        search.focus();
      }
    });
    root.addEventListener('keydown', event => {
      const row = event.target.closest('[data-part-id]');
      if (!row || event.altKey || event.metaKey || event.ctrlKey) return;
      const current = matches.findIndex(entry => row.dataset.partId === entry.part.id);
      const last = matches.length - 1;
      const keys = {ArrowUp: Math.max(0, current - 1), ArrowDown: Math.min(last, current + 1), Home: 0, End: last};
      if (!Object.hasOwn(keys, event.key)) return;
      event.preventDefault();
      focusPart(matches[keys[event.key]].part.id);
    });

    return {
      render,
      focusPart,
      position: id => index.get(id)?.number || '',
      count: () => matches.length
    };
  }

  window.AtlasRegister = Object.freeze({create});
})();
