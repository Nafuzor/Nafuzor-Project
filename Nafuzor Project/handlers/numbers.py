from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from database import get_connection, is_section_disabled
from states import NumberState
import keyboards as kb
import re

router = Router()

@router.callback_query(F.data == "nav_numbers")
async def show_numbers_menu(call: types.CallbackQuery):
    if is_section_disabled("nav_numbers"): return await call.answer("🔴 Раздел отключен", show_alert=True)
    await call.message.edit_text("<blockquote>Выберите раздел:</blockquote>", reply_markup=kb.numbers_main_kb(), parse_mode="HTML")

@router.callback_query(F.data == "num_add")
async def add_number_cat(call: types.CallbackQuery):
    if is_section_disabled("num_add"): return await call.answer("🔴 Раздел отключен", show_alert=True)
    
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT is_active FROM cards WHERE user_id = ?", (call.from_user.id,))
    res = c.fetchone()
    conn.close()
    if not res or not res[0]: return await call.answer("⚠️ Сначала активируйте карту!", show_alert=True)

    await call.message.edit_text("<blockquote>Выберите категорию</blockquote>", reply_markup=kb.number_category_kb(), parse_mode="HTML")

@router.callback_query(F.data == "cat_max")
async def input_max(call: types.CallbackQuery, state: FSMContext):
    if is_section_disabled("cat_max"): return await call.answer("🔴 Категория отключена", show_alert=True)
    await call.message.edit_text("<blockquote>Введите номер (+7...):</blockquote>", parse_mode="HTML")
    await state.set_state(NumberState.waiting_for_max)

@router.message(NumberState.waiting_for_max)
async def process_max(message: types.Message, state: FSMContext):
    if not re.match(r"^\+7\d{10}$", message.text): return await message.answer("⚠️ Неверный формат! Введите +7XXXXXXXXXX")
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO numbers (user_id, number, category, created_at) VALUES (?, ?, ?, datetime('now'))", (message.from_user.id, message.text, "MAX"))
    conn.commit()
    conn.close()
    await state.clear()
    await message.answer("✅ Номер добавлен!", reply_markup=kb.main_menu_kb())

@router.callback_query(F.data == "cat_wa")
async def input_wa(call: types.CallbackQuery, state: FSMContext):
    if is_section_disabled("cat_wa"): return await call.answer("🔴 Категория отключена", show_alert=True)
    await call.message.edit_text("<blockquote>Введите номер (9...):</blockquote>", parse_mode="HTML")
    await state.set_state(NumberState.waiting_for_wa)

@router.message(NumberState.waiting_for_wa)
async def process_wa(message: types.Message, state: FSMContext):
    if not re.match(r"^9\d{9}$", message.text): return await message.answer("⚠️ Неверный формат! Введите 9XXXXXXXXX")
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO numbers (user_id, number, category, created_at) VALUES (?, ?, ?, datetime('now'))", (message.from_user.id, message.text, "WhatsApp"))
    conn.commit()
    conn.close()
    await state.clear()
    await message.answer("✅ Номер добавлен!", reply_markup=kb.main_menu_kb())

@router.callback_query(F.data == "num_my")
async def my_numbers(call: types.CallbackQuery):
    if is_section_disabled("num_my"): return await call.answer("🔴 Раздел отключен", show_alert=True)
    await call.message.edit_text("<blockquote>Выберите категорию</blockquote>", reply_markup=kb.my_numbers_filter_kb(), parse_mode="HTML")

@router.callback_query(F.data.startswith("filter_"))
async def show_filtered_numbers(call: types.CallbackQuery):
    if is_section_disabled(call.data): return await call.answer("🔴 Категория отключена", show_alert=True)
    status_map = {"filter_work": "В работе", "filter_wait": "Ожидает", "filter_success": "Успех", "filter_block": "Блок"}
    status = status_map[call.data]
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT number FROM numbers WHERE user_id = ? AND status = ?", (call.from_user.id, status))
    nums = c.fetchall()
    conn.close()
    text = f"<blockquote>Номера: {status}</blockquote>"
    keyboard = [[types.InlineKeyboardButton(text=f"📱 {n[0]}", callback_data="ignore")] for n in nums]
    keyboard.append([types.InlineKeyboardButton(text="🔙 Назад", callback_data="num_my")])
    await call.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")