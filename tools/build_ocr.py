"""Сканы -> датированные занятия (группы заочных/очно-заочных направлений)."""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = os.path.join(ROOT, "data", "ocr_pages")
OUT = os.path.join(ROOT, "data", "dated")

PROGRAM = {
    "sestrinskoe-delo-o-zaochn": ("34.03.01", "Сестринское дело", "очно-заочная"),
    "socialnaya-rabota-bakalavriat-zaochn": ("39.03.02", "Социальная работа (бакалавриат)", "заочная"),
    "socialnaya-rabota-magistratura-zaochn": ("39.04.02", "Социальная работа (магистратура)", "заочная"),
    "obschestvennoe-zdravoohranenie-magistratura-o-zaochn": ("32.04.01", "Общественное здравоохранение (магистратура)", "очно-заочная"),
}

TEACH_RE = re.compile(r"[,;]?\s*((?:доц|проф|ст\.?\s?преп|асс|преп)\.?\s*[А-ЯЁ][а-яё\-]+(?:\s+[А-ЯЁ]\.\s?[А-ЯЁ]?\.?)?)\s*$")
GROUP_RE = re.compile(r"(\d{4})\s*[-–]?\s*(о?з)\b", re.I)


def split_teacher(s):
    m = TEACH_RE.search(s)
    if m:
        return s[:m.start()].strip(" ,;"), m.group(1).strip(" ,;")
    return s, ""


def norm_date(d):
    dd, mm, yy = d.split(".")
    return f"{yy}-{mm}-{dd}"


def main():
    os.makedirs(OUT, exist_ok=True)
    result = {}
    for fn in sorted(os.listdir(PAGES)):
        if not fn.endswith(".json"):
            continue
        d = json.load(open(os.path.join(PAGES, fn), encoding="utf-8"))
        key = d["key"]
        base = key.split("__")[0]
        course = int(re.sub(r"\D", "", key.split("__")[-1]) or 0)
        code, program, form = PROGRAM.get(base, ("", base, "заочная"))

        header = " ".join(d.get("header", []))
        gm = GROUP_RE.search(header)
        group = (gm.group(1) + ("-оз" if (gm.group(2) or "").lower().startswith("з") else "")) if gm else ""
        if not group:
            # ищем в тексте вида «группа 8101-03»
            gm = re.search(r"групп[аы]?\s*(\d{4})\s*[-–]?\s*(оз|\d{2})?", header, re.I)
            group = f"{gm.group(1)}-{gm.group(2) or 'оз'}" if gm else key.split("__")[-1]

        lessons, seen = [], set()
        for r in d["rows"]:
            subj, teacher = split_teacher(r["s"])
            t1, t2 = r["t"].split("-")
            rec = {
                "d": norm_date(r["d"]), "ts": t1, "te": t2,
                "subject": subj.strip(), "teacher": teacher,
                "place": (r.get("p") or "").strip(),
                "type": {"лекция": "lecture", "практика": "practice", "экзамен": "exam"}.get(
                    (r.get("k") or "").lower(), "practice"),
            }
            sig = json.dumps(rec, ensure_ascii=False, sort_keys=True)
            if sig in seen:
                continue
            seen.add(sig)
            lessons.append(rec)

        dates = sorted({l["d"] for l in lessons})
        payload = {
            "key": key, "group": group, "code": code, "program": program, "course": course,
            "form": form, "rows": len(lessons),
            "period": [dates[0], dates[-1]] if dates else [],
            "lessons": lessons,
        }
        json.dump(payload, open(os.path.join(OUT, key + ".json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        result[key] = payload
        print(f"{key}: группа {group}, занятий {len(lessons)}, "
              f"период {payload['period']}")
    json.dump({k: {"group": v["group"], "code": v["code"], "program": v["program"],
                   "course": v["course"], "form": v["form"], "period": v["period"]}
               for k, v in result.items()},
              open(os.path.join(ROOT, "data", "dated_index.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    sys.exit(main())
