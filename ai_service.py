import logging
from openai import AsyncOpenAI
from config import config

logger = logging.getLogger(__name__)

# Ленивая инициализация — клиент создаётся при первом вызове
_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    return _client


async def generate_birthday_message(name: str, username: str, age: int | None = None) -> str:
    """Генерируем красивое поздравление через GPT."""
    age_part = f", ему/ей исполняется {age} лет" if age else ""

    prompt = (
        f"Напиши тёплое и искреннее поздравление с днём рождения для человека по имени {name} "
        f"(ник в телеграме @{username}{age_part}). "
        f"Поздравление должно начинаться примерно так: "
        f"'В этот прекрасный день поздравляем @{username} {name} с днём рождения! 🎉' — "
        f"затем добавь несколько тёплых слов, пожеланий счастья, здоровья и удачи. "
        f"Текст должен быть живым, не шаблонным, 3-5 предложений. "
        f"Используй 1-2 уместных эмодзи. Отвечай только текстом поздравления, без заголовков."
    )

    try:
        response = await _get_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.9,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        # Fallback если API недоступен
        return (
            f"🎂 В этот прекрасный день поздравляем @{username} {name} с днём рождения! "
            f"Желаем счастья, здоровья и всего самого лучшего! 🎉"
        )