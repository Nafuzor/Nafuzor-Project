from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from states import PaymentState
import keyboards as kb

router = Router()

@router.callback_query(F.data == "pay_deposit")
async def select_deposit_method(call: types.CallbackQuery):
    await call.message.edit_text("Выберите валюту платежа:", reply_markup=kb.payment_method_kb())

# Выбор метода
@router.callback_query(F.data.in_({"pay_method_stars", "pay_method_crypto", "pay_method_card"}))
async def show_amounts(call: types.CallbackQuery):
    method = call.data.replace("pay_method_", "")
    msg = "<blockquote>Выберите/укажите сумму пополнения:</blockquote>" if method == 'card' else "<blockquote>Выберите сумму пополнения:</blockquote>"
    await call.message.edit_text(msg, reply_markup=kb.amount_select_kb(method), parse_mode="HTML")

# Ввод своей суммы
@router.callback_query(F.data.startswith("pay_input_"))
async def input_amount_ask(call: types.CallbackQuery, state: FSMContext):
    method = call.data.split("_")[2]
    currency = "$" if method == "crypto" else "₽"
    
    await call.message.edit_text(f"✍️ Введите сумму ({currency}):", reply_markup=kb.back_kb("pay_deposit"))
    
    if method == "stars": await state.set_state(PaymentState.input_amount_stars)
    elif method == "crypto": await state.set_state(PaymentState.input_amount_crypto)
    elif method == "card": await state.set_state(PaymentState.input_amount_card)