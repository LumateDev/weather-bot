"""
Telegram-бот прогноза погоды (Яндекс.Погода).

Команды:
  /start       — приветствие и справка
  /now         — погода сейчас
  /today       — прогноз на сегодня
  /days3       — прогноз на 3 дня
  /subscribe   — подписка на утреннюю рассылку в 8:00
  /unsubscribe — отписка от рассылки
"""

import logging
import json
from pathlib import Path

from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from config import (
    TELEGRAM_BOT_TOKEN,
    MORNING_CHAT_ID,
    MORNING_HOUR,
    MORNING_MINUTE,
    CITY_NAME,
    validate_config,
)
from weather import get_current_weather, get_today_forecast, get_3day_forecast

# --- Логирование ---
logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

SUBSCRIBERS_FILE = "subscribers.json"
MOSCOW_TZ = pytz.timezone("Europe/Moscow")


# ============================================================
# Подписчики
# ============================================================

def load_subscribers() -> set:
    if Path(SUBSCRIBERS_FILE).exists():
        try:
            with open(SUBSCRIBERS_FILE, "r") as f:
                return set(json.load(f))
        except (json.JSONDecodeError, TypeError):
            return set()
    return set()


def save_subscribers(subs: set) -> None:
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump(list(subs), f)


subscribers: set = load_subscribers()


# ============================================================
# Обработчики команд
# ============================================================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start — приветствие. Подписка НЕ автоматическая."""
    user_name = update.effective_user.first_name or "друг"

    # Проверяем, подписан ли уже
    is_subscribed = update.effective_chat.id in subscribers
    sub_status = "✅ Ты подписан на утреннюю рассылку" if is_subscribed else "📭 Ты не подписан на рассылку"

    text = (
        f"👋 Привет, <b>{user_name}</b>!\n\n"
        f"Я показываю погоду в городе <b>{CITY_NAME}</b>.\n\n"
        f"📋 <b>Команды:</b>\n"
        f"  /now — погода прямо сейчас\n"
        f"  /today — прогноз на сегодня\n"
        f"  /days3 — прогноз на 3 дня\n"
        f"  /subscribe — подписка на рассылку в {MORNING_HOUR:02d}:{MORNING_MINUTE:02d}\n"
        f"  /unsubscribe — отписаться\n\n"
        f"💬 Можно писать текстом: <b>сейчас</b>, <b>сегодня</b>, <b>3 дня</b>\n\n"
        f"{sub_status}"
    )

    await update.message.reply_text(text, parse_mode="HTML")
    logger.info(f"/start от {update.effective_chat.id} ({user_name})")


async def cmd_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/subscribe — подписка на утреннюю рассылку."""
    chat_id = update.effective_chat.id

    if chat_id in subscribers:
        await update.message.reply_text(
            f"✅ Ты уже подписан!\n"
            f"Рассылка приходит каждый день в {MORNING_HOUR:02d}:{MORNING_MINUTE:02d} МСК.",
            parse_mode="HTML",
        )
        return

    subscribers.add(chat_id)
    save_subscribers(subscribers)

    await update.message.reply_text(
        f"🔔 <b>Подписка оформлена!</b>\n\n"
        f"Каждый день в <b>{MORNING_HOUR:02d}:{MORNING_MINUTE:02d}</b> (МСК) "
        f"я буду присылать тебе прогноз погоды.\n\n"
        f"Чтобы отписаться — /unsubscribe",
        parse_mode="HTML",
    )
    logger.info(f"Подписка: {chat_id}")


async def cmd_unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/unsubscribe — отписка от рассылки."""
    chat_id = update.effective_chat.id

    if chat_id not in subscribers:
        await update.message.reply_text(
            "📭 Ты и так не подписан.\n"
            "Чтобы подписаться — /subscribe",
            parse_mode="HTML",
        )
        return

    subscribers.discard(chat_id)
    save_subscribers(subscribers)

    await update.message.reply_text(
        "🔕 <b>Ты отписан от утренней рассылки.</b>\n\n"
        "Погода по запросу по-прежнему доступна: /now, /today, /days3",
        parse_mode="HTML",
    )
    logger.info(f"Отписка: {chat_id}")


