import asyncio
import logging

import html

from aiogram import Bot, Dispatcher, types, Router
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

from utils.db import TELEGRAM_BOT_TOKEN, create_db_pool
from utils.managers import fetch_manager_by_telegram_id, fetch_task_instances_by_manager_today
from utils.scheduler import get_tasks_to_create, schedule_tasks_for_managers
from utils.tasks import mark_task_instance_completed

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize router
router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message, db_pool, bot: Bot):
    """
    Handle /start command. Checks if the user is a registered manager.
    """
    telegram_id = message.from_user.id

    async with db_pool.acquire() as conn:
        manager = await fetch_manager_by_telegram_id(conn, telegram_id)

    if manager:
        await schedule_tasks_for_managers(db_pool, bot)
        await message.answer(
            f"Welcome back, {manager['full_name']}! 👋\n"
            "Use the menu below to manage your restaurant tasks."
        )
        # Here you would typically show a main menu keyboard
    else:
        await message.answer(
            "Welcome to the Restaurant Task Bot! 📋\n\n"
            "It looks like you are not registered as an active manager. "
            "Please contact your administrator with your Telegram ID: "
            f"<code>{telegram_id}</code>",
            parse_mode="HTML"
        )


@router.callback_query(
    lambda callback: bool(callback.data and callback.data.startswith("mark_done:"))
)
async def on_mark_done(callback: types.CallbackQuery, db_pool):
    """Handle inline keyboard callback to mark a task instance completed."""
    if callback.data is None or callback.message is None:
        await callback.answer("Unable to mark task as done.", show_alert=True)
        return

    payload = callback.data.split(":", 1)
    if len(payload) != 2 or not payload[1].isdigit():
        await callback.answer("Invalid action.", show_alert=True)
        return

    task_instance_id = int(payload[1])
    async with db_pool.acquire() as conn:
        await mark_task_instance_completed(conn, task_instance_id)

    original_text = callback.message.text or ""
    escaped_text = html.escape(original_text)
    struck_text = f"<s>{escaped_text}</s>"

    try:
        await callback.message.edit_text(
            struck_text,
            parse_mode="HTML",
            reply_markup=None,
        )
    except Exception:
        pass

    await callback.answer("Task marked done ✅")


@router.message(Command("test"))
async def cmd_test(message: types.Message, db_pool):
    """
    Test command to test the bot for various functions
    """
    telegram_id = message.from_user.id

    async with db_pool.acquire() as conn:
        manager = await fetch_manager_by_telegram_id(conn, telegram_id)
        if not manager:
            await message.answer("Access denied. Manager not found.")
            return

    async with db_pool.acquire() as conn:
        sample_tasks = await get_tasks_to_create(conn)

    logger.info("Test command executed for %s", telegram_id)
    print(sample_tasks, flush=True)
    await message.answer("Test is working")
    # print(await get_tasks_to_create())


@router.message(Command("tasks"))
async def cmd_tasks(message: types.Message, db_pool):
    """
    List pending tasks for the manager.
    """
    telegram_id = message.from_user.id

    async with db_pool.acquire() as conn:
        manager = await fetch_manager_by_telegram_id(conn, telegram_id)
        if not manager:
            await message.answer("Access denied. Manager not found.")
            return

        tasks = await fetch_task_instances_by_manager_today(conn, manager["id"])

    if not tasks:
        await message.answer("You have no pending tasks for today! Well done. 🎉")
    else:
        task_list = "\n".join(
            [
                f"🔹 {task['title']} (Due: {task['due_at'] or 'unspecified'})"
                for task in tasks
            ]
        )
        await message.answer(f"Your tasks for today:\n\n{task_list}")

async def main():
    # Initialize DB pool
    db_pool = await create_db_pool()

    # Initialize bot and dispatcher
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Pass db_pool to handlers context
    dp["db_pool"] = db_pool

    # Include routers
    dp.include_router(router)

    try:
        logger.info("Bot started polling...")
        await dp.start_polling(bot)
    finally:
        await db_pool.close()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
