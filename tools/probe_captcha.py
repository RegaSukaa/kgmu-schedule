"""Проверяем, можно ли получить токен SmartCaptcha и дернуть API из контекста страницы."""
import json
import sys
import time

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from cdp import Browser  # noqa: E402

b = Browser(port=9336, user_data=r"C:\Users\Rubin\AppData\Local\Temp\edge-probe4").start()
try:
    b.send("Network.enable")
    b.navigate("https://calendar.kazangmu.org/", wait=8)

    print("капча-скрипты:", [e["params"]["request"]["url"] for e in b.events
                             if e.get("method") == "Network.requestWillBeSent"
                             and "captcha" in e["params"]["request"]["url"]][:5])

    print("getResponse:", b.evaluate("typeof window.smartCaptcha.getResponse === 'function' ? String(window.smartCaptcha.getResponse()) : 'нет'"))
    print("widgets:", b.evaluate("""
      (() => { try { return JSON.stringify(Object.keys(window.smartCaptcha).map(k=>k)); } catch(e){ return String(e); } })()
    """))

    # пробуем разные способы получения токена
    for expr in [
        "window.smartCaptcha.executePromise ? 'есть executePromise' : 'нет'",
        "(async () => { try { const t = await window.smartCaptcha.executePromise(); return 'TOKEN:' + String(t).slice(0,40); } catch(e) { return 'ERR:' + e.message; } })()",
        "(async () => { try { const t = await new Promise((res,rej)=>{ const r=window.smartCaptcha.execute(()=>res('cb')); if(r&&r.then) r.then(res,rej); }); return 'EXEC:'+String(t).slice(0,40); } catch(e){ return 'ERR2:'+e.message; } })()",
    ]:
        try:
            print("->", b.evaluate(expr, await_promise=True))
        except Exception as e:  # noqa: BLE001
            print("-> исключение:", str(e)[:200])
finally:
    b.close()