async def cmd_now(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/now — текущая погода."""
    chat_id = update.effective_chat.id
    logger.info(f"/now от {chat_id}")

    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        text = get_current_weather()
        await update.message.reply_text(text, parse_mode="HTML")
    except ConnectionError as e:
        logger.error(f"API ошибка: {e}")
        await update.message.reply_text(
            "⚠️ Сервис погоды временно недоступен. Попробуй позже.",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.exception(f"Ошибка: {e}")
        await update.message.reply_text("❌ Произошла ошибка.", parse_mode="HTML")


async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/today — прогноз на сегодня."""
    chat_id = update.effective_chat.id
    logger.info(f"/today от {chat_id}")

    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        text = get_today_forecast()
        await update.message.reply_text(text, parse_mode="HTML")
    except ConnectionError as e:
        logger.error(f"API ошибка: {e}")
        await update.message.reply_text(
            "⚠️ Сервис погоды временно недоступен. Попробуй позже.",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.exception(f"Ошибка: {e}")
        await update.message.reply_text("❌ Произошла ошибка.", parse_mode="HTML")


async def cmd_days3(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/days3 — прогноз на 3 дня."""
    chat_id = update.effective_chat.id
    logger.info(f"/days3 от {chat_id}")

    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        text = get_3day_forecast()
        await update.message.reply_text(text, parse_mode="HTML")
    except ConnectionError as e:
        logger.error(f"API ошибка: {e}")
        await update.message.reply_text(
            "⚠️ Сервис погоды временно недоступен. Попробуй позже.",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.exception(f"Ошибка: {e}")
        await update.message.reply_text("❌ Произошла ошибка.", parse_mode="HTML")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка текстовых сообщений — ключевые слова."""
    text = update.message.text.strip().lower()

    # Маппинг ключевых слов на команды
    now_keywords = {"погода", "сейчас", "now", "weather"}
    today_keywords = {"сегодня", "today", "прогноз"}
    days3_keywords = {"3 дня", "три дня", "3 days", "3дня"}
    sub_keywords = {"подписка", "подписаться", "subscribe"}
    unsub_keywords = {"отписаться", "отписка", "unsubscribe"}

    if text in now_keywords:
        await cmd_now(update, context)
    elif text in today_keywords:
        await cmd_today(update, context)
    elif text in days3_keywords:
        await cmd_days3(update, context)
    elif text in sub_keywords:
        await cmd_subscribe(update, context)
    elif text in unsub_keywords:
        await cmd_unsubscribe(update, context)
    else:
        await update.message.reply_text(
            "🤔 Не понимаю. Попробуй:\n\n"
            "  /now — погода сейчас\n"
            "  /today — прогноз на сегодня\n"
            "  /days3 — прогноз на 3 дня\n\n"
            "Или напиши: <b>сейчас</b>, <b>сегодня</b>, <b>3 дня</b>",
            parse_mode="HTML",
        )


# ============================================================
# Утренняя рассылка
# ============================================================

async def morning_broadcast(bot) -> None:
    """Рассылка прогноза всем подписчикам."""
    logger.info("🌅 Утренняя рассылка...")

    recipients = set(subscribers)
    if MORNING_CHAT_ID:
        try:
            recipients.add(int(MORNING_CHAT_ID))
        except ValueError:
            pass

    if not recipients:
        logger.warning("Нет подписчиков")
        return

    # Получаем прогноз один раз
    try:
        forecast = get_today_forecast()
        text = f"☀️ <b>Доброе утро!</b>\n\n{forecast}"
    except Exception as e:
        logger.error(f"Ошибка получения прогноза: {e}")
        text = (
            "☀️ <b>Доброе утро!</b>\n\n"
            "⚠️ Сервис погоды временно недоступен.\n"
            "Используй /now позже."
        )

    ok, fail = 0, 0
    for chat_id in recipients:
        try:
            await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
            ok += 1
        except Exception as e:
            logger.error(f"Ошибка отправки в {chat_id}: {e}")
            fail += 1
            if "Forbidden" in str(e) or "blocked" in str(e).lower():
                subscribers.discard(chat_id)
                save_subscribers(subscribers)

    logger.info(f"Рассылка: ✅ {ok} | ❌ {fail}")


# ============================================================
# Установка меню команд в Telegram
# ============================================================

async def post_init(application) -> None:
    """Устанавливает список команд в меню бота (кнопка ☰)."""
    commands = [
        BotCommand("now", "Погода сейчас"),
        BotCommand("today", "Прогноз на сегодня"),
        BotCommand("days3", "Прогноз на 3 дня"),
        BotCommand("subscribe", "Подписка на рассылку"),
        BotCommand("unsubscribe", "Отписаться от рассылки"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("📋 Меню команд установлено")


# ============================================================
# Запуск
# ============================================================

def main() -> None:
    validate_config()
    logger.info("✅ Конфигурация валидна")

    # Создаём приложение с post_init для установки меню
    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # --- Команды ---
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("now", cmd_now))
    app.add_handler(CommandHandler("today", cmd_today))
    app.add_handler(CommandHandler("days3", cmd_days3))
    app.add_handler(CommandHandler("subscribe", cmd_subscribe))
    app.add_handler(CommandHandler("unsubscribe", cmd_unsubscribe))

    # --- Текстовые сообщения ---
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # --- Планировщик ---
    scheduler = AsyncIOScheduler(timezone=MOSCOW_TZ)
    scheduler.add_job(
        morning_broadcast,
        trigger=CronTrigger(
            hour=MORNING_HOUR, minute=MORNING_MINUTE, timezone=MOSCOW_TZ
        ),
        args=[app.bot],
        id="morning_weather",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"⏰ Рассылка в {MORNING_HOUR:02d}:{MORNING_MINUTE:02d} МСК")

    # --- Запуск ---
    logger.info("🤖 Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()