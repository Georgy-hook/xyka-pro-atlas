/* Canvas-only touch grammar. OrbitControls still owns the camera math, mouse and wheel. */
(() => {
  'use strict';

  function bind(canvas, {pick, orbit, magnification, zoomBy, setMoving}) {
    const contacts = new Map();
    let tap = null;
    let pinch = null;

    function span() {
      const [a, b] = contacts.values();
      // Nearly coincident contacts (also while crossing) aren't a meaningful ruler.
      return Math.max(16, Math.hypot(a.x - b.x, a.y - b.y));
    }

    function rebase() {
      pinch = contacts.size === 2 ? {span: span(), zoom: magnification()} : null;
      if (!contacts.size) setMoving(false);
    }

    function down(event) {
      canvas.setPointerCapture(event.pointerId);
      contacts.set(event.pointerId, {x: event.clientX, y: event.clientY});
      tap = contacts.size === 1 && event.isPrimary
        ? {x: event.clientX, y: event.clientY, start: event.timeStamp} : null;
      rebase();
    }

    function move(event) {
      const p = contacts.get(event.pointerId);
      if (!p) return;
      const previousX = p.x;
      const previousY = p.y;
      p.x = event.clientX;
      p.y = event.clientY;

      if (pinch) {
        if (p.x === previousX && p.y === previousY) return;
        // Absolute ratio from the start of THIS pair, not compounded per event.
        // Translating the centroid doesn't pan the CAD target. Lift/replant to zoom further.
        const ratio = Math.max(0.25, Math.min(4, span() / pinch.span));
        const factor = pinch.zoom * ratio / magnification();
        if (Math.abs(factor - 1) > 1e-8) {
          setMoving(true);
          zoomBy(factor);
        }
      } else if (contacts.size === 1) {
        let dx = p.x - previousX;
        let dy = p.y - previousY;
        if (tap) {
          // A little resting tremor can pick, but never both pick AND orbit. On
          // crossing the 3 CSS-pixel radius apply the whole stroke, including its start.
          const outside = sample => Math.hypot(sample.clientX - tap.x, sample.clientY - tap.y) > 3;
          if (!outside(event) && !event.getCoalescedEvents?.().some(outside)) return;
          dx = p.x - tap.x;
          dy = p.y - tap.y;
          tap = null;
        }
        if (dx || dy) {
          setMoving(true);
          orbit(dx, dy);
        }
      }
      // Three or more fingers suspend the gesture; returning to two starts a new pair.
    }

    function end(event) {
      if (!contacts.has(event.pointerId)) return;
      // Consume the lift position too: a browser need not deliver a final pointermove.
      if (event.type === 'pointerup') move(event);
      const hit = event.type === 'pointerup' && tap && event.timeStamp - tap.start <= 500;
      contacts.delete(event.pointerId);
      tap = null;  // A finger left over after a pinch may orbit, but cannot tap.
      rebase();
      if (hit) pick(event);
    }

    function reset() {
      for (const id of contacts.keys()) {
        if (canvas.hasPointerCapture(id)) canvas.releasePointerCapture(id);
      }
      contacts.clear();
      tap = null;
      rebase();
    }

    function handle(event) {
      if (event.pointerType !== 'touch') return;
      // Capture phase: exactly one interpreter for a canvas touch. Don't intercept
      // mouse, pen, wheel, document scrolling or gestures starting outside the canvas.
      event.stopPropagation();
      if (event.type === 'pointerdown') down(event);
      else if (event.type === 'pointermove') move(event);
      else end(event);
    }

    const events = ['pointerdown', 'pointermove', 'pointerup', 'pointercancel', 'lostpointercapture'];
    for (const type of events) canvas.addEventListener(type, handle, true);
    window.addEventListener('blur', reset);
    window.addEventListener('pagehide', reset);
    return {
      reset,
      dispose() {
        for (const type of events) canvas.removeEventListener(type, handle, true);
        window.removeEventListener('blur', reset);
        window.removeEventListener('pagehide', reset);
        reset();
      },
    };
  }

  window.AtlasViewportTouch = Object.freeze({bind});
})();
