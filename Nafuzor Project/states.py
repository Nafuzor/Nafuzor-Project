from aiogram.fsm.state import State, StatesGroup

class NumberState(StatesGroup):
    waiting_for_max = State()
    waiting_for_wa = State()

class CardState(StatesGroup):
    waiting_for_transfer_user = State()
    waiting_for_transfer_amount = State()

class PaymentState(StatesGroup):
    input_amount_stars = State()
    input_amount_crypto = State()
    input_amount_card = State()

class AdminState(StatesGroup):
    sending_code = State()
    reporting_drop_time = State()
    
    give_sub_user = State()
    give_sub_name = State()
    give_bal_user = State()
    give_bal_amount = State()

    card_action_user = State()
    card_balance_user = State()
    card_balance_amount = State()
    
    pwd_clear_stats = State()
    pwd_clear_queue = State()
    
    add_admin_user = State()
    del_admin_user = State()
    
    broadcast_content = State()
    broadcast_buttons_type = State()
    broadcast_url_input = State()
    broadcast_sys_select = State()
    broadcast_preview = State()