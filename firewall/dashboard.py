"""
Firewall Dashboard - Web interface for monitoring and managing firewall
"""
from flask import Flask, render_template_string, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import json
import os
import subprocess

app = Flask(__name__)
CORS(app)

# File paths
LOGS_DIR = '/app/logs'
DATA_DIR = '/app/data'
REQUESTS_LOG = f'{LOGS_DIR}/requests.jsonl'
BLOCKED_IPS_FILE = f'{DATA_DIR}/blocked_ips.txt'
ALLOWED_IPS_FILE = f'{DATA_DIR}/allowed_ips.txt'
BLOCKED_MACS_FILE = f'{DATA_DIR}/blocked_macs.txt'

# Ensure directories exist
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# Initialize files if they don't exist
for file_path in [BLOCKED_IPS_FILE, ALLOWED_IPS_FILE, BLOCKED_MACS_FILE, REQUESTS_LOG]:
    if not os.path.exists(file_path):
        open(file_path, 'a').close()

def read_file_lines(filepath):
    """Read non-empty, non-comment lines from a file"""
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

def write_file_lines(filepath, lines):
    """Write lines to a file"""
    with open(filepath, 'w') as f:
        for line in lines:
            f.write(f"{line}\n")

def get_recent_requests(minutes=10):
    """Get recent requests from log"""
    if not os.path.exists(REQUESTS_LOG):
        return []
    
    cutoff_time = datetime.now() - timedelta(minutes=minutes)
    requests = []
    
    try:
        with open(REQUESTS_LOG, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        req = json.loads(line)
                        req_time = datetime.fromisoformat(req['timestamp'])
                        if req_time >= cutoff_time:
                            requests.append(req)
                    except:
                        continue
    except:
        pass
    
    return sorted(requests, key=lambda x: x['timestamp'], reverse=True)

def get_statistics():
    """Get firewall statistics"""
    requests = get_recent_requests(60)  # Last hour
    
    total_requests = len(requests)
    blocked_requests = sum(1 for r in requests if r.get('blocked', False) or r.get('status', 200) >= 400)
    allowed_requests = total_requests - blocked_requests
    
    # Detect potential DDoS
    ip_counts = {}
    for req in get_recent_requests(1):  # Last minute
        ip = req.get('client_ip', 'unknown')
        ip_counts[ip] = ip_counts.get(ip, 0) + 1
    
    ddos_alerts = [{'ip': ip, 'count': count} for ip, count in ip_counts.items() if count > 10]
    
    # Top IPs
    all_ips = {}
    for req in requests:
        ip = req.get('client_ip', 'unknown')
        all_ips[ip] = all_ips.get(ip, 0) + 1
    
    top_ips = sorted(all_ips.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        'total_requests': total_requests,
        'allowed_requests': allowed_requests,
        'blocked_requests': blocked_requests,
        'ddos_alerts': ddos_alerts,
        'top_ips': top_ips,
        'blocked_ips_count': len(read_file_lines(BLOCKED_IPS_FILE)),
        'allowed_ips_count': len(read_file_lines(ALLOWED_IPS_FILE)),
        'blocked_macs_count': len(read_file_lines(BLOCKED_MACS_FILE))
    }

def run_iptables_command(command):
    """Execute iptables command"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        return str(e)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Firewall Dashboard</title>
    <meta http-equiv="refresh" content="10">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        .header {
            background: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .header h1 {
            color: #2c3e50;
            display: flex;
            align-items: center;
            gap: 15px;
        }
        .header .status {
            background: #2ecc71;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: normal;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .stat-card h3 {
            color: #7f8c8d;
            font-size: 14px;
            margin-bottom: 10px;
            text-transform: uppercase;
        }
        .stat-card .value {
            font-size: 36px;
            font-weight: bold;
            color: #2c3e50;
        }
        .stat-card.allowed .value { color: #2ecc71; }
        .stat-card.blocked .value { color: #e74c3c; }
        .stat-card.total .value { color: #3498db; }
        .stat-card.warning .value { color: #f39c12; }
        
        .content-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .card {
            background: white;
            border-radius: 10px;
            padding: 25px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .card h2 {
            color: #2c3e50;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #ecf0f1;
        }
        .form-group {
            margin-bottom: 15px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            color: #34495e;
            font-weight: 600;
        }
        .form-group input, .form-group select {
            width: 100%;
            padding: 10px;
            border: 2px solid #ecf0f1;
            border-radius: 5px;
            font-size: 14px;
        }
        .form-group input:focus, .form-group select:focus {
            outline: none;
            border-color: #3498db;
        }
        button {
            background: #3498db;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: background 0.3s;
        }
        button:hover {
            background: #2980b9;
        }
        .btn-danger {
            background: #e74c3c;
        }
        .btn-danger:hover {
            background: #c0392b;
        }
        .list-item {
            padding: 10px;
            background: #f8f9fa;
            margin-bottom: 8px;
            border-radius: 5px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .list-item code {
            background: #ecf0f1;
            padding: 4px 8px;
            border-radius: 3px;
            font-family: monospace;
        }
        .alert {
            background: #fff3cd;
            border-left: 4px solid #f39c12;
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 5px;
        }
        .alert.danger {
            background: #f8d7da;
            border-left-color: #e74c3c;
        }
        .alert.success {
            background: #d4edda;
            border-left-color: #2ecc71;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ecf0f1;
        }
        th {
            background: #f8f9fa;
            font-weight: 600;
            color: #2c3e50;
        }
        tr:hover {
            background: #f8f9fa;
        }
        .badge {
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: 600;
        }
        .badge.success { background: #d4edda; color: #155724; }
        .badge.danger { background: #f8d7da; color: #721c24; }
        .full-width {
            grid-column: 1 / -1;
        }
        .scroll-container {
            max-height: 400px;
            overflow-y: auto;
        }
        .empty-state {
            text-align: center;
            padding: 40px;
            color: #95a5a6;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>
                🛡️ Firewall Control Dashboard
                <span class="status">ACTIVE</span>
            </h1>
            <p style="color: #7f8c8d; margin-top: 10px;">Real-time monitoring and management • Auto-refresh: 10s</p>
        </div>

        {% if stats.ddos_alerts %}
        <div class="alert danger">
            <strong>⚠️ DDoS ALERT!</strong> Potential attack detected from {{ stats.ddos_alerts|length }} IP(s):
            {% for alert in stats.ddos_alerts %}
                {{ alert.ip }} ({{ alert.count }} requests/min)
            {% endfor %}
        </div>
        {% endif %}

        <div class="stats-grid">
            <div class="stat-card total">
                <h3>Total Requests</h3>
                <div class="value">{{ stats.total_requests }}</div>
                <small>Last hour</small>
            </div>
            <div class="stat-card allowed">
                <h3>Allowed</h3>
                <div class="value">{{ stats.allowed_requests }}</div>
                <small>Passed through</small>
            </div>
            <div class="stat-card blocked">
                <h3>Blocked</h3>
                <div class="value">{{ stats.blocked_requests }}</div>
                <small>Denied access</small>
            </div>
            <div class="stat-card warning">
                <h3>Rules Active</h3>
                <div class="value">{{ stats.blocked_ips_count + stats.blocked_macs_count }}</div>
                <small>Total block rules</small>
            </div>
        </div>

        <div class="content-grid">
            <div class="card">
                <h2>🚫 Block IP Address</h2>
                <form method="POST" action="/block_ip">
                    <div class="form-group">
                        <label>IP Address:</label>
                        <input type="text" name="ip" placeholder="e.g., 172.20.0.5" required>
                    </div>
                    <button type="submit" class="btn-danger">Block IP</button>
                </form>
                
                <h3 style="margin-top: 25px; color: #e74c3c;">Blocked IPs ({{ stats.blocked_ips_count }})</h3>
                <div class="scroll-container">
                    {% if blocked_ips %}
                        {% for ip in blocked_ips %}
                        <div class="list-item">
                            <code>{{ ip }}</code>
                            <form method="POST" action="/unblock_ip" style="display: inline;">
                                <input type="hidden" name="ip" value="{{ ip }}">
                                <button type="submit" style="padding: 5px 10px; font-size: 12px;">Unblock</button>
                            </form>
                        </div>
                        {% endfor %}
                    {% else %}
                        <div class="empty-state">No blocked IPs</div>
                    {% endif %}
                </div>
            </div>

            <div class="card">
                <h2>✅ Allow IP Address</h2>
                <form method="POST" action="/allow_ip">
                    <div class="form-group">
                        <label>IP Address:</label>
                        <input type="text" name="ip" placeholder="e.g., 172.20.0.4" required>
                    </div>
                    <button type="submit">Allow IP</button>
                </form>
                
                <h3 style="margin-top: 25px; color: #2ecc71;">Allowed IPs ({{ stats.allowed_ips_count }})</h3>
                <div class="scroll-container">
                    {% if allowed_ips %}
                        {% for ip in allowed_ips %}
                        <div class="list-item">
                            <code>{{ ip }}</code>
                            <form method="POST" action="/remove_allowed_ip" style="display: inline;">
                                <input type="hidden" name="ip" value="{{ ip }}">
                                <button type="submit" class="btn-danger" style="padding: 5px 10px; font-size: 12px;">Remove</button>
                            </form>
                        </div>
                        {% endfor %}
                    {% else %}
                        <div class="empty-state">No explicitly allowed IPs</div>
                    {% endif %}
                </div>
            </div>

            <div class="card">
                <h2>🔒 Block MAC Address</h2>
                <form method="POST" action="/block_mac">
                    <div class="form-group">
                        <label>MAC Address:</label>
                        <input type="text" name="mac" placeholder="e.g., 02:42:ac:14:00:05" required>
                    </div>
                    <button type="submit" class="btn-danger">Block MAC</button>
                </form>
                
                <h3 style="margin-top: 25px; color: #e74c3c;">Blocked MACs ({{ stats.blocked_macs_count }})</h3>
                <div class="scroll-container">
                    {% if blocked_macs %}
                        {% for mac in blocked_macs %}
                        <div class="list-item">
                            <code>{{ mac }}</code>
                            <form method="POST" action="/unblock_mac" style="display: inline;">
                                <input type="hidden" name="mac" value="{{ mac }}">
                                <button type="submit" style="padding: 5px 10px; font-size: 12px;">Unblock</button>
                            </form>
                        </div>
                        {% endfor %}
                    {% else %}
                        <div class="empty-state">No blocked MAC addresses</div>
                    {% endif %}
                </div>
            </div>

            <div class="card">
                <h2>📊 Top IP Addresses</h2>
                <table>
                    <thead>
                        <tr>
                            <th>IP Address</th>
                            <th>Requests</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% if stats.top_ips %}
                            {% for ip, count in stats.top_ips %}
                            <tr>
                                <td><code>{{ ip }}</code></td>
                                <td>{{ count }}</td>
                                <td>
                                    <form method="POST" action="/block_ip" style="display: inline;">
                                        <input type="hidden" name="ip" value="{{ ip }}">
                                        <button type="submit" class="btn-danger" style="padding: 5px 10px; font-size: 12px;">Block</button>
                                    </form>
                                </td>
                            </tr>
                            {% endfor %}
                        {% else %}
                            <tr><td colspan="3" style="text-align: center; color: #95a5a6;">No traffic yet</td></tr>
                        {% endif %}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="card full-width">
            <h2>📝 Recent Traffic Log</h2>
            <div class="scroll-container">
                <table>
                    <thead>
                        <tr>
                            <th>Timestamp</th>
                            <th>Client IP</th>
                            <th>Method</th>
                            <th>Path</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% if recent_requests %}
                            {% for req in recent_requests[:50] %}
                            <tr>
                                <td>{{ req.timestamp[:19] }}</td>
                                <td><code>{{ req.client_ip }}</code></td>
                                <td><strong>{{ req.method }}</strong></td>
                                <td>{{ req.path }}</td>
                                <td>
                                    {% if req.status < 400 %}
                                        <span class="badge success">{{ req.status }}</span>
                                    {% else %}
                                        <span class="badge danger">{{ req.status }}</span>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endfor %}
                        {% else %}
                            <tr><td colspan="5" style="text-align: center; color: #95a5a6;">No traffic logged yet</td></tr>
                        {% endif %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def dashboard():
    """Main dashboard page"""
    stats = get_statistics()
    recent_requests = get_recent_requests(10)
    blocked_ips = read_file_lines(BLOCKED_IPS_FILE)
    allowed_ips = read_file_lines(ALLOWED_IPS_FILE)
    blocked_macs = read_file_lines(BLOCKED_MACS_FILE)
    
    return render_template_string(
        DASHBOARD_HTML,
        stats=stats,
        recent_requests=recent_requests,
        blocked_ips=blocked_ips,
        allowed_ips=allowed_ips,
        blocked_macs=blocked_macs
    )

@app.route('/block_ip', methods=['POST'])
def block_ip():
    """Block an IP address"""
    ip = request.form.get('ip', '').strip()
    if ip:
        blocked_ips = read_file_lines(BLOCKED_IPS_FILE)
        if ip not in blocked_ips:
            blocked_ips.append(ip)
            write_file_lines(BLOCKED_IPS_FILE, blocked_ips)
            # Apply rule immediately
            run_iptables_command(f"iptables -A FORWARD -s {ip} -j DROP")
            run_iptables_command(f"iptables -A INPUT -s {ip} -j DROP")
    return dashboard()

@app.route('/unblock_ip', methods=['POST'])
def unblock_ip():
    """Unblock an IP address"""
    ip = request.form.get('ip', '').strip()
    if ip:
        blocked_ips = read_file_lines(BLOCKED_IPS_FILE)
        if ip in blocked_ips:
            blocked_ips.remove(ip)
            write_file_lines(BLOCKED_IPS_FILE, blocked_ips)
            # Remove rule immediately
            run_iptables_command(f"iptables -D FORWARD -s {ip} -j DROP 2>/dev/null || true")
            run_iptables_command(f"iptables -D INPUT -s {ip} -j DROP 2>/dev/null || true")
    return dashboard()

@app.route('/allow_ip', methods=['POST'])
def allow_ip():
    """Add IP to allow list"""
    ip = request.form.get('ip', '').strip()
    if ip:
        allowed_ips = read_file_lines(ALLOWED_IPS_FILE)
        if ip not in allowed_ips:
            allowed_ips.append(ip)
            write_file_lines(ALLOWED_IPS_FILE, allowed_ips)
            # Apply rule immediately
            run_iptables_command(f"iptables -I FORWARD -s {ip} -j ACCEPT")
    return dashboard()

@app.route('/remove_allowed_ip', methods=['POST'])
def remove_allowed_ip():
    """Remove IP from allow list"""
    ip = request.form.get('ip', '').strip()
    if ip:
        allowed_ips = read_file_lines(ALLOWED_IPS_FILE)
        if ip in allowed_ips:
            allowed_ips.remove(ip)
            write_file_lines(ALLOWED_IPS_FILE, allowed_ips)
            # Remove rule immediately
            run_iptables_command(f"iptables -D FORWARD -s {ip} -j ACCEPT 2>/dev/null || true")
    return dashboard()

@app.route('/block_mac', methods=['POST'])
def block_mac():
    """Block a MAC address"""
    mac = request.form.get('mac', '').strip()
    if mac:
        blocked_macs = read_file_lines(BLOCKED_MACS_FILE)
        if mac not in blocked_macs:
            blocked_macs.append(mac)
            write_file_lines(BLOCKED_MACS_FILE, blocked_macs)
            # Apply rule immediately
            run_iptables_command(f"iptables -A FORWARD -m mac --mac-source {mac} -j DROP")
            run_iptables_command(f"iptables -A INPUT -m mac --mac-source {mac} -j DROP")
    return dashboard()

@app.route('/unblock_mac', methods=['POST'])
def unblock_mac():
    """Unblock a MAC address"""
    mac = request.form.get('mac', '').strip()
    if mac:
        blocked_macs = read_file_lines(BLOCKED_MACS_FILE)
        if mac in blocked_macs:
            blocked_macs.remove(mac)
            write_file_lines(BLOCKED_MACS_FILE, blocked_macs)
            # Remove rule immediately
            run_iptables_command(f"iptables -D FORWARD -m mac --mac-source {mac} -j DROP 2>/dev/null || true")
            run_iptables_command(f"iptables -D INPUT -m mac --mac-source {mac} -j DROP 2>/dev/null || true")
    return dashboard()

@app.route('/api/stats')
def api_stats():
    """API endpoint for statistics"""
    return jsonify(get_statistics())

@app.route('/api/logs')
def api_logs():
    """API endpoint for recent logs"""
    minutes = request.args.get('minutes', 10, type=int)
    return jsonify(get_recent_requests(minutes))

if __name__ == '__main__':
    print("=" * 50)
    print("Firewall Dashboard Starting")
    print("Access at: http://localhost:8080")
    print("=" * 50)
    app.run(host='0.0.0.0', port=8080, debug=False)
