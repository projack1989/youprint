import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from youprint import routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "youprint.settings")

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,  # untuk request HTTP biasa
    "websocket": AuthMiddlewareStack(
        URLRouter(
            routing.websocket_urlpatterns  # arahkan ke websocket_urlpatterns
        )
    ),
})
