/* Расписание КГМУ — статичный клон (данные: kazangmu.ru / calendar.kazangmu.org) */
'use strict';

const DAY_NAMES = { 1: 'ПН', 2: 'ВТ', 3: 'СР', 4: 'ЧТ', 5: 'ПТ', 6: 'СБ', 7: 'ВС' };
const DAY_FULL = { 1: 'Понедельник', 2: 'Вторник', 3: 'Среда', 4: 'Четверг', 5: 'Пятница', 6: 'Суббота', 7: 'Воскресенье' };
const DAY_COLORS = {
  1: 'var(--mon1)', 2: 'var(--tue1)', 3: 'var(--wed1)',
  4: 'var(--thu1)', 5: 'var(--fri1)', 6: 'var(--sat1)', 7: '#ffffff'
};
const TYPE_LABEL = { lecture: 'Лекция', practice: 'Практика', cycle: 'Цикл', seminar: 'Семинар' };

const $ = (sel) => document.querySelector(sel);
const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
};

let DATA = null;
let state = { program: 0, programId: '', course: 0, group: '', view: 'grid', query: '' };

/* ---------- url ---------- */
function readUrl() {
  const p = new URLSearchParams(location.search);
  state.programId = p.get('p') || '';
  state.course = Number(p.get('c') || 0);
  state.group = p.get('g') || '';
  state.view = p.get('v') === 'days' ? 'days' : 'grid';
  state.query = p.get('q') || '';
}

function writeUrl() {
  const p = new URLSearchParams();
  p.set('p', curProgram().id);
  p.set('c', state.course);
  if (state.group) p.set('g', state.group);
  if (state.view !== 'grid') p.set('v', state.view);
  if (state.query) p.set('q', state.query);
  const url = location.pathname + '?' + p.toString();
  history.replaceState(null, '', url);
}

/* ---------- выбор ---------- */
function curProgram() { return DATA.programs[state.program] || DATA.programs[0]; }
function curCourse() {
  const p = curProgram();
  return p.courses[state.course] || p.courses[0];
}

function fillPrograms() {
  const sel = $('#selProgram');
  sel.innerHTML = '';
  DATA.programs.forEach((p, i) => {
    const o = el('option', null, `${p.code ? p.code + ' — ' : ''}${p.title}${p.form && p.form !== 'очная' ? ' (' + p.form + ')' : ''}`);
    o.value = i;
    sel.appendChild(o);
  });
  sel.value = state.program;
}

function resolveProgram() {
  if (!state.programId) return;
  const i = DATA.programs.findIndex((p) => p.id === state.programId);
  state.program = i >= 0 ? i : 0;
}

function fillCourses() {
  const sel = $('#selCourse');
  sel.innerHTML = '';
  curProgram().courses.forEach((c, i) => {
    const o = el('option', null, c.label);
    o.value = i;
    sel.appendChild(o);
  });
  sel.value = state.course;
}

function fillGroups() {
  const c = curCourse();
  const names = c.groups.map((g) => g.name);
  if (!names.includes(state.group)) state.group = names[0] || '';
  const inp = $('#inpGroup');
  inp.disabled = !names.length;
  inp.placeholder = names.length ? 'номер группы' : 'скан документа';
  const dl = $('#groupList');
  dl.innerHTML = '';
  names.forEach((n) => {
    const o = el('option');
    o.value = n;
    dl.appendChild(o);
  });
  $('#inpGroup').value = state.group;
}

/* ---------- отрисовка ---------- */
function renderMeta() {
  const p = curProgram(), c = curCourse();
  $('#docProgram').textContent = (p.code ? p.code + ' ' : '') + p.title;
  $('#docLevel').textContent = p.level || '—';
  $('#docForm').textContent = p.form || '—';
  $('#docCourse').textContent = c.label || '';
  $('#docSemester').textContent = `на ${DATA.semester} семестр ${DATA.year.replace('/', ' /')} уч.г.`;
}

function lessonGroups(l) { return l.groups && l.groups.length ? l.groups : []; }

function filterLessons(list) {
  const q = state.query.trim().toLowerCase();
  if (!q) return list;
  return list.filter((l) =>
    (l.subject || '').toLowerCase().includes(q) ||
    (l.teacher || '').toLowerCase().includes(q) ||
    (l.place || '').toLowerCase().includes(q));
}

