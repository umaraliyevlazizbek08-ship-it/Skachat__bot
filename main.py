import os
import asyncio
import sqlite3
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from yt_dlp import YoutubeDL
from aiohttp import web

TOKEN = "8821143666:AAH7dxU0EpEK-w3FuVIGQDtYuRMNecCF1sU"
ADMIN_ID = 8691162431

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Ma'lumotlar bazasini ulash
conn = sqlite3.connect("bot_users.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, lang TEXT DEFAULT 'uz')")
conn.commit()

def add_user(user_id):
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()

# Instagram va boshqa videolar uchun universal yuklash funksiyasi
def download_video(url: str):
    if os.path.exists('video.mp4'):
        os.remove('video.mp4')

    # Instagram uchun maxsus API
    if "instagram.com" in url:
        try:
            api_url = f"https://apis.davidcyriltech.my.id/instagram?url={url}"
            response = requests.get(api_url, timeout=15).json()
            if response.get("status") == 200 and response.get("download_url"):
                video_url = response["download_url"]
                vid_data = requests.get(video_url, timeout=20)
                if vid_data.status_code == 200:
                    with open('video.mp4', 'wb') as f:
                        f.write(vid_data.content)
                    return 'video.mp4'
        except Exception as e:
            print(f"Instagram API xatosi: {e}")

    # TikTok, YouTube va boshqalar uchun yt-dlp
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'video.mp4',
        'quiet': True,
        'no_warnings': True,
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        if os.path.exists('video.mp4'):
            return 'video.mp4'
    except Exception as e:
        print(f"yt-dlp xatolik: {e}")
        
    return None

# Pastki menyu: Chiroyli va tartibli tugmalar
def get_reply_menu(user_id, lang='uz'):
    builder = ReplyKeyboardBuilder()
    if lang == 'uz':
        builder.button(text="🌐 Tilni o'zgartirish")
        if user_id == ADMIN_ID:
            builder.button(text="📊 Statistika")
    else:
        builder.button(text="🌐 Изменить язык")
        if user_id == ADMIN_ID:
            builder.button(text="📊 Статистика")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

# /start komandasi
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    add_user(message.from_user.id)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🇺🇿 O'zbekcha", callback_data="lang_uz")
    builder.button(text="🇷🇺 Русский", callback_data="lang_ru")
    builder.adjust(2)
    
    await message.answer(
        "👋 **Assalomu alaykum! Botimizga xush kelibsiz.**\n"
        "Iltimos, muloqot tilini tanlang:\n\n"
        "👋 **Здравствуйте! Доброловать.**\n"
        "Пожалуйста, выберите язык:",
        reply_markup=builder.as_markup()
    )

# Tilni saqlash
@dp.callback_query(F.data.startswith("lang_"))
async def set_language(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    cursor.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))
    conn.commit()
    
    if lang == "uz":
        text = "✅ **Til muvaffaqiyatli o'zgartirildi!**\n\n📥 Menga TikTok, Instagram yoki YouTube havolasini yuboring:"
    else:
        text = "✅ **Язык успешно изменен!**\n\n📥 Отправьте мне ссылку на TikTok, Instagram или YouTube:"

    await callback.message.answer(text, reply_markup=get_reply_menu(user_id, lang))
    try:
        await callback.message.delete()
    except Exception:
        pass

# Pastdagi tilni o'zgartirish tugmasi
@dp.message(F.text.in_(["🌐 Tilni o'zgartirish", "🌐 Изменить язык"]))
async def change_lang_menu(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="🇺🇿 O'zbekcha", callback_data="lang_uz")
    builder.button(text="🇷🇺 Русский", callback_data="lang_ru")
    builder.adjust(2)
    
    await message.answer(
        "Iltimos, tilni tanlang:\nПожалуйста, выберите язык:",
        reply_markup=builder.as_markup()
    )

# Statistika (admin uchun)
@dp.message(F.text.in_(["📊 Statistika", "📊 Статистика"]))
async def stats_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    await message.answer(f"📊 **Bot statistikasi:**\n\n👥 Jami foydalanuvchilar: {total_users} ta")

# Havolalarni qabul qilish va video yuklash
@dp.message(F.text.startswith("http"))
async def process_download(message: types.Message):
    user_id = message.from_user.id
    add_user(user_id)
    url = message.text.strip()
    
    cursor.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    lang = res[0] if res else 'uz'
    
    wait_text = "⏳ **Video yuklab olinmoqda, biroz kuting...**" if lang == 'uz' else "⏳ **Видео загружается, подождите...**"
    sent_msg = await message.answer(wait_text)
    
    loop = asyncio.get_running_loop()
    file_path = await loop.run_in_executor(None, download_video, url)
    
    if file_path and os.path.exists(file_path):
        try:
            await message.answer_video(types.FSInputFile(file_path))
            await sent_msg.delete()
        except Exception as e:
            await message.answer(f"❌ Xatolik: {e}")
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
    else:
        err_link = "❌ Kechirasiz, bu videoni yuklab bo'lmadi." if lang == 'uz' else "❌ Не удалось скачать видео."
        await message.answer(err_link)
        await sent_msg.delete()

# Veb server (Render uchun)
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
