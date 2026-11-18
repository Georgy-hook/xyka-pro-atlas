/* UI-side adapter only. Geometry, orbit controls and picking belong to viewport.js. */
(() => {
  'use strict';

  function create({data, finishes, onPick, onExplode, onFinish, onViewport}) {
    const byId = id => document.getElementById(id);
    const canvas = byId('atlas-canvas');
    const slider = byId('explode-slider');
    const nativeRange = byId('explode-native');
    const finishButtons = new Map();
    const finishMaps = new Map();
    // Painted skins can belong to different functional units. Only IDs named by
    // the finish catalogue get a coat; electrical assemblies keep their CAD colours.
    const electrical = new Set(['MainPCB', 'DisplayPCB', 'Harness', 'Battery']);
    const shellIDs = new Set(data.parts.filter(p => !electrical.has(p.group)).map(p => p.id));
    const screenButton = document.querySelector('[data-action="screen"]');
    let viewport = null;
    let previous = null;
    let failed = false;
    let screenAvailable = false;
    let updatingRange = true;
    let rangeEnabled = null;

    function hasColor(value) {
      return typeof value === 'string' && /^#[\da-f]{6}$/i.test(value);
    }

    for (const finish of finishes) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'finish-swatch';
      button.dataset.finish = finish.id;
      button.setAttribute('aria-label', finish.label);
      button.title = [finish.label, finish.source].filter(Boolean).join(' · ');
      if (hasColor(finish.swatch)) button.style.setProperty('--swatch', finish.swatch);
      button.addEventListener('click', () => onFinish(finish.id));
      finishButtons.set(finish.id, button);
      byId('finishes').append(button);
      // Full replacement map, not a global material or scene tint.
      const colors = Object.entries(finish.colors || {}).filter(([id, css]) => shellIDs.has(id) && hasColor(css));
      finishMaps.set(finish.id, Object.fromEntries(colors));
    }
    if (!finishes.length) {
      const note = document.createElement('span');
      note.className = 'no-finishes';
      note.textContent = 'Нет ведомости расцветок';
      byId('finishes').append(note);
    }

    function rangeChanged(percent) {
      if (!updatingRange && rangeEnabled) onExplode(Math.max(0, Math.min(100, Math.round(percent))) / 100);
    }

    nativeRange.addEventListener('input', () => rangeChanged(nativeRange.valueAsNumber));
    if (window.noUiSlider) {
      window.noUiSlider.create(slider, {
        range: {min: 0, max: 100},
        start: 0,
        step: 1,
        connect: [true, false],
        keyboardSupport: true,
        handleAttributes: [{'aria-labelledby': 'explode-label'}],
        ariaFormat: {to: n => `${Math.round(n)} %`, from: parseFloat}
      });
      slider.noUiSlider.on('update.atlas', (values, handle, raw) => rangeChanged(raw[handle]));
      nativeRange.hidden = true;
      slider.hidden = false;
    }
    updatingRange = false;

    function reportFailure(message) {
      if (failed) return;
      failed = true;
      const old = viewport;
      viewport = null;
      old?.destroy();
      byId('print-note').textContent = data.parts.length
        ? '3D недоступен. Показан общий вид из CAD. Выбирайте детали в ведомости.'
        : 'Файл сцены недоступен. Показан печатный вид сборки из CAD.';
      byId('print-note').title = String(message || '');
      // Refer to the current CAD publication, never to a frozen image of a prior revision.
      const print = byId('print-image');
      print.onerror = () => {
        print.hidden = true;
        byId('print-note').textContent = '3D недоступен. Печатного листа нет рядом с атласом. Данные деталей доступны в ведомости.';
      };
      print.src = '../XKAH_PRO_A43_assembly_assembled.png';
      onViewport('fallback');
    }

    async function start() {
      try {
        if (!data.parts.length) throw new Error('Не загружен реестр CAD в data/scene.js.');
        if (!window.AtlasViewport?.create) throw new Error('Не загружен модуль viewport.js.');
        const instance = await window.AtlasViewport.create(canvas, data, {onPick, onError: reportFailure});
        if (failed) {
          instance?.destroy();
          return;
        }
        if (!instance) throw new Error('Не создан просмотрщик WebGL.');
        viewport = instance;
        if (data.service?.steps?.length && typeof instance.setOffsets !== 'function') {
          throw new Error('Модуль 3D не поддерживает положения деталей этого выпуска.');
        }
        // Success means the trace AND its physical optical carrier were matched by the renderer.
        screenAvailable = Boolean(data.presentation?.lcd?.artwork?.polygons?.length && instance.setScreenOn?.(true));
        onViewport('ready', screenAvailable);
      } catch (error) {
        reportFailure(error.message);
      }
    }

    function updateRange(value, enabled, context) {
      const percent = Math.round(value * 100);
      updatingRange = true;
      if (slider.noUiSlider && Number(slider.noUiSlider.get()) !== percent) slider.noUiSlider.set(percent);
      nativeRange.value = percent;
      byId('explode-value').textContent = context || `${percent} %`;
      slider.title = context || 'Сдвинуть узлы относительно друг друга';
      nativeRange.title = slider.title;
      if (rangeEnabled !== enabled) {
        rangeEnabled = enabled;
        nativeRange.disabled = !enabled;
        if (slider.noUiSlider) {
          if (enabled) slider.noUiSlider.enable();
          else slider.noUiSlider.disable();
          slider.querySelector('[role="slider"]').setAttribute('aria-disabled', String(!enabled));
        }
      }
      updatingRange = false;
    }

    function hasScreen() {
      return screenAvailable && Boolean(viewport);
    }

    function setScreen(wanted) {
      if (!hasScreen()) return false;
      const result = viewport.setScreenOn(wanted);
      return Boolean(result && wanted);
    }

    function render(state, intent, pose) {
      const ready = state.viewport === 'ready';
      const fallback = state.viewport === 'fallback';
      canvas.hidden = fallback;
      canvas.classList.toggle('is-interactive', ready);
      byId('loading-note').hidden = state.viewport !== 'loading';
      byId('print-fallback').hidden = !fallback;
      byId('gesture-hint').hidden = !ready;
      screenButton.hidden = !hasScreen() || !ready;
      screenButton.disabled = screenButton.hidden;
      screenButton.setAttribute('aria-pressed', String(state.screenOn));
      screenButton.textContent = state.screenOn ? 'Экран: вкл.' : 'Экран: выкл.';
      screenButton.title = 'Показать или скрыть заставку по каталогу XYKA. Это иллюстрация, не работа электроники.';
      document.querySelector('[data-action="fit"]').disabled = !ready;
      document.querySelector('[data-action="leave-isolation"]').hidden = !state.isolated;
      const isolate = document.querySelector('[data-action="isolate"]');
      isolate.disabled = !ready || !state.selected;
      isolate.hidden = fallback;
      const returnLabel = state.group === 'all' ? 'Вернуть в сборку' : 'Вернуть в узел';
      isolate.querySelector('span').textContent = state.isolated ? returnLabel : 'Осмотреть отдельно';
      document.querySelector('[data-action="leave-isolation"]').lastChild.textContent = state.group === 'all' ? 'К сборке' : 'К узлу';
      isolate.title = ready ? '' : 'Осмотр отдельно доступен в 3D';
      for (const button of document.querySelectorAll('[data-view]')) {
        const extended = ['left', 'right', 'bottom'].includes(button.dataset.view);
        button.disabled = !ready || (extended && typeof viewport?.setOffsets !== 'function');
        button.setAttribute('aria-pressed', String(button.dataset.view === state.view));
      }
      byId('picked-caption').hidden = !state.selected || !ready;
      byId('picked-id').textContent = state.selected || '';
      for (const [id, button] of finishButtons) {
        button.disabled = !ready;
        button.setAttribute('aria-pressed', String(id === state.finish));
      }
      byId('finish-name').textContent = finishButtons.get(state.finish)?.getAttribute('aria-label') || '—';
      // Manual explosion and the absolute service pose are mutually exclusive.
      const rangeContext = pose ? 'По этапам' : state.isolated || state.group !== 'all' ? 'Только в сборе' : '';
      updateRange(state.explode, ready && !rangeContext, rangeContext);

      if (!viewport || !ready) return;
      // setGroup itself releases isolation and resets the camera. Do not call it on
      // a search, pick, sidebar navigation or finish change: the user's orbit stays put.
      try {
        const groupChanged = !previous || state.group !== previous.group || intent === 'reset';
        const isolationChanged = groupChanged || state.isolated !== previous.isolated;
        const stepChanged = !previous || previous.serviceStep !== state.serviceStep;
        if (groupChanged) viewport.setGroup(state.group);
        if (!groupChanged && isolationChanged && previous.isolated) viewport.isolate(null);
        if (!previous || state.finish !== previous.finish || intent === 'reset') {
          viewport.setFinish(finishMaps.get(state.finish) || {});
        }
        if (stepChanged || isolationChanged || state.explode !== previous.explode) viewport.setExplode(state.explode);
        if (stepChanged || intent === 'reset') viewport.setOffsets?.(pose?.offsets || {});
        if (stepChanged || isolationChanged || state.selected !== previous.selected) {
          viewport.select(state.selected || pose?.focusIds[0] || null);
        }
        if (isolationChanged && state.isolated) viewport.isolate(state.isolated);
        if (stepChanged || isolationChanged || state.view !== previous.view || intent === 'view') viewport.setView(state.view);
        if (stepChanged || isolationChanged || intent === 'fit') viewport.fit();
        previous = {
          group: state.group, view: state.view, isolated: state.isolated,
          selected: state.selected, finish: state.finish, explode: state.explode, serviceStep: state.serviceStep
        };
      } catch (error) {
        reportFailure(error.message);
      }
    }

    window.addEventListener('pagehide', event => {
      if (!event.persisted) viewport?.destroy();
    });
    return {start, render, setScreen};
  }

  window.AtlasDrawing = Object.freeze({create});
})();
