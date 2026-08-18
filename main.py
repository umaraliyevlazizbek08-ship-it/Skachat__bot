import os
import asyncio
import sqlite3
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

# Videoni yuklab olish
def download_video(url: str):
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'video.mp4',
        'quiet': True,
        'no_warnings': True,
        'geo_bypass': True,
    }
    try:
        if os.path.exists('video.mp4'):
            os.remove('video.mp4')
            
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        if os.path.exists('video.mp4'):
            return 'video.mp4'
    except Exception as e:
        print(f"Xatolik: {e}")
    return None

# Pastki menyu (Klaviaturadagi tugmalar: Tilni o'zgartirish va Statistika faqat admin uchun)
def get_reply_menu(user_id, lang='uz'):
    builder = ReplyKeyboardBuilder()
    if lang == 'uz':
        builder.button(text="🇺🇿 / 🇷🇺 Tilni o'zgartirish")
        if user_id == ADMIN_ID:
            builder.button(text="📊 Statistika")
    else:
        builder.button(text="🇺🇿 / 🇷🇺 Изменить язык")
        if user_id == ADMIN_ID:
            builder.button(text="📊 Статистика")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

# /start komandasi
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    add_user(user_id)
    
    cursor.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    lang = res[0] if res else 'uz'
    
    if lang == 'uz':
        text = "Salom! Botimizga xush kelibsiz. Menga TikTok yoki YouTube havolasini yuboring:"
    else:
        text = "Привет! Добро пожаловать. Отправьте мне ссылку на TikTok или YouTube:"
        
    await message.answer(text, reply_markup=get_reply_menu(user_id, lang))

# Pastdagi "Tilni o'zgartirish" tugmasi bosilganda
@dp.message(F.text.in_(["🇺🇿 / 🇷🇺 Tilni o'zgartirish", "🇺🇿 / 🇷🇺 Изменить язык"]))
async def change_lang_handler(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="🇺🇿 O'zbekcha", callback_data="setlang_uz")
    builder.button(text="🇷🇺 Русский", callback_data="setlang_ru")
    builder.adjust(2)
    
    await message.answer("Iltimos, tilni tanlang:\nПожалуйста, выберите язык:", reply_markup=builder.as_markup())

# Inline orqali tilni tanlab saqlash
@dp.callback_query(F.data.startswith("setlang_"))
async def save_language(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    cursor.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))
    conn.commit()
    
    if lang == "uz":
        text = "✅ Til O'zbek tiliga o'zgartirildi!"
    else:
        text = "✅ Язык изменен на Русский!"
        
    await callback.message.answer(text, reply_markup=get_reply_menu(user_id, lang))
    await callback.message.delete()

# Pastdagi "Statistika" tugmasi bosilganda (faqat adminga)
@dp.message(F.text.in_(["📊 Statistika", "📊 Статистика"]))
async def stats_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
        
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    await message.answer(f"📊 **Bot statistikasi:**\n\nJami foydalanuvchilar: {total_users} ta")

# Havolalarni qabul qilish va video yuklash
@dp.message(F.text.startswith("http"))
async def process_download(message: types.Message):
    user_id = message.from_user.id
    add_user(user_id)
    url = message.text.strip()
    
    cursor.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    lang = res[0] if res else 'uz'
    
    wait_text = "⏳ Video yuklab olinmoqda, biroz kuting..." if lang == 'uz' else "⏳ Видео загружается, подождите..."
    sent_msg = await message.answer(wait_text)
    
    loop = asyncio.get_running_loop()
    file_path = await loop.run_in_executor(None, download_video, url)
    
    if file_path and os.path.exists(file_path):
        try:
            await message.answer_video(types.FSInputFile(file_path))
            await sent_msg.delete()
        except Exception as e:
            await message.answer(f"Xatolik: {e}")
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
