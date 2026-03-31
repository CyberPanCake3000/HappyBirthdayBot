import logging
import google.generativeai as genai
from config import config

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        genai.configure(api_key=config.GEMINI_API_KEY)
        _model = genai.GenerativeModel("gemini-1.5-flash")
    return _model


async def generate_birthday_message(name: str, username: str, age: int | None = None) -> str:
    """Генерируем красивое поздравление через Gemini."""
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
        response = await _get_model().generate_content_async(
            prompt,
            generation_config=genai.GenerationConfig(
                max_output_tokens=300,
                temperature=0.9,
            ),
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return (
            f"🎂 В этот прекрасный день поздравляем @{username} {name} с днём рождения! "
            f"Желаем счастья, здоровья и всего самого лучшего! 🎉"
        )