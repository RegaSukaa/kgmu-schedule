"""Мини-клиент Chrome DevTools Protocol для Edge (без сторонних библиотек, кроме websocket-client)."""
import json
import os
import subprocess
import time
import urllib.request

import websocket

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


class Browser:
    def __init__(self, port=9333, user_data=None, headless=True):
        self.port = port
        self.proc = None
        self.user_data = user_data or os.path.join(os.environ["LOCALAPPDATA"], "Temp", "edge-cdp")
        self.headless = headless
        self.ws = None
        self._id = 0
        self.events = []

    def start(self):
        args = [EDGE, f"--remote-debugging-port={self.port}", f"--user-data-dir={self.user_data}",
                "--no-first-run", "--no-default-browser-check", "--disable-gpu",
                "--disable-features=Translate", "--window-size=1400,1000"]
        if self.headless:
            args.insert(1, "--headless=new")
        args.append("about:blank")
        self.proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(60):
            try:
                targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json/list", timeout=1))
                pages = [t for t in targets if t["type"] == "page"]
                if pages:
                    self.ws = websocket.create_connection(pages[0]["webSocketDebuggerUrl"],
                                                          timeout=60, max_size=200 * 1024 * 1024)
                    return self
            except Exception:  # noqa: BLE001
                time.sleep(0.5)
        raise RuntimeError("не удалось подключиться к Edge по CDP")

    def send(self, method, **params):
        self._id += 1
        mid = self._id
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})
            self.events.append(msg)

    def evaluate(self, expr, await_promise=False):
        r = self.send("Runtime.evaluate", expression=expr, returnByValue=True,
                      awaitPromise=await_promise, userGesture=True)
        if r.get("exceptionDetails"):
            raise RuntimeError(json.dumps(r["exceptionDetails"])[:500])
        return r.get("result", {}).get("value")

    def navigate(self, url, wait=3.0):
        self.send("Page.enable")
        self.send("Page.navigate", url=url)
        time.sleep(wait)

    def close(self):
        try:
            if self.ws:
                self.ws.close()
        except Exception:  # noqa: BLE001
            pass
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except Exception:  # noqa: BLE001
                self.proc.kill()
