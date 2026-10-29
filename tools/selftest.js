// Самопроверка нового интерфейса: выбор группы, поиск, метрики вёрстки.
(function () {
  const out = { errors: [], steps: [] };
  window.addEventListener('error', (e) => out.errors.push(String(e.message)));

  function rect(el) { const r = el.getBoundingClientRect(); return { w: Math.round(r.width), h: Math.round(r.height) }; }

  async function run() {
    const d = document;
    out.groups = (await (await fetch('data/index.json')).json()).groups.length;
    out.overflowX = d.documentElement.scrollWidth - window.innerWidth;

    // 1) имитируем ввод группы
    const inp = d.getElementById('groupInput');
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(inp, '1401');
    inp.dispatchEvent(new Event('input', { bubbles: true }));
    await new Promise((r) => setTimeout(r, 400));
    out.steps.push({ step: 'drop-open', items: d.querySelectorAll('.combo-item').length });
    const first = d.querySelector('.combo-item');
    if (first) first.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
    await new Promise((r) => setTimeout(r, 200));
    out.steps.push({ step: 'picked', value: inp.value });

    // 2) даты + поиск
    d.getElementById('dateFrom').value = '2026-10-05';
    d.getElementById('dateTo').value = '2026-10-08';
    d.getElementById('searchForm').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    await new Promise((r) => setTimeout(r, 1500));

    const lessons = Array.from(d.querySelectorAll('.lesson'));
    const days = Array.from(d.querySelectorAll('.day'));
    out.lessons = lessons.length;
    out.days = days.length;
    out.dayTitles = days.map((x) => x.querySelector('.day-title').textContent.trim());
    out.sample = lessons.slice(0, 3).map((x) => x.textContent.replace(/\s+/g, ' ').trim().slice(0, 120));

    // 3) переполнения внутри карточек и мелкие элементы
    out.overflowing = lessons.filter((x) => x.scrollWidth > x.clientWidth + 2).length;
    out.smallTargets = Array.from(d.querySelectorAll('button'))
      .filter((b) => b.offsetParent && rect(b).h < 32 && !b.classList.contains('chip-btn')).length;

    // 4) габариты
    out.viewport = { w: window.innerWidth, h: window.innerHeight };
    out.headOverflow = d.querySelector('.site-head').scrollWidth > window.innerWidth + 2;

    const pre = d.createElement('pre');
    pre.textContent = 'SELFTEST_' + 'JSON:' + JSON.stringify(out);
    d.body.appendChild(pre);
  }

  setTimeout(() => { run().catch((e) => out.errors.push('run: ' + e.message)); }, 900);
})();
