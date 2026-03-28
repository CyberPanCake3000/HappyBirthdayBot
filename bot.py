import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from handlers import register_handlers
from scheduler import start_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    bot = Bot(token=config.TELEGRAM_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    register_handlers(dp)

    # Запуск планировщика поздравлений
    scheduler = await start_scheduler(bot)

    logger.info("Бот запущен!")
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())