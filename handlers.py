import logging
from datetime import datetime

from aiogram import Dispatcher, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, Document

from config import config
from database import (
    upsert_person, get_all_people, delete_person,
    register_chat
)
from parser import parse_text, parse_csv_bytes

logger = logging.getLogger(__name__)
router = Router()


# ──────────────────────────────────────────────
# Утилиты
# ──────────────────────────────────────────────

def _month_name(month: int) -> str:
    names = ["янв", "фев", "мар", "апр", "май", "июн",
             "июл", "авг", "сен", "окт", "ноя", "дек"]
    return names[month - 1]


# ──────────────────────────────────────────────
# /start
# ──────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message):
    await register_chat(
        chat_id=message.chat.id,
        chat_type=message.chat.type,
        title=message.chat.title or message.chat.full_name or "",
    )
    text = (
        "🎂 <b>Birthday Bot</b>\n\n"
        "Я слежу за днями рождения и поздравляю именинников!\n\n"
        "<b>Как добавить людей:</b>\n"
        "• Отправь CSV-файл (nick,имя,дата)\n"
        "• Или текст в формате:\n"
        "  <code>@username, Имя, DD.MM.YYYY</code>\n"
        "  (можно несколько строк сразу)\n\n"
        "<b>Команды:</b>\n"
        "/list — список всех добавленных\n"
        "/delete @username — удалить человека\n"
        "/today — именинники сегодня\n"
        "/help — подробная справка"
    )
    await message.answer(text, parse_mode="HTML")


# ──────────────────────────────────────────────
# /help
# ──────────────────────────────────────────────

@router.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "📖 <b>Справка</b>\n\n"
        "<b>Форматы добавления людей:</b>\n\n"
        "1️⃣ <b>CSV-файл</b> — прикрепи файл .csv:\n"
        "<code>@username,Имя,DD.MM.YYYY</code>\n\n"
        "2️⃣ <b>Текстом</b> — просто напиши (можно несколько строк):\n"
        "<code>@alex, Алексей, 15.03.1990\n"
        "@masha, Мария, 22.07\n"
        "@petya; Пётр; 01.01.1985</code>\n\n"
        "ℹ️ Год необязателен. Разделители: запятая, точка с запятой или пробел.\n\n"
        "<b>Команды:</b>\n"
        "/list — все люди в этом чате\n"
        "/delete @username — удалить по нику\n"
        "/today — кто именинник сегодня\n\n"
        "🤖 Каждый день в 9:00 бот проверяет дни рождения и отправляет поздравления."
    )
    await message.answer(text, parse_mode="HTML")


# ──────────────────────────────────────────────
# Приём текста с данными о людях
# ──────────────────────────────────────────────

@router.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: Message):
    text = message.text.strip()

    # Проверяем, похоже ли это на список людей
    # (содержит @ или разделители с датой)
    import re
    if not re.search(r"@\w+|,|;|\d{1,2}\.\d{1,2}", text):
        return  # не наши данные, игнорируем

    await register_chat(
        chat_id=message.chat.id,
        chat_type=message.chat.type,
        title=message.chat.title or message.chat.full_name or "",
    )

    people, errors = parse_text(text)

    if not people and not errors:
        await message.answer("Не нашёл данных для добавления. Проверь формат — /help")
        return

    added = []
    for p in people:
        await upsert_person(
            chat_id=message.chat.id,
            username=p.username,
            name=p.name,
            birthday=p.birthday,
        )
        added.append(p)

    lines = []
    if added:
        lines.append(f"✅ Добавлено/обновлено: <b>{len(added)}</b>")
        for p in added:
            year_str = f".{p.birthday.year}" if p.birthday.year != 1900 else ""
            lines.append(f"  • @{p.username} ({p.name}) — {p.birthday.day:02d}.{p.birthday.month:02d}{year_str}")
    if errors:
        lines.append(f"\n❌ Ошибки ({len(errors)}):")
        lines.extend(errors)

    await message.answer("\n".join(lines), parse_mode="HTML")


# ──────────────────────────────────────────────
# Приём CSV-файла
# ──────────────────────────────────────────────

