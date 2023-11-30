from aiogram.types.inline_keyboard import InlineKeyboardMarkup, InlineKeyboardButton


async def pay_kb(url: str):
    kb_pay = InlineKeyboardMarkup()
    btn_pay = InlineKeyboardButton(text='✅ Показать билет', url=url)
    return kb_pay.add(btn_pay)
