#!/bin/bash

echo "=================================================="
echo "Initializing Firewall Rules"
echo "=================================================="

# Enable IP forwarding
echo 1 > /proc/sys/net/ipv4/ip_forward
echo "✓ IP forwarding enabled"

# Flush existing rules
iptables -F
iptables -X
iptables -t nat -F
iptables -t nat -X
iptables -t mangle -F
iptables -t mangle -X
echo "✓ Existing rules flushed"

# Set default policies
iptables -P INPUT ACCEPT
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT
echo "✓ Default policies set"

# Allow loopback
iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT
echo "✓ Loopback traffic allowed"

# Allow established and related connections
iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
echo "✓ Established connections allowed"

# Load blocked IPs from file
if [ -f /app/data/blocked_ips.txt ]; then
    echo "Loading blocked IPs..."
    while IFS= read -r ip; do
        if [ ! -z "$ip" ] && [ "${ip:0:1}" != "#" ]; then
            iptables -A FORWARD -s "$ip" -j DROP
            iptables -A INPUT -s "$ip" -j DROP
            echo "  Blocked IP: $ip"
        fi
    done < /app/data/blocked_ips.txt
fi

# Load allowed IPs from file
if [ -f /app/data/allowed_ips.txt ]; then
    echo "Loading allowed IPs..."
    while IFS= read -r ip; do
        if [ ! -z "$ip" ] && [ "${ip:0:1}" != "#" ]; then
            iptables -A FORWARD -s "$ip" -j ACCEPT
            echo "  Allowed IP: $ip"
        fi
    done < /app/data/allowed_ips.txt
fi

# Load blocked MACs from file
if [ -f /app/data/blocked_macs.txt ]; then
    echo "Loading blocked MAC addresses..."
    while IFS= read -r mac; do
        if [ ! -z "$mac" ] && [ "${mac:0:1}" != "#" ]; then
            iptables -A FORWARD -m mac --mac-source "$mac" -j DROP
            iptables -A INPUT -m mac --mac-source "$mac" -j DROP
            echo "  Blocked MAC: $mac"
        fi
    done < /app/data/blocked_macs.txt
fi

# Block SSH (port 22) by default
iptables -A FORWARD -p tcp --dport 22 -j DROP
echo "✓ SSH port (22) blocked"

# Allow HTTP (port 80)
iptables -A FORWARD -p tcp --dport 80 -j ACCEPT
echo "✓ HTTP port (80) allowed"

# Allow HTTPS (port 443)
iptables -A FORWARD -p tcp --dport 443 -j ACCEPT
echo "✓ HTTPS port (443) allowed"

# Allow Flask app port (5000)
iptables -A FORWARD -p tcp --dport 5000 -j ACCEPT
echo "✓ Flask port (5000) allowed"

# DDoS Protection: Connection rate limiting
# Limit new connections to 20 per minute per IP
iptables -A FORWARD -p tcp --syn -m recent --name ddos --set
iptables -A FORWARD -p tcp --syn -m recent --name ddos --update --seconds 60 --hitcount 20 -j DROP
echo "✓ DDoS protection: Connection rate limiting enabled (20 conn/min per IP)"

# DDoS Protection: SYN flood protection
iptables -A FORWARD -p tcp --syn -m limit --limit 10/s --limit-burst 20 -j ACCEPT
iptables -A FORWARD -p tcp --syn -j DROP
echo "✓ DDoS protection: SYN flood protection enabled"

# DDoS Protection: Limit concurrent connections per IP
iptables -A FORWARD -p tcp --syn --dport 5000 -m connlimit --connlimit-above 10 -j DROP
echo "✓ DDoS protection: Max 10 concurrent connections per IP"

# ICMP rate limiting (ping flood protection)
iptables -A FORWARD -p icmp --icmp-type echo-request -m limit --limit 1/s -j ACCEPT
iptables -A FORWARD -p icmp --icmp-type echo-request -j DROP
echo "✓ ICMP flood protection enabled"

# Log dropped packets
iptables -A FORWARD -m limit --limit 5/min -j LOG --log-prefix "FIREWALL-DROP: " --log-level 4
iptables -A INPUT -m limit --limit 5/min -j LOG --log-prefix "FIREWALL-INPUT-DROP: " --log-level 4

echo "=================================================="
echo "Firewall Rules Initialized Successfully"
echo "=================================================="

# Keep monitoring and reloading rules every 30 seconds
while true; do
    sleep 30
    # Reload rules if files have been modified
    if [ -f /app/data/reload_rules ]; then
        echo "Reloading firewall rules..."
        rm /app/data/reload_rules
        # Re-execute this script
        exec /app/firewall.sh
    fi
done
