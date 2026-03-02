from aiogram import BaseMiddleware
from config import ADMIN_IDS

class RoleCheckMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        data["is_admin"] = event.from_user.id in ADMIN_IDS
        return await handler(event, data)
