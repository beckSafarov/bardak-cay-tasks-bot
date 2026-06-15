import asyncio
import html
import logging
import re
from typing import Optional

from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

from utils.db import TELEGRAM_BOT_TOKEN, create_db_pool
from utils.managers import fetch_manager_by_telegram_id, fetch_task_instances_by_manager_today
from utils.scheduler import get_tasks_to_create, schedule_tasks_for_managers
from utils.tasks import mark_task_instance_completed, mark_task_instance_incomplete
from utils.keyboards import build_mark_done_keyboard, build_mark_undone_keyboard

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


def parse_mark_status_payload(callback_data: str) -> Optional[int]:
    parts = callback_data.split(":", 1)
    if len(parts) != 2 or not parts[1].isdigit():
        return None
    return int(parts[1])


async def strike_message_text(message: types.Message, task_instance_id: int = None):
    original_text = message.text or ""
    escaped_text = html.escape(original_text)
    struck_text = f"<s>{escaped_text}</s>"
    await message.edit_text(
        struck_text,
        parse_mode="HTML",
        reply_markup=build_mark_undone_keyboard(task_instance_id),
    )


async def unstrike_message_text(message: types.Message, task_instance_id: int = None):
    original_text = message.text or ""
    escaped_text = html.escape(original_text)
    unstruck_text = re.sub(
        r"^\s*<s>\s*|\s*</s>\s*$", "", escaped_text, flags=re.IGNORECASE
    )
    await message.edit_text(
        unstruck_text,
        parse_mode="HTML",
        reply_markup=build_mark_done_keyboard(task_instance_id),
    )


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


@router.callback_query(
    lambda callback: bool(callback.data and callback.data.startswith("mark_done:"))
)
async def on_mark_done(callback: types.CallbackQuery, db_pool):
    """Handle inline keyboard callback to mark a task instance completed."""
    if callback.data is None or callback.message is None:
        await callback.answer("Unable to mark task as done.", show_alert=True)
        return

    task_instance_id = parse_mark_status_payload(callback.data)
    if task_instance_id is None:
        await callback.answer("Invalid action.", show_alert=True)
        return

    async with db_pool.acquire() as conn:
        await mark_task_instance_completed(conn, task_instance_id)

    try:
        await strike_message_text(callback.message, task_instance_id)
    except Exception:
        pass

    await callback.answer("Task marked done ✅")


@router.callback_query(
    lambda callback: bool(callback.data and callback.data.startswith("mark_undone:"))
)
async def on_mark_undone(callback: types.CallbackQuery, db_pool):
    """Handle inline keyboard callback to mark a task instance as incomplete."""
    if callback.data is None or callback.message is None:
        await callback.answer("Unable to mark task as incomplete.", show_alert=True)
        return

    task_instance_id = parse_mark_status_payload(callback.data)
    if task_instance_id is None:
        await callback.answer("Invalid action.", show_alert=True)
        return

    async with db_pool.acquire() as conn:
        await mark_task_instance_incomplete(conn, task_instance_id)

    try:
        await unstrike_message_text(callback.message, task_instance_id)
    except Exception:
        pass

    await callback.answer("Task marked incomplete ❌")


@router.message(Command("tasks"))
async def cmd_tasks(message: types.Message, db_pool):
    """List pending tasks for the manager."""

    manager = await require_manager(message, db_pool)
    if not manager:
        return

    async with db_pool.acquire() as conn:
        tasks = await fetch_task_instances_by_manager_today(conn, manager["id"])

    await message.answer(format_task_list(tasks))


async def main():
    db_pool = await create_db_pool()
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp["db_pool"] = db_pool
    dp.include_router(router)

    try:
        logger.info("Bot started polling...")
        await dp.start_polling(bot)
    finally:
        await db_pool.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
