"""Сканы расписаний (PDF без текстового слоя) -> WebP-страницы для сайта."""
import json
import os
import re
import sys

import pymupdf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "site", "scans")
ZOOM = 2.2


def main():
    man = json.load(open(os.path.join(ROOT, "data", "manifest.json"), encoding="utf-8"))
    index = {}
    for m in man:
        if not m["file"].endswith(".xlsx"):
            continue
        path = os.path.join(RAW, m["file"])
        with open(path, "rb") as f:
            head = f.read(5)
        if head != b"%PDF-":
            continue
        doc = pymupdf.open(path)
        if doc.page_count and doc[0].get_text().strip():
            print("текстовый PDF, пропускаю:", m["key"])
            continue
        outdir = os.path.join(OUT, m["key"])
        os.makedirs(outdir, exist_ok=True)
        pages = []
        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=pymupdf.Matrix(ZOOM, ZOOM))
            name = f"page-{i + 1:02d}.webp"
            pix.pil_save(os.path.join(outdir, name), format="WEBP", quality=82)
            pages.append(f"scans/{m['key']}/{name}")
        index[m["key"]] = {"pages": pages, "source": m["url"], "label": m.get("label", ""),
                           "program_page": m.get("program", ""), "pages_count": len(pages)}
        print(f"{m['key']}: {len(pages)} стр.")
    json.dump(index, open(os.path.join(ROOT, "data", "scans.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("всего сканов:", len(index), "файлов:", sum(v["pages_count"] for v in index.values()))


if __name__ == "__main__":
    sys.exit(main())
