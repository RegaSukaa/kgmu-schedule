// Самопроверка страницы: метрики вёрстки печатаются в <pre>SELFTEST_JSON:....
(function () {
  function run() {
    const out = { errors: [], overflowX: null, lessons: 0, overflowing: [], overlaps: [], scroll: {} };
    const host = document.getElementById('viewHost');
    out.overflowX = document.documentElement.scrollWidth - window.innerWidth;
    out.viewport = { w: window.innerWidth, h: window.innerHeight };

    const cells = Array.from(document.querySelectorAll('.glesson'));
    out.lessons = cells.length;

    // 1) текст не влезает в свою ячейку
    cells.forEach((c) => {
      if (c.scrollHeight > c.clientHeight + 2 || c.scrollWidth > c.clientWidth + 2) {
        out.overflowing.push({
          text: c.textContent.slice(0, 60),
          clientH: c.clientHeight, scrollH: c.scrollHeight,
          clientW: c.clientWidth, scrollW: c.scrollWidth,
        });
      }
    });

    // 2) пересечения ячеек внутри одной колонки
    const byCol = {};
    cells.forEach((c) => {
      const col = c.style.gridColumnStart || '';
      (byCol[col] = byCol[col] || []).push({ r: c.getBoundingClientRect(), t: c.textContent.slice(0, 70) });
    });
    Object.entries(byCol).forEach(([col, rects]) => {
      for (let i = 0; i < rects.length; i += 1) {
        for (let j = i + 1; j < rects.length; j += 1) {
          const a = rects[i].r, b = rects[j].r;
          const ox = Math.min(a.right, b.right) - Math.max(a.left, b.left);
          const oy = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
          if (ox > 1 && oy > 1) out.overlaps.push({ col, ox: Math.round(ox), oy: Math.round(oy), a: rects[i].t, b: rects[j].t });
        }
      }
    });

    // 3) прокрутка контейнера сетки
    const wrap = document.querySelector('.grid-wrap');
    if (wrap) {
      out.scroll.gridWidth = wrap.scrollWidth;
      out.scroll.wrapWidth = wrap.clientWidth;
      out.scroll.rows = document.querySelectorAll('.grid > *').length;
    }
    // 4) сколько ячеек-заголовков групп
    out.headers = Array.from(document.querySelectorAll('.gcell.head')).map((h) => h.textContent);

    const pre = document.createElement('pre');
    pre.textContent = 'SELFTEST_' + 'JSON:' + JSON.stringify(out);
    document.body.appendChild(pre);
  }
  window.addEventListener('error', (e) => {
    const pre = document.createElement('pre');
    pre.textContent = 'SELFTEST_' + 'JSON:' + JSON.stringify({ jsError: String(e.message) });
    document.body.appendChild(pre);
  });
  setTimeout(run, 2200);
})();
