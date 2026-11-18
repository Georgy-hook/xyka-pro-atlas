/* UI-side adapter only. Geometry, orbit controls and picking belong to viewport.js. */
(() => {
  'use strict';

  // Only this adapter exposes renderer diagnostics to the reader (the print-note tooltip).
  // Keep the renderer independent of the UI locale and preserve literal CAD/node IDs.
  function rendererMessage(message) {
    const raw = String(message || '');
    const {lang, t} = window.AtlasLocale;
    if (!raw || lang === 'ru') return raw;
    const reason = raw.replace(/^Не удалось открыть 3D: /, '');
    const reasons = [
      ['В данных атласа нет встроенного GLB.', 'The atlas data contains no embedded GLB.', '图册数据中没有嵌入的 GLB 模型。'],
      ['Повреждён заголовок или размер GLB 2.0.', 'The GLB 2.0 header or file size is invalid.', 'GLB 2.0 文件头或文件大小无效。'],
      ['Для этой модели требуется внешний ресурс; атлас рассчитан на автономный GLB.',
        'The model requires an external resource, but this atlas needs a self-contained GLB.',
        '模型需要外部资源，但此图册要求使用不依赖外部文件的 GLB。'],
      ['Каталог и GLB относятся к разным ревизиям CAD.', 'The catalogue and GLB are from different CAD revisions.',
        '目录和 GLB 来自不同的 CAD 版本。'],
      [/^Повторяется узел glTF: (.+)\.$/, 'Duplicate glTF node: {id}.', 'glTF 节点重复：{id}。'],
      [/^Нет узла или вектора разнесения для группы (.+)\.$/, 'Group {id} is missing its node or explosion vector.',
        '组件 {id} 缺少节点或分解位移向量。'],
      [/^Не сопоставлена деталь (.+)\.$/, 'Could not match part {id} to the model.', '无法将零件 {id} 与模型匹配。'],
      [/^В узле (.+) нет геометрии\.$/, 'Node {id} has no geometry.', '节点 {id} 中没有几何数据。'],
      ['Каталог деталей пуст.', 'The parts list is empty.', '零件清单为空。'],
      ['Не найдена локальная библиотека three-atlas.js.', 'The local three-atlas.js library was not found.', '找不到本地库 three-atlas.js。'],
      ['Не переданы canvas или каталог сцены.', 'The canvas or scene catalogue is missing.', '缺少画布或场景目录。'],
      ['Браузер не создал контекст WebGL 2. Каталог и данные деталей доступны без 3D.',
        'The browser could not start WebGL 2. The parts list and part details are available without 3D.',
        '浏览器无法创建 WebGL 2 上下文。无需 3D 也能查看零件清单和详情。'],
      ['Потерян контекст WebGL. Каталог деталей остаётся доступен.',
        'The WebGL context was lost. The parts list is still available.', 'WebGL 上下文已丢失，仍可查看零件清单。'],
      ['Потерян контекст WebGL.', 'The WebGL context was lost.', 'WebGL 上下文已丢失。']
    ];
    for (const [pattern, en, zh] of reasons) {
      if (typeof pattern === 'string') {
        if (pattern === reason) return t(raw, en, zh);
      } else {
        const match = reason.match(pattern);
        if (match) return t(raw, en, zh).replace('{id}', () => match[1]);
      }
    }
    return t(raw, 'The 3D viewer could not display this model.', '3D 查看器无法显示此模型。');
  }

  function create({data, finishes, narrow, onPick, onExplode, onFinish, onViewport}) {
    const {t} = window.AtlasLocale;
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
    const optionsToggle = byId('options-toggle');
    const options = byId('view-options');
    const instrumentBar = document.querySelector('.inspect-bar');
    const instruments = Array.from(instrumentBar.querySelectorAll('[data-inspect]'));
    let viewport = null;
    let previous = null;
    let failed = false;
    let screenAvailable = false;
    let updatingRange = true;
    let rangeEnabled = null;
    let optionsOpen = false;

    const instrumentNames = {
      left: t('Повернуть камеру влево', 'Orbit left', '向左环绕'),
      right: t('Повернуть камеру вправо', 'Orbit right', '向右环绕'),
      in: t('Приблизить модель', 'Zoom in', '放大模型'),
      out: t('Отдалить модель', 'Zoom out', '缩小模型')
    };
    instrumentBar.setAttribute('aria-label', t('Управление моделью', 'Model controls', '模型操作'));
    for (const button of instruments) {
      button.title = instrumentNames[button.dataset.inspect];
      button.setAttribute('aria-label', button.title);
    }
    byId('orbit-label').textContent = t('Поворот', 'Orbit', '旋转');
    byId('zoom-label').textContent = t('Масштаб', 'Zoom', '缩放');
    byId('fit-label').textContent = t('Вписать', 'Fit', '完整显示');
    byId('picked-open').textContent = t('Открыть паспорт детали', 'Open part record', '查看零件档案');
    const guide = byId('gesture-hint').querySelector('.touch-hint');
    guide.querySelector('b').textContent = t('Вращайте модель одним пальцем.',
      'Drag with one finger to rotate.', '单指拖动可旋转模型。');
    guide.querySelector('span').textContent = t('Щипок меняет масштаб. Коснитесь детали, чтобы выбрать её.',
      'Pinch to zoom. Tap a part to select it.', '双指捏合可缩放，轻点即可选中零件。');
    optionsToggle.querySelector('span').textContent = t('Настроить вид', 'View settings', '视图设置');

    function showOptions() {
      // Don't leave an invisible row of projections or a slider in the tab order.
      options.hidden = failed || (narrow.matches && !optionsOpen);
      optionsToggle.hidden = failed;
      optionsToggle.setAttribute('aria-expanded', String(!options.hidden));
    }
    optionsToggle.addEventListener('click', () => {
      optionsOpen = !optionsOpen;
      showOptions();
    });
    byId('drawing').addEventListener('keydown', event => {
      if (event.key !== 'Escape' || !narrow.matches || !optionsOpen ||
          !(options.contains(event.target) || optionsToggle.contains(event.target))) return;
      event.stopPropagation();
      optionsOpen = false;
      showOptions();
      optionsToggle.focus({preventScroll: true});
    });
    narrow.addEventListener('change', () => {
      const wasEditing = options.contains(document.activeElement);
      showOptions();
      if (wasEditing && options.hidden && !failed) optionsToggle.focus({preventScroll: true});
    });
    showOptions();

    instrumentBar.addEventListener('click', event => {
      const button = event.target.closest('[data-inspect]');
      if (!button || button.disabled || !viewport) return;
      switch (button.dataset.inspect) {
        case 'left':
          viewport.turnBy(-20);
          break;
        case 'right':
          viewport.turnBy(20);
          break;
        case 'in':
          viewport.zoomBy(1.25);
          break;
        case 'out':
          viewport.zoomBy(0.8);
          break;
      }
    });

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
      note.textContent = t('Нет ведомости расцветок', 'No finishes listed', '未提供配色清单');
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
      showOptions();
      const old = viewport;
      viewport = null;
      old?.destroy();
      byId('print-note').textContent = data.parts.length
        ? t('3D недоступен. Показан общий вид из CAD. Выбирайте детали в ведомости.',
          '3D is unavailable. This is a static CAD view of the assembly. Select parts in the parts list.',
          '3D 不可用。当前显示 CAD 装配静态图，可在零件清单中选择零件。')
        : t('Файл сцены недоступен. Показан печатный вид сборки из CAD.',
          'The scene file is unavailable. This is a static CAD view of the assembly.', '场景文件不可用。当前显示 CAD 装配静态图。');
      byId('print-note').title = String(message || '');
      // Refer to the current CAD publication, never to a frozen image of a prior revision.
      const print = byId('print-image');
      print.alt = t('Статичный вид собранной модели XYKA PRO со стороны экрана',
        'Static CAD view of the assembled XYKA PRO from the display side', 'XYKA PRO 装配模型的静态屏幕侧视图');
      print.onerror = () => {
        print.hidden = true;
        byId('print-note').textContent = data.parts.length
          ? t('3D недоступен. Печатного листа нет рядом с атласом. Данные деталей доступны в ведомости.',
            '3D is unavailable and the CAD illustration could not be loaded. Part details are still available in the parts list.',
            '3D 不可用，CAD 静态图也未能加载。仍可在零件清单中查看详情。')
          : t('Файл сцены недоступен. Печатного листа нет рядом с атласом.',
            'Neither the scene file nor the static CAD illustration could be loaded.', '场景文件与 CAD 静态图均未能加载。');
      };
      print.src = '../XKAH_PRO_A43_assembly_assembled.png';
      onViewport('fallback');
    }

    async function start() {
      try {
        if (!data.parts.length) return reportFailure(t('Не загружен реестр CAD в data/scene.js.',
          'The CAD register in data/scene.js was not loaded.', '未加载 data/scene.js 中的 CAD 零件清单。'));
        if (!window.AtlasViewport?.create) return reportFailure(t('Не загружен модуль viewport.js.',
          'The viewport.js module was not loaded.', '未加载 viewport.js 模块。'));
        const instance = await window.AtlasViewport.create(canvas, data, {
          onPick, onError: message => reportFailure(rendererMessage(message))
        });
        if (failed) {
          instance?.destroy();
          return;
        }
        if (!instance) return reportFailure(t('Не создан просмотрщик WebGL.', 'Could not start the WebGL viewer.', '无法启动 WebGL 查看器。'));
        viewport = instance;
        if (data.service?.steps?.length && typeof instance.setOffsets !== 'function') {
          return reportFailure(t('Модуль 3D не поддерживает положения деталей этого выпуска.',
            'The 3D viewer cannot display the part positions in this release.', '3D 查看器不支持此版本中的零件位置。'));
        }
        // Success means the trace AND its physical optical carrier were matched by the renderer.
        screenAvailable = Boolean(data.presentation?.lcd?.artwork?.polygons?.length && instance.setScreenOn?.(true));
        onViewport('ready', screenAvailable);
      } catch (error) {
        reportFailure(rendererMessage(error?.message || error));
      }
    }

    function updateRange(value, enabled, context) {
      const percent = Math.round(value * 100);
      updatingRange = true;
      if (slider.noUiSlider && Number(slider.noUiSlider.get()) !== percent) slider.noUiSlider.set(percent);
      nativeRange.value = percent;
      byId('explode-value').textContent = context || `${percent} %`;
      slider.title = context || t('Сдвинуть узлы относительно друг друга', 'Move the groups apart', '拉开各组件之间的距离');
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
      byId('gesture-hint').hidden = !ready || Boolean(state.selected);
      for (const button of instruments) {
        const turn = button.dataset.inspect === 'left' || button.dataset.inspect === 'right';
        button.disabled = !ready || typeof viewport?.[turn ? 'turnBy' : 'zoomBy'] !== 'function';
      }
      screenButton.hidden = !hasScreen() || !ready;
      screenButton.disabled = screenButton.hidden;
      screenButton.setAttribute('aria-pressed', String(state.screenOn));
      screenButton.textContent = state.screenOn ? t('Экран: вкл.', 'Screen: on', '屏幕：开') : t('Экран: выкл.', 'Screen: off', '屏幕：关');
      screenButton.title = t('Показать или скрыть заставку по каталогу XYKA. Это иллюстрация, не работа электроники.',
        'Show or hide the screen artwork from the XYKA catalogue. This is an illustration, not an electronic simulation.',
        '显示或隐藏 XYKA 产品目录中的屏幕图案。这是示意图，不是电子功能仿真。');
      document.querySelector('[data-action="fit"]').disabled = !ready;
      document.querySelector('[data-action="leave-isolation"]').hidden = !state.isolated;
      const isolate = document.querySelector('[data-action="isolate"]');
      isolate.disabled = !ready || !state.selected;
      isolate.hidden = fallback;
      const returnLabel = state.group === 'all'
        ? t('Вернуть в сборку', 'Return to assembly', '返回装配体') : t('Вернуть в узел', 'Return to subassembly', '返回组件');
      isolate.querySelector('span').textContent = state.isolated ? returnLabel : t('Осмотреть отдельно', 'Isolate part', '单独查看');
      document.querySelector('[data-action="leave-isolation"]').lastChild.textContent = state.group === 'all'
        ? t('К сборке', 'Back to assembly', '返回装配体') : t('К узлу', 'Back to subassembly', '返回组件');
      isolate.title = ready ? '' : t('Осмотр отдельно доступен в 3D', 'Parts can be isolated in the 3D view', '可在 3D 视图中单独查看零件');
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
      const rangeContext = pose ? t('По этапам', 'Set by stage', '按阶段') : state.isolated || state.group !== 'all'
        ? t('Только в сборе', 'Assembly only', '仅限完整装配体') : '';
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
        reportFailure(rendererMessage(error?.message || error));
      }
    }

    window.addEventListener('pagehide', event => {
      if (!event.persisted) viewport?.destroy();
    });
    return {
      start,
      render,
      setScreen,
      captureOrbit: () => viewport?.captureOrbit?.() ?? null,
      restoreOrbit: orbit => viewport?.restoreOrbit?.(orbit)
    };
  }

  window.AtlasDrawing = Object.freeze({create});
})();