/* --- сетка как в оригинале --- */
function renderGrid() {
  const c = curCourse();
  const host = $('#viewHost');
  host.innerHTML = '';

  let groups = c.groups.map((g) => g.name);
  const lessons = c.lessons;
  const matches = filterLessons(lessons);
  const matchIds = new Set(matches.map((m) => m));

  // строки: все встречающиеся начала занятий
  const starts = Array.from(new Set(lessons.map((l) => l.ts))).sort();
  if (!starts.length) {
    host.appendChild(el('p', 'empty', 'Для этого курса расписание пока не загружено.'));
    return;
  }
  const idx = new Map(starts.map((s, i) => [s, i]));
  // типичное время окончания для каждого начала (в сетке строки по 45 минут)
  const endByStart = new Map();
  lessons.forEach((l) => {
    if (!endByStart.has(l.ts)) endByStart.set(l.ts, new Map());
    const m = endByStart.get(l.ts);
    m.set(l.te, (m.get(l.te) || 0) + 1);
  });
  const slotEnd = (s) => {
    const m = endByStart.get(s);
    if (!m) return '';
    return Array.from(m.entries()).sort((a, b) => b[1] - a[1])[0][0];
  };
  const days = Array.from(new Set(lessons.map((l) => l.wd))).sort((a, b) => a - b);

  const narrow = window.matchMedia('(max-width: 640px)').matches;
  if (narrow && state.group && groups.includes(state.group)) groups = [state.group];
  const colOffset = narrow ? 3 : 4;   // в какой столбец начинаются группы
  const wrap = el('div', 'grid-wrap');
  const grid = el('div', 'grid');
  grid.style.gridTemplateColumns = narrow
    ? `2.4rem 2.8rem minmax(0, 1fr)`
    : `3rem 3rem 3rem repeat(${groups.length}, minmax(13rem, auto))`;
  grid.classList.toggle('narrow', narrow);

  // шапка
  const heads = narrow ? ['', ''] : ['', '', ''];
  heads.forEach((h) => grid.appendChild(el('div', 'gcell head', h)));
  const headEls = [];
  groups.forEach((g) => {
    const h = el('div', 'gcell head', g);
    headEls.push(h);
    grid.appendChild(h);
  });

  const gi0 = groups.indexOf(state.group);
  if (gi0 >= 0) headEls[gi0].classList.add('active');

  // индексы занятий по (день, группа)
  const byDayGroup = new Map();
  lessons.forEach((l) => {
    lessonGroups(l).forEach((g) => {
      const key = l.wd + '|' + g;
      if (!byDayGroup.has(key)) byDayGroup.set(key, []);
      byDayGroup.get(key).push(l);
    });
  });

  let row = 2;
  days.forEach((wd) => {
    const blockStart = row;
    starts.forEach((s, si) => {
      const t = lessons.find((l) => l.wd === wd && l.ts === s);
      const te = slotEnd(s);
      const dayCell = el('div', 'gcell day sticky-l pos-1' + (si === 0 ? '' : ' hidden-day'), DAY_NAMES[wd]);
      if (si === 0) {
        dayCell.style.gridArea = `${blockStart} / 1 / span ${starts.length}`;
        grid.appendChild(dayCell);
      }
      const c1 = el('div', 'gcell time sticky-l pos-2', s);
      c1.style.gridArea = `${row} / 2`;
      c1.style.background = DAY_COLORS[wd];
      grid.appendChild(c1);
      if (!narrow) {
        const c2 = el('div', 'gcell time sticky-l pos-3', te);
        c2.style.gridArea = `${row} / 3`;
        c2.style.background = DAY_COLORS[wd];
        grid.appendChild(c2);
      }
      row += 1;
    });

    // занятия: размещаем по колонкам групп со спаном строк
    groups.forEach((g, gi) => {
      const items = (byDayGroup.get(wd + '|' + g) || []).slice().sort((a, b) => a.ts.localeCompare(b.ts));
      const covered = new Set();
      // занятия, перекрывающиеся по времени (подгруппы), собираем в одну ячейку
      const clusters = [];
      items.forEach((l) => {
        const last = clusters[clusters.length - 1];
        if (last && l.ts < last.te) {
          last.items.push(l);
          if (l.te > last.te) last.te = l.te;
        } else {
          clusters.push({ ts: l.ts, te: l.te, items: [l] });
        }
      });
      clusters.forEach((cl) => {
        const i0 = idx.get(cl.ts);
        if (i0 == null) return;
        let span = 1;
        for (let k = i0 + 1; k < starts.length; k += 1) {
          if (starts[k] < cl.te) span += 1; else break;
        }
        for (let k = i0; k < i0 + span; k += 1) covered.add(k);
        const cell = el('div', 'glesson');
        cell.style.gridArea = `${blockStart + i0} / ${colOffset + gi} / span ${span} / span 1`;
        cell.style.background = DAY_COLORS[wd];
        cl.items.forEach((l, li) => {
          if (li) cell.appendChild(el('span', 'sep'));
          const line = el('span', 'gitem');
          if (state.query && !matchIds.has(l)) line.style.opacity = '.3';
          if (l.type && TYPE_LABEL[l.type]) {
            line.appendChild(el('span', 'lt', TYPE_LABEL[l.type] + ': '));
          }
          line.appendChild(document.createTextNode(`«${l.subject}»`));
          if (l.subgroups) line.appendChild(document.createTextNode(` (${l.subgroups})`));
          cell.appendChild(line);
          const meta = [l.teacher, l.place].filter(Boolean).join(', ');
          if (meta) cell.appendChild(el('span', 'meta', meta));
        });
        grid.appendChild(cell);
      });
      // пустые ячейки для строк без занятий
      starts.forEach((s, si) => {
        if (covered.has(si)) return;
        const empty = el('div', 'gcell', '');
        empty.style.gridArea = `${blockStart + si} / ${colOffset + gi}`;
        grid.appendChild(empty);
      });
    });
  });

  grid.style.gridTemplateRows = `auto repeat(${row - 2}, minmax(22px, auto))`;
  wrap.appendChild(grid);
  host.appendChild(wrap);
  if (gi0 >= 0 && headEls[gi0]) {
    requestAnimationFrame(() => {
      wrap.scrollLeft = Math.max(0, headEls[gi0].offsetLeft - 80);
    });
  }
}

