from aiogram import types
from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from avia_bot.glossaries.glossary import glossary
from database.mysqldb import database
from avia_api.models import Ticket
# from aiogram.dispatcher.filters import Text
# from aiogram.dispatcher.filters.state import State
# from aiogram.dispatcher.filters.state import StatesGroup



# @dp.message_handler(commands=['start'])
async def command_start(message: types.Message, state: FSMContext) -> None:
    await message.answer(
        text=glossary.get_phrase("start_greeting", username=message.from_user.first_name), reply_markup=None,)


def register_handlers_client(dp: Dispatcher):
    dp.register_message_handler(command_start, commands=["start"], state=None)

