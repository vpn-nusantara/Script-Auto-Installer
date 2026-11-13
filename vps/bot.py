#!/usr/bin/env python3
# VPN NUSANTARA - bot Telegram (admin, reseller, dan akun trial untuk umum)
import os, sys, time, html, random

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import core  # noqa: E402

TRIAL_MINUTES, TRIAL_MAX_ACTIVE, RESELLER_MAX_DAYS = 60, 20, 30
HELP_PUBLIC = """<b>VPN NUSANTARA</b>
/trial &lt;tipe&gt; - akun percobaan %d menit (1x per 24 jam)
Tipe: ssh, vmess, vless, trojan, zivpn
/id - lihat ID Telegram Anda""" % TRIAL_MINUTES
HELP_RESELLER = """
<b>Reseller</b>
/buat &lt;tipe&gt; &lt;user&gt; &lt;hari&gt; [limit] - buat akun (1 kuota)
/perpanjang &lt;tipe&gt; &lt;user&gt; &lt;hari&gt; - perpanjang (1 kuota)
/hapus &lt;tipe&gt; &lt;user&gt; - hapus akun
/detail &lt;tipe&gt; &lt;user&gt; - lihat detail akun
/list [tipe] - daftar akun
/kuota - sisa kuota"""
HELP_ADMIN = """
<b>Admin</b>
/online - pengguna yang sedang online
/info - status server
/backup - kirim file backup
/addreseller &lt;id&gt; &lt;kuota&gt; - tambah / isi kuota reseller
/delreseller &lt;id&gt; - hapus reseller
/resellers - daftar reseller"""


def send(chat, text):
    for i in range(0, len(text), 3800):
        try:
            core.tg("sendMessage", {"chat_id": chat, "text": text[i:i + 3800], "parse_mode": "HTML",
                                    "disable_web_page_preview": True}, timeout=20)
        except Exception as e:
            print("send gagal:", e, flush=True)


def card(det):
    out = ["<b>AKUN %s</b>" % det["type"].upper()]
    out += ["%s: <code>%s</code>" % (html.escape(k), html.escape(str(v))) for k, v in det["lines"]]
    for k, v in det["links"].items():
        out.append("\n<b>%s</b>\n<code>%s</code>" % (html.escape(k), html.escape(v)))
    out.append("\n<i>%s</i>" % core.BRAND)
    return "\n".join(out)


def use_quota(uid):
    with core.Store() as d:
        r = d["resellers"].get(str(uid))
        if not r or r["used"] >= r["quota"]:
            raise core.NusError("Kuota reseller habis. Hubungi admin.")
        r["used"] += 1


def refund(uid):
    with core.Store() as d:
        r = d["resellers"].get(str(uid))
        if r and r["used"] > 0:
            r["used"] -= 1


def trial(uid, t):
    core.check_type(t)
    with core.Store() as d:
        if time.time() - d["trials"].get(str(uid), 0) < 86400:
            raise core.NusError("Anda sudah mengambil trial dalam 24 jam terakhir")
        active = sum(1 for ty in core.TYPES for r in d["accounts"][ty].values() if r.get("owner") == "trial")
        if active >= TRIAL_MAX_ACTIVE:
            raise core.NusError("Slot trial sedang penuh, coba lagi nanti")
        d["trials"][str(uid)] = int(time.time())
    try:
        return core.create(t, "trial%04d" % random.randint(0, 9999), limit=1, owner="trial", minutes=TRIAL_MINUTES)
    except core.NusError:
        with core.Store() as d:
            d["trials"].pop(str(uid), None)
        raise


