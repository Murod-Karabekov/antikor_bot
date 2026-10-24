from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    first_name = State()
    last_name = State()
    confirm = State()
    joined = State()
