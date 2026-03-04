# GTYC Server — Quick Reference

## Server Details

- **Machine:** gtyc (Linux Mint 22.3)
- **Local IP:** 192.168.0.211 (will change at new location)
- **Tailscale IP:** 100.94.1.31 (works from anywhere)
- **SSH (local):** `ssh gtyc@192.168.0.211`
- **SSH (remote):** `ssh gtyc@100.94.1.31`
- **Public URL:** https://gtyc.share.zrok.io
- **Project path:** /home/gtyc/gtyc
- **Virtual env:** /home/gtyc/gtyc/venv

---

## Quick Health Check

```bash
ssh gtyc@100.94.1.31
sudo systemctl status gtyc zrok x11vnc
```

All should show `active (running)`.

## Restart Services

```bash
# Restart Django/Gunicorn
sudo systemctl restart gtyc

# Restart zrok tunnel
sudo systemctl restart zrok

# Restart both
sudo systemctl restart gtyc zrok
```

## View Logs

```bash
# Gunicorn logs
sudo journalctl -u gtyc -n 50 --no-pager

# zrok logs
sudo journalctl -u zrok -n 50 --no-pager
```

## Deploy from PyCharm

1. Right-click project > Deployment > Upload to GTYC Server
2. SSH in and run:
```bash
cd /home/gtyc/gtyc && venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart gtyc
```

## Run Migrations After Deploy

```bash
cd /home/gtyc/gtyc && venv/bin/python manage.py migrate
sudo systemctl restart gtyc
```

---

# Full Setup Documentation

## 1. Machine Configuration

### Operating System
Linux Mint 22.3 on x86_64 hardware. Auto-login enabled so the machine
boots straight to the desktop without user interaction.

### BIOS — Power Recovery
BIOS setting "AC Back" is set to "Always On". After a power cut, the
machine automatically powers on when electricity is restored. Combined
with auto-login, this means full unattended recovery.

### Automatic OS Updates
`unattended-upgrades` is installed and configured to automatically
download and install security and stable updates.

```bash
# Check update status
sudo unattended-upgrade --dry-run
```

### SSH Access
OpenSSH server is installed. Key-based authentication is set up from the
Mac (dereksmith) to the server. No password required.

```bash
# Local network
ssh gtyc@192.168.0.211

# Remote (via Tailscale — works from anywhere)
ssh gtyc@100.94.1.31
```

### Tailscale — Remote Access VPN
Tailscale is installed on both the gtyc machine and the Mac (Sonia).
It creates a mesh VPN so both machines can reach each other regardless
of what network they are on. No port forwarding or firewall config needed.

- **gtyc Tailscale IP:** 100.94.1.31
- Tailscale runs as a system service and auto-starts on boot
- On the Mac, Tailscale runs as a menu bar app (installed from App Store)

### x11vnc — Remote Desktop
x11vnc provides VNC access to the gtyc desktop. It is bound to
localhost only — access is via SSH tunnel over Tailscale for security.

**Service file:** `/etc/systemd/system/x11vnc.service`
```ini
[Unit]
Description=x11vnc VNC Server
After=display-manager.service

[Service]
User=gtyc
ExecStart=/usr/bin/x11vnc -display :0 -auth guess -forever -loop -noxdamage -rfbauth /home/gtyc/.vnc/passwd -rfbport 5900 -localhost
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**To connect from Mac:**
```bash
# 1. Start SSH tunnel (runs in background)
ssh -L 5900:localhost:5900 gtyc@100.94.1.31 -N &

# 2. Open VNC viewer (Cmd+K in Finder, or from terminal)
open vnc://localhost:5900
```
Enter the VNC password when prompted.

## 2. Application Stack

### Overview

```
Internet
   │
   ▼
zrok tunnel (systemd: zrok.service)
   │  receives HTTPS traffic at gtyc.share.zrok.io
   │  forwards to http://127.0.0.1:8000
   ▼
Gunicorn (systemd: gtyc.service)
   │  WSGI server, 2 workers
   │  serves Django app
   ▼
Django + SQLite
   │  project at /home/gtyc/gtyc
   │  database: /home/gtyc/gtyc/GTYC.sqlite3
   ▼
WhiteNoise
      serves static files (CSS, JS, images)
```

### Python Virtual Environment
Located at `/home/gtyc/gtyc/venv`. Uses Python 3.12 (system).
Dependencies are listed in `requirements.txt`:
- Django 6.x
- gunicorn
- whitenoise
- python-dotenv

To recreate:
```bash
cd /home/gtyc/gtyc
rm -rf venv
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

