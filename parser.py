"""
Парсер входящих данных о людях.

Поддерживаемые форматы:
  CSV-файл или текст:
    @username,Имя,DD.MM.YYYY
    @username,Имя,DD.MM          ← без года
    username;Имя;DD.MM.YYYY      ← разделитель ;
  Одна строка:
    @username Имя DD.MM.YYYY
"""

import csv
import io
import re
from datetime import datetime
from dataclasses import dataclass


@dataclass
class ParsedPerson:
    username: str
    name: str
    birthday: datetime
    raw: str


class ParseError(Exception):
    pass


_DATE_FORMATS = ["%d.%m.%Y", "%d.%m.%y", "%d/%m/%Y", "%d-%m-%Y", "%d.%m"]


def _parse_date(raw: str) -> datetime:
    raw = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            dt = datetime.strptime(raw, fmt)
            # Если год не указан, ставим 1900 как маркер
            if fmt == "%d.%m":
                dt = dt.replace(year=1900)
            return dt
        except ValueError:
            continue
    raise ParseError(f"Не удалось распознать дату: '{raw}'. Используй формат DD.MM.YYYY или DD.MM")


def _clean_username(raw: str) -> str:
    return raw.strip().lstrip("@").lower()


def _parse_row(parts: list[str], raw_line: str) -> ParsedPerson:
    if len(parts) < 3:
        raise ParseError(f"Нужно минимум 3 поля (ник, имя, дата), получено: {parts}")
    username = _clean_username(parts[0])
    name = parts[1].strip()
    birthday = _parse_date(parts[2])
    if not username:
        raise ParseError("Ник не может быть пустым")
    if not name:
        raise ParseError("Имя не может быть пустым")
    return ParsedPerson(username=username, name=name, birthday=birthday, raw=raw_line)


def parse_text(text: str) -> tuple[list[ParsedPerson], list[str]]:
    """
    Разбираем многострочный текст или CSV.
    Возвращает (успешные, ошибки).
    """
    people: list[ParsedPerson] = []
    errors: list[str] = []

    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]

    for line in lines:
        # Пропускаем заголовки
        if re.match(r"(?i)(username|ник|nick|имя|name|дата|date)", line):
            continue

        # Определяем разделитель
        if "," in line:
            parts = [p.strip() for p in line.split(",")]
        elif ";" in line:
            parts = [p.strip() for p in line.split(";")]
        elif "\t" in line:
            parts = [p.strip() for p in line.split("\t")]
        else:
            # Пробуем по пробелам: @username Имя DD.MM.YYYY
            parts = line.split(None, 2)

        try:
            people.append(_parse_row(parts, line))
        except ParseError as e:
            errors.append(f"⚠️ Строка «{line}»: {e}")

    return people, errors


def parse_csv_bytes(data: bytes) -> tuple[list[ParsedPerson], list[str]]:
    """Разбираем CSV-файл."""
    text = data.decode("utf-8-sig", errors="replace")
    # Определяем диалект
    sample = text[:2048]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel

    people: list[ParsedPerson] = []
    errors: list[str] = []

    reader = csv.reader(io.StringIO(text), dialect)
    for i, row in enumerate(reader, start=1):
        if not any(row):
            continue
        # Пропускаем заголовок
        if i == 1 and re.match(r"(?i)(username|ник|nick|имя|name)", row[0].strip()):
            continue
        raw_line = ",".join(row)
        try:
            people.append(_parse_row(row, raw_line))
        except ParseError as e:
            errors.append(f"⚠️ Строка {i} «{raw_line}»: {e}")

    return people, errors