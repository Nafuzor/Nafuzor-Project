from aiogram import Router, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from database import add_user, get_user, get_connection, get_setting, is_admin, is_section_disabled
from states import NumberState
import keyboards as kb
import json
from config import SUBSCRIPTIONS

router = Router()

def get_site_data(user_id):
    conn = get_connection()
    c = conn.cursor()
    user = get_user(user_id) 
    c.execute("SELECT card_number, balance, cvv, created_at, is_active FROM cards WHERE user_id = ?", (user_id,))
    card = c.fetchone()
    c.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (user_id,))
    ref_count = c.fetchone()[0]
    c.execute("SELECT number, category, status FROM numbers WHERE user_id = ? ORDER BY id DESC LIMIT 30", (user_id,))
    nums_raw = c.fetchall()
    nums_list = [{"n": r[0], "c": r[1], "s": r[2]} for r in nums_raw]
    work_status = get_setting('work_status')
    latest_news = get_setting('latest_news')
    conn.close()
    return {'uid': user_id, 'bal': user[2], 'sub': user[3], 'ref': ref_count, 'cn': card[0] if card and card[4] else '****', 'cb': card[1] if card and card[4] else 0, 'cc': card[2] if card and card[4] else '***', 'cd': card[3].split()[0] if card and card[4] else '-', 'ct': f"nfz_{user_id}", 'ws': work_status, 'nums': nums_list, 'news': latest_news}

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext = None):
    args = message.text.split()
    payload = args[1] if len(args) > 1 else None
    
    # Регистрация
    ref_id = int(payload) if payload and payload.isdigit() else None
    add_user(message.from_user.id, message.from_user.username, ref_id)
    
    if state: await state.clear()
    
    # --- DEEP LINKING ---
    if payload and not payload.isdigit():
        if payload == 'cabinet':
            if is_section_disabled('nav_cabinet'): return await message.answer("🚫 Раздел отключен")
            # Перенаправляем на хендлер кабинета (эмуляция)
            # Чтобы не дублировать код, просто вызываем логику показа кабинета через start (но лучше через call)
            # Здесь упростим: отправим текст, как будто нажали кнопку
            from handlers.cabinet import show_cabinet_msg
            await show_cabinet_msg(message)
            return
            
        elif payload == 'numbers':
            if is_section_disabled('nav_numbers'): return await message.answer("🚫 Раздел отключен")
            await message.answer("📂 <b>Управление номерами</b>", reply_markup=kb.numbers_main_kb(), parse_mode="HTML")
            return
            
        elif payload == 'add_num':
            if is_section_disabled('num_add'): return await message.answer("🚫 Раздел отключен")
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT is_active FROM cards WHERE user_id = ?", (message.from_user.id,))
            res = c.fetchone()
            conn.close()
            if not res or not res[0]: return await message.answer("⚠️ Сначала активируйте карту!")
            await message.answer("<blockquote>Выберите категорию</blockquote>", reply_markup=kb.number_category_kb(), parse_mode="HTML")
            return
            
        elif payload == 'my_nums':
            if is_section_disabled('num_my'): return await message.answer("🚫 Раздел отключен")
            await message.answer("<blockquote>Выберите категорию</blockquote>", reply_markup=kb.my_numbers_filter_kb(), parse_mode="HTML")
            return

        elif payload == 'card':
            if is_section_disabled('cab_card'): return await message.answer("🚫 Раздел отключен")
            from handlers.card import show_card_msg
            await show_card_msg(message)
            return

        elif payload == 'ref':
            if is_section_disabled('cab_ref'): return await message.answer("🚫 Раздел отключен")
            from handlers.cabinet import show_ref_msg
            await show_ref_msg(message)
            return

        elif payload == 'buy_sub':
            if is_section_disabled('cab_sub'): return await message.answer("🚫 Раздел отключен")
            from handlers.cabinet import show_sub_msg
            await show_sub_msg(message)
            return

    # Обычный старт
    site_data = get_site_data(message.from_user.id)
    work_status = get_setting('work_status')
    queue_count = get_setting('queue_count')
    
    text = (
        f"<blockquote>👋 {message.from_user.first_name}, добро пожаловать!</blockquote>\n\n"
        f"➖ <b>Статус ворка:</b> {work_status}\n"
        f"➖ <b>Общая очередь:</b> {queue_count}"
    )
    
    await message.answer(text, reply_markup=kb.main_menu_kb(site_data), parse_mode="HTML")

@router.callback_query(F.data == "nav_main")
async def nav_main(call: types.CallbackQuery, state: FSMContext):
    # Тут исправлено имя: используем call.from_user.first_name
    site_data = get_site_data(call.from_user.id)
    work_status = get_setting('work_status')
    queue_count = get_setting('queue_count')
    
    text = (
        f"<blockquote>👋 {call.from_user.first_name}, добро пожаловать!</blockquote>\n\n"
        f"➖ <b>Статус ворка:</b> {work_status}\n"
        f"➖ <b>Общая очередь:</b> {queue_count}"
    )
    await call.message.edit_text(text, reply_markup=kb.main_menu_kb(site_data), parse_mode="HTML")

@router.message(F.web_app_data)
async def web_app_handler(message: types.Message, state: FSMContext):
    try:
        data = json.loads(message.web_app_data.data)
        action = data.get('action')
        
        if action == 'add_number':
            if is_section_disabled('num_add'): return await message.answer("🚫 Прием номеров отключен.")
            number = data.get('number')
            category = data.get('category')
            conn = get_connection()
            c = conn.cursor()
            c.execute("INSERT INTO numbers (user_id, number, category, created_at) VALUES (?, ?, ?, datetime('now'))", (message.from_user.id, number, category))
            conn.commit()
            conn.close()
            await message.answer(f"✅ <b>Заявка принята!</b>\n📱 {number} ({category})", parse_mode="HTML")
            await cmd_start(message, state)

        elif action == 'admin_publish_news':
            if not is_admin(message.from_user.id): return
            text = data.get('text')
            conn = get_connection()
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('latest_news', ?)", (text,))
            conn.commit()
            conn.close()
            await message.answer(f"📢 <b>Новость сохранена!</b>\n{text}", parse_mode="HTML")
            await cmd_start(message, state)

    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {e}")