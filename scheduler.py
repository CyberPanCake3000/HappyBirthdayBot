import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot

from config import config
from database import (
    get_all_active_chats, get_birthdays_today,
    already_congratulated, mark_congratulated
)
from ai_service import generate_birthday_message

logger = logging.getLogger(__name__)


async def send_birthday_greetings(bot: Bot):
    """Главная задача планировщика — обходит все чаты и поздравляет."""
    chats = await get_all_active_chats()
    now = datetime.now()
    logger.info(f"[scheduler] Проверка дней рождений. Чатов: {len(chats)}")

    for chat in chats:
        chat_id = chat["chat_id"]
        try:
            people = await get_birthdays_today(chat_id=chat_id)
            for person in people:
                username = person["username"]

                # Не поздравляем дважды в один год
                if await already_congratulated(chat_id, username, now.year):
                    continue

                age = (now.year - person["birthday_year"]) if person.get("birthday_year") else None
                text = await generate_birthday_message(person["name"], username, age)

                await bot.send_message(chat_id=chat_id, text=text)
                await mark_congratulated(chat_id, username, now.year)
                logger.info(f"[scheduler] Поздравили @{username} в чате {chat_id}")

        except Exception as e:
            logger.error(f"[scheduler] Ошибка в чате {chat_id}: {e}")


async def start_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=config.TIMEZONE)

    scheduler.add_job(
        send_birthday_greetings,
        trigger=CronTrigger(
            hour=config.CONGRATS_HOUR,
            minute=config.CONGRATS_MINUTE,
            timezone=config.TIMEZONE,
        ),
        kwargs={"bot": bot},
        id="birthday_check",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        f"[scheduler] Запущен. Поздравления в {config.CONGRATS_HOUR:02d}:{config.CONGRATS_MINUTE:02d} "
        f"({config.TIMEZONE})"
    )
    return scheduler