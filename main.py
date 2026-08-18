import os
import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from yt_dlp import YoutubeDL
from aiohttp import web

TOKEN = "8821143666:AAHsRDIvy6b1V-0GVH2il03D_NcG1aN2NQY"
ADMIN_ID = 8691162431

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Ma'lumotlar bazasini ulash
conn = sqlite3.connect("bot_users.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, lang TEXT DEFAULT 'uz')")
conn.commit()

# Render uchun veb-server
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

# Til tanlash uchun tugmalar
def get_lang_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🇺🇿 O'zbekcha", callback_data="lang_uz")
    builder.button(text="🇷🇺 Русский", callback_data="lang_ru")
    builder.adjust(2)
    return builder.as_markup()

# Asosiy menyu tugmalari
def get_main_menu(lang, user_id):
    builder = ReplyKeyboardBuilder()
    if lang == "ru":
        builder.button(text="🌐 Сменить язык")
        if user_id == ADMIN_ID:
            builder.button(text="📊 Статистика")
    else:
        builder.button(text="🌐 Tilni o'zgartirish")
        if user_id == ADMIN_ID:
            builder.button(text="📊 Statistika")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

# /start komandasi
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("INSERT OR IGNORE INTO users (user_id, lang) VALUES (?, 'uz')", (user_id,))
    conn.commit()
    await message.answer("Iltimos, tilni tanlang / Пожалуйста, выберите язык:", reply_markup=get_lang_keyboard())

# Tilni o'zgartirish callback
@dp.callback_query(F.data.startswith("lang_"))
async def set_language(call: types.CallbackQuery):
    lang = call.data.split("_")[1]
    user_id = call.from_user.id
    cursor.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))
    conn.commit()
    try:
        await call.message.delete()
    except Exception:
        pass
    msg = "Til muvaffaqiyatli tanlandi! Video havolasini yuboring." if lang == "uz" else "Язык успешно изменен! Отправьте ссылку на видео."
    await call.message.answer(msg, reply_markup=get_main_menu(lang, user_id))

# Menyudan tilni o'zgartirish
@dp.message(F.text.in_(["🌐 Tilni o'zgartirish", "🌐 Сменить язык"]))
async def change_lang(message: types.Message):
    await message.answer("Iltimos, tilni tanlang / Пожалуйста, выберите язык:", reply_markup=get_lang_keyboard())

# Statistika (faqat admin uchun)
@dp.message(Command("stat"))
@dp.message(F.text.in_(["📊 Statistika", "📊 Статистика"]))
async def show_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    await message.answer(f"📊 **Bot statistikasi:**\n\nFoydalanuvchilar soni: **{count}** ta")

# Videolarni yuklab olish funksiyasi (Faqat havolalarni ushlash uchun filtr qo'shildi)
@dp.message(F.text.startswith("http"))
async def download_video(message: types.Message):
    url = message.text.strip()
    user_id = message.from_user.id
    
    cursor.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    lang = row[0] if row else "uz"

    wait_msg = "Video yuklanmoqda, kuting..." if lang == "uz" else "Видео загружается, подождите..."
    status_msg = await message.answer(wait_msg)
    
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'video.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    }
    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        
        if os.path.exists(filename):
            video_file = types.FSInputFile(filename)
            caption = "Video yuklandi! 🚀" if lang == "uz" else "Видео успешно загружено! 🚀"
            await message.answer_video(video=video_file, caption=caption)
            os.remove(filename)
        else:
            await message.answer("Xatolik yuz berdi." if lang == "uz" else "Произошла ошибка.")
    except Exception:
        err_msg = "Kechirasiz, bu videoni yuklab bo'lmadi. Havola ochiq ekanligini tekshiring." if lang == "uz" else "Извините, не удалось скачать видео."
        await message.answer(err_msg)
    finally:
        try:
            await status_msg.delete()
        except Exception:
            pass

async def main():
    await start_web_server()
    print("Bot muvaffaqiyatli ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
