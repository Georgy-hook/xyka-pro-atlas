/* Classic scripts so the atlas can be opened directly from disk. */
(() => {
  'use strict';

  const byId = id => document.getElementById(id);
  const data = window.ATLAS_SCENE || {parts: [], groups: []};
  const notes = window.ATLAS_NOTES || {};
  const finishes = Array.isArray(notes.finishes) ? notes.finishes : [];
  const defaultFinish = finishes.find(f => f.id === 'graphite')?.id || finishes[0]?.id || null;
  const parts = new Map(data.parts.map(part => [part.id, part]));
  const groups = [{id: 'all', label: 'В сборе', no: '00'}, ...data.groups.map((group, i) => ({
    id: group.id,
    label: group.shortLabel || (group.label || group.id).replace(/^\d+\s+/, ''),
    no: String(i + 1).padStart(2, '0')
  }))];
  const groupIndex = new Map(groups.map(g => [g.id, g]));
  const pageTabs = Array.from(byId('sheets-nav').querySelectorAll('[role="tab"]'));
  const narrow = window.matchMedia('(max-width: 780px)');
  const state = {
    page: 'assembly', group: 'all', selected: null, isolated: null,
    query: '', sub: '', view: 'iso', explode: 0, finish: defaultFinish, viewport: 'loading',
    serviceStep: null, screenOn: false
  };
  let returnView = 'iso';
  let passportID = null;
  let renderedSpecs = false;
  let registerKey = null;

  function buildTab(group) {
    const button = document.createElement('button');
    button.id = `node-${group.id}`;
    button.type = 'button';
    button.className = 'node-tab';
    button.dataset.group = group.id;
    button.setAttribute('role', 'tab');
    button.setAttribute('aria-controls', 'node-sheet');
    button.title = data.groups.find(item => item.id === group.id)?.label || 'Вся сборка';
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
    announce(`Расцветка корпуса: ${byId('finish-name').textContent}`);
  }

  function focusPassport() {
    byId('part-focus').focus({preventScroll: true});
    if (narrow.matches) byId('register').scrollIntoView({block: 'start'});
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
      state.screenOn = catalogScreen;
      if (status === 'fallback' && state.isolated) {
        state.isolated = null;
        state.view = returnView;
      }
      render();
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

  function renderPassport() {
    const part = parts.get(state.selected);
    byId('register-pane').hidden = !!part;
    byId('passport').hidden = !part;
    byId('to-register').querySelector('span').textContent = part ? 'К паспорту' : 'К ведомости';
    if (part && passportID !== part.id) {
      byId('part-focus').textContent = part.label || part.id;
      byId('part-id').textContent = part.id;
      byId('passport-number').textContent = `Поз. ${register.position(part.id)}`;
      byId('passport').dataset.partId = part.id;
      window.AtlasEvidence.renderPassport(byId('passport-body'), part, evidenceContext);
      byId('passport').querySelector('.passport-scroll').scrollTop = 0;
    }
    if (!part && passportID !== null) {
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
    byId('node-sheet').setAttribute('aria-labelledby', `node-${group.id}`);
    const printOnly = state.viewport === 'fallback';
    const showPose = pose && !printOnly;
    byId('figure-number').textContent = `Фиг. ${printOnly ? '00' : group.no}`;
    byId('figure-number').hidden = Boolean(showPose);
    byId('step-link').hidden = !showPose;
    byId('to-service-view').hidden = !showPose;
    if (showPose) byId('step-link').textContent = `Этап ${String(pose.ordinal).padStart(2, '0')}`;
    byId('drawing-title').textContent = printOnly ? 'Печатный вид сборки' :
      pose ? pose.title : state.isolated ? 'Осмотр детали' : group.id === 'all' ? 'Общий вид' : group.label;

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
    announce(pose ? `Этап ${pose.ordinal}. ${pose.title}.` : 'Все детали возвращены в сборку.');
  }

  function selectPart(id, origin) {
    const part = parts.get(id);
    if (!part) return;
    const fromSheet = origin === 'specs' || origin === 'service' || !!state.serviceStep;
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
    if (origin !== 'drawing' || narrow.matches) focusPassport();
    announce(`Выбрано: ${part.label || part.id}. CAD ID: ${part.id}`);
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
      returnView = state.view;
      state.isolated = state.selected;
      state.view = 'part';
    }
    render();
    if (narrow.matches) byId('drawing').scrollIntoView({block: 'start'});
    const target = state.isolated ? 'leave-isolation' : narrow.matches || fromField ? 'fit' : 'isolate';
    document.querySelector(`[data-action="${target}"]`).focus({preventScroll: true});
    announce(state.isolated ? 'В поле показана только выбранная деталь.' : 'Деталь возвращена в текущий узел.');
  }

  function reset() {
    Object.assign(state, {
      group: 'all', selected: null, isolated: null, query: '', sub: '', view: 'iso', explode: 0,
      finish: defaultFinish, serviceStep: null, screenOn: drawing.setScreen(true)
    });
    returnView = 'iso';
    registerKey = null;
    render('reset');
    announce('Восстановлены сборка, изометрия и исходная расцветка. Разнос и фильтры сброшены.');
  }

  for (const tab of pageTabs) tab.addEventListener('click', () => switchPage(tab.dataset.page));
  bindTabKeys(byId('sheets-nav'), pageTabs);
  bindTabKeys(byId('group-tabs'), groupTabs);
  window.addEventListener('resize', () => {
    if (state.page === 'assembly') revealTab(byId(`node-${state.group}`));
  });
  byId('to-register').addEventListener('click', event => {
    event.preventDefault();
    if (state.selected) focusPassport();
    else {
      byId('register').scrollIntoView({block: 'start'});
      byId('part-search').focus({preventScroll: true});
    }
  });
  byId('picked-caption').addEventListener('click', event => {
    event.preventDefault();
    focusPassport();
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
    if (state.page !== 'assembly' || event.isComposing || event.ctrlKey || event.altKey || event.metaKey) return;
    const typing = event.target.closest('input, select, textarea, [contenteditable="true"]');
    if (event.key === '/' && !typing) {
      event.preventDefault();
      closePassport(false);
      byId('part-search').focus();
    } else if (event.key === 'Escape' && !typing) {
      if (state.isolated) toggleIsolation();
      else if (state.selected) closePassport(true);
      else if (state.serviceStep) setStep(null);
    }
  });

  window.AtlasUI = Object.freeze({getState: snapshot});
  render();
  document.documentElement.dataset.uiReady = 'true';
  window.dispatchEvent(new CustomEvent('atlas:ready', {detail: snapshot()}));
  drawing.start();
})();
