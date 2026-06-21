import logging
from sched import scheduler
from aiogram import Bot, Router, types
from aiogram.filters import Command
from utils.managers import (
    fetch_manager_by_telegram_id,
)
from utils.set_and_send_checklist import set_and_send_checklists
from utils.managers import (
    fetch_manager_by_telegram_id,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()


async def fetch_manager(message: types.Message, db_pool):
    async with db_pool.acquire() as conn:
        return await fetch_manager_by_telegram_id(conn, message.from_user.id)


async def require_manager(message: types.Message, db_pool):
    manager = await fetch_manager(message, db_pool)
    if not manager:
        await message.answer("Access denied. Manager not found.")
    return manager


@router.message(Command("start"))
async def cmd_start(message: types.Message, db_pool, bot: Bot):
    """Handle /start command and schedule tasks for registered managers."""

    manager = await fetch_manager(message, db_pool)

    if not manager:
        await message.answer(
            "Welcome to the Restaurant Task Bot! 📋\n\n"
            "It looks like you are not registered as an active manager. "
            "Please contact your administrator with your Telegram ID: "
            f"<code>{message.from_user.id}</code>",
            parse_mode="HTML",
        )
        return

    await message.answer(
        f"Welcome back, {manager['full_name']}! 👋\n"
        "Use the menu below to manage your restaurant tasks."
    )


@router.message(Command("tasks"))
async def cmd_tasks(message: types.Message, db_pool, bot: Bot):
    """List pending tasks for the manager."""

    manager = await require_manager(message, db_pool)
    if not manager:
        return

    await message.answer("Fetching your tasks for today... ⏳")
    await set_and_send_checklists(db_pool, bot)
