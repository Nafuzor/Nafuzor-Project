from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import get_connection, is_admin, get_setting_bool, set_setting, get_setting, is_section_disabled
from config import ADMIN_ID, SUBSCRIPTIONS
from states import AdminState
import keyboards as kb
from datetime import datetime, timedelta
import asyncio

router = Router()

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def get_id_by_username(username):
    """Получение ID пользователя по юзернейму"""
    if not username: return None
    username = username.replace("@", "").strip()
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE username = ?", (username,))
    res = c.fetchone()
    conn.close()
    return res[0] if res else None

async def safe_edit(message: types.Message, text: str, reply_markup=None):
    """Безопасное редактирование сообщения"""
    try:
        if message.photo:
            # Если это фото, меняем подпись
            await message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="HTML")
        else:
            # Если это текст, меняем текст
            await message.edit_text(text=text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception as e:
        # Если сообщение слишком старое или удалено, удаляем и шлем новое
        try: await message.delete()
        except: pass
        await message.answer(text, reply_markup=reply_markup, parse_mode="HTML")

# ==========================================
# ОБРАБОТКА ДЕЙСТВИЙ ЮЗЕРА (ВВЕЛ / СКИП)
# ==========================================
# Эти хендлеры должны быть доступны ВСЕМ, не только админу

@router.callback_query(F.data == "code_entered")
async def user_code_enter(call: types.CallbackQuery):
    # 1. Убираем часики
    await call.answer()
    
    # 2. Логика базы данных
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    c = conn.cursor()
    
    # Ищем номер, который "Ожидает" у этого юзера
    c.execute("UPDATE numbers SET status = 'В работе', entered_at = ? WHERE user_id = ? AND status = 'Ожидает'", (now, call.from_user.id))
    
    # Получаем юзернейм для уведомления админа
    c.execute("SELECT username FROM users WHERE user_id = ?", (call.from_user.id,))
    res = c.fetchone()
    username = res[0] if res else "Unknown"
    
    conn.commit()
    conn.close()
    
    # 3. Изменяем сообщение у пользователя (убираем кнопки)
    try:
        success_text = "✅ <b>Вы подтвердили ввод кода!</b>\nОжидайте проверку."
        if call.message.photo:
            await call.message.edit_caption(caption=success_text, reply_markup=None, parse_mode="HTML")
        else:
            await call.message.edit_text(text=success_text, reply_markup=None, parse_mode="HTML")
    except:
        # Если не вышло отредактировать, просто шлем сообщение
        await call.message.delete()
        await call.message.answer("✅ <b>Вы подтвердили ввод кода!</b>", parse_mode="HTML")

    # 4. Уведомляем админа
    try:
        await call.bot.send_message(ADMIN_ID, f"🟢 Пользователь @{username} успешно ввел код!")
    except: pass

@router.callback_query(F.data == "code_skip")
async def user_code_skip(call: types.CallbackQuery):
    await call.answer()
    
    conn = get_connection()
    c = conn.cursor()
    
    # Удаляем номер из очереди
    c.execute("DELETE FROM numbers WHERE user_id = ? AND status = 'Ожидает'", (call.from_user.id,))
    
    c.execute("SELECT username FROM users WHERE user_id = ?", (call.from_user.id,))
    res = c.fetchone()
    username = res[0] if res else "Unknown"
    
    conn.commit()
    conn.close()
    
    try:
        skip_text = "⏭️ <b>Вы пропустили этот номер.</b>\nОн удален из очереди."
        if call.message.photo:
            await call.message.edit_caption(caption=skip_text, reply_markup=None, parse_mode="HTML")
        else:
            await call.message.edit_text(text=skip_text, reply_markup=None, parse_mode="HTML")
    except:
        await call.message.delete()
        await call.message.answer("⏭️ <b>Вы пропустили номер.</b>", parse_mode="HTML")

    try:
        await call.bot.send_message(ADMIN_ID, f"🔴 Пользователь @{username} скипнул (отменил) код.")
    except: pass


# ==========================================
# ГЛАВНОЕ МЕНЮ АДМИНКИ
# ==========================================

@router.message(F.text == "/panel")
async def open_panel(message: types.Message):
    if not is_admin(message.from_user.id): return
    await message.answer("👑 <b>Админ панель</b>", reply_markup=kb.admin_panel_kb(), parse_mode="HTML")

@router.callback_query(F.data == "admin_panel")
async def back_panel(call: types.CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return
    await state.clear()
    await safe_edit(call.message, "👑 <b>Админ панель</b>", reply_markup=kb.admin_panel_kb())

# --- КОМАНДА /su (ССЫЛКИ) ---
@router.message(F.text == "/su")
async def su_command(message: types.Message):
    if not is_admin(message.from_user.id): return
    
    bot_info = await message.bot.get_me()
    bn = bot_info.username
    
    links = {
        "Личный кабинет": "cabinet", "Главное меню": "main",
        "Управление номерами": "numbers", "Мои номера": "my_nums", 
        "Категория MAX": "cat_max", "Категория WhatsApp": "cat_wa", 
        "В работе": "flt_work", "Ожидает": "flt_wait", "Успех": "flt_success",
        "Блок": "flt_block", "Статистика": "stats",
        "Купить подписку": "buy_sub", "Рефералка": "ref", "Моя карта": "card"
    }
    
    msg = "🔐 <b>Ссылки на разделы:</b>\n\n"
    for name, code in links.items():
        link = f"https://t.me/{bn}?start={code}"
        msg += f"▫️ <a href='{link}'>{name}</a>\n"
        
    await message.answer(msg, parse_mode="HTML", disable_web_page_preview=True)

# ==========================================
# 2. РАБОТА С НОМЕРАМИ (ПОЛУЧИТЬ, СЛЕТ)
# ==========================================

@router.callback_query(F.data == "adm_get_num")
async def get_number_list(call: types.CallbackQuery):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT n.id, n.number, n.category, u.reputation FROM numbers n JOIN users u ON n.user_id = u.user_id WHERE n.status = 'Ожидает' ORDER BY u.reputation DESC")
    nums = c.fetchall()
    conn.close()
    if not nums: return await call.answer("📭 Очередь пуста", show_alert=True)

    kb_list = [[types.InlineKeyboardButton(text=f"{n[2]} | {n[1]} (Rep: {n[3]})", callback_data=f"adm_proc_num_{n[0]}")] for n in nums]
    kb_list.append([types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")])
    await safe_edit(call.message, "📱 <b>Выберите номер:</b>", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb_list))

@router.callback_query(F.data.startswith("adm_proc_num_"))
async def process_number_view(call: types.CallbackQuery, state: FSMContext):
    try: num_id = int(call.data.split("_")[3])
    except: return
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT n.number, n.category, u.subscription, u.user_id FROM numbers n JOIN users u ON n.user_id = u.user_id WHERE n.id = ?", (num_id,))
    data = c.fetchone()
    conn.close()
    if not data: return await call.answer("Не актуально", show_alert=True)
    
    sub_name = SUBSCRIPTIONS.get(data[2], {}).get('name', 'Нет')
    price = SUBSCRIPTIONS.get(data[2], {}).get('rates', {}).get('base', 5)
    
    text = (f"🔢 <b>Номер:</b> {data[0]}\n📂 <b>Категория:</b> {data[1]}\n💎 <b>Подписка:</b> {sub_name}\n💲 <b>Прайс старт:</b> {price}$")
    await state.update_data(target_user_id=data[3])
    await safe_edit(call.message, text + "\n\n📸 <b>Отправьте код (текст или фото):</b>", reply_markup=kb.back_kb("adm_get_num"))
    await state.set_state(AdminState.sending_code)

@router.message(AdminState.sending_code)
async def send_code_to_user(message: types.Message, state: FSMContext):
    data = await state.get_data()
    try:
        if message.photo:
            await message.bot.send_photo(data['target_user_id'], message.photo[-1].file_id, caption="⚠️ <b>push-уведомление</b>\n⏳ Действителен 5 минут!", reply_markup=kb.user_code_confirm_kb(), parse_mode="HTML")
        elif message.text:
            msg_text = f"<blockquote>⚠️ <b>push-уведомление</b>\n🔐 Ваш код: {message.text}\n⏳ Действителен 5 минут!</blockquote>"
            await message.bot.send_message(data['target_user_id'], msg_text, reply_markup=kb.user_code_confirm_kb(), parse_mode="HTML")
        else: return await message.answer("Текст или фото!")
        await message.answer("✅ Код отправлен пользователю!")
    except Exception as e: await message.answer(f"Ошибка: {e}")
    await state.clear()
    await open_panel(message)

# --- СЛЕТ ---
@router.callback_query(F.data == "adm_report_drop")
async def report_drop_list(call: types.CallbackQuery):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, number, category FROM numbers WHERE status = 'В работе'")
    nums = c.fetchall()
    conn.close()
    if not nums: return await call.answer("Нет номеров в работе", show_alert=True)
    kb_list = [[types.InlineKeyboardButton(text=f"{n[2]} | {n[1]}", callback_data=f"drop_sel_{n[0]}")] for n in nums]
    kb_list.append([types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")])
    await safe_edit(call.message, "📉 <b>Выберите номер для слета:</b>", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb_list))

@router.callback_query(F.data.startswith("drop_sel_"))
async def input_drop_time(call: types.CallbackQuery, state: FSMContext):
    try: num_id = int(call.data.split("_")[2])
    except: return
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT number, category, entered_at, user_id FROM numbers WHERE id = ?", (num_id,))
    data = c.fetchone()
    conn.close()
    if not data: return await call.answer("Номер не найден", show_alert=True)
    
    # Форматируем время входа (если оно есть)
    time_str = data[2].split()[1] if data[2] else "??"
    
    await state.update_data(drop_data=data, num_id=num_id)
    await safe_edit(call.message, f"🔢 {data[0]}\n⏱ Принят: {time_str}\n\n✍️ <b>Введите время слета (например 10:00):</b>")
    await state.set_state(AdminState.reporting_drop_time)

@router.message(AdminState.reporting_drop_time)
async def calc_hold(message: types.Message, state: FSMContext):
    try:
        drop_time = datetime.strptime(message.text.strip(), "%H:%M")
        data = await state.get_data()
        # Парсим время из базы
        entered_at = datetime.strptime(data['drop_data'][2], "%Y-%m-%d %H:%M:%S")
        drop_dt = entered_at.replace(hour=drop_time.hour, minute=drop_time.minute, second=0)
        
        if drop_dt < entered_at: drop_dt += timedelta(days=1)
        
        hold_min = int((drop_dt - entered_at).total_seconds() / 60)
        hours, mins = hold_min // 60, hold_min % 60
        hold_str = f"{hours}ч {mins}м"
        
        await state.update_data(hold_str=hold_str, drop_dt=drop_dt.strftime("%Y-%m-%d %H:%M:%S"), total_min=hold_min)
        await message.answer(f"⏳ Холд: {hold_str}\n\nВыберите действие:", reply_markup=kb.drop_confirm_kb(), parse_mode="HTML")
    except Exception as e: await message.answer(f"Ошибка времени: {e}")

@router.callback_query(F.data == "confirm_drop")
async def finish_drop(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT subscription FROM users WHERE user_id = ?", (data['drop_data'][3],))
    sub = c.fetchone()[0] or 'none'
    
    sub_config = SUBSCRIPTIONS.get(sub, SUBSCRIPTIONS['none'])
    rates = sub_config.get('rates', {'base': 5, 'extra': 2.4})
    
    mins = data['total_min']
    payout = 0
    if mins >= 60:
        payout += rates['base']
        remain = mins - 60
        if remain > 0:
            payout += (remain // 30) * rates['extra']
            
    c.execute("UPDATE numbers SET status='Успех', drop_time=?, hold_time=?, payout_amount=? WHERE id=?", 
              (data['drop_dt'], data['hold_str'], payout, data['num_id']))
    conn.commit()
    conn.close()
    
    try: await call.bot.send_message(data['drop_data'][3], f"✅ Ваш номер успешно отстоял {data['hold_str']}.\nОжидайте выплату: {payout}$")
    except: pass
    await safe_edit(call.message, f"✅ Слет зафиксирован. К выплате: {payout}$")
    await state.clear()

@router.callback_query(F.data == "confirm_block")
async def finish_block(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE numbers SET status='Блок', drop_time=?, hold_time=? WHERE id=?", 
              (data['drop_dt'], data['hold_str'], data['num_id']))
    conn.commit()
    conn.close()
    try: await call.bot.send_message(data['drop_data'][3], f"⛔ Номер заблокирован.\nХолд: {data['hold_str']}")
    except: pass
    await safe_edit(call.message, "⛔ Номер отправлен в Блок.")
    await state.clear()


# ==========================================
# 3. ДОПОЛНИТЕЛЬНО
# ==========================================

@router.callback_query(F.data == "adm_extra")
async def extra_menu(call: types.CallbackQuery):
    await safe_edit(call.message, "⚙️ <b>Дополнительно</b>", reply_markup=kb.admin_extra_kb())

# --- ОТЧЕТЫ ---
@router.callback_query(F.data == "adm_report")
async def report_menu(call: types.CallbackQuery):
    keyb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ Успех", callback_data="rep_success"),
         types.InlineKeyboardButton(text="⛔ Блок", callback_data="rep_block")],
        [types.InlineKeyboardButton(text="🔙 Назад", callback_data="adm_extra")]
    ])
    await safe_edit(call.message, "Выберите статус для отчета:", reply_markup=keyb)

@router.callback_query(F.data.in_({"rep_success", "rep_block"}))
async def send_report_file(call: types.CallbackQuery):
    status = "Успех" if call.data == "rep_success" else "Блок"
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT number, hold_time, category FROM numbers WHERE status = ?", (status,))
    rows = c.fetchall()
    conn.close()
    text = "\n".join([f"{r[0]} - {r[1]} - {r[2]}" for r in rows]) if rows else "Пусто"
    file = types.BufferedInputFile(text.encode('utf-8'), filename=f"report_{call.data}.txt")
    await call.message.answer_document(file, caption=f"📄 Отчет: {status}")

# --- ВЫДАЧА ПОДПИСКИ ---
@router.callback_query(F.data == "adm_give_sub")
async def ask_sub_user(call: types.CallbackQuery, state: FSMContext):
    await safe_edit(call.message, "👤 Введите Username пользователя:", reply_markup=kb.back_kb("adm_extra"))
    await state.set_state(AdminState.give_sub_user)

@router.message(AdminState.give_sub_user)
async def ask_sub_name(message: types.Message, state: FSMContext):
    uid = get_id_by_username(message.text)
    if not uid: return await message.answer("Не найден.")
    await state.update_data(target_uid=uid)
    keyb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Alpha", callback_data="set_sub_alpha"),
         types.InlineKeyboardButton(text="Nucleus", callback_data="set_sub_nucleus")],
        [types.InlineKeyboardButton(text="Zero Limits", callback_data="set_sub_zero_limits"),
         types.InlineKeyboardButton(text="Убрать", callback_data="set_sub_none")]
    ])
    await message.answer("Выберите подписку:", reply_markup=keyb)