def handle(msg):
    text = (msg.get("text") or "").strip()
    if not text.startswith("/") or msg["chat"].get("type") != "private":
        return
    uid, chat = msg["from"]["id"], msg["chat"]["id"]
    a = text.split()
    cmd = a[0][1:].split("@")[0].lower()
    c = core.conf()
    admin = bool(c.get("admin_id")) and uid == c.get("admin_id")
    reseller = str(uid) in core.load_db()["resellers"]
    owner = None if admin else "tg:%s" % uid
    if cmd in ("start", "help", "menu"):
        return send(chat, HELP_PUBLIC + (HELP_RESELLER if admin or reseller else "") + (HELP_ADMIN if admin else "")
                    + "\n\n<i>%s</i>" % core.BRAND)
    if cmd == "id":
        return send(chat, "ID Telegram Anda: <code>%s</code>" % uid)
    if cmd == "trial":
        return send(chat, card(trial(uid, a[1].lower())) + "\nTrial berlaku %d menit." % TRIAL_MINUTES)
    if not (admin or reseller):
        return send(chat, "Perintah ini hanya untuk admin dan reseller.\n" + HELP_PUBLIC)
    if cmd == "buat":
        days = int(a[3])
        if not admin:
            if days > RESELLER_MAX_DAYS:
                raise core.NusError("Reseller maksimal %d hari per akun" % RESELLER_MAX_DAYS)
            use_quota(uid)
        try:
            det = core.create(a[1].lower(), a[2], days, a[4] if len(a) > 4 else 2, owner=owner or "admin")
        except core.NusError:
            if not admin:
                refund(uid)
            raise
        return send(chat, card(det))
    if cmd == "perpanjang":
        days = int(a[3])
        if not admin:
            if days > RESELLER_MAX_DAYS:
                raise core.NusError("Reseller maksimal %d hari per perpanjangan" % RESELLER_MAX_DAYS)
            core.get(core.load_db(), a[1].lower(), a[2], owner)
            use_quota(uid)
        det = core.renew(a[1].lower(), a[2], days, owner)
        return send(chat, "Diperpanjang.\n" + card(det))
    if cmd == "hapus":
        core.delete(a[1].lower(), a[2], owner)
        return send(chat, "Akun %s <code>%s</code> dihapus." % (html.escape(a[1]), html.escape(a[2])))
    if cmd == "detail":
        core.get(core.load_db(), a[1].lower(), a[2], owner)
        return send(chat, card(core.show(a[1].lower(), a[2])))
    if cmd == "list":
        rows = core.listing(a[1].lower() if len(a) > 1 else None, owner)
        body = "\n".join("%s  <code>%s</code>  s/d %s" % (r["type"], r["user"], core.fmt_time(r["exp"])) for r in rows)
        return send(chat, "<b>Daftar akun (%d)</b>\n%s" % (len(rows), body or "Belum ada akun"))
    if cmd == "kuota":
        r = core.load_db()["resellers"].get(str(uid))
        return send(chat, "Kuota: tanpa batas (admin)" if admin else "Kuota terpakai %s dari %s" % (r["used"], r["quota"]))
    if not admin:
        return send(chat, "Perintah ini hanya untuk admin.")
    if cmd == "online":
        rows = core.online()
        body = "\n".join("%s  <code>%s</code>  %s  (%s)" % (r["type"], r["user"], r["ip"], r["via"]) for r in rows)
        return send(chat, "<b>Online (%d)</b>\n%s" % (len(rows), body or "Tidak ada pengguna online"))
    if cmd == "info":
        i = core.info()
        sv = "\n".join("%s %s" % ("🟢" if v == "active" else "🔴", k) for k, v in i["services"].items())
        return send(chat, "<b>%s</b>\n%s\nRAM %s/%s MB • Load %s\nAkun: %s\n\n%s" % (
            html.escape(i["domain"]), html.escape(i["os"]), i["mem_used"], i["mem_total"], " ".join(i["load"]),
            ", ".join("%s=%s" % kv for kv in i["counts"].items()), sv))
    if cmd == "backup":
        core.backup_to_telegram()
        return
    if cmd == "addreseller":
        rid, quota = str(int(a[1])), int(a[2])
        with core.Store() as d:
            r = d["resellers"].setdefault(rid, {"quota": 0, "used": 0})
            r["quota"] += quota
        send(int(rid), "Anda terdaftar sebagai reseller VPN NUSANTARA. Kuota ditambah %d akun. Ketik /menu" % quota)
        return send(chat, "Reseller <code>%s</code>: kuota %s, terpakai %s" % (rid, r["quota"], r["used"]))
    if cmd == "delreseller":
        with core.Store() as d:
            d["resellers"].pop(str(int(a[1])), None)
        return send(chat, "Reseller dihapus (akun yang sudah dibuat tetap aktif).")
    if cmd == "resellers":
        rs = core.load_db()["resellers"]
        return send(chat, "<b>Reseller</b>\n" + ("\n".join("<code>%s</code>  %s/%s" % (k, v["used"], v["quota"]) for k, v in rs.items()) or "Belum ada"))
    send(chat, "Perintah tidak dikenal. Ketik /menu")


def main():
    if not core.conf().get("bot_token"):
        print("Token bot belum diatur. Jalankan menu > Bot Telegram.", flush=True)
        time.sleep(3600)
        return
    offset = 0
    while True:
        try:
            res = core.tg("getUpdates", {"offset": offset, "timeout": 50, "allowed_updates": ["message"]})
        except Exception as e:
            print("getUpdates gagal:", e, flush=True)
            time.sleep(5)
            continue
        for up in res.get("result", []):
            offset = up["update_id"] + 1
            msg = up.get("message")
            if not msg or "from" not in msg:
                continue
            try:
                handle(msg)
            except core.NusError as e:
                send(msg["chat"]["id"], "Gagal: " + html.escape(str(e)))
            except (IndexError, ValueError):
                send(msg["chat"]["id"], "Format perintah salah. Ketik /menu untuk contoh.")
            except Exception as e:
                print("error:", e, flush=True)


if __name__ == "__main__":
    main()
