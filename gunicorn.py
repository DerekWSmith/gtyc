# Gunicorn configuration for GTYC on Bertha
#
# Start with:
#   cd /usr/local/var/www/gtyc
#   gunicorn -c gunicorn.py

# WSGI app
wsgi_app = "gtyc.wsgi:application"

# Bind to localhost only — Nginx fronts this on :7030
bind = "127.0.0.1:7031"

# Workers — small site, 2 is plenty
workers = 2

# Logging
accesslog = "/usr/local/var/www/gtyc/_logs/gunicorn-access.log"
errorlog = "/usr/local/var/www/gtyc/_logs/gunicorn-error.log"
loglevel = "info"

# Process naming
proc_name = "gtyc"

# Timeout — 30s is fine for a small site
timeout = 30

# Preload app for faster worker startup
preload_app = True
