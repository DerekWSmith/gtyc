"""
WSGI config for gtyc project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gtyc.settings')

_application = get_wsgi_application()


def application(environ, start_response):
    """Wrap WSGI to inject X-Forwarded-Proto for Cloudflare tunnel."""
    environ['HTTP_X_FORWARDED_PROTO'] = 'https'
    return _application(environ, start_response)
