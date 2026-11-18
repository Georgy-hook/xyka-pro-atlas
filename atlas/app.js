/* Classic scripts so the atlas can be opened directly from disk. */
(() => {
  'use strict';

  const byId = id => document.getElementById(id);
  const {t} = window.AtlasLocale;
  const {data, notes} = window.AtlasLocale.catalogue(window.ATLAS_SCENE || {parts: [], groups: []}, window.ATLAS_NOTES || {});
  const finishes = Array.isArray(notes.finishes) ? notes.finishes : [];
  const defaultFinish = finishes.find(f => f.id === 'graphite')?.id || finishes[0]?.id || null;
  const parts = new Map(data.parts.map(part => [part.id, part]));
  const groups = [{id: 'all', label: t('В сборе', 'Assembled', '装配状态'), no: '00'}, ...data.groups.map((group, i) => ({
    id: group.id,
    label: group.shortLabel || (group.label || group.id).replace(/^\d+\s+/, ''),
    no: String(i + 1).padStart(2, '0')
  }))];
  const groupIndex = new Map(groups.map(g => [g.id, g]));
  const pageTabs = Array.from(byId('sheets-nav').querySelectorAll('[role="tab"]'));
  // A landscape phone still needs the stacked register and touch instrument panel.
  const narrow = window.matchMedia('(max-width: 780px), (pointer: coarse) and (max-width: 1024px)');
  const state = {
    page: 'assembly', group: 'all', selected: null, isolated: null,
    query: '', sub: '', view: 'iso', explode: 0, finish: defaultFinish, viewport: 'loading',
    serviceStep: null, screenOn: false
  };
  let returnView = 'iso';
  let passportID = null;
  let renderedSpecs = false;
  let registerKey = null;
  let restoreScreenOff = false;
  let restoringViewport = false;
  let pendingOrbit = null;
  let drawingWaypoint = null;

  const groupPicker = byId('inspect-group');
  byId('inspect-group-label').textContent = t('Узел модели', 'Model assembly', '模型组件');
  for (const group of groups) groupPicker.add(new Option(`${group.no} · ${group.label}`, group.id));
  groupPicker.addEventListener('change', () => switchGroup(groupPicker.value));
  byId('to-drawing').querySelector('span').textContent = t('К модели', 'Back to model', '返回模型');

  function buildTab(group) {
    const button = document.createElement('button');
    button.id = `node-${group.id}`;
    button.type = 'button';
    button.className = 'node-tab';
    button.dataset.group = group.id;
    button.setAttribute('role', 'tab');
    button.setAttribute('aria-controls', 'node-sheet');
    button.title = data.groups.find(item => item.id === group.id)?.label || t('Вся сборка', 'Complete assembly', '完整装配模型');
    const folio = document.createElement('span');
    folio.className = 'node-no';
    folio.textContent = group.no;
    button.append(folio, document.createTextNode(group.label));
    byId('group-tabs').append(button);
    button.addEventListener('click', () => switchGroup(group.id));
    return button;
  }
  const groupTabs = groups.map(buildTab);

  function tabState(button, active) {
    button.setAttribute('aria-selected', String(active));
    button.tabIndex = active ? 0 : -1;
  }

  function bindTabKeys(list, tabs) {
    list.addEventListener('keydown', event => {
      const index = tabs.indexOf(event.target);
      if (index < 0 || event.altKey || event.ctrlKey || event.metaKey) return;
      const keys = {
        Home: 0,
        End: tabs.length - 1,
        ArrowLeft: (index + tabs.length - 1) % tabs.length,
        ArrowRight: (index + 1) % tabs.length
      };
      if (!Object.hasOwn(keys, event.key)) return;
      event.preventDefault();
      const next = tabs[keys[event.key]];
      next.focus();
      next.click();
    });
  }

  function announce(text) {
    byId('announcer').textContent = text;
  }

  function chooseFinish(id) {
    state.finish = id;
    render();
    const label = byId('finish-name').textContent;
    announce(t(`Расцветка корпуса: ${label}`, `Housing finish: ${label}`, `外壳配色：${label}`));
  }

  function focusPassport() {
    byId('part-focus').focus({preventScroll: true});
    if (narrow.matches) byId('register').scrollIntoView({block: 'start'});
  }

  function openRecordFromDrawing(opener) {
    if (narrow.matches) {
      drawingWaypoint = {
        id: state.selected, opener, width: innerWidth,
        top: byId('drawing-field').getBoundingClientRect().top
      };
    }
    focusPassport();
  }

  function backToDrawing() {
    const mark = drawingWaypoint;
    drawingWaypoint = null;
    const field = byId('drawing-field');
    if (mark && mark.id === state.selected && mark.width === innerWidth) {
      // Measure from the field, not the document: titles can reflow above it.
      window.scrollBy({top: field.getBoundingClientRect().top - mark.top, behavior: 'instant'});
      mark.opener.focus({preventScroll: true});
    } else {
      byId('drawing').scrollIntoView({block: 'start'});
      byId('drawing').focus({preventScroll: true});
    }
  }

  function revealTab(button) {
    // Scroll just the spine strip, not the page or the drawing under inspection.
    const strip = byId('group-tabs');
    const {left, right} = button.getBoundingClientRect();
    const bounds = strip.getBoundingClientRect();
    if (left < bounds.left) strip.scrollLeft += left - bounds.left;
    if (right > bounds.right) strip.scrollLeft += right - bounds.right;
  }

  const register = window.AtlasRegister.create({
    parts: data.parts,
    groups,
    onSelect: id => selectPart(id, 'register'),
    onFilter(query, sub) {
      state.query = query;
      state.sub = sub;
      render();
    }
  });

  const drawing = window.AtlasDrawing.create({
    data,
    finishes,
    narrow,
    onPick(id) {
      if (state.page !== 'assembly') return;
      if (parts.has(id)) selectPart(id, 'drawing');
      else if (id == null && !state.isolated) closePassport(false);
    },
    onExplode(value) {
      state.explode = value;
      render();
    },
    onFinish: chooseFinish,
    onViewport(status, catalogScreen = false) {
      state.viewport = status;
      state.screenOn = catalogScreen && restoreScreenOff ? drawing.setScreen(false) : catalogScreen;
      restoreScreenOff = false;
      if (status === 'fallback' && state.isolated) {
        state.isolated = null;
        state.view = returnView;
      }
      if (status === 'fallback' && restoringViewport) {
        // The print always shows the assembled model, but the step list and part record still work.
        state.explode = 0;
        state.view = service.get(state.serviceStep)?.view || 'iso';
      }
      restoringViewport = false;
      render();
      const orbit = pendingOrbit;
      pendingOrbit = null;
      if (status === 'ready' && orbit) drawing.restoreOrbit(orbit);
    }
  });

  const service = window.AtlasService.create({
    data, parts, groups: groupIndex, onStep: setStep, onPart: id => selectPart(id, 'service')
  });

  const product = window.AtlasProduct.create({
    data, finishes, onFinish: chooseFinish, onOverview: () => switchPage('assembly'),
    onStep: setStep, onGroup: id => switchGroup(id, true)
  });

  const evidenceContext = {data, notes, onPart: id => selectPart(id, 'specs')};

  function restoreLocaleContext() {
    // Only an explicit language navigation supplies this small one-shot snapshot.
    // IDs, not translated captions, bind it to the currently loaded catalogue.
    let saved;
    try {
      saved = window.AtlasLocale.takeContext?.();
    } catch {
      return null;
    }
    if (!saved || typeof saved !== 'object' || Array.isArray(saved)) return null;
    if (pageTabs.some(tab => tab.dataset.page === saved.page)) state.page = saved.page;
    if (finishes.some(finish => finish.id === saved.finish)) state.finish = saved.finish;

    const pose = service.get(saved.serviceStep);
    if (pose) {
      // Step offsets and their focus part apply to the whole assembly, never to an isolated part.
      state.serviceStep = pose.id;
      state.view = pose.view;
      if (parts.has(saved.selected)) state.selected = saved.selected;
    } else {
      if (groupIndex.has(saved.group)) state.group = saved.group;
      const part = parts.get(saved.selected);
      if (part && (state.group === 'all' || part.group === state.group)) {
        state.selected = part.id;
        if (saved.isolated === part.id) {
          state.isolated = part.id;
          state.view = 'part';
        }
      }
      if (state.group === 'all' && Number.isFinite(saved.explode) && saved.explode >= 0 && saved.explode <= 1) {
        state.explode = Math.round(saved.explode * 100) / 100;
      }
    }
    const namedView = Array.from(document.querySelectorAll('[data-view]')).some(button => button.dataset.view === saved.view);
    if (namedView) {
      state.view = saved.view;
      if (state.isolated) returnView = saved.view;
    }
    if (typeof saved.query === 'string') state.query = saved.query.slice(0, 512);
    if (typeof saved.sub === 'string' && saved.sub && data.parts.some(part =>
      (state.group === 'all' || part.group === state.group) && (part.subKey ?? part.sub) === saved.sub)) {
      state.sub = saved.sub;
    }
    restoreScreenOff = saved.screenOn === false;
    pendingOrbit = saved.orbit || null;
    restoringViewport = true;
    return Number.isFinite(saved.scrollY) && saved.scrollY >= 0 ? saved.scrollY : null;
  }

  function restoreScrollAfter(startup, top) {
    if (top === null) return;
    // Defer past the browser's own fragment navigation and the print/3D layout.
    // Never move the reader back if they started navigating during a slow load.
    const input = new AbortController();
    const cancel = () => input.abort();
    for (const type of ['pointerdown', 'keydown', 'wheel', 'touchstart']) {
      window.addEventListener(type, cancel, {passive: true, signal: input.signal});
    }
    const loaded = document.readyState === 'complete' ? Promise.resolve() : new Promise(done => {
      window.addEventListener('load', done, {once: true});
    });
    Promise.all([startup, loaded]).then(() => requestAnimationFrame(() => {
      if (!input.signal.aborted) window.scrollTo({top, behavior: 'instant'});
      input.abort();
    }));
  }

  function renderPassport() {
    const part = parts.get(state.selected);
    if (part?.id !== drawingWaypoint?.id) drawingWaypoint = null;
    byId('to-drawing').hidden = state.viewport !== 'ready';
    byId('register-pane').hidden = !!part;
    byId('passport').hidden = !part;
    byId('to-register').querySelector('span').textContent = part
      ? t('К паспорту', 'Part record', '零件档案') : t('К ведомости', 'Parts list', '零件清单');
    if (part && passportID !== part.id) {
      byId('picked-name').textContent = part.label || part.id;
      byId('part-focus').textContent = part.label || part.id;
      byId('part-id').textContent = part.id;
      const number = register.position(part.id);
      byId('passport-number').textContent = t(`Поз. ${number}`, `Item ${number}`, `序号 ${number}`);
      byId('passport').dataset.partId = part.id;
      window.AtlasEvidence.renderPassport(byId('passport-body'), part, evidenceContext);
      byId('passport').querySelector('.passport-scroll').scrollTop = 0;
    }
    if (!part && passportID !== null) {
      byId('picked-name').textContent = '';
      delete byId('passport').dataset.partId;
      byId('part-id').textContent = '';
      byId('part-focus').textContent = '';
      byId('passport-body').replaceChildren();
    }
    passportID = part?.id || null;
  }

  function render(intent) {
    const group = groupIndex.get(state.group);
    const pose = service.get(state.serviceStep);
    for (const button of pageTabs) {
      const active = button.dataset.page === state.page;
      tabState(button, active);
      byId(button.dataset.page).hidden = !active;
    }
    for (const button of groupTabs) tabState(button, button.dataset.group === state.group);
    groupPicker.value = group.id;
    const sheet = byId('node-sheet');
    sheet.setAttribute('role', narrow.matches ? 'region' : 'tabpanel');
    sheet.setAttribute('aria-labelledby', narrow.matches ? 'drawing-title' : `node-${group.id}`);
    const printOnly = state.viewport === 'fallback';
    const showPose = pose && !printOnly;
    const figure = printOnly ? '00' : group.no;
    byId('figure-number').textContent = t(`Фиг. ${figure}`, `Fig. ${figure}`, `图 ${figure}`);
    byId('figure-number').hidden = Boolean(showPose);
    byId('step-link').hidden = !showPose;
    byId('to-service-view').hidden = !showPose;
    if (showPose) {
      const number = String(pose.ordinal).padStart(2, '0');
      byId('step-link').textContent = t(`Этап ${number}`, `Stage ${number}`, `阶段 ${number}`);
    }
    const title = byId('drawing-title');
    if (printOnly) title.textContent = t('Печатный вид сборки', 'Static assembly view', '静态装配图');
    else if (pose) title.textContent = pose.title;
    else if (state.isolated) title.textContent = t('Осмотр детали', 'Part inspection', '零件详视');
    else title.textContent = group.id === 'all' ? t('Общий вид', 'Assembly overview', '装配总览') : group.label;

    const key = JSON.stringify([state.group, state.query, state.sub]);
    if (key !== registerKey) {
      register.render(state);
      registerKey = key;
      if (state.page === 'assembly') revealTab(byId(`node-${group.id}`));
    }
    renderPassport();
    if (state.page === 'specs' && !renderedSpecs) {
      window.AtlasEvidence.renderSpecs(byId('spec-body'), evidenceContext);
      renderedSpecs = true;
    }
    service.render(state);
    product.render(state.finish, printOnly);
    drawing.render(state, intent, pose);
    const flags = document.documentElement.dataset;
    flags.activePage = state.page;
    flags.activeGroup = state.group;
    flags.selectedId = state.selected || '';
    flags.isolatedId = state.isolated || '';
    flags.viewportState = state.viewport;
    flags.serviceStep = state.serviceStep || '';
    window.dispatchEvent(new CustomEvent('atlas:change', {detail: snapshot()}));
  }

  function snapshot() {
    const offsets = service.get(state.serviceStep)?.offsets || service.rest;
    const serviceOffsets = Object.fromEntries(Object.entries(offsets).map(([id, xyz]) => [id, [...xyz]]));
    return {...state, resultCount: register.count(), serviceOffsets};
  }

  function switchPage(page) {
    if (state.page === page) return;
    state.page = page;
    render();
    if (page === 'assembly') revealTab(byId(`node-${state.group}`));
    window.scrollTo({top: 0, behavior: 'instant'});
  }

  function switchGroup(id, openDefaultView = false) {
    if (!openDefaultView && state.group === id && !state.isolated && !state.serviceStep) return;
    Object.assign(state, {group: id, query: '', sub: '', selected: null, isolated: null, serviceStep: null, explode: 0, view: 'iso'});
    returnView = 'iso';
    render(openDefaultView ? 'reset' : undefined);
  }

  function setStep(id) {
    const pose = service.get(id);
    if (id && !pose) return;
    const focus = document.activeElement;
    Object.assign(state, {
      page: 'assembly', group: 'all', selected: null, isolated: null, query: '', sub: '',
      explode: 0, serviceStep: pose?.id || null, view: pose?.view || 'iso'
    });
    returnView = 'iso';
    render('step');
    if (focus?.disabled) byId('service-step').focus({preventScroll: true});
    announce(pose ? t(`Этап ${pose.ordinal}. ${pose.title}.`, `Stage ${pose.ordinal}. ${pose.title}.`, `第 ${pose.ordinal} 阶段：${pose.title}。`)
      : t('Все детали возвращены в сборку.', 'All parts are back in the assembly.', '所有零件已恢复至装配状态。'));
  }

  function selectPart(id, origin) {
    const part = parts.get(id);
    if (!part) return;
    // Inspecting a displaced part on a phone must not dismantle its stage or
    // change the camera. Explicit list/service/spec links still open the record.
    const stayInField = origin === 'drawing' && narrow.matches;
    const fromSheet = origin === 'specs' || origin === 'service' || (state.serviceStep && !stayInField);
    if (fromSheet || (state.group !== 'all' && state.group !== part.group)) {
      Object.assign(state, {page: 'assembly', group: part.group, query: '', sub: '', isolated: null, serviceStep: null, explode: 0, view: 'iso'});
      returnView = 'iso';
    } else if (state.isolated && state.isolated !== id) {
      state.isolated = null;
      state.view = returnView;
    }
    state.selected = id;
    render();
    if (fromSheet) {
      revealTab(byId(`node-${state.group}`));
      if (!narrow.matches) byId('drawing').scrollIntoView({block: 'start'});
    }
    if (origin !== 'drawing') focusPassport();
    const label = part.label || part.id;
    announce(t(`Выбрано: ${label}. CAD ID: ${part.id}`, `Selected: ${label}. CAD ID: ${part.id}`, `已选择：${label}。CAD ID：${part.id}`));
  }

  function closePassport(focusList) {
    const old = state.selected;
    if (!old) return;
    if (state.isolated) state.view = returnView;
    state.selected = null;
    state.isolated = null;
    render();
    if (focusList) register.focusPart(old);
  }

  function toggleIsolation() {
    if (state.viewport !== 'ready' || !state.selected) return;
    const fromField = document.activeElement?.dataset.action === 'leave-isolation';
    if (state.isolated) {
      state.isolated = null;
      state.view = returnView;
    } else {
      if (state.serviceStep) {
        state.serviceStep = null;
        state.view = 'iso';
      }
      returnView = state.view;
      state.isolated = state.selected;
      state.view = 'part';
    }
    render();
    if (narrow.matches) byId('drawing').scrollIntoView({block: 'start'});
    const target = state.isolated ? 'leave-isolation' : narrow.matches || fromField ? 'fit' : 'isolate';
    document.querySelector(`[data-action="${target}"]`).focus({preventScroll: true});
    announce(state.isolated
      ? t('В поле показана только выбранная деталь.', 'Only the selected part is shown.', '当前视图只显示所选零件。')
      : t('Деталь возвращена в текущий узел.', 'The part is back in its assembly.', '零件已返回当前组件。'));
  }

  function reset() {
    restoreScreenOff = false;
    Object.assign(state, {
      group: 'all', selected: null, isolated: null, query: '', sub: '', view: 'iso', explode: 0,
      finish: defaultFinish, serviceStep: null, screenOn: drawing.setScreen(true)
    });
    returnView = 'iso';
    registerKey = null;
    render('reset');
    announce(t('Восстановлены сборка, изометрия и исходная расцветка. Разнос и фильтры сброшены.',
      'Assembly, isometric view and original finish restored. Exploded view and filters reset.',
      '已恢复完整装配模型、轴测视图和原始配色，并重置分解视图和筛选条件。'));
  }

  for (const tab of pageTabs) tab.addEventListener('click', () => switchPage(tab.dataset.page));
  bindTabKeys(byId('sheets-nav'), pageTabs);
  bindTabKeys(byId('group-tabs'), groupTabs);
  narrow.addEventListener('change', () => render());
  window.addEventListener('resize', () => {
    if (state.page === 'assembly') revealTab(byId(`node-${state.group}`));
  });
  byId('to-register').addEventListener('click', event => {
    event.preventDefault();
    if (state.selected) openRecordFromDrawing(event.currentTarget);
    else {
      byId('register').scrollIntoView({block: 'start'});
      byId('part-search').focus({preventScroll: true});
    }
  });
  byId('picked-caption').addEventListener('click', event => {
    event.preventDefault();
    openRecordFromDrawing(event.currentTarget);
  });
  byId('to-drawing').addEventListener('click', event => {
    event.preventDefault();
    backToDrawing();
  });
  byId('assembly').addEventListener('click', event => {
    const button = event.target.closest('button');
    if (!button || button.disabled) return;
    if (button.dataset.view && state.viewport === 'ready') {
      state.view = button.dataset.view;
      render('view');
    }
    switch (button.dataset.action) {
      case 'screen':
        state.screenOn = drawing.setScreen(!state.screenOn);
        render();
        break;
      case 'fit':
        render('fit');
        break;
      case 'reset':
        reset();
        break;
      case 'catalog':
        closePassport(true);
        break;
      case 'isolate':
      case 'leave-isolation':
        toggleIsolation();
        break;
    }
  });

  document.addEventListener('keydown', event => {
    if (state.page !== 'assembly' || byId('language-dialog')?.hasAttribute('open')) return;
    if (event.isComposing || event.ctrlKey || event.altKey || event.metaKey) return;
    const typing = event.target.closest('input, select, textarea, [contenteditable="true"]');
    if (event.key === '/' && !typing) {
      event.preventDefault();
      closePassport(false);
      byId('part-search').focus();
    } else if (event.key === 'Escape' && !typing) {
      if (state.isolated) toggleIsolation();
      else if (state.selected) {
        const keepDrawing = narrow.matches && byId('drawing').contains(document.activeElement);
        closePassport(!keepDrawing);
        if (keepDrawing) byId('drawing').focus({preventScroll: true});
      } else if (state.serviceStep) setStep(null);
    }
  });

  const returnScrollY = restoreLocaleContext();
  function visitGroupFragment() {
    // The desktop tab strip is replaced by a select on phones. Its individual
    // #node-* links still need a visible destination (including on first load).
    if (!narrow.matches || !location.hash.startsWith('#node-')) return;
    const id = location.hash.slice('#node-'.length);
    if (!groupIndex.has(id)) return;
    switchPage('assembly');
    switchGroup(id, true);
    byId('drawing').scrollIntoView({block: 'start'});
  }
  window.addEventListener('hashchange', visitGroupFragment);
  window.AtlasUI = Object.freeze({getState: snapshot, getOrbit: drawing.captureOrbit});
  render();
  document.documentElement.dataset.uiReady = 'true';
  window.dispatchEvent(new CustomEvent('atlas:ready', {detail: snapshot()}));
  if (returnScrollY === null) visitGroupFragment();
  restoreScrollAfter(window.AtlasStudioMotion.startViewer(drawing.start), returnScrollY);
})();
