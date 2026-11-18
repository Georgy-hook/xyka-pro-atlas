/* Local studio renders of the four CAD finishes. The assembly owns the selection. */
(() => {
  'use strict';

  const byId = id => document.getElementById(id);
  const t = window.AtlasLocale.t;
  const supported = new Set(['graphite', 'silver', 'blue', 'pink']);

  function visitTarget(id) {
    const target = byId(id);
    target.focus({preventScroll: true});
    target.scrollIntoView({block: 'start', behavior: 'instant'});
  }

  function bindLink(id, activate) {
    byId(id).addEventListener('click', event => {
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      activate();
    });
  }

  function create({data, finishes, onFinish, onOverview, onStep, onGroup}) {
    const options = new Map();
    const image = byId('product-image');
    const steps = data.service?.steps || [];
    let staticView = false;
    byId('product-part-count').textContent = data.parts.length || '—';
    const boards = data.groups.filter(group => group.id === 'MainPCB' || group.id === 'DisplayPCB');
    byId('product-board-count').textContent = boards.length || '—';

    for (const {id, label, swatch} of finishes) {
      if (!supported.has(id)) continue;
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'product-chip';
      button.dataset.productFinish = id;
      button.title = label;
      button.setAttribute('aria-label', label);
      button.style.setProperty('--swatch', swatch);
      button.addEventListener('click', () => onFinish(id));
      options.set(id, {button, label});
      byId('product-finishes').append(button);
    }
    bindLink('overview-link', () => {
      onOverview();
      visitTarget('overview');
    });
    bindLink('explore-model', () => visitTarget('explorer'));
    if (boards.length) {
      bindLink('explore-mainboard', () => {
        onGroup(boards[0].id);
        visitTarget(staticView ? 'register-title' : 'drawing');
      });
    }
    if (steps.length) {
      bindLink('explore-steps', () => {
        onStep(steps[0].id);
        visitTarget(staticView ? 'service-title' : 'drawing');
      });
    } else {
      byId('explore-steps').hidden = true;
    }

    return {
      render(finish, isStatic) {
        if (isStatic !== staticView) {
          staticView = isStatic;
          byId('explore-label').textContent = isStatic
            ? t('Открыть атлас', 'Explore the atlas', '打开图集')
            : t('Открыть в 3D', 'Explore in 3D', '查看 3D 模型');
        }
        const selected = options.get(finish);
        if (!selected || image.dataset.finishShown === finish) return;
        const url = `media/hero-${finish}.webp`;
        if (url !== image.getAttribute('src')) image.src = url;
        image.dataset.finishShown = finish;
        image.alt = t(`Чаша XYKA PRO, отделка «${selected.label}», вид со стороны экрана`,
          `${selected.label} XYKA PRO, viewed from the display side`, `${selected.label} XYKA PRO，屏幕侧视图`);
        byId('product-finish-name').textContent = selected.label;
        for (const [id, {button}] of options) {
          button.setAttribute('aria-pressed', String(id === finish));
        }
      }
    };
  }

  window.AtlasProduct = Object.freeze({create});
})();