/* --- скан официального документа --- */
function renderScans(c) {
  const host = $('#viewHost');
  host.innerHTML = '';
  const wrap = el('div', 'scans');
  c.scans.forEach((src, i) => {
    const fig = el('figure', 'scan');
    const img = document.createElement('img');
    img.loading = i ? 'lazy' : 'eager';
    img.src = src;
    img.alt = `Страница ${i + 1} расписания`;
    img.decoding = 'async';
    fig.appendChild(img);
    fig.appendChild(el('figcaption', null, `Страница ${i + 1} из ${c.scans.length}`));
    wrap.appendChild(fig);
  });
  host.appendChild(wrap);
}

/* --- цикловые занятия (4-6 курс) --- */
function renderCycles(c) {
  const host = $('#viewHost');
  host.innerHTML = '';
  const group = state.group || (c.groups[0] && c.groups[0].name);
  const list = c.cycles.filter((x) => x.group === group);
  const box = el('div', 'cycles');
  const head = el('p', 'cycles-head', `Группа ${group} · ${list.length} циклов`);
  box.appendChild(head);
  if (!list.length) {
    box.appendChild(el('p', 'empty', 'Для этой группы циклы не найдены.'));
  }
  list.forEach((cy) => {
    const card = el('div', 'cycle');
    const top = el('div', 'cycle-top');
    top.appendChild(el('span', 'cycle-subj', cy.subject));
    card.appendChild(top);
    if (cy.teacher) card.appendChild(el('div', 'cycle-meta', cy.teacher));
    if (cy.place) card.appendChild(el('div', 'cycle-meta', cy.place));
    const periods = el('div', 'cycle-periods');
    cy.periods.forEach((p) => {
      const row = el('div', 'cycle-period');
      row.appendChild(el('span', 'cp-dates', p.dates || '—'));
      if (p.start) row.appendChild(el('span', 'cp-time', `${p.start}–${p.end}`));
      if (p.hours) row.appendChild(el('span', 'cp-hours', `${p.hours} ч`));
      periods.appendChild(row);
    });
    card.appendChild(periods);
    box.appendChild(card);
  });
  host.appendChild(box);
}

