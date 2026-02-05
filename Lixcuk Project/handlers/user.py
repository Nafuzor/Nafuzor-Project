import asyncio
from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest

import database as db
import keyboards as kb
import states
import config

router = Router()

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

async def safe_edit(call, text, reply_markup=None):
    if isinstance(call, types.Message):
        await call.answer(text, reply_markup=reply_markup, parse_mode="HTML")
        return

    try: 
        await call.message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
    except TelegramBadRequest as e: 
        if "message is not modified" in str(e):
            return
        try:
            await call.message.delete()
            await call.message.answer(text, reply_markup=reply_markup, parse_mode="HTML")
        except: pass
    except Exception: 
        await call.message.answer(text, reply_markup=reply_markup, parse_mode="HTML")

async def safe_answer(call, text, show_alert=False):
    if not hasattr(call, 'answer') or getattr(call, 'id', '0') == '0':
        if show_alert and isinstance(call, types.CallbackQuery) and call.message:
             msg = await call.message.answer(f"⚠️ {text}")
             await asyncio.sleep(2)
             try: await msg.delete()
             except: pass
        return
    try:
        await call.answer(text, show_alert=show_alert)
    except: pass

async def is_disabled(section):
    disabled = await db.get_lixcuk_setting('disabled_sections')
    return section in disabled

async def delete_prev_bot_msg(state: FSMContext, bot: Bot, chat_id: int):
    """Удаляет предыдущее сообщение бота, ID которого сохранен в state"""
    data = await state.get_data()
    last_id = data.get('last_bot_msg_id')
    if last_id:
        try: await bot.delete_message(chat_id, last_id)
        except: pass

# --- START & MENU ---

@router.message(CommandStart())
async def cmd_start(message: types.Message, command: CommandObject, state: FSMContext):
    await state.clear()
    await db.add_lixcuk_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    
    args = command.args
    
    if args and args in ["withdraw", "my_withdraws", "card", "main"]:
        fake_call = types.CallbackQuery(
            id='0',
            from_user=message.from_user,
            chat_instance='0',
            message=message,
            data=f"manual_{args}"
        )
        
        if args == "withdraw": await cb_withdraw(fake_call, state)
        elif args == "my_withdraws": await cb_my_withdraws(fake_call, state)
        elif args == "card": await cb_my_card(fake_call, state)
        elif args == "main": await cb_main(fake_call, state)
        return

    session = await db.get_lixcuk_session(message.from_user.id)
    is_connected = bool(session)
    
    text = f"{message.from_user.full_name}, добро пожаловать в Lixcuk!\n\n<blockquote>— Тут ты можешь обменять деньги с карты Nafuzor Wallet</blockquote>\n\n"
    text += f"Твой баланс карты: {session['card_balance']} $" if is_connected else "Твой баланс карты: (Карта не подключена)"
    
    await message.answer(text, reply_markup=kb.main_menu_kb(is_connected), parse_mode="HTML")

@router.message(Command("su"))
async def cmd_su(message: types.Message):
    bot_name = (await message.bot.get_me()).username
    txt = (
        f"🔗 <b>Быстрые ссылки Lixcuk:</b>\n\n"
        f"🏠 Главная: https://t.me/{bot_name}?start=main\n"
        f"💸 Вывод: https://t.me/{bot_name}?start=withdraw\n"
        f"📂 Мои выводы: https://t.me/{bot_name}?start=my_withdraws\n"
        f"💳 Моя карта: https://t.me/{bot_name}?start=card"
    )
    await message.answer(txt, parse_mode="HTML", disable_web_page_preview=True)