@router.callback_query(F.data.startswith("set_sub_"))
async def set_subscription(call: types.CallbackQuery, state: FSMContext):
    sub = call.data.replace("set_sub_", "")
    data = await state.get_data()
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET subscription = ? WHERE user_id = ?", (sub, data['target_uid']))
    conn.commit()
    conn.close()
    await safe_edit(call.message, f"✅ Подписка {sub} выдана.")
    await state.clear()

# --- ВЫДАЧА БАЛАНСА ---
@router.callback_query(F.data == "adm_give_bal")
async def ask_bal_user(call: types.CallbackQuery, state: FSMContext):
    await safe_edit(call.message, "👤 Введите Username для пополнения:", reply_markup=kb.back_kb("adm_extra"))
    await state.set_state(AdminState.give_bal_user)

@router.message(AdminState.give_bal_user)
async def ask_bal_amount(message: types.Message, state: FSMContext):
    uid = get_id_by_username(message.text)
    if not uid: return await message.answer("Не найден.")
    await state.update_data(target_uid=uid)
    await message.answer("💰 Введите сумму (RUB):")
    await state.set_state(AdminState.give_bal_amount)

@router.message(AdminState.give_bal_amount)
async def set_balance(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        data = await state.get_data()
        target_uid = data['target_uid']
        conn = get_connection()
        c = conn.cursor()
        c.execute("UPDATE users SET balance_rub = balance_rub + ? WHERE user_id = ?", (amount, target_uid))
        
        # Рефералка 15%
        c.execute("SELECT referrer_id FROM users WHERE user_id = ?", (target_uid,))
        res = c.fetchone()
        ref_msg = ""
        if res and res[0]:
            bonus = amount * 0.15
            c.execute("UPDATE users SET balance_rub = balance_rub + ?, ref_earnings = ref_earnings + ? WHERE user_id = ?", (bonus, bonus, res[0]))
            try: await message.bot.send_message(res[0], f"💰 <b>Реферальный бонус!</b>\n+{bonus} RUB за пополнение друга.")
            except: pass
            ref_msg = f" (+{bonus} рефереру)"

        conn.commit()
        conn.close()
        await message.answer(f"✅ Баланс пополнен!{ref_msg}")
        await state.clear()
    except ValueError: await message.answer("Число введи.")

# --- СТАТУС ВОРКА ---
@router.callback_query(F.data == "adm_chg_status")
async def change_work_status(call: types.CallbackQuery):
    keyb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🟢 Full work", callback_data="set_work_full"),
         types.InlineKeyboardButton(text="🛑 Stop work", callback_data="set_work_stop")],
        [types.InlineKeyboardButton(text="🔙 Назад", callback_data="adm_extra")]
    ])
    current = get_setting('work_status')
    await safe_edit(call.message, f"Текущий статус: {current}\nВыберите новый:", reply_markup=keyb)

