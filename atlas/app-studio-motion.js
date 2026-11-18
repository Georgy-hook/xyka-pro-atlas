/* Motion is presentation-only. The assembly still owns the finish, selection and pose. */
(() => {
  'use strict';

  const root = document.documentElement;
  const visual = document.querySelector('.product-visual');
  const preference = matchMedia('(prefers-reduced-motion: reduce)');
  const ease = 'cubic-bezier(.22,.72,.16,1)';
  const still = () => preference.matches || document.visibilityState === 'hidden';

  function settleIntro() {
    root.dataset.studioSeen = 'true';
  }

  // Do not replay the entrance when the reader returns from another sheet or language.
  visual.addEventListener('animationend', event => {
    if (event.animationName === 'studio-settle') settleIntro();
  });
  if (still() || root.dataset.localeHandoff || location.hash) settleIntro();
  document.addEventListener('pointerdown', settleIntro, {once: true, passive: true});
  document.addEventListener('keydown', settleIntro, {once: true});
  window.addEventListener('pagehide', settleIntro);
  // A cached first paint can finish before this deferred enhancement is parsed.
  requestAnimationFrame(() => {
    if (!visual.getAnimations?.().some(effect => effect.animationName === 'studio-settle' && effect.playState === 'running')) {
      settleIntro();
    }
  });

  function visit(id, fromPointer = false) {
    const element = document.getElementById(id);
    if (!element) return;
    settleIntro();
    const coarse = matchMedia('(pointer: coarse)').matches;
    const landing = fromPointer && coarse && id === 'explorer' && root.dataset.viewportState !== 'fallback'
      ? document.getElementById('drawing') : element;
    element.focus({preventScroll: true});
    landing.scrollIntoView({block: 'start', behavior: still() ? 'instant' : 'smooth'});
  }

  // Avoid compiling the 3D scene's first frame on top of the one-shot entrance.
  // Reading, opening a deep link or asking to inspect the model never waits for the cue.
  function startViewer(start) {
    if (still() || root.dataset.studioSeen || root.dataset.localeHandoff || location.hash || scrollY > 16) {
      return start();
    }
    return new Promise(resolve => {
      const input = new AbortController();
      const run = () => {
        clearTimeout(deadline);
        input.abort();
        resolve(start());
      };
      const deadline = setTimeout(run, 1500);
      visual.addEventListener('animationend', e => {
        if (e.animationName === 'studio-settle') run();
      }, {signal: input.signal});
      for (const type of ['pointerdown', 'keydown', 'scroll', 'wheel', 'touchstart']) {
        window.addEventListener(type, run, {capture: true, passive: true, signal: input.signal});
      }
      preference.addEventListener('change', run, {signal: input.signal});
    });
  }

  // Keep a decoded finish on screen throughout a change. Rapid swatches coalesce to the last
  // requested image; we never queue a carousel of old colors or blend the actual CAD materials.
  function finishes(image) {
    let wanted = image.getAttribute('src');
    let generation = 0;
    let outgoing = null;
    let dissolve = null;
    let pending = null;

    function clearLayer() {
      const old = dissolve;
      dissolve = null;
      if (old) {
        old.onfinish = null;
        old.cancel();
      }
      outgoing?.remove();
      outgoing = null;
    }

    function snap() {
      generation++;
      pending = null;
      clearLayer();
      if (image.getAttribute('src') !== wanted) image.src = wanted;
    }

    async function present() {
      if (still() || typeof image.animate !== 'function') {
        snap();
        return;
      }
      if (dissolve) {
        // Finish the current blend more quickly; don't jump from a half-mixed surface.
        dissolve.playbackRate = 2.5;
        return;
      }
      const url = wanted;
      if (image.getAttribute('src') === url || pending === url) return;
      const ticket = ++generation;
      pending = url;
      const next = new Image();
      next.src = url;
      try {
        await next.decode();
      } catch {
        if (generation === ticket) {
          pending = null;
          image.src = url;
        }
        return;
      }
      if (ticket !== generation || wanted !== url) return;
      pending = null;
      if (still()) {
        snap();
        return;
      }
      const previous = image.cloneNode(false);
      previous.removeAttribute('id');
      previous.removeAttribute('fetchpriority');
      previous.removeAttribute('data-finish-shown');
      previous.className = 'finish-outgoing';
      previous.setAttribute('aria-hidden', 'true');
      previous.alt = '';
      image.after(previous);
      image.src = url;
      outgoing = previous;
      dissolve = previous.animate([{opacity: 1}, {opacity: 0}], {duration: 340, easing: ease, fill: 'both'});
      dissolve.onfinish = () => {
        clearLayer();
        if (image.getAttribute('src') !== wanted) present();
      };
    }

    function change(url) {
      if (wanted === url) return;
      wanted = url;
      generation++;
      pending = null;
      settleIntro();
      present();
    }
    preference.addEventListener('change', () => {
      if (preference.matches) {
        settleIntro();
        snap();
      }
    });
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) snap();
    });
    return change;
  }

  // A little continuity when the evidence changes. Leave the CAD canvas stationary and
  // never rerun an effect for a new frame, a typed search or a dragging slider.
  let last = null;
  const accents = new Map();
  function accent(selector) {
    const element = document.querySelector(selector);
    if (!element?.animate || !element.getClientRects().length) return;
    const bounds = element.getBoundingClientRect();
    if (bounds.bottom <= 0 || bounds.top >= innerHeight) return;
    accents.get(selector)?.cancel();
    const effect = element.animate([
      {opacity: .72, transform: 'translateY(5px)'},
      {opacity: 1, transform: 'none'},
    ], {duration: 250, easing: ease});
    accents.set(selector, effect);
    effect.onfinish = () => {
      if (accents.get(selector) === effect) accents.delete(selector);
    };
  }
  window.addEventListener('atlas:change', ({detail: current}) => {
    if (last && !still() && current.viewport === 'ready') {
      if (last.page !== current.page && current.page === 'specs') accent('#spec-body .ev-head');
      else if (last.selected !== current.selected && current.selected) accent('#part-focus');
      else if (last.serviceStep !== current.serviceStep || last.group !== current.group) accent('.sheet-title');
    }
    last = {page: current.page, group: current.group, selected: current.selected, serviceStep: current.serviceStep};
  });
  preference.addEventListener('change', () => {
    if (preference.matches) {
      settleIntro();
      // Cancel an in-flight native smooth scroll at its current position, too.
      window.scrollTo({top: window.scrollY, behavior: 'instant'});
      accents.forEach(effect => effect.cancel());
      accents.clear();
    }
  });
  window.AtlasStudioMotion = Object.freeze({visit, finishes, startViewer});
})();
