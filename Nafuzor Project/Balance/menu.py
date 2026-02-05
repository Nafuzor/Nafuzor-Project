from aiogram import Router, F, types
from database import get_user, is_section_disabled
import keyboards as kb

router = Router()

@router.callback_query(F.data == "cab_balance")
async def show_balance_menu(call: types.CallbackQuery):
    if is_section_disabled("cab_balance"): return await call.answer("🔴 Раздел отключен", show_alert=True)
    user = get_user(call.from_user.id)
    text = (
        f"<blockquote>Управление вашим балансом 💰</blockquote>\n\n"
        f"Ваш баланс: {user[2]} ₽"
    )
    await call.message.edit_text(text, reply_markup=kb.balance_menu_kb(), parse_mode="HTML")