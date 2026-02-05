from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_kb(is_connected=False):
    card_btn = InlineKeyboardButton(text="💳 Моя карта", callback_data="menu_card") if is_connected else \
               InlineKeyboardButton(text="➕ Подключить карту", callback_data="connect_card_start")
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Вывод", callback_data="menu_withdraw"),
         InlineKeyboardButton(text="📂 Мои выводы", callback_data="menu_my_withdraws")],
        [card_btn]
    ])

def my_withdraws_cat_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏳ Ожидающие", callback_data="with_list_waiting")],
        [InlineKeyboardButton(text="✅ Успешные", callback_data="with_list_success"),
         InlineKeyboardButton(text="🔒 Закрытые", callback_data="with_list_closed")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_main")]
    ])

def my_card_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отключить карту", callback_data="disconnect_card")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_main")]
    ])

def withdraw_confirm_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="wd_confirm")],
        [InlineKeyboardButton(text="✏️ Юзернейм", callback_data="wd_edit_user"),
         InlineKeyboardButton(text="✏️ Сумма", callback_data="wd_edit_amount")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="menu_main")]
    ])

def withdraw_cancel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="wd_back_to_confirm")]
    ])

# КНОПКА НАЗАД ДЛЯ ВВОДА СУММЫ (НОВАЯ)
def back_to_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_main")]
    ])

# КНОПКА ПРИ ОТСУТСТВИИ КАРТЫ (ИСПРАВЛЕНИЕ ОШИБКИ)
def withdraw_no_card_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Подключить карту", callback_data="connect_card_start")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_main")]
    ])

# --- ADMIN ---

def admin_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Заявки (Ожидают)", callback_data="adm_with_waiting")],
        [InlineKeyboardButton(text="✅ Успешные", callback_data="adm_with_success"),
         InlineKeyboardButton(text="🔒 Закрытые", callback_data="adm_with_closed")],
        [InlineKeyboardButton(text="⚙️ Настройки бота", callback_data="adm_settings_menu")]
    ])

def admin_settings_kb(notify, disabled_str):
    notif_emoji = "🟢" if notify == '1' else "🔴"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📣 Рассылка", callback_data="adm_broadcast")],
        [InlineKeyboardButton(text="➕ Админ", callback_data="adm_add_admin"),
         InlineKeyboardButton(text="➖ Админ", callback_data="adm_rem_admin")],
        [InlineKeyboardButton(text=f"🔔 Уведомления о выводах {notif_emoji}", callback_data="adm_tog_notify")],
        [InlineKeyboardButton(text="🚫 Отключить раздел", callback_data="adm_disable_sec")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")]
    ])

def admin_disable_sections_kb(disabled_str):
    sections = {
        "withdraw": "Вывод средств",
        "my_withdraws": "Мои выводы",
        "card": "Моя карта"
    }
    rows = []
    for key, name in sections.items():
        status = "🔴" if key in disabled_str else "🟢"
        rows.append([InlineKeyboardButton(text=f"{name} {status}", callback_data=f"adm_tog_sec_{key}")])
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="adm_settings_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def broadcast_type_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 URL Buttons", callback_data="bc_type_url"),
         InlineKeyboardButton(text="🤖 System Buttons", callback_data="bc_type_sys")],
        [InlineKeyboardButton(text="➡️ Без кнопок", callback_data="bc_send_now")],
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="adm_settings_menu")]
    ])

def broadcast_sys_kb(selected):
    opts = {"menu_main": "Главное меню", "menu_withdraw": "Вывод", "menu_card": "Карта"}
    rows = []
    for k, v in opts.items():
        mark = "✅" if k in selected else "⬜️"
        rows.append([InlineKeyboardButton(text=f"{mark} {v}", callback_data=f"bc_sys_tog_{k}")])
    rows.append([InlineKeyboardButton(text="Готово ✅", callback_data="bc_sys_done")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def broadcast_confirm_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Отправить", callback_data="bc_final_send")],
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="adm_settings_menu")]
    ])