/* Service poses are CAD translations, not joint kinematics. Never add a pose to the last frame. */
(() => {
  'use strict';

  const rest = Object.freeze({});
  const presets = new Set(['iso', 'front', 'back', 'left', 'right', 'top', 'bottom']);
  const byId = id => document.getElementById(id);
  const number = n => String(n).padStart(2, '0');

  function compile(steps, parts) {
    const poses = [];
    const index = new Map();
    let prior = rest;
    let view = 'iso';
    for (const item of steps) {
      if (!item.id || !item.title || index.has(item.id)) throw new Error('Некорректный индекс этапов.');
      const offsets = Object.assign(Object.create(null), prior);
      const focusIds = [...new Set(item.focusIds || [])];
      const involved = new Set(focusIds);
      const shifted = new Set();
      for (const id of involved) {
        if (!parts.has(id)) throw new Error(`В сцене нет ориентира ${id}.`);
      }
      for (const {ids, d} of item.moves) {
        if (!Array.isArray(d) || d.length !== 3 || !d.every(Number.isFinite)) {
          throw new Error('Смещение CAD должно содержать три координаты в метрах.');
        }
        for (const id of new Set(ids)) {
          if (!parts.has(id)) throw new Error(`В сцене нет детали ${id}.`);
          const xyz = offsets[id] || [0, 0, 0];
          const v = xyz.map((v0, axis) => v0 + d[axis]);
          if (v.every(n => Math.abs(n) < 1e-12)) delete offsets[id];
          else offsets[id] = Object.freeze(v);
          involved.add(id);
          if (d.some(n => n !== 0)) shifted.add(id);
        }
      }
      if (presets.has(item.view)) view = item.view;
      prior = Object.freeze(offsets);
      const pose = {
        id: item.id, title: item.title, text: item.text, source: item.source,
        offsets: prior, view, focusIds, shifted, parts: [...involved], ordinal: poses.length + 1
      };
      poses.push(pose);
      index.set(pose.id, pose);
    }
    return {poses, index};
  }

  function citation(root, source) {
    root.replaceChildren();
    root.hidden = !source;
    if (!source) return;
    const label = typeof source === 'string' ? source : source.title || source.label || source.url;
    const url = typeof source === 'object' ? source.url : source;
    root.append('Основание: ');
    if (typeof url === 'string' && /^https?:\/\/\S+$/i.test(url)) {
      try {
        const link = document.createElement('a');
        const target = new URL(url);
        link.textContent = label === url ? target.host : label;
        link.href = target.href;
        link.title = target.href;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        root.append(link);
        return;
      } catch { /* A textual citation does not require a working URL. */ }
    }
    root.append(label || 'Не указано');
  }

  function create({data, parts, groups, onStep, onPart}) {
    let plan;
    let error;
    try {
      plan = compile(data.service?.steps || [], parts);
    } catch (e) {
      // A mismatched publication may still be explored through its regular catalogue.
      plan = compile([], parts);
      error = e.message;
    }
    const {index, poses} = plan;
    const select = byId('service-step');
    const prev = document.querySelector('[data-action="service-prev"]');
    const next = document.querySelector('[data-action="service-next"]');
    const reset = document.querySelector('[data-action="service-rest"]');
    const details = byId('service-parts');
    const list = byId('service-items');
    let pose;
    let lastViewport;
    const get = id => index.get(id) || null;

    for (const p of poses) select.add(new Option(`${number(p.ordinal)} · ${p.title}`, p.id));
    byId('service-controls').hidden = !poses.length;
    byId('service-boundary').hidden = !poses.length;
    select.addEventListener('change', () => onStep(select.value || null));
    prev.addEventListener('click', () => onStep(poses[(pose?.ordinal || 0) - 2]?.id || null));
    next.addEventListener('click', () => {
      const after = poses[pose?.ordinal || 0];
      if (after) onStep(after.id);
    });
    reset.addEventListener('click', () => onStep(null));
    list.addEventListener('click', e => {
      const row = e.target.closest('button[data-service-part]');
      if (row) onPart(row.dataset.servicePart);
    });

    function listParts() {
      if (!details.open || !pose || list.childElementCount) return;
      const fragment = document.createDocumentFragment();
      for (const id of pose.parts) {
        const part = parts.get(id);
        const button = document.createElement('button');
        button.type = 'button';
        button.dataset.servicePart = id;
        button.textContent = part.label || id;
        const code = document.createElement('code');
        code.textContent = id;
        const role = document.createElement('small');
        role.textContent = pose.shifted.has(id) ? 'Смещается' : 'Ориентир';
        button.append(code, role);
        fragment.append(button);
      }
      list.replaceChildren(fragment);
    }
    details.addEventListener('toggle', listParts);

    function render(state) {
      const target = get(state.serviceStep);
      if (pose === target && lastViewport === state.viewport) return;
      const changed = pose !== target;
      pose = target;
      lastViewport = state.viewport;
      const current = pose?.ordinal || 0;
      const root = byId('service-order');
      root.dataset.step = pose?.id || '';
      select.value = pose?.id || '';
      byId('service-position').textContent = poses.length ? `${number(current)} / ${number(poses.length)}` : '—';
      prev.disabled = reset.disabled = !pose;
      next.disabled = current >= poses.length;
      const mode = state.viewport === 'fallback' ? 'Статичный общий вид; этапы доступны как список.' : 'Выберите этап для разборки модели.';
      byId('service-text').textContent = pose ? pose.text || pose.title : poses.length ? mode :
        error ? `Этапы не согласованы с моделью: ${error}` : 'В этом выпуске CAD последовательность не задана.';
      citation(byId('service-source'), pose?.source);
      if (changed) {
        details.open = false;
        list.replaceChildren();
      }
      details.hidden = !pose?.parts.length;
      if (pose) {
        const names = new Set(pose.parts.map(id => groups.get(parts.get(id).group)?.label || parts.get(id).group));
        byId('service-summary').textContent = `Детали этапа: ${pose.parts.length} · ${[...names].join(', ')}`;
      }
    }
    return {get, render, rest};
  }

  window.AtlasService = Object.freeze({create});
})();
