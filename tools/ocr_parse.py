"""OCR сканированных расписаний (Windows.Media.Ocr) и разбор таблицы в строки."""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCANS = os.path.join(ROOT, "site", "scans")
TMP = os.path.join(os.environ["LOCALAPPDATA"], "Temp", "kgmu", "ocrpages")
PS = os.path.join(os.environ["LOCALAPPDATA"], "Temp", "ocr2.ps1")
OUT = os.path.join(ROOT, "data", "ocr_pages")

DATE_RE = re.compile(r"^[!1lI]?\s*(\d{1,2})[.,](\d{1,2})[.,](\d{4})$")
TIME_RE = re.compile(r"^(\d{1,2})[:.](\d{2})\s*[-–—]\s*(\d{1,2})[:.](\d{2})$")
TYPE_RE = re.compile(r"^(Лекция|Практика|Экзамен|Зач[её]т)$", re.I)


def ocr(image, out_json):
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", PS,
                    "-Img", image, "-Out", out_json], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)


def rows_from_page(data):
    """Строки таблицы: якоря — время в колонке «ЧАСЫ», остальные слова привязываем по Y."""
    words = []
    for ln in data:
        for w in ln.get("words", []):
            t = (w.get("t") or "").strip()
            if t:
                words.append({"t": t, "x": float(w["x"]), "y": float(w["y"])})
    if not words:
        return []
    words.sort(key=lambda w: (w["y"], w["x"]))

    # колонки определяем по гистограмме X
    width = max(w["x"] for w in words)
    times = [w for w in words if TIME_RE.match(w["t"])]
    if not times:
        return []
    tx = min(w["x"] for w in times)

    # якоря — время в левой колонке
    anchors = sorted({round(w["y"] / 3) * 3 for w in times if w["x"] <= tx + 60})
    dates = [(w["y"], w["t"]) for w in words if DATE_RE.match(w["t"]) and w["x"] < tx]

    rows, cur_date = [], None
    for i, ay in enumerate(anchors):
        y0 = ay - 12
        y1 = (anchors[i + 1] - 12) if i + 1 < len(anchors) else ay + 80
        chunk = [w for w in words if y0 <= w["y"] < y1]
        # дата: ближайшая сверху
        for dy, dt in dates:
            if dy <= y0 + 20:
                m = DATE_RE.match(dt)
                if m:
                    d, mo, yy = m.groups()
                    cur_date = f"{int(d):02d}.{int(mo):02d}.{yy}"
        tm = None
        subj, place, kind = [], [], ""
        for w in chunk:
            if TIME_RE.match(w["t"]) and abs(w["x"] - tx) < 60:
                mm = TIME_RE.match(w["t"])
                h1, m1, h2, m2 = mm.groups()
                tm = f"{int(h1):02d}:{m1}-{int(h2):02d}:{m2}"
                continue
            if TYPE_RE.match(w["t"]):
                kind = w["t"].capitalize()
                continue
            if DATE_RE.match(w["t"]) or w["x"] < tx:
                continue
            x = w["x"] / max(width, 1)
            if x > 0.86:
                continue
            if x > 0.74:
                place.append(w["t"])
            elif x > 0.2:
                subj.append(w["t"])
        subject = " ".join(subj).strip(" ,;")
        if not tm or not subject or not cur_date:
            continue
        rows.append({"d": cur_date, "t": tm, "s": subject,
                     "p": " ".join(place).strip(" ,;"), "k": kind or "Практика"})
    return rows


def main():
    os.makedirs(TMP, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    for key in sorted(os.listdir(SCANS)):
        d = os.path.join(SCANS, key)
        if not os.path.isdir(d):
            continue
        all_rows, header = [], []
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".webp"):
                continue
            img = os.path.join(d, fn)
            tmp = os.path.join(TMP, f"{key}__{fn}.json")
            if not os.path.exists(tmp):
                ocr(img, tmp)
            data = json.load(open(tmp, encoding="utf-8"))
            if fn == "page-01.webp":
                header = [ln.get("text", "") for ln in data[:14]]
            all_rows.extend(rows_from_page(data))
        out = {"key": key, "header": header, "rows": all_rows}
        json.dump(out, open(os.path.join(OUT, key + ".json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"{key}: {len(all_rows)} строк")


if __name__ == "__main__":
    sys.exit(main())
