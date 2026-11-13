#!/bin/bash
# VPN NUSANTARA - menu utama
LIB=/usr/local/nusantara
C='\033[1;36m'; G='\033[1;32m'; Y='\033[1;33m'; R='\033[1;31m'; W='\033[1;37m'; D='\033[0;90m'; N='\033[0m'
[ "$EUID" -ne 0 ] && { echo "Jalankan sebagai root"; exit 1; }

rainbow() {
  local s="$1" i out="" cols=(196 208 226 46 51 33 129 201)
  for ((i = 0; i < ${#s}; i++)); do out+="\033[1;38;5;${cols[i % 8]}m${s:$i:1}"; done
  echo -ne "$out\033[0m"
}
line() { echo -e "${C} ├──────────────────────────────────────────────────────┤${N}"; }
header() {
  clear
  echo -e "${C} ╭──────────────────────────────────────────────────────╮${N}"
  echo -e "${C} │$(printf '%*s' 20 '')$(rainbow 'VPN NUSANTARA')$(printf '%*s' 21 '')${C}│${N}"
  echo -e "${C} │${D}      Script Auto Installer • Tunneling Lengkap       ${C}│${N}"
  echo -e "${C} ╰──────────────────────────────────────────────────────╯${N}"
}
pause() { echo; read -rp " Tekan Enter untuk kembali ke menu..." _; }
pick_type() {
  echo -e " ${W}Pilih tipe:${N}  ${G}1${N}) SSH  ${G}2${N}) VMess  ${G}3${N}) VLESS  ${G}4${N}) Trojan  ${G}5${N}) ZIVPN"
  read -rp " Tipe [1-5]: " n
  case "$n" in 1) T=ssh;; 2) T=vmess;; 3) T=vless;; 4) T=trojan;; 5) T=zivpn;; *) T="";; esac
  [ -n "$T" ]
}

buat() {
  pick_type || return
  read -rp " Username            : " u
  P=""
  if [ "$T" = ssh ] || [ "$T" = zivpn ]; then read -rp " Password (kosong=acak): " P; fi
  read -rp " Masa aktif (hari) [30]: " d; d=${d:-30}
  read -rp " Batas login [2]     : " l; l=${l:-2}
  echo
  if [ -n "$P" ]; then nus add "$T" "$u" "$d" "$l" "$P"; else nus add "$T" "$u" "$d" "$l"; fi
}
hapus() { pick_type || return; nus list "$T"; read -rp " Username yang dihapus: " u; [ -n "$u" ] && nus del "$T" "$u"; }
perpanjang() { pick_type || return; nus list "$T"; read -rp " Username: " u; read -rp " Tambah berapa hari [30]: " d; [ -n "$u" ] && nus renew "$T" "$u" "${d:-30}"; }
detail() { pick_type || return; nus list "$T"; read -rp " Username: " u; [ -n "$u" ] && nus show "$T" "$u"; }
putus() { nus online; pick_type || return; read -rp " Username yang diputus: " u; [ -n "$u" ] && nus kick "$T" "$u"; }
banner() { ${EDITOR:-nano} /etc/nusantara/banner.txt; echo " Banner disimpan. Berlaku untuk login berikutnya."; }
restore() {
  ls -1 /root/backup-nusantara-*.json 2>/dev/null
  read -rp " Lokasi file backup: " f
  [ -f "$f" ] || { echo -e " ${R}File tidak ditemukan${N}"; return; }
  read -rp " Semua akun sekarang akan diganti. Lanjut? [y/N]: " y
  [ "$y" = y ] || [ "$y" = Y ] && nus restore "$f"
}
layanan() {
  nus services
  echo; read -rp " Restart semua layanan? [y/N]: " y
  if [ "$y" = y ] || [ "$y" = Y ]; then
    for s in ssh dropbear stunnel4 nginx xray nus-ws udp-custom zivpn nus-panel nus-bot nus-ttyd; do systemctl restart "$s" 2>/dev/null; done
    echo -e " ${G}Layanan direstart${N}"
  fi
}
panel() {
  echo -e " Panel web  : ${G}https://$(nus get domain)/panel/${N}"
  echo -e " Terminal   : ${G}https://$(nus get domain)/terminal/${N}"
  echo -e " Username   : ${W}$(nus get panel_user)${N}"
  echo -e " Kunci API  : ${W}$(nus get api_key)${N}  ${D}(untuk panel terpisah)${N}"
  echo; read -rp " Ganti login panel? [y/N]: " y
  if [ "$y" = y ] || [ "$y" = Y ]; then
    read -rp " Username baru: " u; read -rsp " Password baru (min 8): " p; echo
    nus panel-pass "$u" "$p" && systemctl restart nus-panel nginx
  fi
}
bot() {
  echo -e " Buat bot di ${W}@BotFather${N}, lalu ambil ID Anda dengan perintah /id di bot."
  read -rp " Token bot    : " t; read -rp " ID admin     : " i
  [ -n "$t" ] && nus set bot_token "$t"
  [ -n "$i" ] && nus set admin_id "$i"
  systemctl enable nus-bot >/dev/null 2>&1; systemctl restart nus-bot
  echo -e " ${G}Bot dijalankan.${N} Kirim /start ke bot Anda."
}

while true; do
  header
  nus info
  echo -e "${C} ╭──────────────────────────────────────────────────────╮${N}"
  echo -e "${C} │${N}  ${G}01${N} Buat akun            ${G}08${N} Backup akun              ${C}│${N}"
  echo -e "${C} │${N}  ${G}02${N} Hapus akun           ${G}09${N} Restore akun             ${C}│${N}"
  echo -e "${C} │${N}  ${G}03${N} Perpanjang akun      ${G}10${N} Status & restart layanan ${C}│${N}"
  echo -e "${C} │${N}  ${G}04${N} Daftar akun          ${G}11${N} Panel web & terminal     ${C}│${N}"
  echo -e "${C} │${N}  ${G}05${N} Detail akun          ${G}12${N} Bot Telegram             ${C}│${N}"
  echo -e "${C} │${N}  ${G}06${N} Pengguna online      ${G}13${N} Jalankan pengaman VPS    ${C}│${N}"
  echo -e "${C} │${N}  ${G}07${N} Ubah banner login    ${G}14${N} Putuskan pengguna        ${C}│${N}"
  line
  echo -e "${C} │${N}  ${R}00${N} Keluar ke terminal                                ${C}│${N}"
  echo -e "${C} ╰──────────────────────────────────────────────────────╯${N}"
  echo -e "$(printf '%*s' 19 '')$(rainbow 'by : VPN NUSANTARA')"
  read -rp " Pilih menu: " m
  echo
  case "$m" in
    1|01) buat ;; 2|02) hapus ;; 3|03) perpanjang ;; 4|04) nus list ;; 5|05) detail ;;
    6|06) nus online ;; 7|07) banner ;; 8|08) nus backup; nus get bot_token | grep -q . && nus backup --telegram ;;
    9|09) restore ;; 10) layanan ;; 11) panel ;; 12) bot ;; 13) bash "$LIB/secure.sh" ;; 14) putus ;;
    0|00) exit 0 ;; *) echo -e " ${R}Pilihan tidak ada${N}" ;;
  esac
  pause
done
