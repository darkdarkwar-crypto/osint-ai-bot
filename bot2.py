import asyncio
import logging
import os
from aiohttp import web
from groq import Groq
from google import genai as gemini_client
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# ====== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ======
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# URL твоего сервиса на Render
WEBHOOK_HOST = "https://osint-ai-bot.onrender.com"
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

PORT = int(os.environ.get("PORT", 10000))
# ===================================

logging.basicConfig(level=logging.INFO)

# Инициализация двух клиентов
groq_client = Groq(api_key=GROQ_API_KEY)
gemini = gemini_client.Client(api_key=GEMINI_API_KEY)

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()


def ask_groq(text: str) -> str:
    """Запрос к Groq"""
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": text}]
    )
    return response.choices[0].message.content


def ask_gemini(text: str) -> str:
    """Запрос к Gemini"""
    response = gemini.models.generate_content(
        model="gemini-3.5-flash",
        contents=text
    )
    return response.text


@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Добро пожаловать в <b>OSINT AI</b> от @lonqa\n\n"
        "Я — нейросетевой ассистент для поиска и анализа информации.\n\n"
        "Просто напиши мне запрос — я найду всё, что нужно.\n\n"
        "Команды:\n"
        "/clear — очистить историю"
    )


@dp.message(Command("clear"))
async def cmd_clear(message: Message):
    await message.answer("🧹 История очищена.")


@dp.message(F.text)
async def handle_message(message: Message):
    await bot.send_chat_action(message.chat.id, "typing")

    answer = None

    # 1. Пробуем Groq (быстрый и стабильный)
    try:
        answer = await asyncio.to_thread(ask_groq, message.text)
        logging.info("Ответ получен от Groq")
    except Exception as e:
        logging.warning(f"Groq упал: {e}. Переключаюсь на Gemini...")

        # 2. Если Groq упал — идём в Gemini
        try:
            answer = await asyncio.to_thread(ask_gemini, message.text)
            logging.info("Ответ получен от Gemini")
        except Exception as e2:
            logging.error(f"Gemini тоже упал: {e2}")

            # 3. Оба упали — пауза и ещё раз Groq
            await asyncio.sleep(3)
            try:
                answer = await asyncio.to_thread(ask_groq, message.text)
                logging.info("Ответ получен от Groq (со второй попытки)")
            except Exception as e3:
                await message.answer("❌ Оба провайдера недоступны. Попробуй через минуту.")
                return

    # Отправляем ответ
    if answer:
        if len(answer) > 4000:
            for i in range(0, len(answer), 4000):
                await message.answer(answer[i:i+4000])
        else:
            await message.answer(answer)


async def on_startup(bot: Bot):
    await bot.set_webhook(WEBHOOK_URL)
    logging.info(f"✅ Webhook установлен: {WEBHOOK_URL}")


async def on_shutdown(bot: Bot):
    await bot.delete_webhook()


def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()
    webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    logging.info(f"🚀 Сервер запущен на порту {PORT}")
    web.run_app(app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()
