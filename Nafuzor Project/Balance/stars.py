from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from database import create_payment, get_payment, get_user, get_connection
from config import SUBSCRIPTIONS
from states import PaymentState
import keyboards as kb
import uuid

router = Router()

# Дублируем функцию логики успеха (так как файлы разделены), либо импортируем из card_payment.py если они в одной папке
# Для надежности я вставлю её сюда тоже.
async def success_deposit_logic(bot, user_id, amount_rub, order_id, message_to_delete_id=None, chat_id=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET balance_rub = balance_rub + ? WHERE user_id = ?", (amount_rub, user_id))
    c.execute("UPDATE payments SET status = 'paid' WHERE order_id = ?", (order_id,))
    
    c.execute("SELECT referrer_id, username FROM users WHERE user_id = ?", (user_id,))
    res = c.fetchone()
    my_username = f"@{res[1]}" if res[1] else "Пользователь"
    if res and res[0]:
        bonus = amount_rub * 0.15
        c.execute("UPDATE users SET balance_rub = balance_rub + ?, ref_earnings = ref_earnings + ? WHERE user_id = ?", (bonus, bonus, res[0]))
        try: await bot.send_message(res[0], f"💰 <b>Реферальный бонус!</b>\nБонус: {bonus} RUB\nОт: {my_username}", parse_mode="HTML")
        except: pass
    conn.commit()
    conn.close()

    if message_to_delete_id and chat_id:
        try: await bot.delete_message(chat_id, message_to_delete_id)
        except: pass

    user = get_user(user_id)
    sub_conf = SUBSCRIPTIONS.get(user[3], SUBSCRIPTIONS['none'])
    text_cab = (f"<blockquote>👤 <b>Профиль:</b> {user[1]}\n▫️ <b>Баланс:</b> {user[2]} RUB\n▫️ <b>Подписка:</b> {sub_conf['name']}\n▫️ <b>Прайс:</b> {sub_conf['display_rate']}</blockquote>")
    await bot.send_message(user_id, f"✅ <b>Баланс пополнен на {amount_rub} RUB!</b>", parse_mode="HTML")
    await bot.send_message(user_id, text_cab, reply_markup=kb.cabinet_kb(), parse_mode="HTML")


@router.message(PaymentState.input_amount_stars)
async def process_stars_input(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        await create_stars_invoice(message, amount, state)
        try: await message.delete()
        except: pass
    except: await message.answer("Введите число.")

@router.callback_query(F.data.startswith("pay_amt_stars_"))
async def process_stars_btn(call: types.CallbackQuery, state: FSMContext):
    amount = float(call.data.split("_")[3])
    await create_stars_invoice(call.message, amount, state)

async def create_stars_invoice(message, amount_rub, state):
    order_id = str(uuid.uuid4())
    create_payment(order_id, message.chat.id, amount_rub, "stars")
    
    user = get_user(message.chat.id)
    sub_name = SUBSCRIPTIONS.get(user[3], {}).get('name', 'Стандарт')
    
    # 100 RUB = 90 Stars (примерно)
    stars_amount = int(amount_rub * 0.9)
    if stars_amount < 1: stars_amount = 1
    
    prices = [types.LabeledPrice(label=f"Пополнение {amount_rub} RUB", amount=stars_amount)]
    
    # Генерируем ссылку
    link = await message.bot.create_invoice_link(
        title=f"Пополнение {amount_rub} RUB",
        description=f"Баланс бота",
        payload=order_id,
        currency="XTR",
        prices=prices
    )
    
    text = (
        "💳 <b>Счет Звездами</b>\n\n"
        f"📦 Товар: {sub_name}\n"
        f"💰 Сумма: {amount_rub} RUB ({stars_amount} ⭐️)\n"
        f"🔗 Ссылка: <a href='{link}'>Оплатить</a>"
    )
    # Кнопка ссылки здесь не обязательна, так как она в тексте, но можно добавить
    # check_stars тут чисто информативная
    msg = await message.answer(text, reply_markup=kb.invoice_kb(link, order_id, "check_stars"), parse_mode="HTML")
    await state.update_data(invoice_msg_id=msg.message_id)

@router.pre_checkout_query()
async def pre_checkout(query: types.PreCheckoutQuery):
    await query.answer(ok=True)

@router.message(F.successful_payment)
async def successful_payment(message: types.Message, state: FSMContext):
    info = message.successful_payment
    order_id = info.invoice_payload
    amount_rub = int(info.total_amount / 0.9) 
    
    pay = get_payment(order_id)
    if pay and pay[5] != 'paid':
        # Получаем ID сообщения, чтобы удалить инвойс
        data = await state.get_data()
        msg_id = data.get('invoice_msg_id')
        await success_deposit_logic(message.bot, message.from_user.id, amount_rub, order_id, msg_id, message.chat.id)

@router.callback_query(F.data.startswith("check_stars_"))
async def check_stars_manual(call: types.CallbackQuery):
    await call.answer("Оплата звездами проходит автоматически.", show_alert=True)