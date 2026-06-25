import logging
from sched import scheduler
from aiogram import Bot, Router, types, F
from aiogram.filters import Command
from utils.personnel import (
    fetch_personnel_by_phone,
    fetch_personnel_by_telegram_id,
)
from utils.set_and_send_checklist import set_and_send_checklists
from utils.personnel import (
    fetch_personnel_by_telegram_id,
    set_personnel_telegram_id_by_phone,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()


async def fetch_personnel(message: types.Message, db_pool):
    async with db_pool.acquire() as conn:
        return await fetch_personnel_by_telegram_id(conn, message.from_user.id)


async def require_personnel(message: types.Message, db_pool):
    personnel = await fetch_personnel(message, db_pool)
    if not personnel:
        await message.answer("Access denied. Personnel not found.")
    return personnel


@router.message(Command("start"))
async def cmd_start(message: types.Message, db_pool, bot: Bot):
    """Handle /start command and schedule tasks for registered personnel."""

    # Create a keyboard builder
    builder = ReplyKeyboardBuilder()

    # Add a special button that securely requests their contact info
    builder.button(text="📱 Share Phone Number to Authenticate", request_contact=True)

    await message.answer(
        "Welcome to the Restaurant Task Management Bot!\n\n"
        "To access your tasks, we need to verify your identity. "
        "Please click the button below to share your phone number.",
        reply_markup=builder.as_markup(resize_keyboard=True, one_time_keyboard=True),
    )


@router.message(F.contact)
async def handle_contact(message: types.Message, db_pool):
    """
    Receive the secure phone number from Telegram and authenticate the manager.
    """
    contact = message.contact

    # Security Check: Ensure the shared contact actually belongs to the user clicking the button
    if contact.user_id != message.from_user.id:
        await message.answer(
            "❌ Authentication failed. You must share your own phone number.",
            reply_markup=types.ReplyKeyboardRemove(),  # Clears the button
        )
        return

    # Clean the phone number (Telegram usually sends it with a leading '+' or country code)
    phone_number = contact.phone_number.strip().replace("+", "")

    # Look up the personnel in your database by phone number
    personnel = await fetch_personnel_by_phone(db_pool, phone_number)

    if personnel:
        # Optional: Save their telegram_id to the database now so you can push scheduled tasks to them later
        await set_personnel_telegram_id_by_phone(
            db_pool, phone_number, message.from_user.id
        )

        await message.answer(
            f"✅ Authentication Successful! Welcome back {personnel['full_name']}.\n"
            "Use /tasks to see your pending layout for today.",
            reply_markup=types.ReplyKeyboardRemove(),  # Successfully removes the share button
        )
    else:
        await message.answer(
            "❌ Access Denied. This phone number is not registered as an active personnel in our system. "
            "Please contact system administration.",
            reply_markup=types.ReplyKeyboardRemove(),
        )


@router.message(Command("tasks"))
async def cmd_tasks(message: types.Message, db_pool, bot: Bot):
    """List pending tasks for the personnel."""

    personnel = await require_personnel(message, db_pool)
    if not personnel:
        return

    await message.answer("Fetching your tasks for today... ⏳")
    await set_and_send_checklists(db_pool, bot)
