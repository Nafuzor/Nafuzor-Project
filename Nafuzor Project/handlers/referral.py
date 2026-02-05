from aiogram import Router, F, types
from database import get_user, get_connection, is_section_disabled
from utils import generate_qr
import keyboards as kb

router = Router()

@router.callback_query(F.data == "cab_ref")
async def referral_system(call: types.CallbackQuery):
    if is_section_disabled("cab_ref"): return await call.answer("🔴 Раздел отключен", show_alert=True)
    
    user = get_user(call.from_user.id)
    # user[7] это ref_earnings
    ref_earnings = user[7] if len(user) > 7 else 0
    
    bot_info = await call.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user[0]}"
    
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (user[0],))
    count = c.fetchone()[0]
    conn.close()

    text = (
        "👥 <b>Партнёрская программа</b>\n\n"
        "💼 Зарабатывай вместе с нами!\n"
        "<blockquote>1) <a href='https://nafuzor.github.io/nafuzor-site/#sys_view_partner_ref_system_init_loader'>Приглашай друзей и получай 15% с пополнение друга</a></blockquote>\n\n"
        f"🔗 <b>Ваша ссылка:</b>\n<code>{ref_link}</code>\n\n"
        "<blockquote>📊 <b>Ваша статистика:</b>\n"
        f"👤 Приглашено: {count}\n"
        f"🛒 Заработано: {ref_earnings} RUB</blockquote>"
    )
    
    keyb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="📱 Показать QR", callback_data="show_qr")],
        [types.InlineKeyboardButton(text="🔙 Назад", callback_data="nav_cabinet")]
    ])
    await call.message.edit_text(text, reply_markup=keyb, parse_mode="HTML", disable_web_page_preview=True)

@router.callback_query(F.data == "show_qr")
async def show_qr_code(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    bot_info = await call.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user[0]}"
    qr_file = generate_qr(ref_link)
    photo = types.BufferedInputFile(qr_file.read(), filename="qr.png")
    await call.message.answer_photo(photo, caption="📱 Ваш QR")