"""A tiny headless-Chrome driver over the DevTools protocol, standard library only.

Enough for browser tests: open a page, evaluate JavaScript, click, take a
screenshot. Tests that use it skip when no Chrome/Chromium/Edge is installed.
"""

import base64
import json
import os
import shutil
import socket
import struct
import subprocess
import tempfile
import time
import urllib.request

CANDIDATES = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "msedge", "chrome"]
MAC_APPS = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"]


def find_chrome():
    env = os.environ.get("CONDUCTOR_TEST_CHROME")
    if env:
        return env
    for name in CANDIDATES:
        path = shutil.which(name)
        if path:
            return path
    for path in MAC_APPS + [os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
                            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe")]:
        if os.path.exists(path):
            return path
    return None


class _WebSocket:
    """Minimal client: text frames only, which is all DevTools uses."""

    def __init__(self, url):
        host_port, path = url[len("ws://"):].split("/", 1)
        host, port = host_port.split(":")
        self.sock = socket.create_connection((host, int(port)), timeout=30)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f"GET /{path} HTTP/1.1\r\nHost: {host_port}\r\nUpgrade: websocket\r\n"
                           f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        resp = b""
        while b"\r\n\r\n" not in resp:
            resp += self.sock.recv(1)
        if b" 101 " not in resp.split(b"\r\n", 1)[0]:
            raise ConnectionError(resp.decode(errors="replace"))

    def send(self, text):
        data = text.encode()
        head = bytearray([0x81])
        n = len(data)
        if n < 126:
            head.append(0x80 | n)
        elif n < 65536:
            head += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            head += bytes([0x80 | 127]) + struct.pack(">Q", n)
        mask = os.urandom(4)
        self.sock.sendall(bytes(head) + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def _exact(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("websocket closed")
            buf += chunk
        return buf

    def recv(self):
        parts = []
        while True:
            b0, b1 = self._exact(2)
            n = b1 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._exact(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._exact(8))[0]
            parts.append(self._exact(n))
            if b0 & 0x80:
                return b"".join(parts).decode()

    def close(self):
        self.sock.close()


class Browser:
    def __init__(self, width=1300, height=800):
        exe = find_chrome()
        if not exe:
            raise FileNotFoundError("no Chrome, Chromium or Edge found")
        self.profile = tempfile.mkdtemp(prefix="conductor-chrome-")
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        self.proc = subprocess.Popen(
            [exe, "--headless=new", f"--remote-debugging-port={port}", f"--user-data-dir={self.profile}",
             "--no-first-run", "--no-default-browser-check", "--disable-gpu", "--disable-extensions",
             f"--window-size={width},{height}", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.time() + 20
        while True:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=2) as r:
                    pages = [t for t in json.load(r) if t["type"] == "page"]
                if pages:
                    break
            except OSError:
                pass
            if time.time() > deadline:
                self.close()
                raise TimeoutError("Chrome did not start")
            time.sleep(0.1)
        self.ws = _WebSocket(pages[0]["webSocketDebuggerUrl"])
        self._id = 0
        self.call("Page.enable")
        self.call("Runtime.enable")

    def call(self, method, **params):
        self._id += 1
        self.ws.send(json.dumps({"id": self._id, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self._id:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})

    def js(self, expression):
        """Evaluate JavaScript (awaiting promises) and return its JSON value."""
        res = self.call("Runtime.evaluate", expression=expression, awaitPromise=True, returnByValue=True)
        if "exceptionDetails" in res:
            raise RuntimeError(res["exceptionDetails"].get("exception", {}).get("description", res["exceptionDetails"]))
        return res["result"].get("value")

    def init_script(self, source):
        """Run JavaScript in every new document before its own scripts. Returns an id for remove_init_script."""
        return self.call("Page.addScriptToEvaluateOnNewDocument", source=source)["identifier"]

    def remove_init_script(self, identifier):
        self.call("Page.removeScriptToEvaluateOnNewDocument", identifier=identifier)

    def key(self, key, code=None, key_code=0):
        """Press and release one key in the focused element, as a user would."""
        text = {"Enter": "\r", " ": " "}.get(key, key if len(key) == 1 else "")
        down = {"type": "keyDown", "key": key, "code": code or key, "windowsVirtualKeyCode": key_code}
        if text:
            down["text"] = text
        self.call("Input.dispatchKeyEvent", **down)
        self.call("Input.dispatchKeyEvent", type="keyUp", key=key, code=code or key, windowsVirtualKeyCode=key_code)

    def goto(self, url, ready="document.readyState === 'complete'"):
        self.call("Page.navigate", url=url)
        self.wait(ready)

    def wait(self, condition, timeout=10):
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                if self.js(f"!!({condition})"):
                    return
            except RuntimeError:
                pass
            time.sleep(0.05)
        raise TimeoutError(f"timed out waiting for: {condition}")

    def click(self, selector):
        self.js(f"document.querySelector({json.dumps(selector)}).click()")

    def screenshot(self, path):
        data = self.call("Page.captureScreenshot", format="png")["data"]
        with open(path, "wb") as f:
            f.write(base64.b64decode(data))

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        shutil.rmtree(self.profile, ignore_errors=True)
