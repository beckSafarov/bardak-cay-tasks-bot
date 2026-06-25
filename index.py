import asyncio
import logging
from zoneinfo import ZoneInfo
from aiogram import Bot, Dispatcher, Router
from aiogram.fsm.storage.memory import MemoryStorage
from utils.db import TELEGRAM_BOT_TOKEN, create_db_pool
from handlers.start import router as start_router
from handlers.task_status import router as task_status_router
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from utils.set_and_send_checklist import set_and_send_checklists

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("apscheduler").setLevel(logging.DEBUG)

router = Router()
scheduler = AsyncIOScheduler(timezone=ZoneInfo("Asia/Tashkent"))


# --- STARTUP HOOK ---
async def on_startup(bot: Bot, db_pool):
    """This runs ONCE when the bot script boots up, not when a user types a command."""
    # 1. Add the cron job to run every day at 11:43
    job = scheduler.add_job(
        set_and_send_checklists,
        "cron",
        args=(db_pool, bot),
        hour=16,
        minute=00,
        id="daily_checklist_job",
        replace_existing=True,
    )
    # 2. Start the scheduler background loop
    scheduler.start()
    print(f"Job successfully scheduled. Next execution time: {job.next_run_time}")
    print("Background scheduler started successfully!")


async def main():
    db_pool = await create_db_pool()
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp["db_pool"] = db_pool
    dp.startup.register(on_startup)
    dp.include_router(start_router)
    dp.include_router(task_status_router)

    try:
        logger.info("Bot started polling...")
        await dp.start_polling(bot)
    finally:
        await db_pool.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
