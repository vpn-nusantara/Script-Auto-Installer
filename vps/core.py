#!/usr/bin/env python3
# VPN NUSANTARA - mesin pengelola akun (dipakai oleh menu, panel web dan bot Telegram)
import os, sys, json, re, time, uuid, base64, fcntl, subprocess, secrets, hashlib, pwd, socket
import urllib.parse, urllib.request

DRY = os.environ.get("NUS_DRYRUN") == "1"
ROOT = os.environ.get("NUS_ROOT", "/etc/nusantara")
DB, CONF, BANNER = ROOT + "/db.json", ROOT + "/config.json", ROOT + "/banner.txt"
XRAY_CONF = ROOT + "/xray.json" if DRY else "/usr/local/etc/xray/config.json"
ZIVPN_CONF = ROOT + "/zivpn.json" if DRY else "/etc/zivpn/config.json"
XRAY_LOG = "/var/log/xray/access.log"
TYPES = ["ssh", "vmess", "vless", "trojan", "zivpn"]
XRAY_TYPES = ["vmess", "vless", "trojan"]
SERVICES = ["ssh", "dropbear", "stunnel4", "nginx", "xray", "nus-ws", "udp-custom", "zivpn",
            "nus-panel", "nus-bot", "nus-ttyd", "fail2ban", "cron"]
USER_RE = re.compile(r"^[a-z][a-z0-9_]{2,19}$")
PASS_RE = re.compile(r"^[A-Za-z0-9_@.\-]{3,64}$")
LOCK_SECONDS = 600
BRAND = "by : VPN NUSANTARA"
RAINBOW = ["#ff0000", "#ff7f00", "#ffd400", "#00c853", "#00b8d4", "#2979ff", "#aa00ff", "#ff00aa"]


def rainbow_html(txt):
    out, i = "", 0
    for ch in txt:
        if ch == " ":
            out += "&nbsp;"
            continue
        out += '<font color="%s">%s</font>' % (RAINBOW[i % len(RAINBOW)], ch)
        i += 1
    return out


DEFAULT_BANNER = """<center><h2 style="text-align:center"><b>%s</b></h2></center>
""" % rainbow_html("VPN NUSANTARA")


class NusError(Exception):
    pass


def sh(cmd, inp=None, check=False):
    if DRY:
        return ""
    try:
        p = subprocess.run(cmd, input=inp, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           universal_newlines=True, timeout=90)
    except Exception as e:
        if check:
            raise NusError(str(e))
        return ""
    if check and p.returncode != 0:
        raise NusError(p.stdout.strip() or "Perintah gagal: " + cmd[0])
    return p.stdout


def read_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def write_json(path, data, mode=0o600):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.chmod(tmp, mode)
    os.replace(tmp, path)


def empty_db():
    return {"accounts": {t: {} for t in TYPES}, "resellers": {}, "trials": {}}


def load_db():
    d = read_json(DB, empty_db())
    d.setdefault("accounts", {})
    for t in TYPES:
        d["accounts"].setdefault(t, {})
    d.setdefault("resellers", {})
    d.setdefault("trials", {})
    return d


def conf():
    return read_json(CONF, {})


def save_conf(c):
    write_json(CONF, c)


class Store:
    """Buka db dengan kunci file supaya cron, bot dan panel tidak saling menimpa."""

    def __enter__(self):
        os.makedirs(ROOT, exist_ok=True)
        self.f = open(DB + ".lock", "w")
        fcntl.flock(self.f, fcntl.LOCK_EX)
        self.d = load_db()
        return self.d

    def __exit__(self, et, ev, tb):
        if et is None:
            write_json(DB, self.d)
        fcntl.flock(self.f, fcntl.LOCK_UN)
        self.f.close()


# ---------- pengguna sistem (SSH) ----------
def sys_user(u):
    try:
        return pwd.getpwnam(u)
    except KeyError:
        return None


def managed(u):
    p = sys_user(u)
    return p is None or (p.pw_uid >= 1000 and p.pw_shell == "/bin/false")


