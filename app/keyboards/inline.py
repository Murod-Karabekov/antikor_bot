from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def begin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="📝 Boshlash", callback_data="reg:begin")]]
    )


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="reg:confirm")],
            [InlineKeyboardButton(text="✏️ Qayta kiritish", callback_data="reg:redo")],
        ]
    )


def join_keyboard(invite_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Guruhga qo‘shilish", url=invite_url)],
            [InlineKeyboardButton(text="✅ A’zolikni tekshirish", callback_data="grp:check")],
        ]
    )


def reissue_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎉 Tabriknomani qayta olish", callback_data="cert:reissue")]
        ]
    )


def admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Bot holati", callback_data="adm:status")],
            [InlineKeyboardButton(text="👥 Guruh ma’lumoti", callback_data="adm:group")],
            [InlineKeyboardButton(text="🧪 Tabriknoma sinovi", callback_data="adm:test_cert")],
        ]
    )
