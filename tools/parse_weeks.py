"""Разбор файлов «подробное расписание группы по неделям» (листы «N неделя»)."""
import json
import os
import re
import sys
import warnings

import openpyxl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_xlsx import split_top, parse_cell  # noqa: E402

warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "data", "parsed_weeks")
DAYS = {"ПН": 1, "ВТ": 2, "СР": 3, "ЧТ": 4, "ПТ": 5, "СБ": 6, "ВС": 7}


TEACH_RE = re.compile(
    r"((?:асс\.|доц\.|проф\.|ст\.\s?преп\.|преп\.)\s*[А-ЯЁ][а-яёА-ЯЁ\-]+(?:\s+[А-ЯЁ]\.\s*[А-ЯЁ]\.)?)\s*$")
PLACE_RE = re.compile(r"\(([^()]*(?:каф\.|ауд\.|корпус|этаж)[^()]*)\)")
KIND_RE = re.compile(r"^\s*(Лекция|Практика|Цикл|Семинар)\s*:\s*", re.I)
TYPES = {"лекция": "lecture", "практика": "practice", "цикл": "cycle", "семинар": "seminar"}


def split_week_text(txt):
    """«Тема (2-16) (Кафедра …, ауд. 515) асс. Хайруллин Р.М.» -> поля занятия."""
    kind = None
    m = KIND_RE.match(txt)
    if m:
        kind = TYPES[m.group(1).lower()]
        txt = txt[m.end():]
    # срезаем хвостовые скобки (адрес, кафедра, подгруппы)
    parts = []
    for _ in range(4):
        m = re.search(r"\(([^()]*)\)\s*$", txt)
        if not m:
            break
        parts.append(m.group(1).strip())
        txt = txt[:m.start()].strip(" ,;–—-")
    place = ", ".join(p for p in parts if re.search(r"ауд\.|каф\.|этаж|корпус|зал|НУК|УЛК|ГУК|ОСЦ|Маяковск|Бутлеров|Университетск", p))
    teacher = ""
    m = TEACH_RE.search(txt)
    if m:
        teacher = m.group(1).strip()
        txt = txt[:m.start()].strip(" ,;")
    subgroups = ""
    m = re.search(r"\((\d[\d,\s\-–—]*)\)\s*$", txt)
    if m:
        subgroups = m.group(1).strip()
        txt = txt[:m.start()].strip()
    return {"type": kind, "subject": txt.strip(" ,;"), "subgroups": subgroups,
            "teacher": teacher, "place": place}


def parse_file(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    meta = {"direction": "", "course": None, "group": ""}
    weeks = {}
    for ws in wb.worksheets:
        m = re.search(r"(\d+)", ws.title)
        if not m:
            continue
        week_no = int(m.group(1))
        grid = {}
        for row in ws.iter_rows():
            for c in row:
                if c.value not in (None, ""):
                    grid[(c.row, c.column)] = c.value
        # метаданные
        for r in range(1, 15):
            for c in range(1, 5):
                v = grid.get((r, c))
                if not isinstance(v, str):
                    continue
                low = v.lower()
                if low.startswith("направление"):
                    meta["direction"] = re.sub(r"^[^:]*:\s*", "", v).strip()
                    nxt = grid.get((r, c + 1)) or grid.get((r, c + 2))
                    if isinstance(nxt, str) and nxt.strip():
                        meta["direction"] = nxt.strip()
                elif low == "курс" and isinstance(grid.get((r, c - 1)), int):
                    meta["course"] = grid[(r, c - 1)]
        # группа — первая непустая ячейка в строке 11-13 после колонки C
        for r in range(10, 14):
            for c in range(3, 6):
                v = grid.get((r, c))
                if isinstance(v, str) and re.fullmatch(r"\d{4}[а-я]?", v.strip()):
                    meta["group"] = v.strip()
                    break
            if meta["group"]:
                break

        lessons = []
        for r in range(1, ws.max_row + 1):
            day = grid.get((r, 1))
            if not isinstance(day, str) or day.strip().upper() not in DAYS:
                continue
            start = grid.get((r, 2))
            end = grid.get((r, 3))
            val = grid.get((r, 4))
            if hasattr(start, "strftime"):
                start = start.strftime("%H:%M")
            if hasattr(end, "strftime"):
                end = end.strftime("%H:%M")
            if not isinstance(start, str) or not val:
                continue
            txt = " ".join(str(val).split())
            if not txt:
                continue
            parsed = split_week_text(txt)
            lessons.append(dict(parsed, wd=DAYS[day.strip().upper()], ts=start[:5], te=(end or "")[:5]))
        if lessons:
            weeks[week_no] = lessons
    return {"meta": meta, "weeks": weeks}


def main():
    os.makedirs(OUT, exist_ok=True)
    man = json.load(open(os.path.join(ROOT, "data", "manifest.json"), encoding="utf-8"))
    n = 0
    for m in man:
        key = m["key"]
        if not re.search(r"__(1\d{3}|2\d{3}|3\d{3})$", key):
            continue
        data = parse_file(os.path.join(RAW, m["file"]))
        if not data["weeks"]:
            print("пропуск (нет недель):", key)
            continue
        data["key"] = key
        base = key.split("__")[0]
        data["group"] = data["meta"]["group"] or key.split("__")[-1]
        json.dump(data, open(os.path.join(OUT, key + ".json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        n += 1
        print(key, "группа", data["group"], "недель:", len(data["weeks"]),
              "занятий:", sum(len(v) for v in data["weeks"].values()))
    print("готово:", n)


if __name__ == "__main__":
    sys.exit(main())
