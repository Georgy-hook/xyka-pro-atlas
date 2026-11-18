/* Local studio renders of the four CAD finishes. The assembly owns the selection. */
(() => {
  'use strict';

  const byId = id => document.getElementById(id);
  const t = window.AtlasLocale.t;
  const supported = new Set(['graphite', 'silver', 'blue', 'pink']);

  const {visit, finishes: finishPresenter} = window.AtlasStudioMotion;

  function bindLink(id, activate) {
    byId(id).addEventListener('click', event => {
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      activate(event);
    });
  }

  function create({data, finishes, onFinish, onOverview, onStep, onGroup}) {
    const options = new Map();
    const image = byId('product-image');
    const paint = finishPresenter(image);
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
      visit('overview');
    });
    bindLink('explore-model', event => visit('explorer', event.detail > 0));
    // On a touch screen the product photograph is also a clear way into the real orbitable model.
    const inspect = document.createElement('a');
    inspect.id = 'inspect-studio-model';
    inspect.className = 'hero-inspect-link';
    inspect.href = '#drawing';
    const label = document.createElement('span');
    label.textContent = t('Вращать в 3D ↗', 'Rotate in 3D ↗', '旋转查看 ↗');
    inspect.append(label);
    image.parentElement.append(inspect);
    bindLink(inspect.id, () => visit('drawing'));
    if (boards.length) {
      bindLink('explore-mainboard', () => {
        onGroup(boards[0].id);
        visit(staticView ? 'register-title' : 'drawing');
      });
    }
    if (steps.length) {
      bindLink('explore-steps', () => {
        onStep(steps[0].id);
        visit(staticView ? 'service-title' : 'drawing');
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
        paint(url);
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
