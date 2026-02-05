from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from database import create_payment, get_payment, get_user, get_connection
from config import CRYPTO_BOT_TOKEN, SUBSCRIPTIONS
from states import PaymentState
import keyboards as kb
from aiocryptopay import AioCryptoPay, Networks
import uuid
import asyncio
from datetime import datetime

router = Router()
crypto = AioCryptoPay(token=CRYPTO_BOT_TOKEN, network=Networks.MAIN_NET)

# --- ГЛАВНАЯ ЛОГИКА УСПЕХА И ПЕРЕХОДА ---
async def success_deposit_logic(bot, user_id, amount_rub, order_id, message_to_delete_id=None, chat_id=None):
    conn = get_connection()
    c = conn.cursor()
    
    # 1. Пополнение баланса
    c.execute("UPDATE users SET balance_rub = balance_rub + ? WHERE user_id = ?", (amount_rub, user_id))
    # 2. Смена статуса платежа
    c.execute("UPDATE payments SET status = 'paid' WHERE order_id = ?", (order_id,))
    
    # 3. Рефералка 15%
    c.execute("SELECT referrer_id, username FROM users WHERE user_id = ?", (user_id,))
    res = c.fetchone()
    my_username = f"@{res[1]}" if res[1] else "Пользователь"
    
    if res and res[0]:
        referrer_id = res[0]
        bonus = amount_rub * 0.15
        c.execute("UPDATE users SET balance_rub = balance_rub + ?, ref_earnings = ref_earnings + ? WHERE user_id = ?", 
                  (bonus, bonus, referrer_id))
        try:
            await bot.send_message(referrer_id, f"💰 <b>Реферальный бонус!</b>\nБонус: {bonus} RUB\nОт: {my_username}", parse_mode="HTML")
        except: pass
        
    conn.commit()
    conn.close()

    # 4. Удаление сообщений (Инвойс, ввод суммы и т.д.)
    if message_to_delete_id and chat_id:
        try: await bot.delete_message(chat_id, message_to_delete_id)
        except: pass
    
    # 5. Показываем кабинет (Имитируем нажатие "Личный кабинет")
    user = get_user(user_id)
    sub_conf = SUBSCRIPTIONS.get(user[3], SUBSCRIPTIONS['none'])
    text_cab = (
        f"<blockquote>👤 <b>Профиль:</b> {user[1]}\n"
        f"▫️ <b>Баланс:</b> {user[2]} RUB\n"
        f"▫️ <b>Подписка:</b> {sub_conf['name']}\n"
        f"▫️ <b>Прайс:</b> {sub_conf['display_rate']}</blockquote>"
    )
    # Отправляем сообщение об успехе + Кабинет
    await bot.send_message(user_id, f"✅ <b>Баланс пополнен на {amount_rub} RUB!</b>", parse_mode="HTML")
    await bot.send_message(user_id, text_cab, reply_markup=kb.cabinet_kb(), parse_mode="HTML")


# --- ОБРАБОТЧИКИ ---

@router.message(PaymentState.input_amount_crypto)
async def process_crypto_input(message: types.Message, state: FSMContext):
    try:
        usd = float(message.text)
        rub = usd * 92 # Конвертация в рубли для записи
        await create_crypto_invoice(message, rub, state)
        # Удаляем сообщение с вводом суммы пользователя
        try: await message.delete()
        except: pass
    except: await message.answer("Введите число.")

@router.callback_query(F.data.startswith("pay_amt_crypto_"))
async def process_crypto_btn(call: types.CallbackQuery, state: FSMContext):
    amount = float(call.data.split("_")[3])
    await create_crypto_invoice(call.message, amount, state)

async def create_crypto_invoice(message, amount_rub, state):
    order_id = str(uuid.uuid4())
    user_id = message.chat.id
    
    # Сохраняем "pending"
    create_payment(order_id, user_id, amount_rub, "crypto")
    
    user = get_user(user_id)
    sub_name = SUBSCRIPTIONS.get(user[3], {}).get('name', 'Стандарт')
    amount_usd = amount_rub / 92
    
    try:
        invoice = await crypto.create_invoice(asset='USDT', amount=amount_usd)
        pay_url = invoice.bot_invoice_url
        
        text = (
            "💳 <b>Счет CryptoBot</b>\n\n"
            f"📦 Товар: {sub_name}\n"
            f"💰 Сумма: {amount_usd:.2f} $ ({amount_rub} RUB)\n"
            f"🔗 Ссылка: <a href='{pay_url}'>Оплатить</a>"
        )
        msg = await message.answer(
            text, 
            reply_markup=kb.invoice_kb(pay_url, f"{order_id}|{invoice.invoice_id}", "check_crypto"), 
            parse_mode="HTML"
        )
        # Сохраняем ID сообщения с инвойсом, чтобы удалить его при успехе
        await state.update_data(invoice_msg_id=msg.message_id)
        
    except Exception as e:
        await message.answer(f"Ошибка CryptoBot: {e}")

@router.callback_query(F.data.startswith("check_crypto_"))
async def check_crypto(call: types.CallbackQuery, state: FSMContext):
    data_str = call.data.replace("check_crypto_", "")
    order_id, invoice_id = data_str.split("|")
    
    pay_record = get_payment(order_id)
    if not pay_record: return await call.answer("Платеж не найден")
    if pay_record[5] == 'paid': 
        await call.message.delete()
        return
    
    try:
        invoices = await crypto.get_invoices(invoice_ids=[int(invoice_id)])
        if invoices and invoices[0].status == 'paid':
            data = await state.get_data()
            msg_id = data.get('invoice_msg_id')
            # Вызываем логику успеха (удаление и редирект)
            await success_deposit_logic(call.bot, call.from_user.id, pay_record[2], order_id, msg_id, call.message.chat.id)
        else:
            await call.answer("❌ Оплата еще не поступила", show_alert=True)
    except Exception as e:
        await call.answer(f"Ошибка API: {e}", show_alert=True)