import asyncio
import logging
import aiosqlite
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

# --- НАСТРОЙКИ ---
BOT_TOKEN = "9199104364:AAHAnW48xTlYhqYZ5GcspN_97JRjANxV7Is"
ADMIN_ID = 6835078005 # Замените на ваш ID (узнать через @userinfobot)

logging.basicConfig(level=logging.INFO)

# --- БАЗА ДАННЫХ ---
async def init_db():
    async with aiosqlite.connect("bot_database.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                nickname TEXT,
                interests TEXT,
                rating_sum INTEGER DEFAULT 0,
                rating_count INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user_id INTEGER,
                against_user_id INTEGER,
                reason TEXT
            )
        """)
        await db.commit()

# --- СОСТОЯНИЯ (FSM) ---
class UserStates(StatesGroup):
    waiting_for_nickname = State()
    waiting_for_interests = State()
    waiting_for_complaint_reason = State()

# --- КЛАВИАТУРЫ ---
def get_main_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="👤 Мой профиль"), KeyboardButton(text="⭐ Мой рейтинг"))
    builder.row(KeyboardButton(text="🔍 Найти собеседника"), KeyboardButton(text="⚙️ Настройки"))
    return builder.as_markup(resize_keyboard=True)

def get_admin_menu():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"))
    builder.row(InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users"))
    builder.row(InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast"))
    builder.row(InlineKeyboardButton(text="⚠️ Жалобы", callback_data="admin_complaints"))
    return builder.as_markup()

def get_chat_menu():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🚨 Пожаловаться", callback_data="complaint_start"))
    builder.row(InlineKeyboardButton(text="⭐ Оценить собеседника", callback_data="rate_start"))
    builder.row(InlineKeyboardButton(text="❌ Завершить чат", callback_data="end_chat"))
    return builder.as_markup()

def get_rating_kb(target_id):
    builder = InlineKeyboardBuilder()
    for i in range(1, 6):
        builder.button(text="⭐" * i, callback_data=f"rate_{target_id}_{i}")
    builder.adjust(5)
    return builder.as_markup()

# --- ИНИЦИАЛИЗАЦИЯ ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- ОБРАБОТЧИКИ ---

@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    async with aiosqlite.connect("bot_database.db") as db:
        async with db.execute("SELECT nickname FROM users WHERE user_id = ?", (message.from_user.id,)) as cursor:
            user = await cursor.fetchone()
    
    if user and user[0]:
        await message.answer(f"С возвращением, {user[0]}!", reply_markup=get_main_menu())
    else:
        await message.answer("Привет! Давай знакомиться анонимно.\nКак тебя называть? (придумай ник)", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(UserStates.waiting_for_nickname)

@dp.message(UserStates.waiting_for_nickname)
async def process_nickname(message: types.Message, state: FSMContext):
    await state.update_data(nickname=message.text)
    await message.answer(f"Приятно познакомиться, {message.text}!\nЧто тебе интересно? (Напиши через запятую, например: музыка, кино, спорт)")
    await state.set_state(UserStates.waiting_for_interests)

@dp.message(UserStates.waiting_for_interests)
async def process_interests(message: types.Message, state: FSMContext):
    data = await state.get_data()
    nickname = data.get('nickname')
    
    async with aiosqlite.connect("bot_database.db") as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (user_id, nickname, interests) VALUES (?, ?, ?)",
            (message.from_user.id, nickname, message.text)
        )
        await db.commit()
    
    await message.answer(f"Отлично, {nickname}! Твои интересы сохранены. Теперь я не буду спрашивать их каждый раз.\n\nИспользуй меню ниже для навигации.", reply_markup=get_main_menu())
    await state.clear()

# --- ПРОФИЛЬ И РЕЙТИНГ ---
@dp.message(F.text == "👤 Мой профиль")
async def show_profile(message: types.Message):
    async with aiosqlite.connect("bot_database.db") as db:
        async with db.execute("SELECT nickname, interests FROM users WHERE user_id = ?", (message.from_user.id,)) as cursor:
            user = await cursor.fetchone()
    
    if user:
        await message.answer(f"👤 **Твой профиль:**\n\nНик: {user[0]}\nИнтересы: {user[1]}")
    else:
        await message.answer("Профиль не найден. Напиши /start")

@dp.message(F.text == "⭐ Мой рейтинг")
async def show_my_rating(message: types.Message):
    async with aiosqlite.connect("bot_database.db") as db:
        async with db.execute("SELECT rating_sum, rating_count FROM users WHERE user_id = ?", (message.from_user.id,)) as cursor:
            user = await cursor.fetchone()
    
    if user and user[1] > 0:
        avg_rating = round(user[0] / user[1], 1)
        await message.answer(f"⭐ **Твой рейтинг:** {avg_rating} из 5\n📊 Основан на {user[1]} оценках.")
    else:
        await message.answer("У тебя пока нет оценок от других пользователей.")

# --- АДМИН ПАНЕЛЬ ---
@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет доступа к этой команде.")
        return
    
    await message.answer("🛡 **Админ-панель**\nВыбери действие:", reply_markup=get_admin_menu())

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    async with aiosqlite.connect("bot_database.db") as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            users_count = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM complaints") as cursor:
            complaints_count = (await cursor.fetchone())[0]
    
    await callback.message.edit_text(f"📊 **Статистика:**\n\n👥 Пользователей: {users_count}\n⚠️ Жалоб: {complaints_count}", reply_markup=get_admin_menu())
    await callback.answer()

@dp.callback_query(F.data == "admin_complaints")
async def admin_complaints(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    async with aiosqlite.connect("bot_database.db") as db:
        async with db.execute("SELECT from_user_id, against_user_id, reason FROM complaints ORDER BY id DESC LIMIT 10") as cursor:
            complaints = await cursor.fetchall()
    
    if not complaints:
        text = "Жалоб пока нет."
    else:
        text = "⚠️ **Последние жалобы:**\n\n"
        for c in complaints:
            text += f"От: {c[0]} | На: {c[1]}\nПричина: {c[2]}\n\n"
            
    await callback.message.edit_text(text, reply_markup=get_admin_menu())
    await callback.answer()

# --- ЛОГИКА ЧАТА (Жалоба и Рейтинг) ---
# Заглушка словаря для связи собеседников (в реальном боте вы заполняете его при поиске)
active_chats = {} 

@dp.message(F.text == "🔍 Найти собеседника")
async def find_partner(message: types.Message):
    # Здесь должна быть ваша логика поиска. Пока для теста:
    # Допустим, мы нашли собеседника с ID 111222333
    dummy_partner_id = 111222333 
    active_chats[message.from_user.id] = dummy_partner_id
    
    await message.answer("Вы в чате с анонимом! (Тестовый режим)\nНажмите на кнопки ниже, чтобы взаимодействовать:", 
                         reply_markup=get_chat_menu())

@dp.callback_query(F.data == "complaint_start")
async def start_complaint(callback: CallbackQuery, state: FSMContext):
    partner_id = active_chats.get(callback.from_user.id)
    if not partner_id:
        await callback.answer("Вы не в чате!", show_alert=True)
        return
        
    await callback.message.answer("🚨 Напиши причину жалобы на собеседника (текстом):")
    await state.set_state(UserStates.waiting_for_complaint_reason)
    await callback.answer()

@dp.message(UserStates.waiting_for_complaint_reason)
async def process_complaint(message: types.Message, state: FSMContext):
    partner_id = active_chats.get(message.from_user.id)
    if not partner_id:
        await message.answer("Ошибка: вы не в чате.")
        await state.clear()
        return
    
    async with aiosqlite.connect("bot_database.db") as db:
        await db.execute("INSERT INTO complaints (from_user_id, against_user_id, reason) VALUES (?, ?, ?)",
                         (message.from_user.id, partner_id, message.text))
        await db.commit()
    
    await message.answer("✅ Жалоба отправлена администратору. Спасибо!", reply_markup=get_chat_menu())
    await state.clear()
    
    # Уведомление админу
    await bot.send_message(ADMIN_ID, f"⚠️ **Новая жалоба!**\nОт: {message.from_user.id}\nНа: {partner_id}\nПричина: {message.text}")

@dp.callback_query(F.data == "rate_start")
async def start_rating(callback: CallbackQuery):
    partner_id = active_chats.get(callback.from_user.id)
    if not partner_id:
        await callback.answer("Вы не в чате!", show_alert=True)
        return
        
    await callback.message.answer("Оцени своего собеседника:", reply_markup=get_rating_kb(partner_id))
    await callback.answer()

@dp.callback_query(F.data.startswith("rate_"))
async def process_rating(callback: CallbackQuery):
    _, target_id, rating = callback.data.split("_")
    rating = int(rating)
    target_id = int(target_id)
    
    async with aiosqlite.connect("bot_database.db") as db:
        await db.execute("UPDATE users SET rating_sum = rating_sum + ?, rating_count = rating_count + 1 WHERE user_id = ?", (rating, target_id))
        await db.commit()
    
    await callback.message.edit_text(f"✅ Ты поставил оценку {rating} звезд(ы). Спасибо!")
    await callback.answer()

# --- ЗАПУСК ---
async def main():
    await init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
