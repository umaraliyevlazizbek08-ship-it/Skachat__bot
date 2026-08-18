import os
import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
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

# Asosiy menyu (Tilni o'zgartirish tugmasi bilan)
def get_main_menu(lang='uz'):
    builder = InlineKeyboardBuilder()
    if lang == 'uz':
        builder.button(text="🇺🇿 / 🇷🇺 Tilni o'zgartirish", callback_data="change_lang")
    else:
        builder.button(text="🇺🇿 / 🇷🇺 Изменить язык", callback_data="change_lang")
    builder.adjust(1)
    return builder.as_markup()

# /start komandasi - Til tanlash chiqadi
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    add_user(message.from_user.id)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🇺🇿 O'zbekcha", callback_data="lang_uz")
    builder.button(text="🇷🇺 Русский", callback_data="lang_ru")
    builder.adjust(2)
    
    await message.answer(
        "Salom! Botimizga xush kelibsiz.\nIltimos, tilni tanlang:\n\n"
        "Привет! Доброловать.\nПожалуйста, выберите язык:",
        reply_markup=builder.as_markup()
    )

# Tilni saqlash va asosiy menyuga o'tish (Statistika faqat adminga ko'rinadi)
@dp.callback_query(F.data.startswith("lang_"))
async def set_language(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    cursor.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))
    conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    if user_id == ADMIN_ID:
        if lang == "uz":
            text = f"✅ Til O'zbek tiliga o'zgartirildi!\n\n📊 Jami foydalanuvchilar: {total_users} ta\nMenga TikTok yoki YouTube havolasini yuboring:"
        else:
            text = f"✅ Язык изменен на Русский!\n\n📊 Всего пользователей: {total_users}\nОтправьте мне ссылку на TikTok или YouTube:"
    else:
        if lang == "uz":
            text = "✅ Til O'zbek tiliga o'zgartirildi!\nMenga TikTok yoki YouTube havolasini yuboring:"
        else:
            text = "✅ Язык изменен на Русский!\nОтправьте мне ссылку на TikTok или YouTube:"

    try:
        await callback.message.edit_text(text, reply_markup=get_main_menu(lang))
    except Exception:
        await callback.message.answer(text, reply_markup=get_main_menu(lang))

# Tilni o'zgartirish tugmasi bosilganda
@dp.callback_query(F.data == "change_lang")
async def change_lang_menu(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="🇺🇿 O'zbekcha", callback_data="lang_uz")
    builder.button(text="🇷🇺 Русский", callback_data="lang_ru")
    builder.adjust(2)
    
    await callback.message.edit_text(
        "Iltimos, tilni tanlang:\nПожалуйста, выберите язык:",
        reply_markup=builder.as_markup()
    )

# Admin uchun /stats buyrug'i
@dp.message(Command("stats"))
async def stats_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("Bu buyruq faqat admin uchun!")
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    await message.answer(f"📊 **Admin statistikasi:**\n\nJami foydalanuvchilar: {total_users} ta")

# Havolalarni qabul qilish va video yuklash
@dp.message(F.text.startswith("http"))
async def process_download(message: types.Message):
    add_user(message.from_user.id)
    url = message.text.strip()
    
    cursor.execute("SELECT lang FROM users WHERE user_id = ?", (message.from_user.id,))
    res = cursor.fetchone()
    lang = res[0] if res else 'uz'
    
    wait_text = "⏳ Video yuklab olinmoqda, biroz kuting..." if lang == 'uz' else "⏳ Видео загружается, подождите..."
    sent_msg = await message.answer(wait_text)
    
    loop = asyncio.get_running_loop()
    file_path = await loop.run_in_executor(None, download_video, url)
    
    if file_path and os.path.exists(file_path):
        try:
            await message.answer_video(types.FSInputFile(file_path), reply_markup=get_main_menu(lang))
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
