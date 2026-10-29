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
    "obschestvennoe-zdravoohranenie-magistratura-o-zaochn": "Общественное здравоохранение (магистратура, очно-заочная)",
}


def split_direction(s):
    m = re.match(r"^\s*(\d{2}\.\d{2}\.\d{2})\s+(.+)$", s or "")
    if m:
        return m.group(1), m.group(2).strip()
    return "", (s or "").strip()


def prog_key(name):
    return name


def main():
    os.makedirs(OUT, exist_ok=True)
    man = json.load(open(os.path.join(DATA, "manifest.json"), encoding="utf-8"))
    programs = {}

    def prog(code, title, form, level):
        key = f"{code}|{title}|{form}"
        p = programs.setdefault(key, {
            "id": re.sub(r"[^a-z0-9]+", "-", f"{code} {form}".lower()).strip("-"),
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

    plist = sorted(programs.values(), key=lambda p: (p["code"], p["form"]))
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
