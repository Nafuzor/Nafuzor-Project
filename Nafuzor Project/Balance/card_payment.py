from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from database import create_payment, get_payment, get_user, get_connection
from config import YOOMONEY_TOKEN, YOOMONEY_WALLET, SUBSCRIPTIONS
from states import PaymentState
import keyboards as kb
from yoomoney import Quickpay, Client
import uuid
import asyncio

router = Router()

# Логика успешного платежа и редиректа
async def success_deposit_logic(bot, user_id, amount_rub, order_id, message_to_delete_id=None, chat_id=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET balance_rub = balance_rub + ? WHERE user_id = ?", (amount_rub, user_id))
    c.execute("UPDATE payments SET status = 'paid' WHERE order_id = ?", (order_id,))
    
    # Рефералка
    c.execute("SELECT referrer_id, username FROM users WHERE user_id = ?", (user_id,))
    res = c.fetchone()
    my_username = res[1] if res[1] else "User"
    
    if res and res[0]:
        referrer_id = res[0]
        bonus = amount_rub * 0.15
        c.execute("UPDATE users SET balance_rub = balance_rub + ?, ref_earnings = ref_earnings + ? WHERE user_id = ?", (bonus, bonus, referrer_id))
        try:
            await bot.send_message(referrer_id, f"<blockquote>💰 Реферальный бонус!\nБонус {bonus} RUB\nОт @{my_username}</blockquote>", parse_mode="HTML")
        except: pass
    conn.commit()
    conn.close()

    # Удаление сообщений и редирект
    if message_to_delete_id and chat_id:
        try: await bot.delete_message(chat_id, message_to_delete_id)
        except: pass
    
    # Показываем кабинет (вызываем хендлер кабинета)
    from handlers.cabinet import show_cabinet_msg
    # Имитируем объект message для вызова функции
    fake_msg = types.Message(chat=types.Chat(id=user_id, type='private'), from_user=types.User(id=user_id, is_bot=False, first_name="User"), date=datetime.now())
    await show_cabinet_msg(fake_msg)

# Обработка ввода суммы
@router.message(PaymentState.input_amount_card)
async def process_card_input(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        await create_card_invoice(message, amount, state)
    except: await message.answer("Введите число.")

@router.callback_query(F.data.startswith("pay_amt_card_"))
async def process_card_btn(call: types.CallbackQuery, state: FSMContext):
    amount = float(call.data.split("_")[3])
    await create_card_invoice(call.message, amount, state)

async def create_card_invoice(message, amount, state):
    order_id = str(uuid.uuid4())
    user_id = message.chat.id
    create_payment(order_id, user_id, amount, "card")
    
    quickpay = Quickpay(
        receiver=YOOMONEY_WALLET,
        quickpay_form="shop",
        targets=f"Bal {user_id}",
        paymentType="SB",
        sum=amount,
        label=order_id
    )
    
    # Запоминаем ID сообщения для удаления
    msg = await message.answer(
        f"💳 Счет Картой\n💰 Сумма: {amount} RUB\n🔗 Ссылка: <a href='{quickpay.redirected_url}'>Оплатить</a>",
        reply_markup=kb.invoice_kb(quickpay.redirected_url, order_id, "check_yoomoney"),
        parse_mode="HTML"
    )
    await state.update_data(invoice_msg_id=msg.message_id)

@router.callback_query(F.data.startswith("check_yoomoney_"))
async def check_yoomoney(call: types.CallbackQuery, state: FSMContext):
    order_id = call.data.replace("check_yoomoney_", "")
    pay = get_payment(order_id)
    if not pay: return await call.answer("Ошибка")
    if pay[5] == 'paid': return await call.answer("Уже оплачено")
    
    client = Client(YOOMONEY_TOKEN)
    history = client.operation_history(label=order_id)
    if history.operations and history.operations[0].status == 'success':
        data = await state.get_data()
        msg_id = data.get('invoice_msg_id')
        await success_deposit_logic(call.bot, call.from_user.id, pay[2], order_id, msg_id, call.message.chat.id)
    else:
        await call.answer("❌ Не оплачено", show_alert=True)