@router.message(F.document)
async def handle_document(message: Message):
    doc: Document = message.document
    if not doc.file_name or not doc.file_name.lower().endswith(".csv"):
        await message.answer("Принимаю только .csv файлы 📄")
        return

    await register_chat(
        chat_id=message.chat.id,
        chat_type=message.chat.type,
        title=message.chat.title or message.chat.full_name or "",
    )

    # Скачиваем файл
    from io import BytesIO
    bot = message.bot
    file = await bot.get_file(doc.file_id)
    buf = BytesIO()
    await bot.download_file(file.file_path, destination=buf)
    data = buf.getvalue()

    people, errors = parse_csv_bytes(data)

    if not people and not errors:
        await message.answer("Файл пустой или не удалось распознать данные. Проверь формат — /help")
        return

    added = []
    for p in people:
        await upsert_person(
            chat_id=message.chat.id,
            username=p.username,
            name=p.name,
            birthday=p.birthday,
        )
        added.append(p)

    lines = []
    if added:
        lines.append(f"✅ Загружено из файла: <b>{len(added)}</b> чел.")
        for p in added:
            year_str = f".{p.birthday.year}" if p.birthday.year != 1900 else ""
            lines.append(f"  • @{p.username} ({p.name}) — {p.birthday.day:02d}.{p.birthday.month:02d}{year_str}")
    if errors:
        lines.append(f"\n❌ Ошибок: {len(errors)}")
        lines.extend(errors[:10])
        if len(errors) > 10:
            lines.append(f"  ...и ещё {len(errors) - 10}")

    await message.answer("\n".join(lines), parse_mode="HTML")


# ──────────────────────────────────────────────
# /list
# ──────────────────────────────────────────────

@router.message(Command("list"))
async def cmd_list(message: Message):
    people = await get_all_people(chat_id=message.chat.id)
    if not people:
        await message.answer("Список пуст. Добавь людей — /help")
        return

    # Сортируем по месяцу и дню
    people.sort(key=lambda p: (p["birthday_month"], p["birthday_day"]))

    lines = [f"👥 <b>Список ({len(people)} чел.):</b>\n"]
    for p in people:
        year_str = f".{p['birthday_year']}" if p.get("birthday_year") else ""
        lines.append(
            f"• @{p['username']} — {p['name']} "
            f"({p['birthday_day']:02d} {_month_name(p['birthday_month'])}{year_str})"
        )

    await message.answer("\n".join(lines), parse_mode="HTML")


# ──────────────────────────────────────────────
# /delete
# ──────────────────────────────────────────────

@router.message(Command("delete"))
async def cmd_delete(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Укажи ник: <code>/delete @username</code>", parse_mode="HTML")
        return

    username = parts[1].strip().lstrip("@")
    deleted = await delete_person(chat_id=message.chat.id, username=username)
    if deleted:
        await message.answer(f"✅ @{username} удалён из списка.")
    else:
        await message.answer(f"❌ @{username} не найден в списке.")


# ──────────────────────────────────────────────
# /today
# ──────────────────────────────────────────────

@router.message(Command("today"))
async def cmd_today(message: Message):
    from database import get_birthdays_today
    people = await get_birthdays_today(chat_id=message.chat.id)
    if not people:
        now = datetime.now()
        await message.answer(f"Сегодня ({now.day:02d}.{now.month:02d}) именинников нет 🎈")
        return

    await message.answer(f"🎂 Сегодня день рождения у {len(people)} чел.! Сейчас отправлю поздравления...")

    from ai_service import generate_birthday_message
    from database import already_congratulated, mark_congratulated

    now = datetime.now()
    for p in people:
        if await already_congratulated(message.chat.id, p["username"], now.year):
            await message.answer(f"(уже поздравляли @{p['username']} сегодня)")
            continue

        age = (now.year - p["birthday_year"]) if p.get("birthday_year") else None
        text = await generate_birthday_message(p["name"], p["username"], age)
        await message.answer(text)
        await mark_congratulated(message.chat.id, p["username"], now.year)


# ──────────────────────────────────────────────
# Регистрация
# ──────────────────────────────────────────────

def register_handlers(dp: Dispatcher):
    dp.include_router(router)