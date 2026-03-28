import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB: str = os.getenv("MONGO_DB", "birthday_bot")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    # Через сколько минут после полуночи слать поздравления (0 = сразу в 00:00)
    CONGRATS_HOUR: int = int(os.getenv("CONGRATS_HOUR", "9"))
    CONGRATS_MINUTE: int = int(os.getenv("CONGRATS_MINUTE", "0"))
    TIMEZONE: str = os.getenv("TIMEZONE", "Europe/Moscow")


config = Config()