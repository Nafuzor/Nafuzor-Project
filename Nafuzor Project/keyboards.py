from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import json
import urllib.parse

# ⚠️ ВСТАВЬ СВОЮ ССЫЛКУ
SITE_URL = "https://nafuzor.github.io/integration/" 

# --- ГЛАВНОЕ МЕНЮ ---
def main_menu_kb(user_data=None):
    keyboard = []
    if user_data:
        json_str = json.dumps(user_data)
        params = urllib.parse.quote(json_str)
        full_url = f"{SITE_URL}?data={params}"
        keyboard.append([InlineKeyboardButton(text="📱 Открыть Меню", web_app=WebAppInfo(url=full_url))])

    keyboard.append([InlineKeyboardButton(text="📱 Управление номерами", callback_data="nav_numbers")])
    keyboard.append([
        InlineKeyboardButton(text="👤 Личный кабинет", callback_data="nav_cabinet"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="nav_stats")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def back_kb(target="nav_main"):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data=target)]])

# --- НОМЕРА ---
def numbers_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить номер", callback_data="num_add"),
         InlineKeyboardButton(text="📂 Мои номера", callback_data="num_my")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="nav_main")]
    ])

def number_category_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟧 MAX", callback_data="cat_max"),
         InlineKeyboardButton(text="🟩 WhatsApp", callback_data="cat_wa")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="nav_numbers")]
    ])

def my_numbers_filter_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ В работе", callback_data="filter_work"),
         InlineKeyboardButton(text="⏳ Ожидает", callback_data="filter_wait")],
        [InlineKeyboardButton(text="✅ Успех", callback_data="filter_success"),
         InlineKeyboardButton(text="⛔ Блок", callback_data="filter_block")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="nav_numbers")]
    ])

# --- КАБИНЕТ ---
def cabinet_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Мой баланс", callback_data="cab_balance")],
        [InlineKeyboardButton(text="💎 Купить подписку", callback_data="cab_sub"),
         InlineKeyboardButton(text="🔹 Прочее", callback_data="cab_misc")],
        [InlineKeyboardButton(text="👥 Рефералка", callback_data="cab_ref"),
         InlineKeyboardButton(text="💳 Моя Карта", callback_data="cab_card")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="nav_main")]
    ])

# --- БАЛАНС И ОПЛАТА ---
def balance_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 Пополнить баланс", callback_data="pay_deposit"),
         InlineKeyboardButton(text="📜 История пополнения", callback_data="pay_history")],
        [InlineKeyboardButton(text="👤 Личный кабинет", callback_data="nav_cabinet")]
    ])

def payment_method_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Оплата Звездами", callback_data="pay_method_stars"),
         InlineKeyboardButton(text="💲 Криптовалюта", callback_data="pay_method_crypto")],
        [InlineKeyboardButton(text="💳 Картой", callback_data="pay_method_card")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="cab_balance")]
    ])

def amount_select_kb(method):
    sums = [150, 300, 600, 1100]
    keyboard = []
    
    if method == 'stars':
        keyboard.append([InlineKeyboardButton(text="🛒 Купить Звезды", url="https://t.me/PremiumBot")])
        
    row = []
    for s in sums:
        text = f"{s}.00 $" if method == 'crypto' else f"{s}.00 ₽"
        row.append(InlineKeyboardButton(text=text, callback_data=f"pay_amt_{method}_{s}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
            
    keyboard.append([InlineKeyboardButton(text="✍️ Ввести свою сумму", callback_data=f"pay_input_{method}")])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="pay_deposit")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def invoice_kb(pay_url, order_id, check_callback, cancel_callback="pay_deposit"):
    # Если pay_url пустой (например для звезд внутри бота), кнопку ссылки не ставим
    btns = []
    if pay_url:
        btns.append([InlineKeyboardButton(text="🔗 Оплатить", url=pay_url)])
    
    btns.append([InlineKeyboardButton(text="🔄 Проверить", callback_data=f"{check_callback}_{order_id}")])
    btns.append([InlineKeyboardButton(text="❌ Отмена", callback_data=cancel_callback)])
    return InlineKeyboardMarkup(inline_keyboard=btns)

def history_kb(payments):
    keyboard = []
    for p in payments:
        sys_name = "Карта" if p[0] == "card" else ("Крипто" if p[0] == "crypto" else "Звезды")
        keyboard.append([InlineKeyboardButton(text=f"{sys_name} | {p[1]} ₽", callback_data=f"hist_det_{p[3]}")])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="cab_balance")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# --- АДМИНКА ---
