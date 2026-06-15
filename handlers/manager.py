import logging
from aiogram import Bot, Router, types
from aiogram.filters import Command
from utils.managers import (
    fetch_manager_by_telegram_id,
)
from utils.scheduler import schedule_tasks_for_managers
from utils.managers import (
    fetch_manager_by_telegram_id,
    fetch_task_instances_by_manager_today,
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


def format_task_list(tasks):
    if not tasks:
        return "You have no pending tasks for today! Well done. 🎉"

    lines = [
        f"🔹 {task['title']} (Due: {task['due_at'] or 'unspecified'})" for task in tasks
    ]
    return "Your tasks for today:\n\n" + "\n".join(lines)


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

    await schedule_tasks_for_managers(db_pool, bot)
    await message.answer(
        f"Welcome back, {manager['full_name']}! 👋\n"
        "Use the menu below to manage your restaurant tasks."
    )
    # Here you would typically show a main menu keyboard


@router.message(Command("tasks"))
async def cmd_tasks(message: types.Message, db_pool):
    """List pending tasks for the manager."""

    manager = await require_manager(message, db_pool)
    if not manager:
        return

    async with db_pool.acquire() as conn:
        tasks = await fetch_task_instances_by_manager_today(conn, manager["id"])

    await message.answer(format_task_list(tasks))
