/* A native modal plate; the page beneath it never leaves the screen on open or close. */
(() => {
  'use strict';
  const {names, lang, t, remember} = window.AtlasLocale;
  const root = document.documentElement;
  const dialog = document.getElementById('language-dialog');
  const sheet = dialog.querySelector('.language-sheet');
  const choices = [...dialog.querySelectorAll('a[hreflang]')];
  const current = choices.find(link => link.dataset.language === lang);
  const triggers = [document.getElementById('language-link'), document.getElementById('language-nav')];
  const close = document.getElementById('language-close');
  const motion = window.matchMedia?.('(prefers-reduced-motion: no-preference)');
  const exitMs = 200;
  dialog.style.setProperty('--language-exit', `${exitMs}ms`);
  let opener;
  let lockedY = 0;
  let timer;
  let pending;

  function cancelPending() {
    clearTimeout(timer);
    pending = null;
  }

  function finishPending() {
    const action = pending;
    cancelPending();
    action?.();
  }

  function afterExit(action) {
    cancelPending();
    pending = action;
    // Independent of transitionend, assets, WAAPI and cross-document transitions.
    if (motion?.matches) timer = setTimeout(finishPending, exitMs);
    else finishPending();
  }

  function setOpen(open) {
    if (open && !root.classList.contains('language-open')) {
      lockedY = window.scrollY;
      const stable = getComputedStyle(root).scrollbarGutter?.includes('stable');
      const gutter = stable ? 0 : Math.max(0, innerWidth - root.clientWidth);
      root.style.setProperty('--language-gutter', `${gutter}px`);
    }
    root.classList.toggle('language-open', open);
    if (!open) root.style.removeProperty('--language-gutter');
    for (const trigger of triggers) trigger.setAttribute('aria-expanded', String(open));
  }

  function updateLinks() {
    // A reader may have followed a fragment link since this controller loaded.
    for (const link of choices) {
      const dest = new URL(location.href);
      dest.searchParams.set('lang', link.dataset.language);
      link.href = dest.href;
    }
  }

  function present(trigger) {
    cancelPending();
    opener = trigger;
    const r = trigger.getBoundingClientRect();
    const x = Math.max(0, Math.min(innerWidth, r.left + r.width / 2));
    const y = Math.max(0, Math.min(innerHeight, r.top + r.height / 2));
    const fresh = !dialog.hasAttribute('open');
    delete dialog.dataset.localeStamp;
    updateLinks();
    setOpen(true);
    if (fresh) {
      dialog.dataset.phase = 'folded';
      if (typeof dialog.showModal === 'function') dialog.showModal();
      else {
        dialog.setAttribute('open', '');
        dialog.setAttribute('role', 'dialog');
        dialog.setAttribute('aria-modal', 'true');
      }
      dialog.scrollTop = 0;
    }
    // offsetLeft/Top are the untransformed paper edges, even mid-reversal.
    sheet.style.setProperty('--hinge-x', `${x - sheet.offsetLeft}px`);
    sheet.style.setProperty('--hinge-y', `${y - sheet.offsetTop + dialog.scrollTop}px`);
    sheet.style.setProperty('--ink-offset', y < innerHeight / 2 ? '-9px' : '9px');
    if (fresh && motion?.matches) sheet.getBoundingClientRect(); // establish the folded start style
    dialog.dataset.phase = 'open';
    current.focus({preventScroll: true});
  }

  function closed() {
    // Native close events are queued; an old close must not unlock a newer opening.
    if (dialog.hasAttribute('open') || !root.classList.contains('language-open')) return;
    cancelPending();
    delete dialog.dataset.phase;
    delete dialog.dataset.localeStamp;
    setOpen(false);
    opener?.focus({preventScroll: true});
    if (Math.abs(window.scrollY - lockedY) > 1) window.scrollTo({top: lockedY, behavior: 'instant'});
  }

  function closeNow() {
    if (typeof dialog.close === 'function') dialog.close();
    else dialog.removeAttribute('open');
    closed();
  }

  function dismiss() {
    if (!dialog.hasAttribute('open') || dialog.dataset.phase === 'closing') return;
    delete dialog.dataset.localeStamp;
    dialog.dataset.phase = 'closing';
    afterExit(closeNow);
  }

  const nativeName = names[lang];
  const caption = t(`Выбрать язык: ${nativeName}`, `Choose language: ${nativeName}`, `选择语言：${nativeName}`);
  const text = document.querySelector('[data-current-language]');
  text.textContent = nativeName;
  text.lang = lang;
  document.querySelector('[data-language-code]').textContent = {en: 'EN', ru: 'RU', 'zh-CN': '中文'}[lang];
  updateLinks();
  current.setAttribute('aria-current', 'true');
  for (const link of choices) {
    link.addEventListener('click', event => {
      if (event.defaultPrevented || event.altKey || event.shiftKey || event.metaKey || event.ctrlKey || event.button !== 0) return;
      event.preventDefault();
      const next = link.dataset.language;
      if (next === lang) {
        remember(next);
        dismiss();
        return;
      }
      if (dialog.dataset.phase === 'selecting') return;
      dialog.dataset.localeStamp = names[next];
      dialog.dataset.phase = 'selecting';
      afterExit(() => {
        // Save only when committing, not while Escape can still cancel the choice.
        remember(next, window.AtlasUI?.getState(), {href: link.href, trigger: opener?.id, scrollY: lockedY});
        location.assign(link.href);
      });
    });
  }

  for (const trigger of triggers) {
    trigger.hidden = false;
    trigger.title = caption;
    trigger.setAttribute('aria-label', caption);
    trigger.setAttribute('aria-expanded', 'false');
    trigger.addEventListener('click', () => present(trigger));
  }
  close.addEventListener('click', dismiss);
  dialog.addEventListener('close', closed);
  dialog.addEventListener('cancel', event => {
    event.preventDefault();
    dismiss();
  });
  dialog.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
      event.preventDefault();
      event.stopPropagation();
      dismiss();
    }
    if (event.key === 'Tab') {
      const order = [close, ...choices];
      const edge = event.shiftKey ? 0 : order.length - 1;
      if (document.activeElement === order[edge]) {
        event.preventDefault();
        order[event.shiftKey ? order.length - 1 : 0].focus();
      }
    }
  });
  function motionChanged() {
    if (!motion.matches) {
      delete root.dataset.localeStamp;
      finishPending();
    }
  }
  if (motion?.addEventListener) motion.addEventListener('change', motionChanged);
  else motion?.addListener(motionChanged);
  window.addEventListener('pageshow', event => {
    if (event.persisted && dialog.hasAttribute('open')) closeNow();
  });
})();
