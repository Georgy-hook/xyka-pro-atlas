/* The current language is a link in the footer, with a compact shortcut in the masthead. */
(() => {
  'use strict';
  const {names, lang, t, remember} = window.AtlasLocale;
  const dialog = document.getElementById('language-dialog');
  const choices = [...dialog.querySelectorAll('a[hreflang]')];
  const triggers = [document.getElementById('language-link'), document.getElementById('language-nav')];
  const close = document.getElementById('language-close');
  let opener;

  function dismiss() {
    if (typeof dialog.close === 'function') dialog.close();
    else dialog.removeAttribute('open');
    setOpen(false);
    opener?.focus({preventScroll: true});
  }
  function setOpen(open) {
    document.documentElement.classList.toggle('language-open', open);
    for (const trigger of triggers) trigger.setAttribute('aria-expanded', String(open));
  }
  const nativeName = names[lang];
  const caption = t(`Выбрать язык: ${nativeName}`, `Choose language: ${nativeName}`, `选择语言：${nativeName}`);
  const text = document.querySelector('[data-current-language]');
  text.textContent = nativeName;
  text.lang = lang;
  document.querySelector('[data-language-code]').textContent = {en: 'EN', ru: 'RU', 'zh-CN': '中文'}[lang];
  for (const link of choices) {
    const next = link.dataset.language;
    const dest = new URL(location.href);
    dest.searchParams.set('lang', next);
    link.href = dest.href;
    if (next === lang) link.setAttribute('aria-current', 'true');
    link.addEventListener('click', event => {
      if (event.altKey || event.shiftKey || event.metaKey || event.ctrlKey || event.button !== 0) return;
      remember(next, window.AtlasUI?.getState());
      if (next === lang) {
        event.preventDefault();
        dismiss();
      }
    });
  }
  for (const trigger of triggers) {
    trigger.hidden = false;
    trigger.title = caption;
    trigger.setAttribute('aria-label', caption);
    trigger.setAttribute('aria-expanded', 'false');
    trigger.addEventListener('click', () => {
      opener = trigger;
      if (typeof dialog.showModal === 'function') dialog.showModal();
      else dialog.setAttribute('open', '');
      setOpen(true);
      choices.find(link => link.dataset.language === lang)?.focus({preventScroll: true});
    });
  }
  dialog.addEventListener('close', () => {
    // Native close events are queued. A previous close must not mark a newly opened chooser as closed.
    if (dialog.hasAttribute('open')) return;
    setOpen(false);
    opener?.focus({preventScroll: true});
  });
  close.addEventListener('click', dismiss);
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
})();
