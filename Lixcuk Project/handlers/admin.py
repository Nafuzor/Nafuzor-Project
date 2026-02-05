import io
import asyncio
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile

import database as db
import keyboards as kb
import states
import utils # Нужно для парсинга кнопок (utils от Nafuzor можно скопировать или продублировать функции)
import config

# Дублируем функцию парсинга кнопок, чтобы не зависеть от Nafuzor utils
def parse_url_buttons(text):
    rows = []
    for line in text.split('\n'):
        if not line.strip(): continue
        parts = line.split(' ')
        if len(parts) < 2: continue
        name = parts[0].strip()
        link = parts[1].strip()
        rows.append([InlineKeyboardButton(text=name, url=link)])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def create_system_kb(selected_types):
    mapping = {
        "menu_main": ("🏠 Главное меню", "menu_main"),
        "menu_withdraw": ("💸 Вывод", "menu_withdraw"),
        "menu_card": ("💳 Карта", "menu_card")
    }
    rows, row = [], []
    for stype in selected_types:
        if stype in mapping:
            name, cb = mapping[stype]
            row.append(InlineKeyboardButton(text=name, callback_data=cb))
            if len(row) == 2:
                rows.append(row); row = []
    if row: rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)

router = Router()

@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if await db.is_lixcuk_admin(message.from_user.id):
        await message.answer("⚙️ Админ панель Lixcuk:", reply_markup=kb.admin_menu_kb())