def ssh_apply(rec):
    u = rec["user"]
    if not USER_RE.match(u) or not PASS_RE.match(rec["secret"]) or not managed(u):
        raise NusError("Username '%s' tidak bisa dipakai" % u)
    date = time.strftime("%Y-%m-%d", time.localtime(rec["exp"] + 86400))
    if DRY:
        return
    if sys_user(u) is None:
        sh(["useradd", "-M", "-s", "/bin/false", "-e", date, u], check=True)
    else:
        sh(["chage", "-E", date, u])
    sh(["chpasswd"], inp="%s:%s\n" % (u, rec["secret"]), check=True)


def ssh_remove(u):
    if DRY or sys_user(u) is None or not managed(u):
        return
    sh(["pkill", "-KILL", "-u", u])
    sh(["userdel", "-f", u])


# ---------- Xray & ZIVPN ----------
def xray_config(d):
    now = time.time()

    def act(t):
        return [r for r in d["accounts"][t].values() if r.get("locked_until", 0) < now]

    vm = {"clients": [{"id": r["secret"], "alterId": 0, "email": r["user"] + "@vmess"} for r in act("vmess")]}
    vl = {"clients": [{"id": r["secret"], "email": r["user"] + "@vless"} for r in act("vless")], "decryption": "none"}
    tr = {"clients": [{"password": r["secret"], "email": r["user"] + "@trojan"} for r in act("trojan")]}

    def inb(tag, port, proto, settings, net, key):
        ss = {"network": net}
        if net == "ws":
            ss["wsSettings"] = {"path": key}
        else:
            ss["grpcSettings"] = {"serviceName": key}
        return {"tag": tag, "listen": "127.0.0.1", "port": port, "protocol": proto, "settings": settings,
                "streamSettings": ss, "sniffing": {"enabled": True, "destOverride": ["http", "tls"]}}

    return {
        "log": {"access": XRAY_LOG, "error": "/var/log/xray/error.log", "loglevel": "warning"},
        "inbounds": [
            inb("vmess-ws", 10001, "vmess", vm, "ws", "/vmess"),
            inb("vless-ws", 10002, "vless", vl, "ws", "/vless"),
            inb("trojan-ws", 10003, "trojan", tr, "ws", "/trojan-ws"),
            inb("vmess-grpc", 10004, "vmess", vm, "grpc", "vmess-grpc"),
            inb("vless-grpc", 10005, "vless", vl, "grpc", "vless-grpc"),
            inb("trojan-grpc", 10006, "trojan", tr, "grpc", "trojan-grpc"),
        ],
        "outbounds": [{"protocol": "freedom", "tag": "direct"}, {"protocol": "blackhole", "tag": "blocked"}],
        "routing": {"domainStrategy": "AsIs", "rules": [
            {"type": "field", "ip": ["geoip:private"], "outboundTag": "blocked"},
            {"type": "field", "protocol": ["bittorrent"], "outboundTag": "blocked"}]},
    }


def sync_xray(d):
    new = xray_config(d)
    if read_json(XRAY_CONF, None) == new:
        return False
    write_json(XRAY_CONF, new, 0o644)
    sh(["systemctl", "restart", "xray"])
    return True


def sync_zivpn(d):
    c = read_json(ZIVPN_CONF, None)
    if c is None:
        if not DRY:
            return False
        c = {}
    pw = sorted(r["secret"] for r in d["accounts"]["zivpn"].values())
    if not pw:
        pw = ["nus-" + hashlib.sha256((conf().get("api_key", "x")).encode()).hexdigest()[:20]]
    c.setdefault("auth", {"mode": "passwords"})
    if c["auth"].get("config") == pw:
        return False
    c["auth"]["config"] = pw
    write_json(ZIVPN_CONF, c, 0o600)
    sh(["systemctl", "restart", "zivpn"])
    return True


def sync_all(d):
    sync_xray(d)
    sync_zivpn(d)


