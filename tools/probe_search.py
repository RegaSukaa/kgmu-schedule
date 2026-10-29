"""Выбор группы через UI, Поиск, наблюдение за капчей и запросом к API."""
import json
import sys
import time

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from cdp import Browser  # noqa: E402

GROUP = "1206"
SHOT = r"C:\Users\Rubin\AppData\Local\Temp\kgmu"

b = Browser(port=9337, user_data=r"C:\Users\Rubin\AppData\Local\Temp\edge-probe5").start()
try:
    b.send("Network.enable")
    b.navigate("https://calendar.kazangmu.org/", wait=8)

    def shot(name):
        data = b.send("Page.captureScreenshot", format="png")["data"]
        import base64
        open(f"{SHOT}\\{name}.png", "wb").write(base64.b64decode(data))

    b.evaluate("""(() => { const btn=[...document.querySelectorAll('button')].find(x=>x.getAttribute('aria-haspopup')==='listbox'); btn.click(); return true; })()""")
    time.sleep(2)
    print("опций после открытия:", b.evaluate("document.querySelectorAll('[role=option]').length"))
    print("popup text:", (b.evaluate("(document.querySelector('[role=listbox]')||{}).innerText") or "")[:200])
    shot("p5_popup")

    b.evaluate("""(() => {
      const box=document.querySelector('[role=listbox]');
      const inp=box.querySelector('input');
      const setter=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
      setter.call(inp,'%s'); inp.dispatchEvent(new Event('input',{bubbles:true}));
      return true; })()""" % GROUP)
    time.sleep(2)
    print("опций после ввода:", b.evaluate("document.querySelectorAll('[role=option]').length"))
    print("первые опции:", b.evaluate("Array.from(document.querySelectorAll('[role=option]')).slice(0,5).map(o=>o.textContent.trim())"))
    shot("p5_filtered")

    clicked = b.evaluate("""(() => { const o=[...document.querySelectorAll('[role=option]')].find(x=>x.textContent.trim()==='%s'); if(o){o.click(); return true;} return false; })()""" % GROUP)
    print("клик по опции:", clicked)
    time.sleep(1.5)
    print("текущая группа:", b.evaluate("""(() => { const btn=[...document.querySelectorAll('button')].find(x=>x.getAttribute('aria-haspopup')==='listbox'); return btn ? btn.innerText.trim() : null; })()"""))

    print("кнопка Поиск disabled:", b.evaluate("""(() => { const btn=[...document.querySelectorAll('button')].find(x=>x.textContent.trim()==='Поиск'); return btn ? btn.disabled : 'нет кнопки'; })()"""))
    b.evaluate("""(() => { const btn=[...document.querySelectorAll('button')].find(x=>x.textContent.trim()==='Поиск'); btn.click(); return true; })()""")

    for i in range(8):
        time.sleep(2)
        state = b.evaluate("""(() => {
          const api=[...performance.getEntriesByType('resource')].filter(r=>r.name.includes('/api/')).map(r=>r.name);
          return {overlay: !!document.querySelector('[class*=z-50]'), bodytail: document.body.innerText.slice(-300), api: api.slice(-3)};
        })()""")
        print(f"--- {i}:", json.dumps(state, ensure_ascii=False)[:500])
        if i == 2:
            shot("p5_after_search")
finally:
    b.close()
