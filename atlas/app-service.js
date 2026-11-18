/* Service poses are CAD translations, not joint kinematics. Never add a pose to the last frame. */
(() => {
  'use strict';

  const rest = Object.freeze({});
  const {t} = window.AtlasLocale;
  const presets = new Set(['iso', 'front', 'back', 'left', 'right', 'top', 'bottom']);
  const byId = id => document.getElementById(id);
  const number = n => String(n).padStart(2, '0');

  class PlanError extends Error {}

  function compile(steps, parts) {
    const poses = [];
    const index = new Map();
    let prior = rest;
    let view = 'iso';
    for (const item of steps) {
      if (!item.id || !item.title || index.has(item.id)) {
        throw new PlanError(t('Некорректный индекс этапов.', 'The step index is invalid.', '步骤索引无效。'));
      }
      const offsets = Object.assign(Object.create(null), prior);
      const focusIds = [...new Set(item.focusIds || [])];
      const involved = new Set(focusIds);
      const shifted = new Set();
      for (const id of involved) {
        if (!parts.has(id)) {
          throw new PlanError(t(`В сцене нет ориентира ${id}.`, `Reference part ${id} is missing from the scene.`,
            `场景中缺少参考零件 ${id}。`));
        }
      }
      for (const {ids, d} of item.moves) {
        if (!Array.isArray(d) || d.length !== 3 || !d.every(Number.isFinite)) {
          throw new PlanError(t('Смещение CAD должно содержать три координаты в метрах.',
            'A CAD offset must have three coordinates in metres.', 'CAD 位移必须包含三个以米为单位的坐标分量。'));
        }
        for (const id of new Set(ids)) {
          if (!parts.has(id)) {
            throw new PlanError(t(`В сцене нет детали ${id}.`, `Part ${id} is missing from the scene.`,
              `场景中缺少零件 ${id}。`));
          }
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
    root.append(t('Основание: ', 'Source: ', '依据：'));
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
    root.append(label || t('Не указано', 'Not specified', '未注明'));
  }

  function create({data, parts, groups, onStep, onPart}) {
    let plan;
    let error;
    try {
      plan = compile(data.service?.steps || [], parts);
    } catch (e) {
      // A mismatched publication may still be explored through its regular catalogue.
      plan = compile([], parts);
      error = e instanceof PlanError ? e.message : t('Некорректные данные этапов.', 'Invalid step data.', '步骤数据无效。');
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
        role.textContent = pose.shifted.has(id) ? t('Смещается', 'Moves', '移动') : t('Ориентир', 'Reference', '参考零件');
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
      const description = byId('service-text');
      if (pose) {
        description.textContent = pose.text || pose.title;
      } else if (!poses.length) {
        description.textContent = error
          ? t(`Этапы не согласованы с моделью: ${error}`, `The stages do not match the model: ${error}`, `拆解阶段与模型不符：${error}`)
          : t('В этом выпуске CAD последовательность не задана.', 'This CAD release has no disassembly sequence.', '此版本的 CAD 模型未提供拆解顺序。');
      } else {
        description.textContent = state.viewport === 'fallback'
          ? t('Статичный общий вид; этапы доступны как список.', 'Static assembly view. You can still browse the teardown stages below.',
            '当前显示静态装配图，仍可按列表浏览各拆解阶段。')
          : t('Выберите этап для разборки модели.', 'Choose a stage to see how the model comes apart.', '选择一个阶段，查看模型的拆解过程。');
      }
      citation(byId('service-source'), pose?.source);
      if (changed) {
        details.open = false;
        list.replaceChildren();
      }
      details.hidden = !pose?.parts.length;
      if (pose) {
        const names = new Set(pose.parts.map(id => groups.get(parts.get(id).group)?.label || parts.get(id).group));
        const n = pose.parts.length;
        const label = [...names].join(t(', ', ', ', '、'));
        byId('service-summary').textContent = t(`Детали этапа: ${n} · ${label}`, `Parts in this stage: ${n} · ${label}`,
          `本阶段零件：${n} · ${label}`);
      }
    }
    return {get, render, rest};
  }

  window.AtlasService = Object.freeze({create});
})();
