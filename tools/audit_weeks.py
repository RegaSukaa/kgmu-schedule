"""Проверка разметки занятий по учебным неделям (скобки = диапазон недель)."""
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GDIR = os.path.join(ROOT, "site", "data", "g")
WEEK1 = "2026-08-31"   # понедельник недели, в которую попало 1 сентября 2026
TOTAL_WEEKS = 18


def spans(sub):
    s = re.sub(r"\s+", "", str(sub or ""))
    if not s or not re.fullmatch(r"\d+(-\d+)?(,\d+(-\d+)?)*", s):
        return None
    out = []
    for part in s.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.append((int(a), int(b)))
        else:
            out.append((int(part), int(part)))
    return out


def in_week(sub, w):
    sp = spans(sub)
    return True if sp is None else any(a <= w <= b for a, b in sp)


def main():
    rows = []
    bad = []
    for fn in sorted(os.listdir(GDIR)):
        if not fn.endswith(".json"):
            continue
        d = json.load(open(os.path.join(GDIR, fn), encoding="utf-8"))
        lessons = d.get("lessons") or []
        if not lessons:
            continue
        per_week = []
        for w in range(1, TOTAL_WEEKS + 1):
            n = sum(1 for l in lessons if in_week(l.get("sub"), w))
            per_week.append(n)
        empty = [w for w, n in enumerate(per_week, 1) if n == 0]
        rows.append((d["n"], len(lessons), per_week, empty))
        if empty:
            bad.append((d["n"], empty))

    print(f"{'группа':8} {'занятий':>8}  недели 1..18 (сколько занятий остаётся)")
    for name, total, per_week, empty in rows:
        print(f"{name:8} {total:8}  " + " ".join(f"{n:3}" for n in per_week)
              + ("   без занятий: " + ",".join(map(str, empty)) if empty else ""))

    print()
    if bad:
        print("группы с пустыми неделями:", len(bad))
        for n, e in bad[:15]:
            print("  ", n, "->", e)
    else:
        print("пустых недель нет ни у одной группы")

    # сколько занятий реально имеет ограничение по неделям
    limited = sum(1 for fn in os.listdir(GDIR)
                  for l in (json.load(open(os.path.join(GDIR, fn), encoding="utf-8")).get("lessons") or [])
                  if spans(l.get("sub")) is not None)
    total = sum(len(json.load(open(os.path.join(GDIR, fn), encoding="utf-8")).get("lessons") or [])
                for fn in os.listdir(GDIR) if fn.endswith(".json"))
    print(f"\nзанятий с ограничением по неделям: {limited} из {total}")


if __name__ == "__main__":
    sys.exit(main())
