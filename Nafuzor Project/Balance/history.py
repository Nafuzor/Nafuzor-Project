from aiogram import Router, F, types
from database import get_user_payments, get_payment
import keyboards as kb

router = Router()

@router.callback_query(F.data == "pay_history")
async def pay_history(call: types.CallbackQuery):
    payments = get_user_payments(call.from_user.id, limit=10)
    
    if not payments:
        await call.answer("📜 История пуста", show_alert=True)
        return
        
    await call.message.edit_text("<blockquote>📜 Ваша история пополнений:</blockquote>", reply_markup=kb.history_kb(payments), parse_mode="HTML")

@router.callback_query(F.data.startswith("hist_det_"))
async def history_detail(call: types.CallbackQuery):
    order_id = call.data.replace("hist_det_", "")
    pay = get_payment(order_id)
    
    if not pay:
        await call.answer("Не найдено")
        return
        
    # pay: order_id, user_id, amount, currency, system, status, created_at
    
    sys_map = {"stars": "⭐ Звезды", "crypto": "💲 CryptoBot", "card": "💳 Карта"}
    sys_name = sys_map.get(pay[4], pay[4])
    
    text = (
        f"<b>Детали платежа:</b>\n\n"
        f"Способ: {sys_name}\n"
        f"Сумма пополнения: {pay[2]} ₽\n"
        f"Дата: {pay[6]}"
    )
    await call.message.edit_text(text, reply_markup=kb.back_kb("pay_history"), parse_mode="HTML")