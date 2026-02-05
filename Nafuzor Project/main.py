import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database import create_tables
from middleware import ChecksMiddleware

# Импорты роутеров
from handlers import start, numbers, cabinet, card, admin, referral
# Импорты из папки Balance
from handlers.Balance import menu as bal_menu, topup, history, card_payment, stars, crypto

async def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    create_tables()
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    dp.message.outer_middleware(ChecksMiddleware())
    dp.callback_query.outer_middleware(ChecksMiddleware())
    
    # Регистрация
    dp.include_router(start.router)
    dp.include_router(numbers.router)
    dp.include_router(cabinet.router)
    dp.include_router(referral.router)
    dp.include_router(card.router)
    dp.include_router(admin.router)
    
    # Баланс
    dp.include_router(bal_menu.router)
    dp.include_router(topup.router)
    dp.include_router(history.router)
    dp.include_router(card_payment.router)
    dp.include_router(stars.router)
    dp.include_router(crypto.router)
    
    await bot.delete_webhook(drop_pending_updates=True)
    print("🚀 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен")