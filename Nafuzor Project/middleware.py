from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from database import get_user, get_connection, get_setting_bool
from config import CHANNELS
import keyboards as kb
import asyncio

class ChecksMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = data.get('event_from_user')
        if not user:
            return await handler(event, data)

        # 1. Проверка Юзернейма
        if get_setting_bool('check_username'):
            if not user.username:
                text = (
                    "<blockquote>Чтобы пользоваться ботом, вам нужно установить Username.</blockquote>\n\n"
                    "1️⃣ Перейдите в настройки Telegram.\n"
                    "2️⃣ Нажмите на \"Имя пользователя\".\n"
                    "3️⃣ Впишите свой юзернейм.\n"
                    "4️⃣ После этого введите /start."
                )
                if isinstance(event, Message):
                    await event.answer(text, parse_mode="HTML")
                return

        # 2. Проверка Подписки
        if get_setting_bool('check_sub'):
            bot = data['bot']
            not_subbed = False
            for ch_id in CHANNELS:
                try:
                    member = await bot.get_chat_member(chat_id=ch_id, user_id=user.id)
                    if member.status in ['left', 'kicked']:
                        not_subbed = True
                        break
                except:
                    continue 
            
            if not_subbed:
                is_check_btn = False
                if isinstance(event, CallbackQuery) and event.data == "check_subs":
                    is_check_btn = True
                
                if not is_check_btn:
                    text = "<blockquote>Чтобы пользоваться ботом необходимо поддержать владельца</blockquote>"
                    if isinstance(event, Message):
                        await event.answer(text, reply_markup=kb.sub_check_kb(), parse_mode="HTML")
                    elif isinstance(event, CallbackQuery):
                        await event.message.answer(text, reply_markup=kb.sub_check_kb(), parse_mode="HTML")
                        await event.answer()
                    return

        return await handler(event, data)