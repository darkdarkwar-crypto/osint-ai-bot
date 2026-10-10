import asyncio
import logging
from google import genai
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message

# ====== ЗАМЕНИ НА СВОИ ДАННЫЕ ======
import os
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
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

async def main():
    print("🤖 OSINT AI запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен")
