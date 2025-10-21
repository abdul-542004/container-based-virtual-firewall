#!/bin/bash

# Start firewall rules and proxy in background
echo "Starting firewall initialization..."
/app/firewall.sh &

# Start the proxy server
echo "Starting proxy server..."
python /app/proxy.py &

# Start the dashboard
echo "Starting dashboard..."
python /app/dashboard.py
