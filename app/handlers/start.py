from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.keyboards.inline import begin_keyboard

router = Router(name="start")

WELCOME_TEXT = (
    "Assalomu alaykum! 👋\n\n"
    "🎓 Antikorrupsiya klubining rasmiy Telegram botiga xush kelibsiz!\n\n"
    "Klubimizga qo‘shilish va shaxsiy tabriknomangizni olish uchun ro‘yxatdan o‘ting."
)

PRIVACY_TEXT = (
    "🔒 <b>Maxfiylik</b>\n\n"
    "• Bot ism va familiyangizni faqat tabriknoma yaratish uchun vaqtincha ishlatadi.\n"
    "• Ma’lumotlar diskda saqlanmaydi va ma’lumotlar bazasiga yozilmaydi.\n"
    "• Telefon raqami yoki boshqa shaxsiy ma’lumot so‘ralmaydi.\n"
    "• Bot qayta ishga tushsa, ro‘yxatdan o‘tish jarayoni boshidan boshlanadi."
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(WELCOME_TEXT, reply_markup=begin_keyboard())


@router.message(Command("privacy"))
async def cmd_privacy(message: Message) -> None:
    await message.answer(PRIVACY_TEXT)
