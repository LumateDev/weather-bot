"""
Модуль для получения и форматирования данных о погоде
через API Яндекс.Погод�� (эндпоинт /v2/forecast).
"""

import requests
from config import YANDEX_WEATHER_API_KEY, CITY_LAT, CITY_LON, CITY_NAME


YANDEX_WEATHER_URL = "https://api.weather.yandex.ru/v2/forecast"
REQUEST_TIMEOUT = 15

# --- Словари перевода ---

CONDITION_MAP = {
    "clear": "☀️ Ясно",
    "partly-cloudy": "🌤 Малооблачно",
    "cloudy": "⛅ Облачно с прояснениями",
    "overcast": "☁️ Пасмурно",
    "light-rain": "🌦 Небольшой дождь",
    "rain": "🌧 Дождь",
    "heavy-rain": "🌧 Сильный дождь",
    "showers": "🌧 Ливень",
    "wet-snow": "🌨 Дождь со снегом",
    "light-snow": "🌨 Небольшой снег",
    "snow": "❄️ Снег",
    "snow-showers": "❄️ Снегопад",
    "hail": "🌨 Град",
    "thunderstorm": "⛈ Гроза",
    "thunderstorm-with-rain": "⛈ Дождь с грозой",
    "thunderstorm-with-hail": "⛈ Гроза с градом",
}

WIND_DIR_MAP = {
    "nw": "СЗ ↖", "n": "С ↑", "ne": "СВ ↗", "e": "В →",
    "se": "ЮВ ↘", "s": "Ю ↓", "sw": "ЮЗ ↙", "w": "З ←", "c": "Штиль",
}

PART_NAME_MAP = {
    "night": "🌙 Ночь",
    "morning": "🌅 Утро",
    "day": "☀️ День",
    "evening": "🌆 Вечер",
}

# Перевод дней недели
WEEKDAY_MAP = {
    0: "Понедельник",
    1: "Вторник",
    2: "Среда",
    3: "Четверг",
    4: "Пятница",
    5: "Суббота",
    6: "Воскресенье",
}


def _fmt_temp(t) -> str:
    """Форматирует температуру: +/- перед числом."""
    if isinstance(t, (int, float)):
        return f"+{t}" if t > 0 else str(t)
    return str(t)


