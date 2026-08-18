import os
import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from yt_dlp import YoutubeDL

TOKEN = "8905713909:AAHpKWLEPbDyCdG3hhR8ORpQ1UOIXgY0e1M"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Bazani ulash
conn = sqlite3.connect("bot_users.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
conn.commit()

async def update_bot_name():
    try:
        cursor.execute("SELECT COUNT(user_id) FROM users")
        total_users = cursor.fetchone()[0]
        new_name = f"Video Nova Bot | 👥 {total_users} uzer"
        
        # Telegram nom o'zgarmasa xato bermasligi uchun tekshirish
        current_bot = await bot.get_me()
        if current_bot.first_name != new_name:
            await bot.set_my_name(name=new_name)
    except Exception as e:
        print(f"Nom yangilashda xato: {e}")

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    try:
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
    except Exception as e:
        print(f"Baza bilan xatolik: {e}")
        
    await message.answer(f"Salom {message.from_user.full_name}! 👋\nMen Instagram, TikTok va YouTube-dan video yuklovchi botman. Menga video linkini yuboring!")
    await update_bot_name()

@dp.message(Command("stat"))
async def stat_cmd(message: types.Message):
    cursor.execute("SELECT COUNT(user_id) FROM users")
    total_users = cursor.fetchone()[0]
    await message.answer(f"📊 Bot foydalanuvchilari soni: {total_users} ta")

@dp.message()
async def download_video(message: types.Message):
    url = message.text
    if not (url.startswith("http://") or url.startswith("https://")):
        await message.answer("Iltimos, to'g'ri video linkini yuboring! ❌")
        return

    status_msg = await message.answer("Video yuklanmoqda, iltimos kuting... ⏳")

    ydl_opts = {
        'format': 'best',
        'outtmpl': f'video_{message.from_user.id}.%(ext)s',
        'max_filesize': 50 * 1024 * 1024, # 50MB limit
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        if os.path.exists(filename):
            video_file = types.FSInputFile(filename)
            await message.answer_video(video=video_file, caption="Video muvaffaqiyatli yuklandi! 🎉\n\n@VideoNovabot")
            os.remove(filename)
        else:
            await message.answer("Xatolik: Fayl topilmadi. ❌")
            
    except Exception as e:
        await message.answer("Kechirasiz, bu videoni yuklab bo'lmadi. Linkni tekshirib qayta urinib ko'ring! ❌")
        print(f"Yuklashda xato: {e}")
    finally:
        await status_msg.delete()

async def main():
    print("Bot muvaffaqiyatli ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())