@router.callback_query(F.data == "menu_main")
async def cb_main(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    session = await db.get_lixcuk_session(call.from_user.id)
    is_connected = bool(session)
    text = f"{call.from_user.full_name}, добро пожаловать в Lixcuk!\n\n<blockquote>— Тут ты можешь обменять деньги с карты Nafuzor Wallet</blockquote>\n\n"
    text += f"Твой баланс карты: {session['card_balance']} $" if is_connected else "Твой баланс карты: (Карта не подключена)"
    await safe_edit(call, text, kb.main_menu_kb(is_connected))

# --- КАРТА (С УДАЛЕНИЕМ СООБЩЕНИЙ) ---

@router.callback_query(F.data == "connect_card_start")
async def cb_connect_start(call: types.CallbackQuery, state: FSMContext):
    if await is_disabled("card"): return await safe_answer(call, "Раздел отключен", show_alert=True)
    link = config.NAFUZOR_BOT_LINK
    
    text = f"<blockquote>Введите ваш номер карты из <a href='{link}'>Nafuzor Project</a></blockquote>"
    
    # Редактируем сообщение (меню превращается в вопрос)
    await safe_edit(call, text) 
    
    # Сохраняем ID сообщения бота, чтобы удалить его на следующем шаге
    if isinstance(call, types.CallbackQuery):
        await state.update_data(last_bot_msg_id=call.message.message_id)
    
    await state.set_state(states.ConnectCard.number)

@router.message(states.ConnectCard.number)
async def proc_card_num(message: types.Message, state: FSMContext):
    # 1. Удаляем сообщение пользователя (номер)
    try: await message.delete()
    except: pass

    # 2. Удаляем предыдущее сообщение бота ("Введите номер")
    await delete_prev_bot_msg(state, message.bot, message.chat.id)

    await state.update_data(number=message.text.strip())
    link = config.NAFUZOR_BOT_LINK
    
    # 3. Отправляем новое и сохраняем его ID
    msg = await message.answer(f"<blockquote>Введите ваш CVV код из <a href='{link}'>Nafuzor Project</a></blockquote>", parse_mode="HTML")
    await state.update_data(last_bot_msg_id=msg.message_id)
    
    await state.set_state(states.ConnectCard.cvv)

@router.message(states.ConnectCard.cvv)
async def proc_card_cvv(message: types.Message, state: FSMContext):
    try: await message.delete()
    except: pass
    
    await delete_prev_bot_msg(state, message.bot, message.chat.id)

    await state.update_data(cvv=message.text.strip())
    link = config.NAFUZOR_BOT_LINK
    
    msg = await message.answer(f"<blockquote>Введите ваш API токен из <a href='{link}'>Nafuzor Project</a></blockquote>", parse_mode="HTML")
    await state.update_data(last_bot_msg_id=msg.message_id)
    
    await state.set_state(states.ConnectCard.token)

@router.message(states.ConnectCard.token)
async def proc_card_token(message: types.Message, state: FSMContext):
    try: await message.delete()
    except: pass
    
    await delete_prev_bot_msg(state, message.bot, message.chat.id)

    data = await state.get_data()
    token = message.text.strip()
    success = await db.connect_lixcuk_card(message.from_user.id, data['number'], data['cvv'], token)
    
    if success:
        session = await db.get_lixcuk_session(message.from_user.id)
        text = f"💳 Моя карта:\n\n<blockquote>Номер карты: <code>{session['card_number']}</code>\nCVV код: <code>{session['card_cvv']}</code></blockquote>\n\n💰 Баланс: {session['card_balance']}$"
        mk = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отключить карту", callback_data="disconnect_card")], [InlineKeyboardButton(text="🔙 В меню", callback_data="menu_main")]])
        await message.answer(text, reply_markup=mk, parse_mode="HTML")
    else:
        await message.answer("❌ Ошибка подключения. Проверьте данные.", reply_markup=kb.main_menu_kb(False))
    await state.clear()

@router.callback_query(F.data == "menu_card")
async def cb_my_card(call: types.CallbackQuery, state: FSMContext): 
    if await is_disabled("card"): return await safe_answer(call, "Раздел отключен", show_alert=True)
    session = await db.get_lixcuk_session(call.from_user.id)
    
    if not session: 
        await safe_answer(call, "Переход к подключению...", show_alert=False)
        return await cb_connect_start(call, state)
        
    text = f"💳 Моя карта:\n\n<blockquote>Номер карты: <code>{session['card_number']}</code>\nCVV код: <code>{session['card_cvv']}</code></blockquote>\n\n💰 Баланс: {session['card_balance']}$"
    await safe_edit(call, text, kb.my_card_kb())

@router.callback_query(F.data == "disconnect_card")
async def cb_disconnect(call: types.CallbackQuery, state: FSMContext):
    await db.disconnect_lixcuk_card(call.from_user.id)
    await safe_answer(call, "Карта отключена")
    await cb_main(call, state)

# --- ВЫВОД СРЕДСТВ ---

@router.callback_query(F.data == "menu_withdraw")
async def cb_withdraw(call: types.CallbackQuery, state: FSMContext):
    if await is_disabled("withdraw"): return await safe_answer(call, "Раздел отключен", show_alert=True)
    session = await db.get_lixcuk_session(call.from_user.id)
    
    # ЕСЛИ КАРТА НЕ ПОДКЛЮЧЕНА: Показываем сообщение с кнопкой
    if not session:
        await safe_edit(
            call, 
            "❌ <b>Ошибка!</b>\n\nДля вывода средств необходимо подключить карту.", 
            reply_markup=kb.withdraw_no_card_kb() # ТЕПЕРЬ ОНА СУЩЕСТВУЕТ
        )
        return
    
    # Добавил кнопку "Назад" в клавиатуру (функция back_to_menu_kb из keyboards)
    await safe_edit(call, "<blockquote>Укажите сумму вывода 👇</blockquote>", reply_markup=kb.back_to_menu_kb())
    await state.set_state(states.Withdraw.amount)

@router.message(states.Withdraw.amount)
async def proc_withdraw_amt(message: types.Message, state: FSMContext):
    # Удаляем сообщение с суммой
    try: await message.delete()
    except: pass

    try: amount = float(message.text)
    except: 
        msg = await message.answer("⚠️ Введите число")
        await asyncio.sleep(2)
        try: await msg.delete()
        except: pass
        return
    
    if amount <= 0: 
        msg = await message.answer("⚠️ Сумма должна быть > 0")
        await asyncio.sleep(2)
        try: await msg.delete()
        except: pass
        return
    
    target_user = message.from_user.username or message.from_user.full_name
    await state.update_data(amount=amount, target_user=target_user)
    
    await show_confirmation(message, state)

async def show_confirmation(message, state):
    data = await state.get_data()
    text = f"💸 <b>Ваш вывод:</b>\n\n<blockquote>👤 Юзернейм: {data['target_user']}\n💰 Сумма: {data['amount']} $</blockquote>"
    
    if isinstance(message, types.CallbackQuery):
        await safe_edit(message, text, kb.withdraw_confirm_kb())
    else:
        # Если это первый шаг после ввода суммы, отправляем новое сообщение (так как старое "Укажите сумму" было отредактировано или удалено)
        # В данном случае, так как мы удалили сообщение юзера, лучше отправить новое меню.
        await message.answer(text, reply_markup=kb.withdraw_confirm_kb(), parse_mode="HTML")
    
    await state.set_state(states.Withdraw.confirm)

# -- Редактирование --
@router.callback_query(F.data == "wd_edit_user", states.Withdraw.confirm)
async def wd_edit_user(call: types.CallbackQuery, state: FSMContext):
    await safe_edit(call, "Введите новый юзернейм:", kb.withdraw_cancel_kb())
    await state.set_state(states.Withdraw.edit_username)

@router.message(states.Withdraw.edit_username)
async def wd_proc_edit_user(message: types.Message, state: FSMContext):
    try: await message.delete()
    except: pass
    await state.update_data(target_user=message.text)
    await show_confirmation(message, state)

@router.callback_query(F.data == "wd_edit_amount", states.Withdraw.confirm)
async def wd_edit_amount(call: types.CallbackQuery, state: FSMContext):
    await safe_edit(call, "Введите новую сумму:", kb.withdraw_cancel_kb())
    await state.set_state(states.Withdraw.edit_amount)

@router.message(states.Withdraw.edit_amount)
async def wd_proc_edit_amount(message: types.Message, state: FSMContext):
    try: await message.delete()
    except: pass
    try: amount = float(message.text)
    except: return 
    await state.update_data(amount=amount)
    await show_confirmation(message, state)

@router.callback_query(F.data == "wd_back_to_confirm")
async def wd_back(call: types.CallbackQuery, state: FSMContext):
    await show_confirmation(call, state)

# -- Подтверждение --
@router.callback_query(F.data == "wd_confirm", states.Withdraw.confirm)
async def wd_confirm_final(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    amount = data['amount']
    target_user = data['target_user']
    
    session = await db.get_lixcuk_session(call.from_user.id)
    if not session: return await safe_answer(call, "Карта слетела!", show_alert=True)
    
    if session['card_balance'] < amount:
        await safe_answer(call, "❌ Недостаточно средств на карте!", show_alert=True)
        return
    
    await db.create_withdrawal(call.from_user.id, session['user_id'], amount, target_user)
    
    await safe_answer(call, "✅ Заявка успешно создана!", show_alert=False)
    
    notify = await db.get_lixcuk_setting('notify_withdraw')
    if notify == '1':
        admins = await db.get_lixcuk_admins()
        msg_adm = f"🆕 <b>Новая заявка на вывод!</b>\n👤 От: {call.from_user.full_name}\n💸 Сумма: {amount}\n📥 Куда: {target_user}"
        for adm in admins:
            try: await call.bot.send_message(adm['user_id'], msg_adm, parse_mode="HTML")
            except: pass
            
    await state.clear()
    await cb_main(call, state)

# --- СПИСКИ ВЫВОДОВ ---
@router.callback_query(F.data == "menu_my_withdraws")
async def cb_my_withdraws(call: types.CallbackQuery, state: FSMContext): 
    if await is_disabled("my_withdraws"): return await safe_answer(call, "Раздел отключен", show_alert=True)
    await safe_edit(call, "<blockquote>Выберите категорию 👇</blockquote>", kb.my_withdraws_cat_kb())

@router.callback_query(F.data.startswith("with_list_"))
async def cb_with_list(call: types.CallbackQuery):
    status = call.data.split("_")[2]
    rows = await db.get_user_withdrawals(call.from_user.id, status)
    rus_status = {"waiting": "Ожидающие", "success": "Успешные", "closed": "Закрытые"}
    text = f"<blockquote>Количество заявок ({rus_status[status]}): {len(rows)}</blockquote>"
    buttons = []
    for r in rows:
        btn_text = f"Заявка #{r[0]} - {r[1]}$"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"with_info_{r[0]}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="menu_my_withdraws")])
    await safe_edit(call, text, InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("with_info_"))
async def cb_with_info(call: types.CallbackQuery):
    wid = int(call.data.split("_")[2])
    res = await db.get_withdraw_details(wid)
    if not res: return await safe_answer(call, "Не найдено")
    rus_stat = {"waiting": "Ожидает", "success": "Успешно", "closed": "Закрыта"}
    text = f"Информация о заявке #{res[0]}\n\n<blockquote>Сумма вывода: {res[1]}\nЮзернейм получателя: @{res[2]}\nДата: {res[3]}\nСтатус: {rus_stat.get(res[4], res[4])}</blockquote>"
    mk = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data=f"with_list_{res[4]}") ]])
    await safe_edit(call, text, mk)