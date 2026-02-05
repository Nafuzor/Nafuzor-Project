from aiohttp import web
import json
from aiogram.utils.web_app import check_webapp_signature, parse_webapp_data
from config import BOT_TOKEN
from database import get_connection, get_user

# Настройка CORS (чтобы GitHub мог делать запросы к твоему боту)
def cors_setup(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Authorization, Content-Type'
    return response

async def handle_options(request):
    return cors_setup(web.Response())

# --- ПОЛУЧЕНИЕ ДАННЫХ ЮЗЕРА ---
async def get_user_data(request):
    try:
        # 1. Получаем строку авторизации от Telegram (initData)
        init_data = request.headers.get("Authorization")
        if not init_data:
            return cors_setup(web.json_response({"error": "No auth"}, status=401))

        # 2. Проверяем валидность (что это реально ТГ, а не хакер)
        if not check_webapp_signature(BOT_TOKEN, init_data):
            return cors_setup(web.json_response({"error": "Invalid auth"}, status=403))

        # 3. Достаем ID юзера
        web_app_data = parse_webapp_data(BOT_TOKEN, init_data)
        user_id = web_app_data.user.id

        # 4. Берем данные из БД
        conn = get_connection()
        c = conn.cursor()
        
        # Юзер
        c.execute("SELECT balance_rub, subscription, referrer_id FROM users WHERE user_id = ?", (user_id,))
        u_data = c.fetchone()
        
        # Рефералы (считаем)
        c.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (user_id,))
        ref_count = c.fetchone()[0]
        
        # Карта
        c.execute("SELECT card_number, cvv, balance, created_at FROM cards WHERE user_id = ?", (user_id,))
        card_data = c.fetchone()
        
        # Номера
        c.execute("SELECT id, number, category, status FROM numbers WHERE user_id = ?", (user_id,))
        nums = [{"id": r[0], "num": r[1], "cat": r[2], "status": r[3]} for r in c.fetchall()]
        
        conn.close()

        # Формируем ответ
        response_data = {
            "balance": u_data[0] if u_data else 0,
            "subscription": u_data[1] if u_data else "none",
            "ref_count": ref_count,
            "ref_link": f"nafuzor_bot?start={user_id}",
            "card": {
                "number": card_data[0] if card_data else "Нет карты",
                "cvv": card_data[1] if card_data else "***",
                "balance": card_data[2] if card_data else 0,
                "date": card_data[3].split()[0] if card_data else "--.--.--",
                "token": f"nfz_{user_id}_secret" # Фейк токен или реальный если есть
            },
            "numbers": nums
        }
        
        return cors_setup(web.json_response(response_data))

    except Exception as e:
        return cors_setup(web.json_response({"error": str(e)}, status=500))

# --- ДОБАВЛЕНИЕ НОМЕРА ЧЕРЕЗ САЙТ ---
async def add_number_api(request):
    try:
        # Проверка авторизации
        init_data = request.headers.get("Authorization")
        if not check_webapp_signature(BOT_TOKEN, init_data):
            return cors_setup(web.json_response({"error": "Invalid auth"}, status=403))
            
        user_id = parse_webapp_data(BOT_TOKEN, init_data).user.id
        
        # Получаем данные из JS
        data = await request.json()
        number = data.get('number')
        category = data.get('cat')
        
        # Пишем в БД
        conn = get_connection()
        c = conn.cursor()
        c.execute("INSERT INTO numbers (user_id, number, category, created_at) VALUES (?, ?, ?, datetime('now'))", 
                  (user_id, number, category))
        conn.commit()
        conn.close()
        
        return cors_setup(web.json_response({"status": "ok"}))
        
    except Exception as e:
        return cors_setup(web.json_response({"error": str(e)}, status=500))