# ---------- operasi akun ----------
def check_type(t):
    if t not in TYPES:
        raise NusError("Tipe harus salah satu dari: " + ", ".join(TYPES))


def gen_pass(n=10):
    return "".join(secrets.choice("abcdefghjkmnpqrstuvwxyz23456789") for _ in range(n))


def create(t, user, days=30, limit=2, secret=None, owner="admin", minutes=None):
    check_type(t)
    user = (user or "").strip().lower()
    if not USER_RE.match(user):
        raise NusError("Username 3-20 karakter: huruf kecil, angka, garis bawah, diawali huruf")
    try:
        days, limit = int(days), int(limit)
    except (TypeError, ValueError):
        raise NusError("Masa aktif dan batas login harus angka")
    if not minutes and not 1 <= days <= 3650:
        raise NusError("Masa aktif 1 - 3650 hari")
    if not 0 <= limit <= 100:
        raise NusError("Batas login 0 - 100 (0 = tanpa batas)")
    if t in ("ssh", "zivpn"):
        secret = secret or gen_pass()
        if not PASS_RE.match(secret):
            raise NusError("Password 3-64 karakter: huruf, angka dan _ @ . -")
    else:
        secret = str(uuid.uuid4())
    now = int(time.time())
    rec = {"user": user, "secret": secret, "exp": now + (int(minutes) * 60 if minutes else days * 86400),
           "limit": limit, "owner": owner, "created": now}
    with Store() as d:
        if user in d["accounts"][t]:
            raise NusError("Akun %s '%s' sudah ada" % (t, user))
        if t == "ssh" and sys_user(user) is not None:
            raise NusError("Username '%s' sudah dipakai sistem" % user)
        if t == "zivpn" and any(r["secret"] == secret for r in d["accounts"][t].values()):
            raise NusError("Password ZIVPN sudah dipakai akun lain")
        if t == "ssh":
            ssh_apply(rec)
        d["accounts"][t][user] = rec
        sync_all(d) if t != "ssh" else None
    return details(t, rec)


def get(d, t, user, owner=None):
    check_type(t)
    rec = d["accounts"][t].get((user or "").strip().lower())
    if not rec or (owner and rec.get("owner") != owner):
        raise NusError("Akun %s '%s' tidak ditemukan" % (t, user))
    return rec


def delete(t, user, owner=None):
    with Store() as d:
        rec = get(d, t, user, owner)
        del d["accounts"][t][rec["user"]]
        if t == "ssh":
            ssh_remove(rec["user"])
        else:
            sync_all(d)
    return rec


def renew(t, user, days, owner=None):
    try:
        days = int(days)
    except (TypeError, ValueError):
        raise NusError("Jumlah hari harus angka")
    if not 1 <= days <= 3650:
        raise NusError("Perpanjangan 1 - 3650 hari")
    with Store() as d:
        rec = get(d, t, user, owner)
        rec["exp"] = max(rec["exp"], int(time.time())) + days * 86400
        if t == "ssh":
            ssh_apply(rec)
    return details(t, rec)


def show(t, user):
    return details(t, get(load_db(), t, user))


def listing(t=None, owner=None):
    d = load_db()
    out = []
    for ty in ([t] if t else TYPES):
        check_type(ty)
        for r in d["accounts"][ty].values():
            if owner and r.get("owner") != owner:
                continue
            x = dict(r)
            x["type"] = ty
            x["locked"] = r.get("locked_until", 0) > time.time()
            x["days_left"] = max(0, int((r["exp"] - time.time()) // 86400))
            out.append(x)
    return sorted(out, key=lambda r: (r["type"], r["user"]))


def fmt_time(ts):
    return time.strftime("%d-%m-%Y %H:%M", time.localtime(ts))


def details(t, rec):
    c = conf()
    dom = c.get("domain", "domain-anda")
    u, s = rec["user"], rec["secret"]
    q = urllib.parse.quote
    lines = [("Tipe", t.upper()), ("Username", u), ("Domain", dom), ("IP", c.get("ip", "-"))]
    links = {}
    if t == "ssh":
        lines += [("Password", s), ("OpenSSH", "22"), ("Dropbear", "109, 143"), ("SSL/TLS (Stunnel)", "447, 777"),
                  ("SSH WebSocket TLS", "443"), ("SSH WebSocket HTTP", "80"), ("SSH UDP (UDP Custom)", "1-65535"),
                  ("Payload WS", "GET / HTTP/1.1[crlf]Host: %s[crlf]Upgrade: websocket[crlf][crlf]" % dom)]
        links["HTTP Custom UDP"] = "%s:1-65535@%s:%s" % (dom, u, s)
        links["SSH WS TLS"] = "%s:443@%s:%s" % (dom, u, s)
        links["SSH WS HTTP"] = "%s:80@%s:%s" % (dom, u, s)
    elif t == "zivpn":
        lines += [("Password", s), ("Port UDP", "6000-19999 (utama 5667)")]
        links["ZIVPN"] = "Host: %s | Password: %s" % (dom, s)
    else:
        lines += [("UUID / Password", s), ("Port TLS", "443"), ("Port HTTP", "80"),
                  ("Path WebSocket", "/vmess" if t == "vmess" else "/vless" if t == "vless" else "/trojan-ws"),
                  ("Service gRPC", t + "-grpc")]
        if t == "vmess":
            def vm(port, tls, net, path):
                o = {"v": "2", "ps": "%s-%s-%s" % (u, net, "tls" if tls else "http"), "add": dom, "port": str(port),
                     "id": s, "aid": "0", "net": net, "type": "none", "host": dom, "path": path,
                     "tls": "tls" if tls else "", "sni": dom if tls else ""}
                return "vmess://" + base64.b64encode(json.dumps(o).encode()).decode()
            links["VMess WS TLS"] = vm(443, True, "ws", "/vmess")
            links["VMess WS HTTP"] = vm(80, False, "ws", "/vmess")
            links["VMess gRPC"] = vm(443, True, "grpc", "vmess-grpc")
        elif t == "vless":
            b = "vless://%s@%s:" % (s, dom)
            links["VLESS WS TLS"] = b + "443?path=%s&security=tls&encryption=none&type=ws&host=%s&sni=%s#%s" % (q("/vless", safe=""), dom, dom, q(u + "-ws-tls"))
            links["VLESS WS HTTP"] = b + "80?path=%s&security=none&encryption=none&type=ws&host=%s#%s" % (q("/vless", safe=""), dom, q(u + "-ws-http"))
            links["VLESS gRPC"] = b + "443?mode=gun&security=tls&encryption=none&type=grpc&serviceName=vless-grpc&sni=%s#%s" % (dom, q(u + "-grpc"))
        else:
            b = "trojan://%s@%s:" % (s, dom)
            links["Trojan WS TLS"] = b + "443?path=%s&security=tls&type=ws&host=%s&sni=%s#%s" % (q("/trojan-ws", safe=""), dom, dom, q(u + "-ws-tls"))
            links["Trojan WS HTTP"] = b + "80?path=%s&security=none&type=ws&host=%s#%s" % (q("/trojan-ws", safe=""), dom, q(u + "-ws-http"))
            links["Trojan gRPC"] = b + "443?mode=gun&security=tls&type=grpc&serviceName=trojan-grpc&sni=%s#%s" % (dom, q(u + "-grpc"))
    lines += [("Batas login", "tanpa batas" if not rec["limit"] else "%s perangkat" % rec["limit"]),
              ("Berlaku sampai", fmt_time(rec["exp"]))]
    return {"type": t, "user": u, "secret": s, "exp": rec["exp"], "limit": rec["limit"], "owner": rec.get("owner"),
            "domain": dom, "lines": [list(x) for x in lines], "links": links, "brand": BRAND}


def text(det):
    w = max(len(k) for k, _ in det["lines"])
    out = ["━" * 44, "  AKUN %s  •  VPN NUSANTARA" % det["type"].upper(), "━" * 44]
    out += ["  %s : %s" % (k.ljust(w), v) for k, v in det["lines"]]
    for k, v in det["links"].items():
        out += ["━" * 44, "  " + k, "  " + v]
    out += ["━" * 44, "  " + BRAND]
    return "\n".join(out)


# ---------- pengguna online & batas login ----------
def ssh_sessions(users):
    out = []
    if DRY:
        return out
    ips, drop = {}, {}
    j = sh(["journalctl", "-u", "ssh", "-u", "sshd", "-u", "dropbear", "--since", "-48h", "--no-pager", "-o", "short"])
    for line in j.splitlines():
        m = re.search(r"sshd(?:-session)?\[(\d+)\]: Accepted \S+ for (\S+) from (\S+)", line)
        if m:
            ips[m.group(1)] = m.group(3)
            continue
        m = re.search(r"dropbear\[(\d+)\]: Password auth succeeded for '([^']+)' from (\S+?):\d+\s*$", line)
        if m:
            drop[m.group(1)] = (m.group(2), m.group(3))
    for line in sh(["ps", "-eo", "pid=,ppid=,args="]).splitlines():
        p = line.split(None, 2)
        if len(p) < 3:
            continue
        m = re.match(r"sshd(?:-session)?: ([^\s@\[]+)(?:@\S+)?\s*$", p[2])
        if m and m.group(1) in users:
            out.append({"type": "ssh", "user": m.group(1), "pid": int(p[0]), "ip": ips.get(p[1], "-"), "via": "OpenSSH"})
    for pid, (u, ip) in drop.items():
        try:
            with open("/proc/%s/cmdline" % pid) as f:
                alive = "dropbear" in f.read()
        except Exception:
            alive = False
        if alive and u in users:
            out.append({"type": "ssh", "user": u, "pid": int(pid), "ip": ip, "via": "Dropbear"})
    return out


def xray_sessions(window=90):
    """Hasil: {(tipe, user): set(ip)} dari log akses Xray dalam `window` detik terakhir."""
    res = {}
    try:
        with open(XRAY_LOG, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 400000))
            data = f.read().decode("utf-8", "ignore")
    except Exception:
        return res
    now = time.time()
    rx = re.compile(r"^(\d{4}/\d\d/\d\d \d\d:\d\d:\d\d)\S*\s+(?:from\s+)?(?:tcp:|udp:)?\[?([0-9a-fA-F:.]+?)\]?:\d+\s+accepted.*email:\s*(\S+)@(\w+)")
    for line in data.splitlines():
        m = rx.match(line)
        if not m:
            continue
        try:
            ts = time.mktime(time.strptime(m.group(1), "%Y/%m/%d %H:%M:%S"))
        except ValueError:
            continue
        if now - ts <= window:
            res.setdefault((m.group(4), m.group(3)), set()).add(m.group(2))
    return res


def online():
    d = load_db()
    out = ssh_sessions(set(d["accounts"]["ssh"]))
    for (t, u), ips in xray_sessions().items():
        if t in XRAY_TYPES and u in d["accounts"][t]:
            for ip in sorted(ips):
                out.append({"type": t, "user": u, "pid": None, "ip": ip, "via": "Xray"})
    return out


def kick(t, user):
    """Putuskan pengguna: sesi SSH dimatikan, akun Xray dikunci sementara."""
    with Store() as d:
        rec = get(d, t, user)
        if t == "ssh":
            for s in ssh_sessions({rec["user"]}):
                sh(["kill", "-9", str(s["pid"])])
        elif t in XRAY_TYPES:
            rec["locked_until"] = int(time.time()) + LOCK_SECONDS
            sync_xray(d)
        else:
            raise NusError("ZIVPN tidak mendukung pemutusan per pengguna")
    return True


def cron():
    """Dijalankan tiap menit: hapus akun kedaluwarsa dan tegakkan batas login."""
    now = time.time()
    with Store() as d:
        for t in TYPES:
            for u in [u for u, r in d["accounts"][t].items() if r["exp"] <= now]:
                del d["accounts"][t][u]
                if t == "ssh":
                    ssh_remove(u)
        by = {}
        for s in ssh_sessions(set(d["accounts"]["ssh"])):
            by.setdefault(s["user"], []).append(s["pid"])
        for u, pids in by.items():
            lim = d["accounts"]["ssh"][u].get("limit", 0)
            if lim and len(pids) > lim:
                for pid in sorted(pids)[lim:]:
                    sh(["kill", "-9", str(pid)])
        for (t, u), ips in xray_sessions(60).items():
            rec = d["accounts"].get(t, {}).get(u) if t in XRAY_TYPES else None
            if rec and rec.get("limit") and len(ips) > rec["limit"] and rec.get("locked_until", 0) < now:
                rec["locked_until"] = int(now) + LOCK_SECONDS
        d["trials"] = {k: v for k, v in d["trials"].items() if now - v < 86400}
        sync_all(d)


# ---------- info server ----------
def info():
    c = conf()
    d = load_db()

    def rd(p):
        try:
            with open(p) as f:
                return f.read()
        except Exception:
            return ""
    osname = ""
    for line in rd("/etc/os-release").splitlines():
        if line.startswith("PRETTY_NAME="):
            osname = line.split("=", 1)[1].strip('"')
    mem = {}
    for line in rd("/proc/meminfo").splitlines():
        p = line.split()
        if len(p) >= 2:
            mem[p[0].rstrip(":")] = int(p[1]) // 1024
    st = os.statvfs("/")
    up = float((rd("/proc/uptime") or "0").split()[0])
    services = {}
    for s in SERVICES:
        r = sh(["systemctl", "is-active", s]).strip().splitlines()
        services[s] = r[-1] if r else "unknown"
    if services.get("ssh") != "active" and sh(["systemctl", "is-active", "sshd"]).strip() == "active":
        services["ssh"] = "active"
    return {
        "brand": BRAND, "domain": c.get("domain", "-"), "ip": c.get("ip", "-"), "hostname": socket.gethostname(),
        "os": osname, "kernel": os.uname().release, "cpu": os.cpu_count(), "load": rd("/proc/loadavg").split()[:3],
        "uptime": int(up), "mem_total": mem.get("MemTotal", 0),
        "mem_used": mem.get("MemTotal", 0) - mem.get("MemAvailable", mem.get("MemFree", 0)),
        "swap_total": mem.get("SwapTotal", 0), "swap_used": mem.get("SwapTotal", 0) - mem.get("SwapFree", 0),
        "disk_total": st.f_blocks * st.f_frsize // 1048576, "disk_used": (st.f_blocks - st.f_bfree) * st.f_frsize // 1048576,
        "services": services, "counts": {t: len(d["accounts"][t]) for t in TYPES},
        "bot": bool(c.get("bot_token")), "dry_run": DRY,
    }


# ---------- banner, backup, restore ----------
def banner_get():
    try:
        with open(BANNER) as f:
            return f.read()
    except Exception:
        return ""


def banner_set(txt):
    if len(txt) > 8000:
        raise NusError("Banner terlalu panjang (maks 8000 karakter)")
    with open(BANNER, "w") as f:
        f.write(txt if txt.endswith("\n") else txt + "\n")
    os.chmod(BANNER, 0o644)


def backup():
    return {"app": "vpn-nusantara", "version": 1, "created": int(time.time()), "domain": conf().get("domain"),
            "db": load_db(), "banner": banner_get()}


def restore(data):
    if not isinstance(data, dict) or data.get("app") != "vpn-nusantara" or not isinstance(data.get("db"), dict):
        raise NusError("File backup tidak valid")
    new = empty_db()
    src = data["db"].get("accounts", {})
    for t in TYPES:
        for u, r in (src.get(t) or {}).items():
            try:
                rec = {"user": str(r["user"]), "secret": str(r["secret"]), "exp": int(r["exp"]),
                       "limit": int(r.get("limit", 0)), "owner": str(r.get("owner", "admin")),
                       "created": int(r.get("created", time.time()))}
            except Exception:
                raise NusError("Data akun rusak pada %s/%s" % (t, u))
            if rec["user"] != u or not USER_RE.match(u) or not PASS_RE.match(rec["secret"]):
                raise NusError("Data akun tidak valid pada %s/%s" % (t, u))
            new["accounts"][t][u] = rec
    for k, v in (data["db"].get("resellers") or {}).items():
        new["resellers"][str(int(k))] = {"quota": int(v.get("quota", 0)), "used": int(v.get("used", 0))}
    skipped = []
    with Store() as d:
        for u in d["accounts"]["ssh"]:
            if u not in new["accounts"]["ssh"]:
                ssh_remove(u)
        for u, rec in list(new["accounts"]["ssh"].items()):
            try:
                ssh_apply(rec)
            except NusError:
                skipped.append(u)
                del new["accounts"]["ssh"][u]
        d.clear()
        d.update(new)
        sync_all(d)
    if isinstance(data.get("banner"), str) and data["banner"].strip():
        banner_set(data["banner"])
    return {"restored": {t: len(new["accounts"][t]) for t in TYPES}, "skipped": skipped}


# ---------- panel & telegram ----------
def hash_pw(pw, salt):
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 120000).hex()


