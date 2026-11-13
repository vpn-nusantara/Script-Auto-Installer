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

# 🚀 VPN NUSANTARA — AUTO INSTALLER

### Solusi Instalasi Server VPN Otomatis, Praktis & Modern

Nikmati kemudahan membangun server VPN dengan **VPN NUSANTARA AUTO INSTALLER**. Dirancang untuk mempermudah proses instalasi dan konfigurasi server dengan sistem yang praktis, cepat, dan mudah digunakan.

Dilengkapi sistem **lisensi berbasis IP VPS menggunakan Cloudflare**, sehingga akses instalasi dapat dikontrol berdasarkan IP dan masa berlaku lisensi.

---

## 💎 KEUNGGULAN

- ⚡ Instalasi otomatis dan praktis.
- 🔐 Sistem aktivasi lisensi berdasarkan IP VPS.
- ☁️ Verifikasi lisensi melalui Cloudflare.
- 📅 Masa aktif lisensi dengan tanggal kedaluwarsa.
- 🛡️ Kontrol akses instalasi berdasarkan izin IP.
- 🔄 Pengelolaan izin dan masa aktif lisensi.
- 🖥️ Dirancang untuk penggunaan pada VPS Linux.

## 💰 DAFTAR HARGA SEWA LISENSI

**Satu lisensi berlaku untuk 1 IP VPS.**

| Paket | Harga |
|---|---:|
| 30 Hari | **Rp15.000** |
| 90 Hari | **Rp40.000** |
| 180 Hari | **Rp70.000** |
| 1 Tahun | **Rp120.000** |

Semua paket menggunakan sistem aktivasi lisensi berdasarkan IP VPS dan tanggal kedaluwarsa.

## 📌 KETENTUAN SEWA

1. Satu lisensi hanya berlaku untuk satu IP VPS.
2. Lisensi memiliki masa aktif sesuai paket yang dipilih.
3. Lisensi yang kedaluwarsa perlu diperpanjang untuk mendapatkan akses kembali.
4. Penggantian IP VPS harus dikonfirmasi kepada admin.
5. Aktivasi dilakukan setelah konfirmasi pembayaran.

## 📞 HUBUNGI ADMIN

**Tertarik menyewa atau ingin melakukan perpanjangan lisensi? Hubungi kami melalui:**

- WhatsApp: https://wa.me/6285181250313
- Telegram: https://t.me/qim_femashendriyuliadi

## 🔥 VPN NUSANTARA

**Praktis dalam instalasi. Mudah dalam pengelolaan. Terpercaya dalam sistem lisensi.**

Terima kasih telah memilih VPN NUSANTARA!



## ⭐ Dukungan Project

Jika project ini bermanfaat, dukung pengembangannya dengan memberikan **Star** pada repository.

<div align="center">

[⭐ Beri Star di GitHub](https://github.com/vpn-nusantara/Script-Auto-Installer)