@router.callback_query(F.data.startswith("set_work_"))
async def set_work_s(call: types.CallbackQuery):
    new_status = "🟢 Активен" if call.data == "set_work_full" else "🛑 Стоп ворк"
    set_setting('work_status', new_status)
    await call.answer("Статус обновлен!", show_alert=True)
    await extra_menu(call)

# ==========================================
# 4. УПРАВЛЕНИЕ КАРТАМИ
# ==========================================

@router.callback_query(F.data == "adm_cards")
async def cards_menu(call: types.CallbackQuery):
    await safe_edit(call.message, "💳 <b>Управление картами</b>", reply_markup=kb.admin_cards_kb())

@router.callback_query(F.data == "adm_payout")
async def auto_payout(call: types.CallbackQuery):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT user_id, payout_amount, number, hold_time FROM numbers WHERE status = 'Успех'")
    rows = c.fetchall()
    if not rows: return await call.answer("Нет выплат", show_alert=True)
    
    payouts = {}
    report = []
    for r in rows:
        uid, amt, num, hold = r
        payouts[uid] = payouts.get(uid, 0) + amt
        report.append(f"{num} - {hold} - {amt}")

    for uid, total in payouts.items():
        if total > 0:
            c.execute("UPDATE cards SET balance = balance + ? WHERE user_id = ?", (total, uid))
            try: await call.bot.send_message(uid, f"💰 <b>Вам пришла выплата {total}$</b>", parse_mode="HTML")
            except: pass
            
    c.execute("DELETE FROM numbers") # Очистка всей базы
    conn.commit()
    conn.close()
    
    file = types.BufferedInputFile("\n".join(report).encode('utf-8'), filename="success.txt")
    await call.message.answer_document(file, caption="✅ Выплаты произведены. База очищена.")