def set_panel_pass(user, pw):
    if not re.match(r"^[A-Za-z0-9_.\-]{3,32}$", user or "") or len(pw or "") < 8:
        raise NusError("Username 3-32 karakter dan password minimal 8 karakter")
    c = conf()
    salt = secrets.token_hex(16)
    c.update({"panel_user": user, "panel_salt": salt, "panel_hash": hash_pw(pw, salt)})
    save_conf(c)
    h = sh(["openssl", "passwd", "-apr1", "-stdin"], inp=pw + "\n").strip()
    if h:
        with open(ROOT + "/htpasswd", "w") as f:
            f.write("%s:%s\n" % (user, h))
        os.chmod(ROOT + "/htpasswd", 0o644)


def tg(method, params=None, file=None, timeout=70):
    token = conf().get("bot_token")
    if not token:
        raise NusError("Token bot Telegram belum diatur")
    url = "https://api.telegram.org/bot%s/%s" % (token, method)
    if file:
        b = "----nus" + secrets.token_hex(8)
        body = b""
        for k, v in (params or {}).items():
            body += ("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (b, k, v)).encode()
        body += ("--%s\r\nContent-Disposition: form-data; name=\"document\"; filename=\"%s\"\r\nContent-Type: application/json\r\n\r\n" % (b, file[0])).encode()
        body += file[1] + ("\r\n--%s--\r\n" % b).encode()
        req = urllib.request.Request(url, body, {"Content-Type": "multipart/form-data; boundary=" + b})
    else:
        req = urllib.request.Request(url, json.dumps(params or {}).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def backup_to_telegram():
    c = conf()
    if not c.get("admin_id"):
        raise NusError("ID admin Telegram belum diatur")
    name = "backup-nusantara-%s.json" % time.strftime("%Y%m%d-%H%M")
    tg("sendDocument", {"chat_id": c["admin_id"], "caption": "Backup akun %s\n%s" % (c.get("domain", ""), BRAND)},
       file=(name, json.dumps(backup()).encode()))


def init(domain, panel_user, panel_pass, bot_token="", admin_id="", ip=""):
    os.makedirs(ROOT, exist_ok=True)
    c = conf()
    c.update({"domain": domain, "ip": ip})
    c.setdefault("api_key", secrets.token_hex(24))
    if bot_token:
        c["bot_token"] = bot_token
    if admin_id:
        c["admin_id"] = int(admin_id)
    save_conf(c)
    set_panel_pass(panel_user, panel_pass)
    if not os.path.exists(BANNER):
        banner_set(DEFAULT_BANNER)
    with Store() as d:
        sync_all(d)


# ---------- CLI ----------
def human_info():
    i = info()
    up = i["uptime"]
    print("  OS       : %s" % i["os"])
    print("  Domain   : %s   IP: %s" % (i["domain"], i["ip"]))
    print("  CPU/Load : %s core  •  %s" % (i["cpu"], " ".join(i["load"])))
    print("  RAM      : %s / %s MB   Disk: %s / %s MB" % (i["mem_used"], i["mem_total"], i["disk_used"], i["disk_total"]))
    print("  Uptime   : %d hari %d jam %d menit" % (up // 86400, up % 86400 // 3600, up % 3600 // 60))
    print("  Akun     : " + "  ".join("%s=%s" % (k.upper(), v) for k, v in i["counts"].items()))


def main(a):
    cmd = a[0] if a else "help"
    if cmd == "add":
        print(text(create(a[1], a[2], a[3] if len(a) > 3 else 30, a[4] if len(a) > 4 else 2, a[5] if len(a) > 5 else None)))
    elif cmd == "del":
        delete(a[1], a[2])
        print("Akun %s '%s' dihapus" % (a[1], a[2]))
    elif cmd == "renew":
        print(text(renew(a[1], a[2], a[3])))
    elif cmd == "show":
        print(text(show(a[1], a[2])))
    elif cmd == "list":
        rows = listing(a[1] if len(a) > 1 else None)
        print("  %-7s %-20s %-17s %-6s %s" % ("TIPE", "USERNAME", "BERLAKU SAMPAI", "LIMIT", "STATUS"))
        print("  " + "─" * 62)
        for r in rows:
            print("  %-7s %-20s %-17s %-6s %s" % (r["type"], r["user"], fmt_time(r["exp"]), r["limit"] or "∞",
                                                  "terkunci" if r["locked"] else "aktif"))
        print("  " + "─" * 62 + "\n  Total: %d akun" % len(rows))
    elif cmd == "online":
        rows = online()
        print("  %-7s %-20s %-22s %s" % ("TIPE", "USERNAME", "IP", "LEWAT"))
        print("  " + "─" * 62)
        for r in rows:
            print("  %-7s %-20s %-22s %s" % (r["type"], r["user"], r["ip"], r["via"]))
        print("  " + "─" * 62 + "\n  Total: %d koneksi" % len(rows))
    elif cmd == "kick":
        kick(a[1], a[2])
        print("Pengguna diputus")
    elif cmd == "info":
        human_info()
    elif cmd == "services":
        for k, v in info()["services"].items():
            print("  %-12s %s" % (k, "● aktif" if v == "active" else "○ " + v))
    elif cmd == "cron":
        cron()
    elif cmd == "sync":
        with Store() as d:
            sync_all(d)
    elif cmd == "backup":
        if len(a) > 1 and a[1] == "--telegram":
            backup_to_telegram()
            print("Backup dikirim ke Telegram admin")
        else:
            path = a[1] if len(a) > 1 else "/root/backup-nusantara-%s.json" % time.strftime("%Y%m%d-%H%M")
            write_json(path, backup())
            print("Backup tersimpan: " + path)
    elif cmd == "restore":
        print("Restore selesai: %s" % json.dumps(restore(read_json(a[1], None))))
    elif cmd == "panel-pass":
        set_panel_pass(a[1], a[2])
        print("Login panel diperbarui")
    elif cmd == "set":
        if a[1] not in ("bot_token", "admin_id", "domain", "ip"):
            raise NusError("Kunci tidak dikenal")
        c = conf()
        c[a[1]] = int(a[2]) if a[1] == "admin_id" else a[2]
        save_conf(c)
    elif cmd == "get":
        print(conf().get(a[1], ""))
    elif cmd == "init":
        init(*a[1:7])
    else:
        print("Pakai: nus add|del|renew|show|list|online|kick|info|services|backup|restore|panel-pass|set|get|sync|cron")


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except NusError as e:
        print("Gagal: %s" % e)
        sys.exit(1)
    except IndexError:
        print("Argumen kurang. Jalankan 'nus help'")
        sys.exit(1)