def admin_panel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Получить номер", callback_data="adm_get_num"),
         InlineKeyboardButton(text="📉 Сообщить о слете", callback_data="adm_report_drop")],
        [InlineKeyboardButton(text="⚙️ Дополнительно", callback_data="adm_extra")]
    ])

def user_code_confirm_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ввел", callback_data="code_entered"),
         InlineKeyboardButton(text="⏭️ Скип", callback_data="code_skip")]
    ])

def drop_confirm_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📉 Слет", callback_data="confirm_drop"),
         InlineKeyboardButton(text="⛔ Блок", callback_data="confirm_block")]
    ])

def admin_extra_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Отчет", callback_data="adm_report")],
        [InlineKeyboardButton(text="💎 Выдать подписку", callback_data="adm_give_sub"),
         InlineKeyboardButton(text="💰 Выдать баланс", callback_data="adm_give_bal")],
        [InlineKeyboardButton(text="🟢 Изменить статус", callback_data="adm_chg_status")],
        [InlineKeyboardButton(text="💳 Управление картами", callback_data="adm_cards")],
        [InlineKeyboardButton(text="🤖 Настройки бота", callback_data="adm_settings")],
        [InlineKeyboardButton(text="🔔 Напоминалка", callback_data="adm_remind")],
        [InlineKeyboardButton(text="🧹 Очистить статистику", callback_data="adm_clear_stats"),
         InlineKeyboardButton(text="🧹 Очистить очередь", callback_data="adm_clear_queue")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
    ])

def admin_cards_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Выплата (Авто)", callback_data="adm_payout")],
        [InlineKeyboardButton(text="➕ Выдать баланс", callback_data="adm_card_add"),
         InlineKeyboardButton(text="➖ Списать баланс", callback_data="adm_card_sub")],
        [InlineKeyboardButton(text="🔒 Заблокировать карту", callback_data="adm_card_block"),
         InlineKeyboardButton(text="🔓 Разблокировать карту", callback_data="adm_card_unblock")],
        [InlineKeyboardButton(text="👀 Данные карт", callback_data="adm_card_view")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="adm_extra")]
    ])

# --- ПОДПИСКИ ---
def subscription_kb(current_sub_rank):
    buttons = []
    if current_sub_rank < 1:
        buttons.append([InlineKeyboardButton(text="💎 Alpha (300₽)", callback_data="buy_alpha")])
    if current_sub_rank < 2:
        buttons.append([InlineKeyboardButton(text="🔮 Nucleus (600₽)", callback_data="buy_nucleus")])
    if current_sub_rank < 3:
        buttons.append([InlineKeyboardButton(text="🔥 Zero Limits (1100₽)", callback_data="buy_zero")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="nav_cabinet")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def buy_confirm_kb(sub_key):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Купить подписку", callback_data=f"confirm_buy_{sub_key}")],
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="cab_sub")]
    ])

# --- КАРТА ---
def card_start_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔓 Активировать", callback_data="card_activate")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="nav_cabinet")]
    ])

def card_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обменять", url="t.me/Lixcuk_robot")],
        [InlineKeyboardButton(text="💸 Перевести", callback_data="card_transfer"),
         InlineKeyboardButton(text="🔌 API", callback_data="card_api")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="nav_cabinet")]
    ])