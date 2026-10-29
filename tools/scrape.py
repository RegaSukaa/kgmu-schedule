"""Скачивание расписаний КГМУ: каталог + JSON (calendar.kazangmu.org) + Excel (cloud.kazangmu.ru)."""
import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
CATALOG_PAGE = "https://kazangmu.ru/obuchenie/studentam/raspisanie-zanyatij"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


def get(url, data=None, headers=None, timeout=60):
    h = {"User-Agent": UA, "Accept": "*/*"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.headers.get_content_type(), r.status


def parse_catalog(html):
    """Возвращает список {program, label, url} по таблице на сайте."""
    items = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S):
        tds = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        if not tds:
            continue
        spec = " ".join(re.sub(r"<[^>]+>", " ", tds[0]).split())
        if not spec or spec.lower().startswith("направление"):
            continue
        for cell in tds[1:]:
            for url, label in re.findall(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', cell, re.S):
                label = " ".join(re.sub(r"<[^>]+>", "", label).split())
                items.append({"program": spec, "label": label, "url": url})
    return items


def slug(s):
    table = {"а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh",
             "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
             "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "c",
             "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya"}
    s = s.lower()
    out = "".join(table.get(ch, ch) for ch in s)
    out = re.sub(r"[^a-z0-9]+", "-", out).strip("-")
    return out


def main():
    os.makedirs(os.path.join(RAW, "front"), exist_ok=True)
    os.makedirs(os.path.join(RAW, "xlsx"), exist_ok=True)
    html = get(CATALOG_PAGE)[0].decode("utf-8", "ignore")
    items = parse_catalog(html)
    print("позиций в каталоге:", len(items))

    manifest = []
    for it in items:
        rec = dict(it)
        rec["kind"] = "calendar" if "calendar.kazangmu.org" in it["url"] else "cloud"
        name = f'{slug(it["program"])}__{slug(it["label"])}'
        rec["key"] = name
        try:
            if rec["kind"] == "calendar":
                m = re.search(r"/schedule/([^/]+)/front/([^/]+)/([^/]+)$", it["url"])
                ay, ds, cs = m.group(1), m.group(2), m.group(3)
                body = json.dumps({"ds": ds, "cs": cs, "ay": ay}).encode()
                raw, _, code = get("https://calendar.kazangmu.org/api/schedule/front", data=body,
                                   headers={"Content-Type": "application/json", "Accept": "application/json"})
                data = json.loads(raw.decode("utf-8"))
                rec["file"] = f"front/{name}.json"
                rec["ds"], rec["cs"], rec["ay"] = ds, cs, ay
                json.dump(data, open(os.path.join(RAW, "front", name + ".json"), "w", encoding="utf-8"),
                          ensure_ascii=False, indent=1)
                rec["lessons"] = len(data.get("schedule", []))
                rec["program_name"] = data.get("info", {}).get("name")
                print("  calendar", name, code, rec["lessons"], "занятий", rec["program_name"])
            else:
                token = it["url"].rstrip("/").split("/")[-1]
                raw, ctype, code = get(f"https://cloud.kazangmu.ru/public.php/dav/files/{token}/")
                rec["file"] = f"xlsx/{name}.xlsx"
                rec["token"] = token
                open(os.path.join(RAW, "xlsx", name + ".xlsx"), "wb").write(raw)
                print("  cloud   ", name, code, ctype, len(raw), "байт")
            rec["ok"] = True
        except Exception as e:  # noqa: BLE001
            rec["ok"] = False
            rec["error"] = f"{type(e).__name__}: {e}"
            print("  ОШИБКА  ", name, rec["error"])
        manifest.append(rec)
        time.sleep(0.4)

    json.dump(manifest, open(os.path.join(ROOT, "data", "manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    ok = sum(1 for m in manifest if m.get("ok"))
    print(f"готово: {ok}/{len(manifest)}")


if __name__ == "__main__":
    sys.exit(main())
