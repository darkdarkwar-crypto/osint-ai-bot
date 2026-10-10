import asyncio
import logging
import os
from aiohttp import web
from google import genai
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# ====== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ======
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# URL твоего сервиса на Render (уже готов)
WEBHOOK_HOST = "https://osint-ai-bot.onrender.com"
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# Render даёт порт через переменную PORT
PORT = int(os.environ.get("PORT", 10000))
# ===================================

logging.basicConfig(level=logging.INFO)

client = genai.Client(api_key=GEMINI_API_KEY)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


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

    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-3.5-flash",
            contents=message.text
        )
        answer = response.text

        if len(answer) > 4000:
            for i in range(0, len(answer), 4000):
                await message.answer(answer[i:i+4000])
        else:
            await message.answer(answer)

    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)[:200]}")


async def on_startup(bot: Bot):
    await bot.set_webhook(WEBHOOK_URL)
    logging.info(f"✅ Webhook установлен: {WEBHOOK_URL}")


async def on_shutdown(bot: Bot):
    await bot.delete_webhook()


def main():
    # Регистрируем startup/shutdown
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Создаём aiohttp приложение
    app = web.Application()

    # Обработчик webhook
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)

    # Настраиваем startup/shutdown диспетчера
    setup_application(app, dp, bot=bot)

    # Запускаем сервер на порту Render
    logging.info(f"🚀 Сервер запущен на порту {PORT}")
    web.run_app(app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()