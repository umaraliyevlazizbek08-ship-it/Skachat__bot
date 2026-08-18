import os
import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from yt_dlp import YoutubeDL
from aiohttp import web

TOKEN = "8821143666:AAGKJHoSVng8svXMMHzDg05NZlIBMitAnDs"
ADMIN_ID = 8691162431

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Ma'lumotlar bazasini ulash
conn = sqlite3.connect("bot_users.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, lang TEXT DEFAULT 'uz')")
conn.commit()

# Videoni yuklab olish funksiyasi (Instagram va boshqalar uchun eng barqaror sozlamalar)
def download_video(url: str):
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'video.mp4',
        'quiet': True,
        'no_warnings': True,
        'geo_bypass': True,
        'extractor_args': {'instagram': {'max_comments': 0}},
    }
    try:
        if os.path.exists('video.mp4'):
            os.remove('video.mp4')
            
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        if os.path.exists('video.mp4'):
            return 'video.mp4'
    except Exception as e:
        print(f"Yuklashda xatolik: {e}")
    return None

# Start komandasi
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer("Salom! Menga Instagram, TikTok yoki YouTube havolasini yuboring, men uni yuklab beraman.")

# Havolalarni qabul qilib yuklash
@dp.message(F.text.startswith("http"))
async def process_download(message: types.Message):
    url = message.text.strip()
    sent_msg = await message.answer("⏳ Video yuklab olinmoqda, biroz kuting...")
    
    loop = asyncio.get_running_loop()
    file_path = await loop.run_in_executor(None, download_video, url)
    
    if file_path and os.path.exists(file_path):
        try:
            await message.answer_video(types.FSInputFile(file_path))
            await sent_msg.delete()
        except Exception as e:
            await message.answer(f"Videoni yuborishda xatolik yuz berdi: {e}")
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
    else:
        await message.answer("❌ Kechirasiz, bu videoni yuklab bo'lmadi. Havola ochiq ekanligini yoki Instagram/YouTube chekloviga tushmaganini tekshiring.")
        await sent_msg.delete()

# Render uchun veb-server
async def handle(request):
    return web.Response(text="Bot ishlayapti!")

async def web_server():
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    await web_server()
    print("Bot muvaffaqiyatli ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
