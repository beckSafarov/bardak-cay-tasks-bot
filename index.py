import asyncio
import logging
from aiogram import Bot, Dispatcher, Router
from aiogram.fsm.storage.memory import MemoryStorage
from utils.db import TELEGRAM_BOT_TOKEN, create_db_pool
from handlers.manager import router as manager_router
from handlers.task_status import router as task_status_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()


async def main():
    db_pool = await create_db_pool()
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp["db_pool"] = db_pool
    dp.include_router(manager_router)
    dp.include_router(task_status_router)

    try:
        logger.info("Bot started polling...")
        await dp.start_polling(bot)
    finally:
        await db_pool.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
