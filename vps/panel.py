#!/usr/bin/env python3
# VPN NUSANTARA - panel web + API (hanya pustaka bawaan Python, berjalan di belakang nginx /panel/)
import os, sys, json, time, hmac, secrets, urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
import core  # noqa: E402

SESSIONS, FAILS = {}, {}
MAX_BODY = 10 * 1024 * 1024


class Server(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class H(BaseHTTPRequestHandler):
    server_version = "Nusantara"

    def log_message(self, *a):
        pass

    def ip(self):
        return self.headers.get("X-Real-IP") or self.client_address[0]

    def send(self, code, data, headers=None, ctype="application/json"):
        body = data if isinstance(data, bytes) else json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Frame-Options", "DENY")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def body(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except (TypeError, ValueError):
            raise core.NusError("Panjang data tidak valid")
        if n < 0 or n > MAX_BODY:
            raise core.NusError("Ukuran data tidak diizinkan")
        try:
            return json.loads(self.rfile.read(n).decode() or "{}")
        except (UnicodeDecodeError, ValueError):
            raise core.NusError("Format data tidak valid")

    def authed(self):
        key = self.headers.get("X-API-Key")
        api_key = core.conf().get("api_key", "")
        if key and api_key and hmac.compare_digest(key, api_key):
            return True
        for part in (self.headers.get("Cookie") or "").split(";"):
            k, _, v = part.strip().partition("=")
            if k == "nus_session" and SESSIONS.get(v, 0) > time.time():
                return True
        return False

    def login(self):
        ip, now = self.ip(), time.time()
        f = [t for t in FAILS.get(ip, []) if now - t < 900]
        if len(f) >= 5:
            return self.send(429, {"error": "Terlalu banyak percobaan. Coba lagi 15 menit lagi."})
        b, c = self.body(), core.conf()
        ok = c.get("panel_hash") and hmac.compare_digest(str(b.get("username", "")), c.get("panel_user", "")) and \
            hmac.compare_digest(core.hash_pw(str(b.get("password", "")), c["panel_salt"]), c["panel_hash"])
        if not ok:
            FAILS[ip] = f + [now]
            return self.send(401, {"error": "Username atau password salah"})
        FAILS.pop(ip, None)
        # Bersihkan sesi dan catatan gagal yang kedaluwarsa agar memori tidak terus bertambah.
        for token, expiry in list(SESSIONS.items()):
            if expiry <= now:
                SESSIONS.pop(token, None)
        for addr, attempts in list(FAILS.items()):
            recent = [t for t in attempts if now - t < 900]
            if recent:
                FAILS[addr] = recent
            else:
                FAILS.pop(addr, None)
        tok = secrets.token_urlsafe(32)
        SESSIONS[tok] = now + 43200
        self.send(200, {"ok": True}, {"Set-Cookie": "nus_session=%s; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=43200" % tok})

    def route(self, method):
        u = urllib.parse.urlparse(self.path)
        path = u.path.rstrip("/") or "/"
        q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        if method == "GET" and path == "/":
            with open(HERE + "/panel.html", "rb") as f:
                return self.send(200, f.read(), ctype="text/html; charset=utf-8")
        if not path.startswith("/api/"):
            return self.send(404, {"error": "Tidak ditemukan"})
        p = path[5:]
        if method == "POST" and p == "login":
            return self.login()
        if not self.authed():
            return self.send(401, {"error": "Belum login"})
        if method == "POST" and p == "logout":
            for part in (self.headers.get("Cookie") or "").split(";"):
                k, _, v = part.strip().partition("=")
                if k == "nus_session":
                    SESSIONS.pop(v, None)
                    break
            return self.send(200, {"ok": True}, {"Set-Cookie": "nus_session=; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=0"})
        if method == "GET":
            if p == "me":
                return self.send(200, {"user": core.conf().get("panel_user")})
            if p == "info":
                return self.send(200, core.info())
            if p == "accounts":
                return self.send(200, core.listing(q.get("type") or None))
            if p == "accounts/detail":
                return self.send(200, core.show(q.get("type"), q.get("user")))
            if p == "online":
                return self.send(200, core.online())
            if p == "banner":
                return self.send(200, {"banner": core.banner_get()})
            if p == "backup":
                return self.send(200, core.backup())
        if method == "POST":
            b = self.body()
            if p == "accounts":
                return self.send(200, core.create(b.get("type"), b.get("user"), b.get("days", 30), b.get("limit", 2),
                                                  b.get("password") or None))
            if p == "accounts/renew":
                return self.send(200, core.renew(b.get("type"), b.get("user"), b.get("days")))
            if p == "accounts/delete":
                core.delete(b.get("type"), b.get("user"))
                return self.send(200, {"ok": True})
            if p == "online/kick":
                core.kick(b.get("type"), b.get("user"))
                return self.send(200, {"ok": True})
            if p == "banner":
                core.banner_set(str(b.get("banner", "")))
                return self.send(200, {"ok": True})
            if p == "restore":
                return self.send(200, core.restore(b))
        self.send(404, {"error": "Tidak ditemukan"})

    def handle_any(self, method):
        try:
            self.route(method)
        except core.NusError as e:
            self.send(400, {"error": str(e)})
        except Exception as e:
            self.send(500, {"error": "Kesalahan server: %s" % e})

    def do_GET(self):
        self.handle_any("GET")

    def do_POST(self):
        self.handle_any("POST")


if __name__ == "__main__":
    port = int(os.environ.get("NUS_PANEL_PORT", "10020"))
    Server(("127.0.0.1", port), H).serve_forever()
