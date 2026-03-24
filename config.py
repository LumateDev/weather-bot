"""
Модуль конфигурации.
Загружает переменные окружения из .env файла и предоставляет
настройки приложения в виде констант.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- Токены и ключи ---
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
YANDEX_WEATHER_API_KEY: str = os.getenv("YANDEX_WEATHER_API_KEY", "")

# --- Координаты города (по умолчанию — Москва) ---
CITY_LAT: float = float(os.getenv("CITY_LAT", "55.75"))
CITY_LON: float = float(os.getenv("CITY_LON", "37.62"))
CITY_NAME: str = os.getenv("CITY_NAME", "Москва")

# --- Chat ID для утренней рассылки ---
# Можно указать конкретный chat_id, либо оставить пустым —
# тогда бот будет собирать chat_id при команде /start
MORNING_CHAT_ID: str = os.getenv("MORNING_CHAT_ID", "")

# --- Время утренней рассылки (часы и минуты, UTC+3) ---
MORNING_HOUR: int = int(os.getenv("MORNING_HOUR", "8"))
MORNING_MINUTE: int = int(os.getenv("MORNING_MINUTE", "0"))

# --- Валидация обязательных параметров ---
def validate_config() -> None:
    """Проверяет, что все обязательные переменные заданы."""
    errors = []
    if not TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN не задан")
    if not YANDEX_WEATHER_API_KEY:
        errors.append("YANDEX_WEATHER_API_KEY не задан")
    if errors:
        raise ValueError(
            "Ошибки конфигурации:\n" + "\n".join(f"  • {e}" for e in errors)
        )