### Gunicorn — Django Application Server
Managed by systemd as `gtyc.service`.

**Service file:** `/etc/systemd/system/gtyc.service`
```ini
[Unit]
Description=GTYC Gunicorn Django
After=network.target

[Service]
User=gtyc
WorkingDirectory=/home/gtyc/gtyc
ExecStart=/home/gtyc/gtyc/venv/bin/gunicorn gtyc.wsgi:application --bind 127.0.0.1:8000 --workers 2
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

- Binds to `127.0.0.1:8000` (localhost only — not exposed directly)
- 2 worker processes
- Auto-restarts on crash (after 3 seconds)
- Starts automatically on boot

### zrok — Public Tunnel
Managed by systemd as `zrok.service`. Exposes the local Gunicorn server
to the internet via a reserved share with a permanent URL.

**Service file:** `/etc/systemd/system/zrok.service`
```ini
[Unit]
Description=GTYC zrok tunnel
After=network-online.target gtyc.service
Wants=network-online.target

[Service]
User=gtyc
Environment=HOME=/home/gtyc
ExecStart=/usr/bin/zrok share reserved gtyc --headless
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

- Reserved share token: `gtyc`
- Public URL: `https://gtyc.share.zrok.io`
- `--headless` flag is required for running under systemd (no TTY)
- `Environment=HOME=/home/gtyc` is required so zrok finds its config in `~/.zrok`
- Starts after Gunicorn (`After=gtyc.service`)
- Auto-restarts on crash (after 5 seconds)

### Django Settings (production-relevant)
- `DEBUG = False` (controlled by `.env` file)
- `ALLOWED_HOSTS = ['*']`
- `CSRF_TRUSTED_ORIGINS` includes `https://gtyc.share.zrok.io`
- `SECURE_PROXY_SSL_HEADER` set for HTTPS behind the zrok proxy
- WhiteNoise serves static files (no separate Nginx needed)
- SQLite database at `GTYC.sqlite3` in the project root

### Static Files
WhiteNoise serves static files in production. After any changes to
static files (CSS, JS, images), you must collect them:

```bash
cd /home/gtyc/gtyc && venv/bin/python manage.py collectstatic --noinput
```

## 3. Boot Sequence (after power cut)

1. BIOS powers on machine (AC Back = Always On)
2. Linux Mint boots and auto-logs in as `gtyc`
3. Tailscale connects to VPN (remote access available)
4. systemd starts `gtyc.service` (Gunicorn on port 8000)
5. systemd starts `zrok.service` (tunnel to gtyc.share.zrok.io)
6. systemd starts `x11vnc.service` (remote desktop available)
7. Site is accessible at https://gtyc.share.zrok.io

No manual intervention required.

## 4. Moving to a New Network

When the machine arrives at its new location:

1. **Ethernet (easiest):** Plug in an ethernet cable. DHCP assigns an IP
   automatically. Tailscale, zrok, and all services reconnect on their own.

2. **WiFi:** Connect to WiFi via the desktop (need monitor/keyboard at the
   new location, or pre-configure the WiFi before shipping). Once connected,
   everything reconnects automatically.

3. **The local IP will change** (e.g. from 192.168.0.211 to whatever the
   new router assigns). This doesn't matter — use the Tailscale IP
   (100.94.1.31) which stays the same regardless of network.

4. **The public URL stays the same:** https://gtyc.share.zrok.io

## 5. PyCharm Deployment Config

- **Type:** SFTP
- **Host:** 192.168.0.211
- **Username:** gtyc
- **Auth:** Key pair (passwordless)
- **Root path:** /home/gtyc/gtyc
- **Mapping:** local `/usr/local/var/www/gtyc` → remote `/`

## 6. Troubleshooting

### Site is down
```bash
ssh gtyc@100.94.1.31
sudo systemctl status gtyc zrok
```
Restart whichever service is not running.

### 500 errors
```bash
sudo journalctl -u gtyc -n 100 --no-pager
```

### zrok "bad gateway"
Gunicorn is probably not running. Restart it:
```bash
sudo systemctl restart gtyc
```

### Static files missing (unstyled pages)
```bash
cd /home/gtyc/gtyc && venv/bin/python manage.py collectstatic --noinput
```

### Database migrations needed
```bash
cd /home/gtyc/gtyc && venv/bin/python manage.py migrate
sudo systemctl restart gtyc
```
