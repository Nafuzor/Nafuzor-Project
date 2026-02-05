from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from database import get_connection, is_section_disabled
from utils import generate_card_data
from states import CardState
import keyboards as kb

router = Router()

@router.callback_query(F.data == "cab_card")
async def my_card_menu(call: types.CallbackQuery):
    if is_section_disabled("cab_card"): return await call.answer("🔴 Раздел отключен", show_alert=True)
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM cards WHERE user_id = ?", (call.from_user.id,))
    card = c.fetchone()
    conn.close()
    if not card or not card[4]:
        text = "<blockquote>Активируйте карту</blockquote>"
        await call.message.edit_text(text, reply_markup=kb.card_start_kb(), parse_mode="HTML")
    else:
        if card[5]:
            await call.message.edit_text("🚫 ВАША КАРТА ЗАБЛОКИРОВАНА", reply_markup=kb.back_kb("nav_cabinet"))
            return
        date = card[6].split()[0] if card[6] else "N/A"
        text = f"<b>Моя карта:</b>\n\n<blockquote>Номер: <code>{card[1]}</code>\nCVV: <code>{card[2]}</code></blockquote>\n\n<b>Баланс:</b> {card[3]} RUB\nДата: {date}"
        await call.message.edit_text(text, reply_markup=kb.card_main_kb(), parse_mode="HTML")

@router.callback_query(F.data == "card_activate")
async def activate_card(call: types.CallbackQuery):
    num, cvv = generate_card_data()
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO cards (user_id, card_number, cvv, is_active, created_at) VALUES (?, ?, ?, 1, datetime('now'))", (call.from_user.id, num, cvv))
    conn.commit()
    conn.close()
    await my_card_menu(call)

@router.callback_query(F.data == "card_transfer")
async def start_transfer(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("Укажите username получателя:", reply_markup=kb.back_kb("cab_card"))
    await state.set_state(CardState.waiting_for_transfer_user)

@router.message(CardState.waiting_for_transfer_user)
async def process_transfer_user(message: types.Message, state: FSMContext):
    target = message.text.replace("@", "")
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE username = ?", (target,))
    res = c.fetchone()
    if not res: return await message.answer("Не найден.")
    await state.update_data(receiver_id=res[0])
    await message.answer("Укажите сумму:")
    await state.set_state(CardState.waiting_for_transfer_amount)

@router.message(CardState.waiting_for_transfer_amount)
async def process_transfer_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        data = await state.get_data()
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT balance FROM cards WHERE user_id = ?", (message.from_user.id,))
        bal = c.fetchone()[0]
        if amount > bal: return await message.answer("Недостаточно средств.")
        c.execute("UPDATE cards SET balance = balance - ? WHERE user_id = ?", (amount, message.from_user.id))
        c.execute("UPDATE cards SET balance = balance + ? WHERE user_id = ?", (amount, data['receiver_id']))
        conn.commit()
        conn.close()
        await message.answer("✅ Перевод успешен!", reply_markup=kb.back_kb("cab_card"))
        await state.clear()
    except ValueError:
        await message.answer("Число введи.")

@router.callback_query(F.data == "card_api")
async def api_info(call: types.CallbackQuery):
    await call.answer("API в разработке", show_alert=True)