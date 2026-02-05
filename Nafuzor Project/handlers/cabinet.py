from aiogram import Router, F, types
from database import get_user, get_connection, is_section_disabled
from config import SUBSCRIPTIONS
import keyboards as kb

router = Router()

# --- ЛИЧНЫЙ КАБИНЕТ ---
@router.callback_query(F.data == "nav_cabinet")
async def show_cabinet(call: types.CallbackQuery):
    if is_section_disabled("nav_cabinet"): return await call.answer("🔴 Раздел отключен", show_alert=True)
    
    user = get_user(call.from_user.id)
    sub_conf = SUBSCRIPTIONS.get(user[3], SUBSCRIPTIONS['none'])
    
    text = (
        f"<blockquote>👤 <b>Профиль:</b> {user[1]}\n"
        f"▫️ <b>Баланс:</b> {user[2]} RUB\n"
        f"▫️ <b>Подписка:</b> {sub_conf['name']}\n"
        f"▫️ <b>Прайс:</b> {sub_conf['display_rate']}</blockquote>"
    )
    await call.message.edit_text(text, reply_markup=kb.cabinet_kb(), parse_mode="HTML")

# --- ПОКУПКА ПОДПИСКИ ---
@router.callback_query(F.data == "cab_sub")
async def buy_sub_menu(call: types.CallbackQuery):
    if is_section_disabled("cab_sub"): return await call.answer("🔴 Раздел отключен", show_alert=True)
    user = get_user(call.from_user.id)
    
    if user[3] == "zero_limits":
        await call.answer("⚠️ У вас уже куплена максимальная подписка\nПодписка Zero Limits", show_alert=True)
        return

    current_rank = SUBSCRIPTIONS.get(user[3], {}).get('rank', 0)
    text = (
        "<blockquote>🚀 <b>Выберите свой тариф</b>\n\n"
        "💎 <b>Подписка - Alpha</b>\n💰 Цена: 300 ₽/мес\n\n"
        "🔮 <b>Подписка - Nucleus</b>\n💰 Цена: 600 ₽/мес\n\n"
        "🔥 <b>Подписка - Zero Limits</b>\n💰 Цена: 1100 ₽/мес</blockquote>"
    )
    await call.message.edit_text(text, reply_markup=kb.subscription_kb(current_rank), parse_mode="HTML")

@router.callback_query(F.data.startswith("buy_"))
async def sub_details(call: types.CallbackQuery):
    if is_section_disabled(call.data): return await call.answer("🔴 Тариф временно недоступен", show_alert=True)
    
    sub_key = call.data.split("_")[1]
    if sub_key == "zero": sub_key = "zero_limits"
    sub_info = SUBSCRIPTIONS[sub_key]
    user = get_user(call.from_user.id)
    
    text = (
        f"<b>Подписка:</b> {sub_info['name']}\n"
        f"<a href='{sub_info['link']}'>Все функции подписки {sub_info['name']}</a>\n\n"
        f"<b>Ваш баланс:</b> {user[2]} RUB\n"
        f"<b>Срок подписки:</b> 1 месяц"
    )
    await call.message.edit_text(text, reply_markup=kb.buy_confirm_kb(sub_key), parse_mode="HTML", disable_web_page_preview=True)

@router.callback_query(F.data.startswith("confirm_buy_"))
async def process_purchase(call: types.CallbackQuery):
    sub_key = call.data.replace("confirm_buy_", "")
    sub_info = SUBSCRIPTIONS[sub_key]
    user = get_user(call.from_user.id)
    
    if user[2] >= sub_info['price']:
        new_balance = user[2] - sub_info['price']
        conn = get_connection()
        c = conn.cursor()
        c.execute("UPDATE users SET balance_rub = ?, subscription = ? WHERE user_id = ?", 
                  (new_balance, sub_key, call.from_user.id))
        conn.commit()
        conn.close()
        
        text = (
            f"✅ Успешно!\n"
            f"▫️ <b>Подписка:</b> {sub_info['name']}\n"
            f"▫️ <b>Прайс:</b> {sub_info['display_rate']}"
        )
        await call.message.edit_text(text, reply_markup=kb.back_kb("nav_cabinet"), parse_mode="HTML")
    else:
        await call.answer("🚫 Недостаточно средств на балансе!", show_alert=True)