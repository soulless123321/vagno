import urllib.parse

from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async

from .models import User
from .views import get_user


class WebSocketTicketAuthMiddleware(BaseMiddleware):
    """
    Извлекает одноразовый билет из query-параметров и аутентифицирует пользователя.
    """
    @database_sync_to_async
    def get_user_from_ticket(self, ticket: str):
        try:
            user = get_user(ticket, salt="ws_ticket")

            if user and isinstance(user, User) and user.is_active:
                return user
        except Exception:
            pass
        return None

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            # Парсим query-параметры из URL (ws://127.0.0.1:8000/ws/chat/qwe/?ticket=TICKETTOKEN),
            # query-параметры находятся scope['query_string']
            query_string = scope.get("query_string", b"").decode("utf-8")
            query_params = urllib.parse.parse_qs(query_string)


            tickets = query_params.get("ticket")
            ticket = tickets[0] if tickets else None

            user = None
            if ticket:
                # Пытаемся получить пользователя по билету
                user = await self.get_user_from_ticket(ticket)

            # Если билет невалидный, отсутствует или пользователь не активен -закрываем соединение
            if user is None:
                await send({
                    "type": "websocket.close",
                    "code": 4001  # Код закрытия: Unauthorized
                })
                return

            # Если всё успешно, сохраняем объект пользователя в scope
            scope["user"] = user

        # Передаем управление следующему middleware или роутеру
        return await super().__call__(scope, receive, send)
        # return await self.inner(scope, receive, send)
