#!/bin/bash
# VPN NUSANTARA - aturan firewall (dipanggil saat boot dan setelah layanan UDP menyala)
# UDP dibuka penuh karena fitur UDP Custom saat ini memakai rentang 1-65535.
# ZIVPN tetap menggunakan DNAT 6000-19999 menuju port internal 5667.
SSH_PORT=$(sshd -T 2>/dev/null | awk '/^port /{print $2; exit}')
SSH_PORT=${SSH_PORT:-22}
IFACE=$(ip -4 route ls 2>/dev/null | awk '/default/{for(i=1;i<=NF;i++) if($i=="dev"){print $(i+1); exit}}')

zivpn_rule() {
  [ -z "$IFACE" ] && return
  while iptables -t nat -D PREROUTING -i "$IFACE" -p udp --dport 6000:19999 -j DNAT --to-destination :5667 2>/dev/null; do :; done
  iptables -t nat -I PREROUTING 1 -i "$IFACE" -p udp --dport 6000:19999 -j DNAT --to-destination :5667
}

input_rules() {
  iptables -N NUSANTARA 2>/dev/null
  iptables -F NUSANTARA
  iptables -A NUSANTARA -i lo -j ACCEPT
  iptables -A NUSANTARA -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
  # Buang paket invalid sebelum aturan protokol yang lebih luas.
  iptables -A NUSANTARA -m conntrack --ctstate INVALID -j DROP
  iptables -A NUSANTARA -p icmp -j ACCEPT
  iptables -A NUSANTARA -p tcp -m multiport --dports "$SSH_PORT",22,80,443,109,143,447,777 -j ACCEPT
  iptables -A NUSANTARA -p udp -j ACCEPT
  # Jangan biarkan protokol IP lain lolos ke aturan INPUT berikutnya.
  iptables -A NUSANTARA -j DROP
  iptables -C INPUT -j NUSANTARA 2>/dev/null || iptables -I INPUT 1 -j NUSANTARA
}

case "$1" in
  zivpn) zivpn_rule ;;
  off)
    iptables -D INPUT -j NUSANTARA 2>/dev/null
    iptables -F NUSANTARA 2>/dev/null
    echo "Firewall dimatikan"
    ;;
  *) input_rules; zivpn_rule ;;
esac
exit 0
