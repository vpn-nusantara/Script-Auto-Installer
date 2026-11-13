#!/bin/bash
# VPN NUSANTARA - pengaman & setup VPS baru (bisa dijalankan ulang kapan saja)
[ "$EUID" -ne 0 ] && { echo "Jalankan sebagai root"; exit 1; }
LIB=/usr/local/nusantara
say() { echo -e "\033[1;36m[pengaman]\033[0m $*"; }
export DEBIAN_FRONTEND=noninteractive

say "Zona waktu Asia/Jakarta"
timedatectl set-timezone Asia/Jakarta 2>/dev/null || ln -sf /usr/share/zoneinfo/Asia/Jakarta /etc/localtime

if [ "$(swapon --show --noheadings 2>/dev/null | wc -l)" -eq 0 ] && [ "$(awk '/MemTotal/{print int($2/1024)}' /proc/meminfo)" -lt 2048 ]; then
  say "Membuat swap 1 GB"
  if fallocate -l 1G /swapfile 2>/dev/null || dd if=/dev/zero of=/swapfile bs=1M count=1024 status=none; then
    chmod 600 /swapfile && mkswap /swapfile >/dev/null && swapon /swapfile 2>/dev/null \
      && { grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab; }
  fi
fi

say "Optimasi jaringan (BBR) dan perlindungan kernel"
cat > /etc/sysctl.d/99-nusantara.conf <<'EOF'
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
net.ipv4.tcp_fastopen = 3
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_syn_backlog = 8192
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.ip_forward = 1
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
fs.file-max = 1000000
EOF
modprobe tcp_bbr 2>/dev/null
sysctl --system >/dev/null 2>&1

say "Pengerasan SSH"
CFG=/etc/ssh/sshd_config
if [ -f "$CFG" ]; then
  cp -n "$CFG" "$CFG.nusantara.bak"
  sed -i '/# NUSANTARA-BEGIN/,/# NUSANTARA-END/d' "$CFG"
  TMP=$(mktemp)
  cat > "$TMP" <<'EOF'
# NUSANTARA-BEGIN
Banner /etc/nusantara/banner.txt
PasswordAuthentication yes
PermitEmptyPasswords no
MaxAuthTries 4
LoginGraceTime 30
ClientAliveInterval 120
ClientAliveCountMax 3
X11Forwarding no
AllowTcpForwarding yes
PermitTunnel yes
# NUSANTARA-END
EOF
  cat "$CFG" >> "$TMP"
  CURRENT=$(mktemp)
  cp -p "$CFG" "$CURRENT"
  if sshd -t -f "$TMP" 2>/dev/null; then
    install -o root -g root -m 600 "$TMP" "$CFG"
    if systemctl restart ssh 2>/dev/null && systemctl is-active --quiet ssh; then
      say "Konfigurasi SSH berhasil diterapkan"
    elif systemctl restart sshd 2>/dev/null && systemctl is-active --quiet sshd; then
      say "Konfigurasi SSH berhasil diterapkan"
    else
      say "Restart SSH gagal; mengembalikan konfigurasi sebelumnya"
      cp -p "$CURRENT" "$CFG"
      systemctl restart ssh 2>/dev/null || systemctl restart sshd 2>/dev/null || true
    fi
  else
    say "Konfigurasi SSH baru tidak lolos uji, konfigurasi lama dipertahankan"
  fi
  rm -f "$TMP" "$CURRENT"
fi
for s in /bin/false /usr/sbin/nologin; do grep -qx "$s" /etc/shells || echo "$s" >> /etc/shells; done

say "Fail2ban (blokir otomatis percobaan login gagal)"
if command -v fail2ban-server >/dev/null 2>&1; then
  BACKEND=auto; [ -f /var/log/auth.log ] || BACKEND=systemd
  cat > /etc/fail2ban/jail.local <<EOF
[DEFAULT]
ignoreip = 127.0.0.1/8 ::1
bantime = 3600
findtime = 600
maxretry = 5
backend = $BACKEND

[sshd]
enabled = true

[dropbear]
enabled = true
EOF
  systemctl enable fail2ban >/dev/null 2>&1
  systemctl restart fail2ban 2>/dev/null || { sed -i '/^\[dropbear\]/,$d' /etc/fail2ban/jail.local; systemctl restart fail2ban 2>/dev/null; }
fi

say "Firewall: hanya port layanan yang dibuka"
if [ -x "$LIB/firewall.sh" ]; then
  cat > /etc/systemd/system/nus-firewall.service <<EOF
[Unit]
Description=VPN NUSANTARA firewall
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=$LIB/firewall.sh

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable nus-firewall >/dev/null 2>&1
  systemctl restart nus-firewall
fi

say "Membatasi izin berkas sensitif"
chmod 700 /root 2>/dev/null
[ -d /etc/nusantara ] && chmod 755 /etc/nusantara && chmod 600 /etc/nusantara/*.json 2>/dev/null
say "Selesai. VPS sudah diamankan."
