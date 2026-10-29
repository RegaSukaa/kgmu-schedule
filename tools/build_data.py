"""Собирает единый data/schedule.json из скачанных и распарсенных расписаний."""
import json
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "site", "data")

LT = {102: "lecture", 103: "practice", 104: "cycle"}

# человекочитаемые названия направлений (как в таблице на сайте)
TITLES = {
    "31.05.01": "Лечебное дело",
    "31.05.02": "Педиатрия",
    "31.05.03": "Стоматология",
    "32.05.01": "Медико-профилактическое дело",
    "33.05.01": "Фармация",
    "30.05.01": "Медицинская биохимия",
    "30.05.02": "Медицинская биофизика",
    "37.03.01": "Психология (бакалавриат)",
    "34.03.01": "Сестринское дело",
    "39.03.02": "Социальная работа (бакалавриат)",
    "39.04.02": "Социальная работа (магистратура)",
    "32.04.01": "Общественное здравоохранение (магистратура)",
    "33.04.01": "Промышленная фармация",
}

BASE = {
    "lechebnoe-delo": ("31.05.01", "Лечебное дело"),
    "pediatriya": ("31.05.02", "Педиатрия"),
    "stomatologiya": ("31.05.03", "Стоматология"),
    "mediko-profilakticheskoe-delo": ("32.05.01", "Медико-профилактическое дело"),
    "farmaciya": ("33.05.01", "Фармация"),
}

PROGRAM_TITLE = {
    "lechebnoe-delo": "Лечебное дело",
    "pediatriya": "Педиатрия",
    "stomatologiya": "Стоматология",
    "mediko-profilakticheskoe-delo": "Медико-профилактическое дело",
    "farmaciya": "Фармация",
    "medicinskaya-biohimiya": "Медицинская биохимия",
    "medicinskaya-biofizika": "Медицинская биофизика",
    "psihologiya-bakalavriat": "Психология (бакалавриат)",
    "sestrinskoe-delo-ochn": "Сестринское дело (очная)",
    "sestrinskoe-delo-o-zaochn": "Сестринское дело (очно-заочная)",
    "socialnaya-rabota-bakalavriat-ochn": "Социальная работа (бакалавриат, очная)",
    "socialnaya-rabota-bakalavriat-zaochn": "Социальная работа (бакалавриат, заочная)",
    "socialnaya-rabota-magistratura-zaochn": "Социальная работа (магистратура, заочная)",
    "obschestvennoe-zdravoohranenie-magistratura-ochn": "Общественное здравоохранение (магистратура, очная)",
    "obschestvennoe-zdravoohranenie-magistratura-o-zaochn": "Общественное здравоохранение (магистратура)",
    "sestrinskoe-delo-o-zaochn": "Сестринское дело",
    "socialnaya-rabota-bakalavriat-zaochn": "Социальная работа (бакалавриат)",
    "socialnaya-rabota-magistratura-zaochn": "Социальная работа (магистратура)",
}


def split_direction(s):
    m = re.match(r"^\s*(\d{2}\.\d{2}\.\d{2})\s+(.+)$", s or "")
    if m:
        return m.group(1), m.group(2).strip()
    return "", (s or "").strip()


TR = {"а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh",
      "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
      "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "c",
      "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya"}


def slug(text):
    out = "".join(TR.get(ch, ch) for ch in str(text).lower())
    return re.sub(r"[^a-z0-9]+", "-", out).strip("-")


