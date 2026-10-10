import asyncio
import logging
import os
from aiohttp import web
from groq import Groq
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# ====== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ======
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

WEBHOOK_HOST = "https://osint-ai-bot.onrender.com"
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
PORT = int(os.environ.get("PORT", 10000))
# ===================================

logging.basicConfig(level=logging.INFO)

client = Groq(api_key=GROQ_API_KEY)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Добро пожаловать в <b>OSINT AI</b> от @lonqa\n\n"
        "Просто напиши мне запрос — я найду всё, что нужно."
    )

@dp.message(F.text)
async def handle_message(message: Message):
    await bot.send_chat_action(message.chat.id, "typing")
    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": message.text}]
        )
        answer = response.choices[0].message.content
        if len(answer) > 4000:
            for i in range(0, len(answer), 4000):
                await message.answer(answer[i:i+4000])
        else:
            await message.answer(answer)
    except Exception as e:
        logging.error(f"Ошибка Groq: {e}")
        await message.answer(f"❌ Ошибка: {str(e)[:200]}")

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
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()