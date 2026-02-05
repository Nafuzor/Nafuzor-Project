from aiogram.fsm.state import State, StatesGroup

class ConnectCard(StatesGroup):
    number = State()
    cvv = State()
    token = State()

class Withdraw(StatesGroup):
    amount = State()
    confirm = State()
    edit_username = State()
    edit_amount = State()

class AdminLixcuk(StatesGroup):
    add_admin = State()
    remove_admin = State()
    broadcast_msg = State()
    broadcast_buttons = State()
    broadcast_confirm = State()