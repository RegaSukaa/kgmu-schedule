"""Разведка страницы студенческого расписания: как выбрать группу и что уходит в API."""
import json
import sys
import time

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from cdp import Browser  # noqa: E402

b = Browser(port=9333, user_data=r"C:\Users\Rubin\AppData\Local\Temp\edge-probe").start()
try:
    b.send("Network.enable")
    b.navigate("https://calendar.kazangmu.org/", wait=6)

    print("=== кнопки на странице ===")
    print(json.dumps(b.evaluate("""
      Array.from(document.querySelectorAll('button')).map((x,i)=>({i, t:(x.innerText||'').trim().slice(0,40), aria:x.getAttribute('aria-haspopup'), id:x.id}))
    """), ensure_ascii=False))

    print("=== открываю список групп ===")
    b.evaluate("""
      (() => { const btns=[...document.querySelectorAll('button')].filter(x=>x.getAttribute('aria-haspopup')==='listbox'); btns[0].click(); return btns.length; })()
    """)
    time.sleep(1.5)
    print(json.dumps(b.evaluate("""
      (() => { const p=document.querySelector('[role=listbox],[role=dialog]');
        return p ? {html: p.outerHTML.slice(0,800), inputs: [...p.querySelectorAll('input')].map(i=>({ph:i.placeholder, type:i.type}))} : 'no popup'; })()
    """), ensure_ascii=False))
finally:
    b.close()
