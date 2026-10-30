"""Сборка данных для нового сайта: индекс групп + расписание на каждую группу."""
import json
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "site", "data")

LT = {102: "lecture", 103: "practice", 104: "cycle"}
BASE = {
    "lechebnoe-delo": ("31.05.01", "Лечебное дело"),
    "pediatriya": ("31.05.02", "Педиатрия"),
    "stomatologiya": ("31.05.03", "Стоматология"),
    "mediko-profilakticheskoe-delo": ("32.05.01", "Медико-профилактическое дело"),
    "farmaciya": ("33.05.01", "Фармация"),
}


def split_direction(s):
    m = re.match(r"^\s*(\d{2}\.\d{2}\.\d{2})\s+(.+)$", s or "")
    if m:
        return m.group(1), m.group(2).strip()
    return "", (s or "").strip()


def main():
    os.makedirs(os.path.join(OUT, "g"), exist_ok=True)
    man = json.load(open(os.path.join(DATA, "manifest.json"), encoding="utf-8"))

    groups = {}          # имя группы -> {"prog","code","course","form","faculty"}

    def reg_group(name, code, prog, course, form, faculty=""):
        g = groups.setdefault(name, {"n": name, "code": code, "prog": prog, "course": course,
                                     "form": form, "faculty": faculty})
        if course and not g.get("course"):
            g["course"] = course
        return g

    templates = {}       # имя группы -> список занятий
    cycles = {}          # имя группы -> список циклов

    def add_lesson(group, lesson):
        templates.setdefault(group, []).append(lesson)

    # 1) JSON с calendar.kazangmu.org (уже с готовыми занятиями)
    for m in man:
        if not m["file"].endswith(".json"):
            continue
        d = json.load(open(os.path.join(DATA, "raw", m["file"]), encoding="utf-8"))
        code, title = split_direction(d.get("info", {}).get("name", ""))
        crs = (d.get("groups") or [{}])[0].get("crs") or 0
        fac = (d.get("groups") or [{}])[0].get("dep", "")
        form = {5: "очная", 6: "очно-заочная", 7: "заочная"}.get(d.get("info", {}).get("form"), "очная")
        for gname in {g["grp"] for g in d.get("groups", [])}:
            reg_group(gname, code, title, crs, form, fac)
        for x in d.get("schedule", []):
            for gname in (x.get("sg") or []):
                add_lesson(gname, {
                    "wd": (x.get("wd") or 1) - 1, "ts": x.get("ts"), "te": x.get("te"),
                    "type": LT.get(x.get("lt"), "practice"),
                    "subject": (x.get("ln") or "").strip(),
                    "teacher": (x.get("tn") or "").strip(),
                    "sub": (x.get("ws") or "").strip(),
                    "place": (x.get("loc") or "").strip(),
                })

    # 2) Excel-сетки (недельные)
    parsed_dir = os.path.join(DATA, "parsed")
    for fn in sorted(os.listdir(parsed_dir)):
        if not fn.endswith(".json"):
            continue
        d = json.load(open(os.path.join(parsed_dir, fn), encoding="utf-8"))
        base = fn.split("__")[0]
        code, title = BASE.get(base) or split_direction(d["meta"].get("direction", ""))
        course = d["meta"].get("course") or 0
        form = d["meta"].get("form") or "очная"
        for g in d["groups"]:
            reg_group(g["name"], code, title, course, form)
        for day in d["days"]:
            for it in day["lessons"]:
                add_lesson(it["group"], {
                    "wd": day["wd"], "ts": it["start"], "te": it["end"],
                    "type": it["type"] or "practice",
                    "subject": it["subject"], "teacher": it["teacher"],
                    "sub": it["subgroups"], "place": it["place"],
                })

    # 2b) официальные страницы сайта (front API) — приоритет над Excel
    override = {}
    fdir = os.path.join(DATA, "raw", "front_pages")
    if os.path.isdir(fdir):
        for fn in sorted(os.listdir(fdir)):
            if not fn.endswith(".json"):
                continue
            d = json.load(open(os.path.join(fdir, fn), encoding="utf-8"))
            code, title = split_direction(d.get("info", {}).get("name", ""))
            crs = (d.get("groups") or [{}])[0].get("crs") or 0
            fac = (d.get("groups") or [{}])[0].get("dep", "")
            for g in d.get("groups", []):
                reg_group(g["grp"], code, title, g.get("crs") or crs, "очная", fac)
            for x in d.get("schedule", []):
                rec = {
                    "wd": (x.get("wd") or 1) - 1, "ts": x.get("ts"), "te": x.get("te"),
                    "type": LT.get(x.get("lt"), "practice"),
                    "subject": (x.get("ln") or "").strip(),
                    "teacher": (x.get("tn") or "").strip(),
                    "sub": (x.get("ws") or "").strip(),
                    "place": (x.get("loc") or "").strip(),
                }
                for gname in (x.get("sg") or []):
                    bucket = override.setdefault(gname, [])
                    if rec not in bucket:
                        bucket.append(rec)

    # 3) циклы (4-6 курс) — с реальными датами
    cycles_dir = os.path.join(DATA, "parsed_cycles")
    if os.path.isdir(cycles_dir):
        for fn in sorted(os.listdir(cycles_dir)):
            if not fn.endswith(".json"):
                continue
            d = json.load(open(os.path.join(cycles_dir, fn), encoding="utf-8"))
            base = fn.split("__")[0]
            code, title = BASE.get(base) or split_direction(d["meta"].get("direction", ""))
            for c in d["cycles"]:
                reg_group(c["group"], code, title, d["meta"].get("course") or 0, "очная")
                periods = []
                for p in c["periods"]:
                    rng = parse_range(p.get("dates", ""))
                    if not rng:
                        continue
                    periods.append({"from": rng[0], "to": rng[1], "ts": p.get("start") or "08:00",
                                    "te": p.get("end") or "", "hours": p.get("hours") or ""})
                if periods:
                    cycles.setdefault(c["group"], []).append({
                        "subject": c["subject"], "teacher": c["teacher"], "place": c["place"],
                        "periods": periods,
                    })

    # 3b) подробные недельные файлы отдельных групп (1103/1203/1303)
    weeks = {}
    wdir = os.path.join(DATA, "parsed_weeks")
    if os.path.isdir(wdir):
        for fn in sorted(os.listdir(wdir)):
            if not fn.endswith(".json"):
                continue
            d = json.load(open(os.path.join(wdir, fn), encoding="utf-8"))
            base = fn.split("__")[0]
            code, title = BASE.get(base) or split_direction(d["meta"].get("direction", ""))
            gname = d.get("group") or fn.split("__")[-1]
            reg_group(gname, code, title, d["meta"].get("course") or 0, "очная")
            weeks[gname] = {str(k): v for k, v in d["weeks"].items()}

    # 3c) датированные занятия из сканов (заочные/очно-заочные)
    dated = {}
    dated_period = {}
    ddir = os.path.join(DATA, "dated")
    if os.path.isdir(ddir):
        for fn in sorted(os.listdir(ddir)):
            if not fn.endswith(".json"):
                continue
            d = json.load(open(os.path.join(ddir, fn), encoding="utf-8"))
            gname = d["group"]
            reg_group(gname, d.get("code", ""), d.get("program", ""), d.get("course") or 0,
                      d.get("form", "заочная"))
            dated[gname] = d.get("lessons", [])
            if d.get("period"):
                dated_period[gname] = d["period"]

    # 4) сканы (для заочных) — отдельный список
    scans = {}
    sp = os.path.join(DATA, "scans.json")
    if os.path.exists(sp):
        scans = json.load(open(sp, encoding="utf-8"))

    # оставляем только группы, для которых есть хоть какие-то занятия
    def has_data(name):
        return bool(templates.get(name) or override.get(name) or dated.get(name)
                    or cycles.get(name) or weeks.get(name))

    skip = [n for n in groups if not has_data(n)]
    for n in skip:
        groups.pop(n, None)
    if skip:
        print("групп без расписания (исключены):", len(skip))

    index = {"generated": time.strftime("%Y-%m-%d %H:%M"), "year": "2026/2027",
             "semester": "осенний", "groups": sorted(groups.values(), key=lambda g: g["n"]),
             "scans": scans}
    json.dump(index, open(os.path.join(OUT, "index.json"), "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))

    total = 0
    for name, g in groups.items():
        payload = {
            "n": name, "prog": g["prog"], "code": g["code"], "course": g["course"], "form": g["form"],
            "faculty": g.get("faculty", ""),
            "lessons": override.get(name) or templates.get(name, []),
            "cycles": cycles.get(name, []),
            "weeks": weeks.get(name, {}),
            "dated": dated.get(name, []),
            "period": dated_period.get(name, []),
        }
        total += len(payload["lessons"])
        path = os.path.join(OUT, "g", name + ".json")
        json.dump(payload, open(path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"групп: {len(groups)}, занятий: {total}, файлов: {len(groups)}")
    print("index.json:", os.path.getsize(os.path.join(OUT, "index.json")) // 1024, "КБ")


def parse_range(s):
    s = (s or "").strip()
    m = re.match(r"^(\d{2})\.(\d{2})\.(\d{4})\s*[–—-]\s*(\d{2})\.(\d{2})\.(\d{4})$", s)
    if m:
        return (f"{m.group(3)}-{m.group(2)}-{m.group(1)}", f"{m.group(6)}-{m.group(5)}-{m.group(4)}")
    m = re.match(r"^(\d{2})\.(\d{2})\.(\d{4})$", s)
    if m:
        d = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
        return (d, d)
    return None


if __name__ == "__main__":
    sys.exit(main())
