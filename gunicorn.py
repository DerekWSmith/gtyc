# Gunicorn configuration for GTYC
#
# Start with:
#   cd /var/www/gtyc          (Linux Mint server)
#   cd /usr/local/var/www/gtyc (macOS / Bertha)
#   gunicorn -c gunicorn.py
#
# Or run via systemd:
#   sudo systemctl start gtyc

import os

# WSGI app
wsgi_app = "gtyc.wsgi:application"

# Bind to localhost only — Cloudflare Tunnel fronts this
bind = "127.0.0.1:8000"

# Workers — small site, 2 is plenty
workers = 2

# Detect project root from this file's location
_base_dir = os.path.dirname(os.path.abspath(__file__))

# Logging
accesslog = os.path.join(_base_dir, "_logs", "gunicorn-access.log")
errorlog = os.path.join(_base_dir, "_logs", "gunicorn-error.log")
loglevel = "info"

# Process naming
proc_name = "gtyc"

# Timeout — 30s is fine for a small site
timeout = 30

# Preload app for faster worker startup
preload_app = True
