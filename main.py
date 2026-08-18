import os
import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from yt_dlp import YoutubeDL
from aiohttp import web

TOKEN = "8905713909:AAHpKWLEPbDyCdG3hhR8ORpQ1UOIXgY0e1M"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Bazani ulash
conn = sqlite3.connect("bot_users.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
conn.commit()

# Web server javobi
async def handle(request):
    return web.Response(text="Bot ishlayapti!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# --- BOT HANDLERLARI (Javob berish qismi) ---

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    await message.answer("Assalomu alaykum! Video yuklash uchun link yuboring.")

@dp.message()
async def download_video(message: types.Message):
    url = message.text.strip()
    if not url.startswith("http"):
        await message.answer("Iltimos, to'g'ri video havolasini (link) yuboring!")
        return

    status_msg = await message.answer("Video yuklanmoqda, kuting...")
    
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'video.%(ext)s',
        'quiet': True
    }
    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        
        if os.path.exists(filename):
            video_file = types.FSInputFile(filename)
            await message.answer_video(video=video_file, caption="Video yuklandi! 🚀")
            os.remove(filename)
        else:
            await message.answer("Xatolik: Fayl topilmadi.")
    except Exception as e:
        await message.answer("Kechirasiz, bu videoni yuklab bo'lmadi.")
        print(f"Xato: {e}")
    finally:
        await status_msg.delete()

# --- MAIN ---

async def main():
    await start_web_server()
    print("Bot muvaffaqiyatli ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