@router.callback_query(F.data == "admin_menu")
async def cb_adm_menu(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("⚙️ Админ панель Lixcuk:", reply_markup=kb.admin_menu_kb())

# --- SETTINGS MENU ---
@router.callback_query(F.data == "adm_settings_menu")
async def cb_adm_sets(call: types.CallbackQuery):
    notif = await db.get_lixcuk_setting('notify_withdraw')
    dis = await db.get_lixcuk_setting('disabled_sections')
    await call.message.edit_text("🔧 Настройки бота:", reply_markup=kb.admin_settings_kb(notif, dis))

@router.callback_query(F.data == "adm_tog_notify")
async def cb_tog_notify(call: types.CallbackQuery):
    curr = await db.get_lixcuk_setting('notify_withdraw')
    new = '0' if curr == '1' else '1'
    await db.set_lixcuk_setting('notify_withdraw', new)
    await cb_adm_sets(call)

@router.callback_query(F.data == "adm_disable_sec")
async def cb_adm_dis_sec(call: types.CallbackQuery):
    curr = await db.get_lixcuk_setting('disabled_sections')
    await call.message.edit_text("🚫 Отключение разделов:", reply_markup=kb.admin_disable_sections_kb(curr))

@router.callback_query(F.data.startswith("adm_tog_sec_"))
async def cb_tog_sec(call: types.CallbackQuery):
    sec = call.data.replace("adm_tog_sec_", "")
    curr = await db.get_lixcuk_setting('disabled_sections')
    if sec in curr: new = curr.replace(sec, "")
    else: new = curr + sec + ","
    await db.set_lixcuk_setting('disabled_sections', new)
    await cb_adm_dis_sec(call)

# --- ADMIN MANAGEMENT ---
@router.callback_query(F.data == "adm_add_admin")
async def cb_add_adm(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("Введите Username нового админа:")
    await state.set_state(states.AdminLixcuk.add_admin)

@router.message(states.AdminLixcuk.add_admin)
async def proc_add_adm(message: types.Message, state: FSMContext):
    if not message.text: return
    # Find user ID (requires user to be in DB) - Simplified: assume we need ID or just trust username?
    # Better: Try to find in lixcuk_users by username
    user = await db.get_user_by_username(message.text) # From nafuzor users table actually
    if user:
        await db.add_lixcuk_admin(user['user_id'], message.text)
        await message.answer("✅ Админ добавлен.")
    else:
        await message.answer("❌ Пользователь не найден в базе.")
    await state.clear()
    await message.answer("Админ панель:", reply_markup=kb.admin_menu_kb())

@router.callback_query(F.data == "adm_rem_admin")
async def cb_rem_adm(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("Введите Username для удаления:")
    await state.set_state(states.AdminLixcuk.remove_admin)

@router.message(states.AdminLixcuk.remove_admin)
async def proc_rem_adm(message: types.Message, state: FSMContext):
    await db.remove_lixcuk_admin(message.text)
    await message.answer("✅ Админ удален (если был).")
    await state.clear()

# --- BROADCAST ---
@router.callback_query(F.data == "adm_broadcast")
async def cb_bc_start(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("📢 Отправьте сообщение (Текст/Фото/Файл).\nПоддерживаются: {username}, {first_name}")
    await state.set_state(states.AdminLixcuk.broadcast_msg)

@router.message(states.AdminLixcuk.broadcast_msg)
async def proc_bc_msg(message: types.Message, state: FSMContext):
    # Сохраняем контент. Для форматирования нужно брать html_text или caption
    text = message.html_text or message.caption or ""
    # Если есть entities, aiogram их сам обработает при copy_message, но мы хотим replace.
    # Поэтому берем исходный текст/html.
    
    file_id = None
    if message.photo: file_id = message.photo[-1].file_id
    elif message.document: file_id = message.document.file_id
    elif message.animation: file_id = message.animation.file_id
    
    content_type = "text"
    if message.photo: content_type = "photo"
    elif message.document: content_type = "document"
    elif message.animation: content_type = "animation"
    
    await state.update_data(text=text, file_id=file_id, ctype=content_type)
    await message.answer("Выберите тип кнопок:", reply_markup=kb.broadcast_type_kb())

@router.callback_query(F.data == "bc_type_url")
async def cb_bc_url(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("Отправьте кнопки:\n(Название) (Ссылка)")
    await state.set_state(states.AdminLixcuk.broadcast_buttons)

@router.message(states.AdminLixcuk.broadcast_buttons)
async def proc_bc_btns(message: types.Message, state: FSMContext):
    try:
        markup = parse_url_buttons(message.text)
        await state.update_data(markup=markup.model_dump_json())
        await preview_bc(message, state)
    except: await message.answer("Ошибка формата")

@router.callback_query(F.data == "bc_type_sys")
async def cb_bc_sys(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(sel_sys=[])
    await call.message.edit_text("Выберите кнопки:", reply_markup=kb.broadcast_sys_kb([]))

@router.callback_query(F.data.startswith("bc_sys_tog_"))
async def cb_bc_sys_tog(call: types.CallbackQuery, state: FSMContext):
    key = call.data.replace("bc_sys_tog_", "")
    data = await state.get_data()
    sel = list(data.get('sel_sys', []))
    if key in sel: sel.remove(key)
    else: sel.append(key)
    await state.update_data(sel_sys=sel)
    await call.message.edit_reply_markup(reply_markup=kb.broadcast_sys_kb(sel))

@router.callback_query(F.data == "bc_sys_done")
async def cb_bc_sys_done(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    markup = create_system_kb(data.get('sel_sys', []))
    await state.update_data(markup=markup.model_dump_json())
    await preview_bc(call.message, state)

@router.callback_query(F.data == "bc_send_now")
async def cb_bc_now(call: types.CallbackQuery, state: FSMContext):
    await preview_bc(call.message, state)

async def preview_bc(message, state):
    data = await state.get_data()
    mk = InlineKeyboardMarkup.model_validate_json(data['markup']) if 'markup' in data else None
    txt = data.get('text', '').format(username="User", first_name="Name")
    
    await message.answer("📢 Предпросмотр:")
    if data['ctype'] == 'text': await message.answer(txt, reply_markup=mk, parse_mode="HTML")
    elif data['ctype'] == 'photo': await message.answer_photo(data['file_id'], caption=txt, reply_markup=mk, parse_mode="HTML")
    elif data['ctype'] == 'document': await message.answer_document(data['file_id'], caption=txt, reply_markup=mk, parse_mode="HTML")
    
    await message.answer("Отправить?", reply_markup=kb.broadcast_confirm_kb())

@router.callback_query(F.data == "bc_final_send")
async def cb_bc_send(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    users = await db.get_all_lixcuk_users()
    mk = InlineKeyboardMarkup.model_validate_json(data['markup']) if 'markup' in data else None
    
    count = 0
    await call.message.answer("🚀 Рассылка...")
    
    for u in users:
        try:
            txt = data.get('text', '').format(username=u['username'] or "", first_name=u['full_name'])
            if data['ctype'] == 'text': await call.bot.send_message(u['user_id'], txt, reply_markup=mk, parse_mode="HTML")
            elif data['ctype'] == 'photo': await call.bot.send_photo(u['user_id'], data['file_id'], caption=txt, reply_markup=mk, parse_mode="HTML")
            elif data['ctype'] == 'document': await call.bot.send_document(u['user_id'], data['file_id'], caption=txt, reply_markup=mk, parse_mode="HTML")
            count += 1
            await asyncio.sleep(0.05)
        except: pass
        
    await call.message.answer(f"✅ Рассылка завершена. Доставлено: {count}")
    await state.clear()

# --- WITHDRAWAL LIST (Admin) ---
@router.callback_query(F.data.startswith("adm_with_"))
async def cb_adm_list(call: types.CallbackQuery):
    status = call.data.split("_")[2]
    rows = await db.get_withdrawals(status, 50)
    text = f"<blockquote>Общее количество заявок ({status}): {len(rows)}</blockquote>"
    buttons = []
    for r in rows:
        btn_text = f"@{r[2]} | {r[1]}$"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"adm_winfo_{r[0]}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")])
    if call.message: await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")

@router.callback_query(F.data.startswith("adm_winfo_"))
async def cb_adm_info(call: types.CallbackQuery):
    wid = int(call.data.split("_")[2])
    res = await db.get_withdraw_details(wid)
    if not res: return await call.answer("Не найдено")
    text = f"Заявка #{res[0]}\n\nЮзернейм: @{res[2]}\nСумма: {res[1]}\nДата создания: {res[3]}"
    buttons = []
    if res[4] == 'waiting':
        buttons.append([InlineKeyboardButton(text="✅ Успешно", callback_data=f"adm_act_success_{wid}")])
        buttons.append([InlineKeyboardButton(text="🔒 Закрыть", callback_data=f"adm_act_closed_{wid}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"adm_with_{res[4]}")])
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("adm_act_"))
async def cb_adm_action(call: types.CallbackQuery):
    action, wid = call.data.split("_")[2], int(call.data.split("_")[3])
    admin_name = call.from_user.username or call.from_user.full_name
    lixcuk_id = await db.update_withdrawal_status(wid, action, admin_name)
    msg = "✅ Ваша заявка одобрена!" if action == "success" else "🔒 Заявка закрыта."
    try: await call.bot.send_message(lixcuk_id, msg)
    except: pass
    await call.answer("Статус обновлен")
    fake = types.CallbackQuery(id='0', from_user=call.from_user, message=call.message, data="adm_with_waiting", chat_instance=call.chat_instance)
    await cb_adm_list(fake)