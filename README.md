<!-- VPN NUSANTARA | README -->

<div align="center">

#  VPN NUSANTARA

### SCRIPT AUTO INSTALLER

**Bangun, kelola, dan amankan layanan tunneling VPS dalam satu installer.**

<p>
  <img src="https://img.shields.io/badge/Ubuntu-20.04%2B-E95420?style=for-the-badge&logo=ubuntu&logoColor=white" alt="Ubuntu 20.04+">
  <img src="https://img.shields.io/badge/Debian-10%2B-A81D33?style=for-the-badge&logo=debian&logoColor=white" alt="Debian 10+">
  <img src="https://img.shields.io/badge/Architecture-x86__64%20%7C%20ARM64-6C5CE7?style=for-the-badge" alt="x86_64 and ARM64">
  <img src="https://img.shields.io/badge/Language-Bash%20%7C%20Python-2ECC71?style=for-the-badge&logo=gnubash&logoColor=white" alt="Bash and Python">
</p>

[🚀 Instalasi](#-instalasi) · [✨ Fitur](#-fitur-utama) · [🖥️ OS](#️-sistem-operasi) · [💻 Perintah](#-perintah-nus) · [🤖 Telegram](#-bot-telegram) · [🛡️ Keamanan](#️-catatan-keamanan)

</div>

---

## 👋 Tentang Project

**VPN NUSANTARA — Script Auto Installer** adalah perangkat instalasi dan pengelolaan VPS berbasis **Ubuntu dan Debian**. Project ini dirancang untuk membantu menyiapkan berbagai layanan tunneling, mengelola akun pengguna, serta memantau dan mengamankan server melalui menu terminal, panel web, dan bot Telegram.

> **Satu installer untuk kebutuhan pengelolaan layanan VPS.**

## 🚀 Instalasi

### Persiapan

- VPS dengan sistem operasi yang didukung.
- Akses SSH sebagai pengguna `root`.
- Domain yang DNS-nya sudah diarahkan ke IP VPS menggunakan **A record**.
- Koneksi internet pada VPS.

### Jalankan installer

Salin dan jalankan perintah berikut di terminal VPS:

```bash
apt update -y && apt install -y curl
bash <(curl -fsSL https://raw.githubusercontent.com/vpn-nusantara/Script-Auto-Installer/main/install.sh)
```

Ikuti instruksi pada layar untuk mengatur domain, akun panel, dan token bot Telegram (opsional).

### Setelah instalasi

| Keterangan | Detail |
|:--|:--|
| File informasi | `/root/nusantara-info.txt` |
| Menu pengelolaan | Jalankan perintah `menu` |
| Repository | Harus dapat diakses publik agar installer dapat mengunduh file |
| Branch alternatif | Atur variabel `NUS_BRANCH` sesuai nama branch |

## ✨ Fitur Utama

<table>
  <tr>
    <td width="50%">
      <h3>🔐 Manajemen Akun</h3>
      Pengaturan masa aktif, batas login, perpanjangan, dan penghapusan akun kedaluwarsa.
    </td>
    <td width="50%">
      <h3>👥 Monitoring Pengguna</h3>
      Periksa pengguna yang sedang online dan putuskan koneksi bila diperlukan.
    </td>
  </tr>
  <tr>
    <td>
      <h3>🌐 Layanan Tunneling</h3>
      Dukungan SSH, WebSocket, UDP, VMess, VLESS, Trojan, dan ZIVPN.
    </td>
    <td>
      <h3>🤖 Bot Telegram</h3>
      Fitur admin, reseller berkuota, serta pembuatan akun trial 60 menit.
    </td>
  </tr>
  <tr>
    <td>
      <h3>💾 Backup & Restore</h3>
      Backup akun format JSON dan backup harian ke Telegram.
    </td>
    <td>
      <h3>🛡️ Keamanan VPS</h3>
      Firewall, Fail2ban, BBR, hardening SSH, dan swap otomatis.
    </td>
  </tr>
  <tr>
    <td colspan="2">
      <h3>🧭 Menu & Panel</h3>
      Kelola layanan melalui menu terminal, panel web, dan terminal SSH melalui browser.
    </td>
  </tr>
</table>

## 🖥️ Sistem Operasi

| Sistem operasi | Versi yang didukung |
|:--|:--|
| Ubuntu | 20.04, 22.04, 24.04 atau lebih baru |
| Debian | 10, 11, 12, 13 |
| Arsitektur | x86_64 dan ARM64 |
| Catatan | Fitur SSH UDP tersedia untuk x86_64 |

## 🌐 Layanan & Port

| Layanan | Port |
|:--|:--|
| OpenSSH | `22` |
| Dropbear | `109, 143` |
| Stunnel SSL | `447, 777` |
| SSH WebSocket | `80 (HTTP), 443 (TLS)` |
| SSH UDP (UDP Custom) | `1–65535 UDP` |
| ZIVPN | `6000–19999 UDP` |
| VMess / VLESS / Trojan WebSocket | `80 (HTTP), 443 (TLS)` |
| VMess / VLESS / Trojan gRPC | `443` |
| Panel web | `https://domain/panel/` |
| Terminal browser | `https://domain/terminal/` |

## 💻 Perintah nus

Gunakan perintah `nus` untuk mengelola akun langsung dari terminal.

### Contoh penggunaan

```bash
# Membuat akun SSH
nus add ssh budi 30 2 rahasia

# Membuat akun VMess
nus add vmess andi 30 2

# Memperpanjang akun
nus renew ssh budi 30

# Menghapus akun
nus del ssh budi

# Melihat daftar akun
nus list [tipe]

# Melihat pengguna online
nus online

# Backup dan restore
nus backup
nus restore /root/backup-nusantara-xxxx.json
```

### Format pembuatan akun SSH

```text
nus add ssh <username> <hari> <batas-login> [password]
```

Tipe akun yang tersedia: `ssh`, `vmess`, `vless`, `trojan`, dan `zivpn`. Akun SSH juga digunakan untuk layanan SSH UDP.

## 🤖 Bot Telegram

Bot Telegram menyediakan pengelolaan akun berdasarkan hak akses.

| Perintah | Hak akses |
|:--|:--|
| `/trial <tipe>` | Semua pengguna, 1 kali per 24 jam |
| `/buat <tipe> <user> <hari> [limit]` | Admin dan reseller |
| `/perpanjang`, `/hapus`, `/detail`, `/list`, `/kuota` | Admin dan reseller |
| `/online`, `/info`, `/backup` | Admin |
| `/addreseller <id> <kuota>`, `/delreseller <id>`, `/resellers` | Admin |

Token bot dan ID admin dapat diatur saat instalasi atau melalui **menu nomor 12**.

## 📂 Struktur Repository

```text
.
├── install.sh        # Installer utama
├── vps/
│   ├── core.py       # Mesin akun dan perintah nus
│   ├── menu.sh       # Menu terminal
│   ├── panel.py      # Panel web dan API di VPS
│   ├── bot.py        # Bot Telegram
│   ├── ws-proxy.py   # SSH WebSocket
│   ├── secure.sh     # Pengaman VPS (dapat dijalankan mandiri)
│   └── firewall.sh   # Aturan firewall
├── frontend/         # Antarmuka panel multi-server
└── backend/          # Backend panel multi-server
```

## 🧪 Validasi Otomatis

Repository menjalankan pemeriksaan sintaks Bash dan Python melalui GitHub Actions setiap kali ada perubahan. Pemeriksaan ini membantu menemukan kesalahan sintaks lebih awal, tetapi bukan pengganti pengujian pada VPS uji sebelum dipakai di server produksi.

## 🛡️ Catatan Keamanan

- File backup dan `/etc/nusantara/db.json` berisi password akun. Simpan dengan aman dan jangan membagikannya.
- Untuk mematikan firewall: `/usr/local/nusantara/firewall.sh off`.
- Gunakan script hanya pada VPS yang Anda miliki atau kelola dengan izin, serta patuhi ketentuan penyedia VPS.
- Jangan menyimpan GitHub token, password, atau API key di repository publik.
- Firewall mengizinkan UDP penuh karena fitur SSH UDP Custom saat ini menggunakan rentang `1–65535`; aktifkan fitur ini hanya bila memang diperlukan. Aturan firewall juga menolak protokol IP lain yang tidak dipakai layanan.
- Pastikan konfigurasi domain, port, dan firewall sesuai dengan layanan yang Anda aktifkan.

## ⭐ Dukungan Project

Jika project ini bermanfaat, dukung pengembangannya dengan memberikan **Star** pada repository.

<div align="center">

[⭐ Beri Star di GitHub](https://github.com/vpn-nusantara/Script-Auto-Installer)

---

###  VPN NUSANTARA
**BUILD • CONNECT • MANAGE**

*Terima kasih telah menggunakan project ini!*

</div>
