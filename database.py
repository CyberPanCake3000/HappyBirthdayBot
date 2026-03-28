from datetime import datetime
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from config import config

_client: Optional[AsyncIOMotorClient] = None


def get_db():
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(config.MONGO_URI)
    return _client[config.MONGO_DB]


# ──────────────────────────────────────────────
# Люди
# ──────────────────────────────────────────────

async def upsert_person(chat_id: int, username: str, name: str, birthday: datetime) -> dict:
    """Добавить или обновить человека в БД."""
    db = get_db()
    doc = {
        "chat_id": chat_id,
        "username": username.lstrip("@").lower(),
        "name": name,
        "birthday_day": birthday.day,
        "birthday_month": birthday.month,
        "birthday_year": birthday.year if birthday.year != 1900 else None,
        "updated_at": datetime.utcnow(),
    }
    await db.people.update_one(
        {"chat_id": chat_id, "username": doc["username"]},
        {"$set": doc},
        upsert=True,
    )
    return doc


async def get_birthdays_today(chat_id: int) -> list[dict]:
    """Вернуть всех именинников сегодня для данного чата."""
    db = get_db()
    now = datetime.now()
    cursor = db.people.find({
        "chat_id": chat_id,
        "birthday_day": now.day,
        "birthday_month": now.month,
    })
    return await cursor.to_list(length=None)


async def get_all_people(chat_id: int) -> list[dict]:
    db = get_db()
    cursor = db.people.find({"chat_id": chat_id})
    return await cursor.to_list(length=None)


async def delete_person(chat_id: int, username: str) -> int:
    db = get_db()
    result = await db.people.delete_one({
        "chat_id": chat_id,
        "username": username.lstrip("@").lower(),
    })
    return result.deleted_count


# ──────────────────────────────────────────────
# Чаты (откуда бот должен слать поздравления)
# ──────────────────────────────────────────────

async def register_chat(chat_id: int, chat_type: str, title: str = ""):
    db = get_db()
    await db.chats.update_one(
        {"chat_id": chat_id},
        {"$set": {"chat_id": chat_id, "chat_type": chat_type, "title": title, "active": True}},
        upsert=True,
    )


async def get_all_active_chats() -> list[dict]:
    db = get_db()
    cursor = db.chats.find({"active": True})
    return await cursor.to_list(length=None)


# ──────────────────────────────────────────────
# Лог уже отправленных поздравлений (чтобы не дублировать)
# ──────────────────────────────────────────────

async def already_congratulated(chat_id: int, username: str, year: int) -> bool:
    db = get_db()
    doc = await db.congrats_log.find_one({
        "chat_id": chat_id,
        "username": username,
        "year": year,
    })
    return doc is not None


async def mark_congratulated(chat_id: int, username: str, year: int):
    db = get_db()
    await db.congrats_log.insert_one({
        "chat_id": chat_id,
        "username": username,
        "year": year,
        "sent_at": datetime.utcnow(),
    })