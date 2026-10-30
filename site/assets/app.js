/* Расписание КГМУ — поиск по группе и датам */
'use strict';

const MONTHS = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля',
  'августа', 'сентября', 'октября', 'ноября', 'декабря'];
const WEEKDAYS = ['воскресенье', 'понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота'];
const TYPE_LABEL = { lecture: 'Лекция', practice: 'Практика', cycle: 'Цикл', seminar: 'Семинар', exam: 'Экзамен' };
const TEACHER_PREFIX = {
  'доц.': 'Доцент', 'проф.': 'Профессор', 'асс.': 'Ассистент', 'ст.преп.': 'Ст. преподаватель',
  'ст. преп.': 'Ст. преподаватель', 'преп.': 'Преподаватель', 'доцент': 'Доцент',
};

const $ = (s) => document.querySelector(s);
const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
};

let INDEX = null;           // {groups: [...], scans: {...}, generated}
let GROUPS = [];            // [{n, prog, code, course, form}]
let cache = {};             // имя группы -> данные
let activeIdx = -1;

/* ---------- утилиты дат ---------- */
function iso(d) {
  const z = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())}`;
}
function parseIso(s) {
  const [y, m, d] = s.split('-').map(Number);
  return new Date(y, m - 1, d);
}
function fmtLong(d) {
  const wd = WEEKDAYS[d.getDay()];
  const wdCap = wd.charAt(0).toUpperCase() + wd.slice(1);
  return `${wdCap}, ${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()} г.`;
}
function fmtShort(d) {
  return `${String(d.getDate()).padStart(2, '0')}.${String(d.getMonth() + 1).padStart(2, '0')}.${d.getFullYear()}`;
}
function mondayOf(d) {
  const x = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const wd = x.getDay() === 0 ? 7 : x.getDay();
  x.setDate(x.getDate() - (wd - 1));
  return x;
}
function eachDate(from, to, limit = 400) {
  const out = [];
  const cur = new Date(from.getFullYear(), from.getMonth(), from.getDate());
  while (cur <= to && out.length < limit) {
    out.push(new Date(cur));
    cur.setDate(cur.getDate() + 1);
  }
  return out;
}

/* ---------- данные ---------- */
async function loadIndex() {
  const r = await fetch('data/index.json', { cache: 'no-cache' });
  INDEX = await r.json();
  GROUPS = INDEX.groups || [];
  $('#yearLabel').textContent = INDEX.year || '2026/2027';
  $('#stamp').textContent = INDEX.generated || '—';
}

async function loadGroup(name) {
  if (cache[name]) return cache[name];
  const r = await fetch('data/g/' + encodeURIComponent(name) + '.json', { cache: 'no-cache' });
  if (!r.ok) throw new Error('нет данных для группы ' + name);
  const d = await r.json();
  cache[name] = d;
  return d;
}

/* ---------- группа: выпадающий список ---------- */
const drop = () => $('#groupDrop');
const input = () => $('#groupInput');

function groupSub(g) {
  const bits = [];
  if (g.prog) bits.push(g.prog);
  if (g.course) bits.push(g.course + ' курс');
  return bits.join(' · ');
}

function openDrop(query) {
  const q = (query || '').trim().toLowerCase();
  const list = q ? GROUPS.filter((g) => g.n.toLowerCase().includes(q)) : GROUPS;
  const box = drop();
  box.innerHTML = '';
  activeIdx = -1;
  if (!list.length) {
    box.appendChild(el('div', 'combo-empty', 'Группа не найдена'));
  } else {
    list.slice(0, 80).forEach((g, i) => {
      const item = el('div', 'combo-item');
      item.setAttribute('role', 'option');
      item.dataset.name = g.n;
      item.appendChild(el('span', null, g.n));
      item.appendChild(el('small', null, groupSub(g)));
      item.addEventListener('mousedown', (e) => { e.preventDefault(); pickGroup(g.n); });
      if (i === 0) activeIdx = 0;
      box.appendChild(item);
    });
  }
  box.hidden = false;
  input().setAttribute('aria-expanded', 'true');
}

function closeDrop() {
  drop().hidden = true;
  input().setAttribute('aria-expanded', 'false');
}

function pickGroup(name) {
  input().value = name;
  closeDrop();
  updateHint();
}

function updateHint() {
  const name = input().value.trim();
  const g = GROUPS.find((x) => x.n === name);
  const hint = $('#groupHint');
  if (!name) { hint.textContent = ''; return; }
  if (g) {
    hint.textContent = [g.code, g.prog, g.course ? g.course + ' курс' : '', g.form && g.form !== 'очная' ? g.form : '']
      .filter(Boolean).join(' · ');
  } else {
    hint.textContent = 'такой группы нет в базе';
  }
}

/* ---------- расчёт расписания ---------- */
const SEMESTER_WEEK1 = new Date(2026, 7, 31);   // понедельник недели, в которую попадает 1 сентября 2026

function weekNo(date) {
  const d0 = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  return Math.floor((d0 - SEMESTER_WEEK1) / (7 * 864e5)) + 1;
}

function preprocess(payload) {
  const byWd = {};
  (payload.lessons || []).forEach((l) => {
    (byWd[l.wd] = byWd[l.wd] || []).push(l);
  });
  Object.values(byWd).forEach((arr) => arr.sort((a, b) => a.ts.localeCompare(b.ts)));
  const weeks = payload.weeks || {};
  const byWeek = {};
  Object.keys(weeks).forEach((w) => {
    const arr = (weeks[w] || []).slice().sort((a, b) => a.ts.localeCompare(b.ts));
    byWeek[w] = arr;
  });
  const dated = {};
  (payload.dated || []).forEach((l) => {
    (dated[l.d] = dated[l.d] || []).push(l);
  });
  Object.values(dated).forEach((arr) => arr.sort((a, b) => a.ts.localeCompare(b.ts)));
  return { byWd, cycles: payload.cycles || [], byWeek,
           hasWeeks: Object.keys(byWeek).length > 0, dated };
}

function cyclesOn(date, cycles) {
  const key = iso(date);
  const out = [];
  cycles.forEach((c) => {
    c.periods.forEach((p) => {
      if (key >= p.from && key <= p.to) {
        out.push({
          ts: p.ts, te: p.te, type: 'cycle', subject: c.subject,
          teacher: c.teacher, place: c.place, sub: '', hours: p.hours,
        });
      }
    });
  });
  return out;
}

/* Скобки у занятия — диапазон учебных недель: «(2-10)» = со 2-й по 10-ю неделю,
   «(2,4,6,8,10)» = только эти недели. Неделя 1 — та, в которую попало 1 сентября 2026. */
function weekSpans(sub) {
  const s = String(sub || '').replace(/\s+/g, '');
  if (!s || !/^\d+(-\d+)?(,\d+(-\d+)?)*$/.test(s)) return null;
  return s.split(',').map((part) => {
    const [a, b] = part.split('-').map(Number);
    return [a, b === undefined ? a : b];
  });
}

function inWeek(sub, week) {
  const spans = weekSpans(sub);
  if (!spans) return true;
  return spans.some(([a, b]) => week >= a && week <= b);
}

function dayLessons(date, data) {
  const wd = date.getDay() === 0 ? 7 : date.getDay();
  const day = data.dated[iso(date)];
  if (day) return day;
  if (data.hasWeeks) {
    const arr = data.byWeek[String(weekNo(date))] || [];
    return arr.filter((l) => l.wd === wd);
  }
  const wk = weekNo(date);
  const base = (data.byWd[wd] || []).filter((l) => inWeek(l.sub, wk));
  const cyc = cyclesOn(date, data.cycles);
  if (!cyc.length) return base;
  // во время цикла практические занятия группы не идут — остаются лекции
  const cycTimes = new Set(cyc.map((c) => c.ts));
  const kept = base.filter((l) => l.type === 'lecture' || !cycTimes.has(l.ts));
  return kept.concat(cyc).sort((a, b) => a.ts.localeCompare(b.ts));
}

/* ---------- вывод ---------- */

function prettifyTeacher(t) {
  const s = (t || '').trim();
  if (!s) return '';
  for (const [k, v] of Object.entries(TEACHER_PREFIX)) {
    if (s.toLowerCase().startsWith(k)) {
      return v + ' ' + s.slice(k.length).trim();
    }
  }
  return s;
}

function renderLesson(l) {
  const box = el('div', 'lesson');
  const row = el('div', 'lesson-row');
  row.appendChild(el('span', 'time-chip', `${l.ts}–${l.te || ''}`));
  if (l.type && TYPE_LABEL[l.type]) {
    row.appendChild(el('span', 'type-chip', TYPE_LABEL[l.type]));
  }
  if (l.hours) row.appendChild(el('span', 'cycle-chip', `${l.hours} ч`));
  box.appendChild(row);
  if (l.place) box.appendChild(el('div', 'lesson-place', l.place));
  box.appendChild(el('div', 'lesson-subject', l.subject || ''));
  const t = prettifyTeacher(l.teacher);
  if (t) box.appendChild(el('div', 'lesson-teacher', t));
  return box;
}

function renderDays(dates, data) {
  const host = $('#results');
  host.innerHTML = '';
  const today = iso(new Date());
  let total = 0;
  dates.forEach((d) => {
    if (d.getDay() === 0) return;              // воскресенье пропускаем
    const lessons = dayLessons(d, data);
    const block = el('section', 'day');
    const h = el('h2', 'day-title', fmtLong(d));
    const wn = weekNo(d);
    if (wn >= 1) h.appendChild(el('span', 'week-note', `${wn}-я учебная неделя`));
    if (iso(d) === today) h.appendChild(el('span', 'today', 'сегодня'));
    block.appendChild(h);
    if (!lessons.length) {
      block.appendChild(el('div', 'no-lessons', 'Занятий нет'));
    } else {
      lessons.forEach((l) => block.appendChild(renderLesson(l)));
      total += lessons.length;
    }
    host.appendChild(block);
  });
  return total;
}

/* ---------- поиск ---------- */
async function doSearch(push) {
  const name = input().value.trim();
  const from = parseIso($('#dateFrom').value);
  const to = parseIso($('#dateTo').value);
  const host = $('#results');
  if (!name) {
    host.innerHTML = '';
    host.appendChild(el('div', 'empty-state', 'Выберите группу из списка и нажмите «Поиск».'));
    return;
  }
  if (!(from instanceof Date) || isNaN(from) || !(to instanceof Date) || isNaN(to) || to < from) {
    host.innerHTML = '';
    host.appendChild(el('div', 'empty-state', 'Проверьте даты: начало периода должно быть раньше конца.'));
    return;
  }
  if (to - from > 1000 * 60 * 60 * 24 * 120) {
    host.innerHTML = '';
    host.appendChild(el('div', 'empty-state', 'Слишком большой период — выберите не больше 4 месяцев.'));
    return;
  }
  const btn = $('#searchBtn');
  btn.disabled = true;
  host.innerHTML = '';
  host.appendChild(el('div', 'empty-state', 'Загрузка…'));
  try {
    rememberGroup(name);
    const payload = await loadGroup(name);
    const data = preprocess(payload);
    const dates = eachDate(from, to);
    host.innerHTML = '';
    const head = el('div', 'result-head');
    head.innerHTML = '';
    head.appendChild(el('b', null, `Группа ${name}`));
    head.appendChild(document.createTextNode(
      ` · ${payload.prog || ''}${payload.course ? ', ' + payload.course + ' курс' : ''} · ` +
      `${fmtShort(from)} — ${fmtShort(to)}`));
    host.appendChild(head);
    const total = renderDays(dates, data);
    if (!total && payload.period && payload.period.length === 2) {
      const a = payload.period[0].split('-'), b = payload.period[1].split('-');
      const box = el('div', 'empty-state');
      box.appendChild(document.createTextNode(
        `У группы ${name} занятия идут сессией: ${a[2]}.${a[1]}.${a[0]} — ${b[2]}.${b[1]}.${b[0]}. `));
      const btn = el('button', 'chip-btn', 'показать сессию');
      btn.type = 'button';
      btn.addEventListener('click', () => {
        $('#dateFrom').value = payload.period[0];
        $('#dateTo').value = payload.period[1];
        doSearch(true);
      });
      box.appendChild(btn);
      host.appendChild(box);
      return;
    }
    if (!total) {
      const none = el('div', 'empty-state',
        'На этот период занятий в базе нет. Проверьте даты: база содержит осенний семестр 2026/2027.');
      host.appendChild(none);
    }
    if (push && window.matchMedia('(max-width: 760px)').matches) {
      const top = host.getBoundingClientRect().top + window.scrollY - 8;
      window.scrollTo({ top, behavior: 'smooth' });
    }
    if (push) {
      const p = new URLSearchParams();
      p.set('g', name);
      p.set('from', iso(from));
      p.set('to', iso(to));
      history.replaceState(null, '', location.pathname + '?' + p.toString());
    }
  } catch (e) {
    host.innerHTML = '';
    host.appendChild(el('div', 'empty-state', 'Не удалось загрузить расписание этой группы.'));
    console.error(e);
  } finally {
    btn.disabled = false;
  }
}

/* ---------- пресеты дат ---------- */
function markPreset(kind) {
  document.querySelectorAll('[data-preset]').forEach((b) => {
    b.classList.toggle('active', b.dataset.preset === kind);
  });
}

function setPreset(kind) {
  markPreset(kind);
  const now = new Date();
  let from, to;
  if (kind === 'current') {
    // с сегодняшнего дня до конца текущей недели (воскресенья)
    from = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const mon = mondayOf(now);
    to = new Date(mon.getFullYear(), mon.getMonth(), mon.getDate() + 6);
  } else if (kind === 'week') {
    from = mondayOf(now);
    to = new Date(from.getFullYear(), from.getMonth(), from.getDate() + 6);
  } else if (kind === 'next') {
    from = new Date(mondayOf(now).getTime() + 7 * 864e5);
    to = new Date(from.getFullYear(), from.getMonth(), from.getDate() + 6);
  } else {
    from = new Date(now.getFullYear(), now.getMonth(), 1);
    to = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  }
  $('#dateFrom').value = iso(from);
  $('#dateTo').value = iso(to);
  markPreset(kind);
}

/* ---------- сканы ---------- */
function renderScans() {
  const host = $('#results');
  host.innerHTML = '';
  const scans = (INDEX && INDEX.scans) || {};
  const keys = Object.keys(scans);
  if (!keys.length) {
    host.appendChild(el('div', 'empty-state', 'Сканов нет.'));
    return;
  }
  const head = el('div', 'result-head', 'Сканы официальных документов (заочные и магистерские направления)');
  host.appendChild(head);
  const list = el('div', 'scans-list');
  keys.forEach((k) => {
    const s = scans[k];
    const card = el('div', 'scan-card');
    card.appendChild(el('h3', null, s.label ? s.label : k));
    card.appendChild(el('p', null, `${s.status ? 'Страниц: ' + s.pages_count : ''}`.trim() || `Страниц: ${s.pages_count}`));
    const link = el('a', null, 'открыть скан');
    link.href = '#';
    link.addEventListener('click', (e) => { e.preventDefault(); showScan(s); });
    card.appendChild(link);
    list.appendChild(card);
  });
  host.appendChild(list);
}

function showScan(s) {
  const host = $('#results');
  host.innerHTML = '';
  const back = el('button', 'chip-btn', '← назад к списку');
  back.type = 'button';
  back.addEventListener('click', renderScans);
  host.appendChild(back);
  const box = el('div', 'scans-view');
  (s.pages || []).forEach((src, i) => {
    const img = document.createElement('img');
    img.loading = i ? 'lazy' : 'eager';
    img.src = src;
    img.alt = `Страница ${i + 1}`;
    box.appendChild(img);
  });
  host.appendChild(box);
}

/* ---------- запуск ---------- */
function bind() {
  const inp = input();
  // если в поле уже стоит существующая группа — показываем полный список, а не фильтр по ней
  const scopeQuery = () => {
    const v = inp.value.trim();
    return GROUPS.some((g) => g.n === v) ? '' : v;
  };
  inp.addEventListener('focus', () => openDrop(scopeQuery()));
  inp.addEventListener('click', () => openDrop(scopeQuery()));
  inp.addEventListener('input', () => { updateHint(); openDrop(inp.value); });
  inp.addEventListener('keydown', (e) => {
    const items = Array.from(drop().querySelectorAll('.combo-item'));
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      if (!items.length) return;
      const dir = e.key === 'ArrowDown' ? 1 : -1;
      activeIdx = Math.max(0, Math.min(items.length - 1, activeIdx + dir));
      items.forEach((it, i) => it.classList.toggle('active', i === activeIdx));
      items[activeIdx].scrollIntoView({ block: 'nearest' });
    } else if (e.key === 'Enter') {
      if (!drop().hidden && items[activeIdx]) {
        e.preventDefault();
        pickGroup(items[activeIdx].dataset.name);
      }
    } else if (e.key === 'Escape') {
      closeDrop();
    }
  });
  $('#groupToggle').addEventListener('click', () => {
    if (drop().hidden) openDrop(''); else closeDrop();
    inp.focus();
  });
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.group-field')) closeDrop();
  });
  document.querySelectorAll('[data-preset]').forEach((b) => {
    b.addEventListener('click', () => setPreset(b.dataset.preset));
  });
  $('#searchForm').addEventListener('submit', (e) => { e.preventDefault(); doSearch(true); });
  $('#scansLink').addEventListener('click', (e) => { e.preventDefault(); renderScans(); });
}

function savedGroup() {
  try { return localStorage.getItem('kgmu_group') || ''; } catch (e) { return ''; }
}

function rememberGroup(name) {
  try { localStorage.setItem('kgmu_group', name); } catch (e) { /* ignore */ }
}

async function boot() {
  await loadIndex();
  bind();
  setPreset('current');                     // по умолчанию: с сегодня до конца недели
  const p = new URLSearchParams(location.search);
  const from = p.get('from');
  const to = p.get('to');
  if (from) $('#dateFrom').value = from;
  if (to) $('#dateTo').value = to;
  const g = p.get('g') || savedGroup();
  if (g) {
    input().value = g;
    updateHint();
    await doSearch(false);
  } else {
    $('#results').appendChild(el('div', 'empty-state',
      'Выберите группу — например, 1206 — и нажмите «Поиск».'));
  }
}

boot().catch((e) => {
  console.error(e);
  const host = $('#results');
  host.innerHTML = '';
  host.appendChild(el('div', 'empty-state', 'Не удалось загрузить список групп: ' + e.message));
});