@router.callback_query(F.data.in_({"adm_card_add", "adm_card_sub", "adm_card_block", "adm_card_unblock", "adm_card_view"}))
async def card_manual_action(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(card_action=call.data)
    await safe_edit(call.message, "👤 Введите Username:", reply_markup=kb.back_kb("adm_cards"))
    if call.data in ["adm_card_add", "adm_card_sub"]:
        await state.set_state(AdminState.card_balance_user)
    else:
        await state.set_state(AdminState.card_action_user)

@router.message(AdminState.card_action_user)
async def process_card_simple(message: types.Message, state: FSMContext):
    uid = get_id_by_username(message.text)
    if not uid: return await message.answer("Не найден.")
    data = await state.get_data()
    action = data['card_action']
    conn = get_connection()
    c = conn.cursor()
    if action == "adm_card_view":
        c.execute("SELECT card_number, cvv, balance FROM cards WHERE user_id = ?", (uid,))
        res = c.fetchone()
        await message.answer(f"💳 {res}" if res else "Нет карты.")
    elif action == "adm_card_block":
        c.execute("UPDATE cards SET is_blocked = 1 WHERE user_id = ?", (uid,))
        await message.answer("🚫 Заблокировано.")
    elif action == "adm_card_unblock":
        c.execute("UPDATE cards SET is_blocked = 0 WHERE user_id = ?", (uid,))
        await message.answer("✅ Разблокировано.")
    conn.commit()
    conn.close()
    await state.clear()

@router.message(AdminState.card_balance_user)
async def process_card_bal_user(message: types.Message, state: FSMContext):
    uid = get_id_by_username(message.text)
    if not uid: return await message.answer("Не найден.")
    await state.update_data(target_uid=uid)
    await message.answer("💰 Сумма:")
    await state.set_state(AdminState.card_balance_amount)

@router.message(AdminState.card_balance_amount)
async def process_card_bal_exec(message: types.Message, state: FSMContext):
    try:
        amt = float(message.text)
        data = await state.get_data()
        conn = get_connection()
        c = conn.cursor()
        op = "+" if data['card_action'] == "adm_card_add" else "-"
        c.execute(f"UPDATE cards SET balance = balance {op} ? WHERE user_id = ?", (amt, data['target_uid']))
        conn.commit()
        conn.close()
        await message.answer("✅ Баланс карты изменен.")
        await state.clear()
    except: await message.answer("Ошибка.")

# ==========================================
# 5. ОЧИСТКА И НАПОМИНАЛКА
# ==========================================

@router.callback_query(F.data == "adm_remind")
async def send_reminder(call: types.CallbackQuery):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT user_id, number FROM numbers WHERE status = 'Ожидает' ORDER BY id LIMIT 5")
    rows = c.fetchall()
    conn.close()
    for i, row in enumerate(rows, 1):
        try: await call.bot.send_message(row[0], f"📢 <b>СКОРО АКТИВАЦИЯ!</b>\n{row[1]} ({i} в очереди)", parse_mode="HTML")
        except: pass
    await call.answer("Напоминания отправлены")

@router.callback_query(F.data.in_({"adm_clear_stats", "adm_clear_queue"}))
async def ask_pwd_clean(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(clean_type=call.data)
    await call.message.answer("🔒 Пароль (098890):")
    await state.set_state(AdminState.pwd_clear_stats)

@router.message(AdminState.pwd_clear_stats)
async def exec_clean(message: types.Message, state: FSMContext):
    if message.text != "098890": return await message.answer("❌ Пароль неверный")
    data = await state.get_data()
    conn = get_connection()
    c = conn.cursor()
    if data['clean_type'] == "adm_clear_stats":
        c.execute("DELETE FROM numbers WHERE status IN ('Успех', 'Блок')")
    else:
        c.execute("DELETE FROM numbers WHERE status = 'Ожидает'")
    conn.commit()
    conn.close()
    await message.answer("🧹 Очищено.")
    await state.clear()

# ==========================================
# 6. НАСТРОЙКИ, АДМИНЫ, РАССЫЛКА
# ==========================================

@router.callback_query(F.data == "adm_settings")
async def settings_menu(call: types.CallbackQuery):
    kb_sets = []
    sets = {'check_sub': "🔄 Подписка", 'check_username': "👤 Юзернейм", 'check_card': "💳 Карта"}
    for k, v in sets.items():
        st = "✅" if get_setting_bool(k) else "❌"
        kb_sets.append([types.InlineKeyboardButton(text=f"{v} {st}", callback_data=f"toggle_{k}")])
    kb_sets.append([types.InlineKeyboardButton(text="📢 Рассылка", callback_data="adm_broadcast")])
    kb_sets.append([types.InlineKeyboardButton(text="🚫 Отключить раздел", callback_data="adm_disable_section")])
    kb_sets.append([types.InlineKeyboardButton(text="Админы (+/-)", callback_data="adm_add_admin")])
    kb_sets.append([types.InlineKeyboardButton(text="🔙 Назад", callback_data="adm_extra")])
    await safe_edit(call.message, "🤖 <b>Настройки</b>", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb_sets))

@router.callback_query(F.data.startswith("toggle_"))
async def toggle_setting(call: types.CallbackQuery):
    key = call.data.replace("toggle_", "")
    curr = get_setting_bool(key)
    set_setting(key, '0' if curr else '1')
    await settings_menu(call)

# --- РАССЫЛКА (ФИНАЛЬНАЯ) ---
@router.callback_query(F.data == "adm_broadcast")
async def broadcast_start(call: types.CallbackQuery, state: FSMContext):
    await safe_edit(call.message, "📢 <b>Рассылка</b>\nПришлите текст/фото/видео:", reply_markup=kb.back_kb("adm_settings"))
    await state.set_state(AdminState.broadcast_content)

@router.message(AdminState.broadcast_content)
async def broadcast_get_content(message: types.Message, state: FSMContext):
    content = {
        'msg_id': message.message_id, 'chat_id': message.chat.id,
        'has_media': bool(message.photo or message.video or message.document or message.animation),
        'html_text': message.html_text if message.text else (message.caption if message.caption else "")
    }
    if content['html_text'] is None: content['html_text'] = ""
    await state.update_data(bc_content=content, sys_selected=[])
    
    builder = InlineKeyboardBuilder()
    builder.button(text="URL Buttons", callback_data="bc_type_url")
    builder.button(text="System Buttons", callback_data="bc_type_sys")
    builder.button(text="Без кнопок", callback_data="bc_preview")
    builder.adjust(2)
    await message.answer("Кнопки?", reply_markup=builder.as_markup())

@router.callback_query(F.data == "bc_type_url")
async def bc_url_ask(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("Формат:\n(Текст) (Ссылка)")
    await state.set_state(AdminState.broadcast_url_input)

@router.message(AdminState.broadcast_url_input)
async def bc_url_save(message: types.Message, state: FSMContext):
    btns = []
    for line in message.text.split('\n'):
        parts = line.split(maxsplit=1)
        if len(parts)==2: 
            name = parts[0].replace("(", "").replace(")", "")
            url = parts[1].replace("(", "").replace(")", "")
            btns.append(types.InlineKeyboardButton(text=name, url=url))
    await state.update_data(bc_buttons=btns)
    await bc_show_preview(message, state)

@router.callback_query(F.data == "bc_type_sys")
async def bc_sys_select(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get('sys_selected', [])
    options = {'nav_cabinet': 'ЛК', 'nav_main': 'Меню', 'nav_numbers': 'Номера', 'cab_balance': 'Баланс', 'cab_ref': 'Реф', 'cab_card': 'Карта'}
    builder = InlineKeyboardBuilder()
    for c, n in options.items():
        m = "✅" if c in selected else "⬜️"
        builder.button(text=f"{m} {n}", callback_data=f"toggle_sys_{c}")
    builder.button(text="Готово", callback_data="bc_sys_done")
    builder.adjust(2)
    await safe_edit(call.message, "Выберите кнопки:", reply_markup=builder.as_markup())
    await state.set_state(AdminState.broadcast_sys_select) # Важно: остаемся в стейте

@router.callback_query(F.data.startswith("toggle_sys_"))
async def bc_sys_toggle(call: types.CallbackQuery, state: FSMContext):
    code = call.data.replace("toggle_sys_", "")
    data = await state.get_data()
    sel = data.get('sys_selected', [])
    if code in sel: sel.remove(code)
    else: sel.append(code)
    await state.update_data(sys_selected=sel)
    await bc_sys_select(call, state)

@router.callback_query(F.data == "bc_sys_done")
async def bc_sys_finish(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    sys_map = {'nav_cabinet': '👤 ЛК', 'nav_main': '📱 Меню', 'nav_numbers': '📱 Номера', 'cab_balance': '💰 Баланс', 'cab_ref': '👥 Реф', 'cab_card': '💳 Карта'}
    btns = [types.InlineKeyboardButton(text=sys_map[c], callback_data=c) for c in data.get('sys_selected', [])]
    await state.update_data(bc_buttons=btns)
    await bc_show_preview(call.message, state)

@router.callback_query(F.data == "bc_preview")
async def bc_preview_h(call: types.CallbackQuery, state: FSMContext):
    await bc_show_preview(call.message, state)

async def bc_show_preview(message, state):
    data = await state.get_data()
    content = data.get('bc_content')
    btns = data.get('bc_buttons', [])
    builder = InlineKeyboardBuilder()
    for b in btns: builder.add(b)
    builder.adjust(2)
    
    await message.answer("<b>Превью:</b>", parse_mode="HTML")
    try:
        if content['has_media']:
            await message.bot.copy_message(message.chat.id, content['chat_id'], content['msg_id'], caption=content['html_text'], parse_mode="HTML", reply_markup=builder.as_markup())
        else:
            await message.answer(content['html_text'], parse_mode="HTML", reply_markup=builder.as_markup())
    except: pass
    
    kb_conf = InlineKeyboardBuilder()
    kb_conf.button(text="🚀 Разослать", callback_data="bc_go")
    kb_conf.button(text="❌ Отмена", callback_data="adm_settings")
    await message.answer("Отправляем?", reply_markup=kb_conf.as_markup())

@router.callback_query(F.data == "bc_go")
async def bc_send(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    content = data.get('bc_content')
    btns = data.get('bc_buttons', [])
    builder = InlineKeyboardBuilder()
    for b in btns: builder.add(b)
    builder.adjust(2)
    markup = builder.as_markup()
    
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT user_id, username FROM users")
    users = c.fetchall()
    conn.close()
    
    await call.message.edit_text("🚀 Рассылка...")
    cnt = 0
    for u in users:
        try:
            # Форматируем теги
            txt = content['html_text'].format(username=f"@{u[1]}" if u[1] else "User", first_name="User")
            if content['has_media']:
                await call.bot.copy_message(u[0], content['chat_id'], content['msg_id'], caption=txt, parse_mode="HTML", reply_markup=markup)
            else:
                await call.bot.send_message(u[0], txt, parse_mode="HTML", reply_markup=markup)
            cnt += 1
            await asyncio.sleep(0.05)
        except: pass
    await call.message.answer(f"✅ Готово! Доставлено: {cnt}")
    await state.clear()

# --- ОТКЛЮЧЕНИЕ РАЗДЕЛОВ ---
@router.callback_query(F.data == "adm_disable_section")
async def disable_menu(call: types.CallbackQuery):
    sections = {
        'nav_cabinet': 'Личный кабинет',
        'nav_main': 'Главное меню',
        'nav_numbers': 'Управление номерами',
        'num_add': 'Добавить номер',
        'num_my': 'Мои номера',
        'cat_max': '🟧 MAX',
        'cat_wa': '🟩 WhatsApp',
        'filter_work': '⚙️ В работе',
        'filter_wait': '⏳ Ожидает',
        'filter_success': 'Успех',
        'filter_block': 'Блок',
        'nav_stats': 'Статистика',
        'cab_sub': 'Купить подписку',
        'buy_alpha': '💎 Alpha',
        'buy_nucleus': '🔮 Nucleus',
        'buy_zero': '🔥 Zero Limits',
        'cab_ref': 'Рефералка',
        'cab_card': 'Моя карта'
    }
    
    builder = InlineKeyboardBuilder()
    for k, n in sections.items():
        mark = "🔴" if is_section_disabled(k) else "🟢"
        builder.button(text=f"{mark} {n}", callback_data=f"sec_tog_{k}")
    builder.button(text="🔙 Назад", callback_data="adm_settings")
    builder.adjust(2)
    await safe_edit(call.message, "🚫 <b>Разделы:</b>", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("sec_tog_"))
async def disable_toggle(call: types.CallbackQuery):
    key = call.data.replace("sec_tog_", "")
    curr = is_section_disabled(key)
    set_setting(f"dis_{key}", '0' if curr else '1')
    await disable_menu(call)

# --- ДОБАВИТЬ/УДАЛИТЬ АДМИНА ---
@router.callback_query(F.data.in_({"adm_add_admin", "adm_del_admin"}))
async def adm_manage(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(act=call.data)
    await safe_edit(call.message, "Введите Username:")
    await state.set_state(AdminState.add_admin_user)

@router.message(AdminState.add_admin_user)
async def adm_manage_exec(message: types.Message, state: FSMContext):
    uid = get_id_by_username(message.text)
    if not uid: return await message.answer("Не найден.")
    data = await state.get_data()
    conn = get_connection()
    c = conn.cursor()
    if data['act'] == "adm_add_admin":
        c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (uid,))
        await message.answer("✅ Добавлен.")
    else:
        c.execute("DELETE FROM admins WHERE user_id = ?", (uid,))
        await message.answer("✅ Удален.")
    conn.commit()
    conn.close()
    await state.clear()