/* --- карточки по дням --- */
function renderDays() {
  const c = curCourse();
  const host = $('#viewHost');
  host.innerHTML = '';
  const group = state.group;
  const days = el('div', 'days');

  const list = filterLessons(c.lessons.filter((l) => lessonGroups(l).includes(group)));
  const byDay = new Map();
  list.forEach((l) => {
    if (!byDay.has(l.wd)) byDay.set(l.wd, []);
    byDay.get(l.wd).push(l);
  });

  if (!byDay.size) {
    host.appendChild(el('p', 'empty', 'Занятий не найдено.'));
    return;
  }

  Array.from(byDay.keys()).sort((a, b) => a - b).forEach((wd) => {
    const block = el('section', 'day-block');
    const head = el('div', 'day-head');
    head.style.background = DAY_COLORS[wd];
    head.appendChild(el('span', null, DAY_FULL[wd]));
    head.appendChild(el('small', null, group ? 'группа ' + group : ''));
    block.appendChild(head);
    byDay.get(wd).sort((a, b) => a.ts.localeCompare(b.ts)).forEach((l) => {
      const row = el('div', 'lesson');
      row.appendChild(el('div', 'lesson-time', `${l.ts}–${l.te}`));
      const body = el('div', 'lesson-body');
      const subj = el('div', 'lesson-subj');
      if (l.type && TYPE_LABEL[l.type]) subj.appendChild(el('span', 'type', TYPE_LABEL[l.type]));
      subj.appendChild(document.createTextNode(l.subject));
      if (l.subgroups) subj.appendChild(el('span', 'muted', ` · подгр. ${l.subgroups}`));
      body.appendChild(subj);
      const meta = el('div', 'lesson-meta');
      if (l.teacher) meta.appendChild(el('span', null, l.teacher));
      if (l.place) meta.appendChild(el('span', null, l.place));
      if (l.teacher || l.place) body.appendChild(meta);
      row.appendChild(body);
      block.appendChild(row);
    });
    days.appendChild(block);
  });
  host.appendChild(days);
}

function render() {
  const p = curProgram();
  renderMeta();
  $('#viewToggle').textContent = state.view === 'grid' ? 'Сетка' : 'Дни';
  $('#viewToggle').disabled = !!(curCourse().cycles || (curCourse().scans && !curCourse().lessons.length));
  const c = curCourse();
  if (c.cycles && !c.lessons.length) {
    renderCycles(c);
    $('#docNote').textContent = `Цикловые занятия · ${c.groups.length} групп · источник: официальный сайт КГМУ`;
    writeUrl();
    return;
  }
  if (c.scans && !c.lessons.length) {
    renderScans(c);
    $('#docNote').textContent = `Официальный документ (${c.scans.length} стр.) · скан с сайта КГМУ`;
    writeUrl();
    return;
  }
  if (state.view === 'grid') renderGrid(); else renderDays();
  const n = c.lessons.length;
  const who = state.view === 'grid' ? `${c.groups.length} групп` : `группа ${state.group}`;
  $('#docNote').textContent = `${who} · ${n} занятий в недельном цикле · источник: официальный сайт КГМУ`;
  writeUrl();
}

/* ---------- события ---------- */
function bind() {
  $('#selProgram').addEventListener('change', (e) => {
    state.program = Number(e.target.value);
    state.course = 0;
    state.group = '';
    fillCourses(); fillGroups(); render();
  });
  $('#selCourse').addEventListener('change', (e) => {
    state.course = Number(e.target.value);
    state.group = '';
    fillGroups(); render();
  });
  $('#inpGroup').addEventListener('input', (e) => {
    state.group = e.target.value.trim();
    render();
  });
  $('#inpSearch').addEventListener('input', (e) => {
    state.query = e.target.value;
    render();
  });
  $('#viewToggle').addEventListener('click', () => {
    state.view = state.view === 'grid' ? 'days' : 'grid';
    render();
  });
  $('#themeToggle').addEventListener('click', () => {
    const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem('kgmu_theme', next); } catch (e) { /* ignore */ }
  });
}

async function boot() {
  readUrl();
  if (!new URLSearchParams(location.search).has('v') && window.matchMedia('(max-width: 640px)').matches) {
    state.view = 'days';
  }
  try { document.documentElement.dataset.theme = localStorage.getItem('kgmu_theme') || 'light'; } catch (e) { /* ignore */ }
  const res = await fetch('data/schedule.json', { cache: 'no-cache' });
  DATA = await res.json();
  resolveProgram();
  if (state.program >= DATA.programs.length) state.program = 0;
  if (state.course >= curProgram().courses.length) state.course = 0;
  fillPrograms(); fillCourses(); fillGroups();
  $('#inpSearch').value = state.query;
  $('#stampDate').textContent = DATA.generated;
  bind();
  render();
}

boot().catch((e) => {
  $('#viewHost').innerHTML = '<p class="empty">Не удалось загрузить данные расписания: ' + e.message + '</p>';
  console.error(e);
});