def _get_weather_data(limit: int = 1) -> dict:
    """
    Запрос к API Яндекс.Погоды.

    Args:
        limit: Количество дней прогноза (1-7).
    """
    headers = {
        "X-Yandex-Weather-Key": YANDEX_WEATHER_API_KEY,
    }
    params = {
        "lat": CITY_LAT,
        "lon": CITY_LON,
        "lang": "ru_RU",
        "limit": limit,
        "hours": "false",
        "extra": "false",
    }

    try:
        response = requests.get(
            YANDEX_WEATHER_URL,
            headers=headers,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Не удалось подключиться к API: {e}")

    if response.status_code == 403:
        raise ConnectionError(
            "API вернул 403 Forbidden. Проверьте API-ключ."
        )
    if response.status_code != 200:
        raise ConnectionError(
            f"API: HTTP {response.status_code} — {response.text[:300]}"
        )

    return response.json()


def _format_day_parts(parts_dict: dict) -> list:
    """Форматирует части одного дня в список строк."""
    lines = []
    part_order = ["night", "morning", "day", "evening"]

    for part_name in part_order:
        part = parts_dict.get(part_name)
        if not part:
            continue

        part_label = PART_NAME_MAP.get(part_name, part_name)
        temp_min = part.get("temp_min", part.get("temp_avg", "?"))
        temp_max = part.get("temp_max", part.get("temp_avg", "?"))
        feels_like = part.get("feels_like", "?")
        condition = part.get("condition", "")
        wind_speed = part.get("wind_speed", "?")
        wind_gust = part.get("wind_gust", "")
        wind_dir = part.get("wind_dir", "")
        humidity = part.get("humidity", "?")

        condition_text = CONDITION_MAP.get(condition, condition)
        wind_dir_text = WIND_DIR_MAP.get(wind_dir, wind_dir)
        gust_str = f" (порывы {wind_gust})" if wind_gust else ""

        lines.append(
            f"\n  {part_label}\n"
            f"    🌡 {_fmt_temp(temp_min)}..{_fmt_temp(temp_max)}°C "
            f"(ощущается {_fmt_temp(feels_like)}°C)\n"
            f"    {condition_text}\n"
            f"    🌬 {wind_speed} м/с{gust_str}, {wind_dir_text} "
            f"| 💧 {humidity}%"
        )

    return lines


# ============================================================
# ПУБЛИЧНЫЕ ФУНКЦИИ
# ============================================================

def get_current_weather() -> str:
    """Текущая погода прямо сейчас."""
    data = _get_weather_data(limit=1)
    fact = data.get("fact", {})

    temp = fact.get("temp", "?")
    feels_like = fact.get("feels_like", "?")
    humidity = fact.get("humidity", "?")
    pressure_mm = fact.get("pressure_mm", "?")
    wind_speed = fact.get("wind_speed", "?")
    wind_gust = fact.get("wind_gust", "?")
    wind_dir = fact.get("wind_dir", "")
    condition = fact.get("condition", "")

    condition_text = CONDITION_MAP.get(condition, condition)
    wind_dir_text = WIND_DIR_MAP.get(wind_dir, wind_dir)

    return (
        f"🏙 <b>Погода в {CITY_NAME} сейчас</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🌡 Температура: <b>{_fmt_temp(temp)}°C</b>\n"
        f"🤔 Ощущается: <b>{_fmt_temp(feels_like)}°C</b>\n"
        f"🌈 {condition_text}\n"
        f"💧 Влажность: {humidity}%\n"
        f"🌬 Ветер: {wind_speed} м/с (порывы {wind_gust} м/с), {wind_dir_text}\n"
        f"📊 Давление: {pressure_mm} мм рт.ст."
    )


def get_today_forecast() -> str:
    """Прогноз на сегодня по частям дня (утро/день/вечер/ночь)."""
    data = _get_weather_data(limit=1)
    forecasts = data.get("forecasts", [])

    if not forecasts:
        return "⚠️ Прогноз временно недоступен."

    today = forecasts[0]
    date_str = today.get("date", "?")
    parts_dict = today.get("parts", {})

    lines = [
        f"📅 <b>Прогноз на сегодня — {date_str}</b>",
        f"📍 {CITY_NAME}",
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    lines.extend(_format_day_parts(parts_dict))

    lines.append("\n━━━━━━━━━━━━━━━━━━━━")

    return "\n".join(lines)


def get_3day_forecast() -> str:
    """Прогноз на 3 дня — краткий обзор по каждому дню."""
    data = _get_weather_data(limit=3)
    forecasts = data.get("forecasts", [])

    if not forecasts:
        return "⚠️ Прогноз временно недоступен."

    lines = [
        f"📅 <b>Прогноз на 3 дня</b>",
        f"📍 {CITY_NAME}",
    ]

    from datetime import datetime

    for i, day in enumerate(forecasts):
        date_str = day.get("date", "?")

        # Определяем день недели
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            weekday = WEEKDAY_MAP.get(date_obj.weekday(), "")
            date_label = f"{date_str} ({weekday})"
        except ValueError:
            date_label = date_str

        # Заголовок дня
        if i == 0:
            day_title = f"📌 <b>Сегодня — {date_label}</b>"
        elif i == 1:
            day_title = f"📌 <b>Завтра — {date_label}</b>"
        else:
            day_title = f"📌 <b>{date_label}</b>"

        lines.append(f"\n{'━' * 20}")
        lines.append(day_title)

        parts_dict = day.get("parts", {})

        # Для 3-дневного прогноза показываем компактно: день и ночь
        for part_name in ["day", "night"]:
            part = parts_dict.get(part_name)
            if not part:
                continue

            part_label = PART_NAME_MAP.get(part_name, part_name)
            temp_min = part.get("temp_min", part.get("temp_avg", "?"))
            temp_max = part.get("temp_max", part.get("temp_avg", "?"))
            feels = part.get("feels_like", "?")
            condition = part.get("condition", "")
            wind = part.get("wind_speed", "?")
            humidity = part.get("humidity", "?")

            cond_text = CONDITION_MAP.get(condition, condition)

            lines.append(
                f"  {part_label}: {_fmt_temp(temp_min)}..{_fmt_temp(temp_max)}°C "
                f"(ощущ. {_fmt_temp(feels)}°C)\n"
                f"    {cond_text} | 🌬 {wind} м/с | 💧 {humidity}%"
            )

    lines.append(f"\n{'━' * 20}")

    return "\n".join(lines)