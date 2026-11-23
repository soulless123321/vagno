"""
ASGI config for nn_project project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/asgi/
"""

import os

from channels.routing import URLRouter, ProtocolTypeRouter
from django.core.asgi import get_asgi_application

from app.middleware import WebSocketTicketAuthMiddleware
from app.routing import websocket_urlpatterns
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nn_project.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": WebSocketTicketAuthMiddleware(
        URLRouter(websocket_urlpatterns)
    ),
})