def main():
    os.makedirs(OUT, exist_ok=True)
    man = json.load(open(os.path.join(DATA, "manifest.json"), encoding="utf-8"))
    programs = {}

    def prog(code, title, form, level):
        key = f"{code}|{title}|{form}"
        p = programs.setdefault(key, {
            "id": slug(f"{code} {title} {form}"),
            "code": code, "title": title, "form": form, "level": level, "courses": [],
        })
        return p

    def add_course(p, course, label, groups, lessons, source, extra=None):
        c = {"course": course, "label": label, "groups": groups, "lessons": lessons,
             "source": source}
        if extra:
            c.update(extra)
        for i, old in enumerate(p["courses"]):
            if old["course"] == course and old["label"] == label:
                p["courses"][i] = c
                return
        p["courses"].append(c)

    # --- календарные JSON с сайта ---
    for m in man:
        if not m["file"].endswith(".json"):
            continue
        d = json.load(open(os.path.join(DATA, "raw", m["file"]), encoding="utf-8"))
        code, title = split_direction(d.get("info", {}).get("name", ""))
        fac = d.get("groups", [{}])[0].get("dep", "")
        crs = d.get("groups", [{}])[0].get("crs")
        gnames = []
        for g in d.get("groups", []):
            if g["grp"] not in gnames:
                gnames.append(g["grp"])
        lessons = []
        for x in d.get("schedule", []):
            lessons.append({
                "wd": x.get("wd"),
                "ts": x.get("ts"),
                "te": x.get("te"),
                "type": LT.get(x.get("lt"), "practice"),
                "subject": x.get("ln", "").strip(),
                "teacher": (x.get("tn") or "").strip(),
                "subgroups": (x.get("ws") or "").strip(),
                "place": (x.get("loc") or "").strip(),
                "groups": x.get("sg") or gnames,
            })
        form = {5: "очная", 6: "очно-заочная", 7: "заочная"}.get(d.get("info", {}).get("form"), "очная")
        level = {4: "специалитет", 3: "бакалавриат", 5: "магистратура"}.get(d.get("info", {}).get("level"), "специалитет")
        p = prog(code, title, form, level)
        p.setdefault("faculty", fac)
        add_course(p, crs, f"{crs} курс", [{"name": g, "potok": ""} for g in gnames], lessons,
                   m["url"], {"faculty": fac})

    # --- Excel (недельная сетка) ---
    parsed_dir = os.path.join(DATA, "parsed")
    for fn in sorted(os.listdir(parsed_dir)):
        if not fn.endswith(".json"):
            continue
        d = json.load(open(os.path.join(parsed_dir, fn), encoding="utf-8"))
        base = fn.split("__")[0]
        if base in BASE:
            code, title = BASE[base]
        else:
            code, title = split_direction(d["meta"].get("direction", ""))
        if not title:
            title = PROGRAM_TITLE.get(fn.split("__")[0], fn)
        m = next((x for x in man if x["key"] == fn[:-5]), {})
        label = m.get("label", "")
        course = d["meta"].get("course") or 0
        if "4-6" in label:
            label = "4–6 курс (лекции)"
        else:
            label = f"{course} курс"
        lessons = []
        for day in d["days"]:
            for it in day["lessons"]:
                lessons.append({
                    "wd": day["wd"], "ts": it["start"], "te": it["end"],
                    "type": it["type"] or "practice", "subject": it["subject"],
                    "teacher": it["teacher"], "subgroups": it["subgroups"],
                    "place": it["place"], "groups": [it["group"]],
                })
        p = prog(code, title, d["meta"].get("form") or "очная", d["meta"].get("level") or "специалитет")
        add_course(p, course, label, d["groups"], lessons, m.get("url", ""))

    # --- цикловые занятия (4-6 курс) ---
    cycles_dir = os.path.join(DATA, "parsed_cycles")
    if os.path.isdir(cycles_dir):
        for fn in sorted(os.listdir(cycles_dir)):
            if not fn.endswith(".json"):
                continue
            d = json.load(open(os.path.join(cycles_dir, fn), encoding="utf-8"))
            base = fn.split("__")[0]
            code, title = BASE.get(base) or split_direction(d["meta"].get("direction", ""))
            m = next((x for x in man if x["key"] == fn[:-5]), {})
            label = "4–6 курс (циклы)" if "4-6" in m.get("label", "") else "3–5 курс (циклы)"
            groups = []
            for c in d["cycles"]:
                if c["group"] not in [g["name"] for g in groups]:
                    groups.append({"name": c["group"], "potok": ""})
            p = prog(code, title, "очная", "специалитет")
            add_course(p, d["meta"].get("course") or 4, label, groups, [], m.get("url", ""),
                       {"cycles": d["cycles"]})

    # --- сканы PDF (без текстового слоя) ---
    scans_path = os.path.join(DATA, "scans.json")
    if os.path.exists(scans_path):
        scans = json.load(open(scans_path, encoding="utf-8"))
        for key, sc in scans.items():
            base = key.split("__")[0]
            title = PROGRAM_TITLE.get(base, sc["program_page"])
            form = "заочная" if base.endswith("zaochn") and "o-zaochn" not in base else ("очно-заочная" if "o-zaochn" in base else "очная")
            level = "магистратура" if "magistratura" in base else "специалитет"
            m = next((x for x in man if x["key"] == key), {})
            label = m.get("label", sc.get("label", "")) or "курс"
            course_no = int(re.sub(r"\D", "", label) or 0)
            p = prog("", title, form, level)
            add_course(p, course_no, label, [], [], sc.get("source", ""), {"scans": sc["pages"]})

    plist = sorted(programs.values(), key=lambda p: (p["code"] == "", p["code"], p["title"], p["form"]))
    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M"),
        "year": "2026/2027",
        "semester": "осенний",
        "programs": plist,
    }
    path = os.path.join(OUT, "schedule.json")
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    total = sum(len(c["lessons"]) for p in plist for c in p["courses"])
    print(f"программ: {len(plist)}, курсов: {sum(len(p['courses']) for p in plist)}, занятий: {total}")
    print("файл:", path, os.path.getsize(path) // 1024, "КБ")
    for p in plist:
        print(" ", p["code"], p["title"], "|", p["form"], "|", [(c["label"], len(c["groups"]), len(c["lessons"])) for c in p["courses"]])


if __name__ == "__main__":
    sys.exit(main())
