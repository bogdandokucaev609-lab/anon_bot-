import asyncio
import logging
import aiosqlite
import keep_alive
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

# --- НАСТРОЙКИ ---
BOT_TOKEN = "9199104364:AAER0g6UHIjBv_aPUIxPJoth6V6EtLVr6IE" # Вставь свой токен
ADMIN_ID = 6835078005 # Твой ID

logging.basicConfig(level=logging.INFO)

# --- БАЗА ДАННЫХ ---
async def init_db():
    async with aiosqlite.connect("bot_database.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                nickname TEXT,
                interests TEXT,
                avatar_file_id TEXT,
                rating_sum INTEGER DEFAULT 0,
                rating_count INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS likes (
                from_id INTEGER,
                to_id INTEGER,
                PRIMARY KEY (from_id, to_id)
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
        try:
            await db.execute("ALTER TABLE users ADD COLUMN avatar_file_id TEXT")
            await db.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0")
        except:
            pass
        await db.commit()

# --- СОСТОЯНИЯ (FSM) ---
class UserStates(StatesGroup):
    waiting_for_nickname = State()
    waiting_for_interests = State()
    waiting_for_new_nickname = State()
    waiting_for_new_interests = State()
    waiting_for_avatar = State()
    waiting_for_complaint_reason = State()
    waiting_for_ban_id = State()

# --- ОЧЕРЕДЬ И ЧАТЫ ---
waiting_users = []
active_chats = {}

# --- КЛАВИАТУРЫ ---
def get_main_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="👤 Мой профиль"), KeyboardButton(text="🔍 Найти собеседника"))
    builder.row(KeyboardButton(text="⚙️ Настройки"))
    return builder.as_markup(resize_keyboard=True)

def get_settings_menu():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✏️ Изменить ник", callback_data="set_nick"))
    builder.row(InlineKeyboardButton(text="📝 Изменить интересы", callback_data="set_interests"))
    builder.row(InlineKeyboardButton(text="🖼 Поставить аватарку", callback_data="set_avatar"))
    builder.row(InlineKeyboardButton(text="⭐ Мой рейтинг", callback_data="show_my_rating"))
    return builder.as_markup()

def get_admin_menu():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"))
    builder.row(InlineKeyboardButton(text="⚠️ Жалобы", callback_data="admin_complaints"))
    builder.row(InlineKeyboardButton(text="🚫 Забанить по ID", callback_data="admin_ban_start"))
    return builder.as_markup()

def get_chat_menu():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⏭ Следующий", callback_data="next_partner"))
    builder.row(InlineKeyboardButton(text="🚨 Пожаловаться", callback_data="complaint_start"))
    builder.row(InlineKeyboardButton(text="❌ Завершить чат", callback_data="end_chat"))
    return builder.as_markup()

def get_rating_menu(partner_id):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❤️ Симпатия", callback_data=f"like_{partner_id}"))
    builder.row(InlineKeyboardButton(text="👎 Пропустить", callback_data="skip_rate"))
    return builder.as_markup()

# --- ИНИЦИАЛИЗАЦИЯ ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==========================================
# ОБРАБОТЧИКИ КОМАНД И МЕНЮ
# ==========================================

@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    async with aiosqlite.connect("bot_database.db") as db:
        async with db.execute("SELECT nickname, is_banned FROM users WHERE user_id = ?", (uid,)) as cursor:
            user = await cursor.fetchone()
    if user and user[1] == 1:
        await message.answer("🚫 Вы заблокированы за нарушение правил.")
        return
    if user and user[0]:
        await message.answer(f"С возвращением, {user[0]}!", reply_markup=get_main_menu())
    else:
        await message.answer("Привет! Давай знакомиться анонимно.\nКак тебя называть? (придумай ник)", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(UserStates.waiting_for_nickname)

@dp.message(UserStates.waiting_for_nickname)
async def process_nickname(message: types.Message, state: FSMContext):
    await state.update_data(nickname=message.text)
    await message.answer(f"Приятно познакомиться, {message.text}!\nЧто тебе интересно? (кино, музыка, игры...)")
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
    await message.answer(f"Отлично, {nickname}! Профиль создан. Жми '🔍 Найти собеседника'!", reply_markup=get_main_menu())
    await state.clear()

@dp.message(F.text == "👤 Мой профиль")
async def show_profile(message: types.Message):
    async with aiosqlite.connect("bot_database.db") as db:
        async with db.execute("SELECT nickname, interests, avatar_file_id FROM users WHERE user_id = ?", (message.from_user.id,)) as cursor:
            user = await cursor.fetchone()
    if user:
        text = f"👤 **Твой профиль:**\n\nНик: {user[0]}\nИнтересы: {user[1]}"
        if user[2]:
            await message.answer_photo(user[2], caption=text)
        else:
            await message.answer(text + "\n\n(Аватарка не установлена)")
    else:
        await message.answer("Профиль не найден. Напиши /start")

@dp.message(F.text == "⚙️ Настройки")
async def show_settings(message: types.Message):
    await message.answer("⚙️ **Настройки профиля**\nВыбери, что хочешь изменить:", reply_markup=get_settings_menu())

@dp.callback_query(F.data == "set_nick")
async def ask_new_nick(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Напиши свой новый ник:")
    await state.set_state(UserStates.waiting_for_new_nickname)
    await callback.answer()

@dp.message(UserStates.waiting_for_new_nickname)
async def save_new_nick(message: types.Message, state: FSMContext):
    async with aiosqlite.connect("bot_database.db") as db:
        await db.execute("UPDATE users SET nickname = ? WHERE user_id = ?", (message.text, message.from_user.id))
        await db.commit()
    await message.answer(f"✅ Ник изменен на {message.text}!", reply_markup=get_main_menu())
    await state.clear()

@dp.callback_query(F.data == "set_interests")
async def ask_new_interests(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Напиши свои новые интересы:")
    await state.set_state(UserStates.waiting_for_new_interests)
    await callback.answer()

@dp.message(UserStates.waiting_for_new_interests)
async def save_new_interests(message: types.Message, state: FSMContext):
    async with aiosqlite.connect("bot_database.db") as db:
        await db.execute("UPDATE users SET interests = ? WHERE user_id = ?", (message.text, message.from_user.id))
        await db.commit()
    await message.answer("✅ Интересы обновлены!", reply_markup=get_main_menu())
    await state.clear()

@dp.callback_query(F.data == "set_avatar")
async def ask_avatar(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Отправь мне фото, которое хочешь поставить на аватарку:")
    await state.set_state(UserStates.waiting_for_avatar)
    await callback.answer()

@dp.message(UserStates.waiting_for_avatar, F.photo)
async def save_avatar(message: types.Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    async with aiosqlite.connect("bot_database.db") as db:
        await db.execute("UPDATE users SET avatar_file_id = ? WHERE user_id = ?", (file_id, message.from_user.id))
        await db.commit()
    await message.answer_photo(file_id, caption="✅ Аватарка установлена!", reply_markup=get_main_menu())
    await state.clear()

@dp.callback_query(F.data == "show_my_rating")
async def show_rating_callback(callback: CallbackQuery):
    async with aiosqlite.connect("bot_database.db") as db:
        async with db.execute("SELECT rating_sum, rating_count FROM users WHERE user_id = ?", (callback.from_user.id,)) as cursor:
            user = await cursor.fetchone()
    if user and user[1] > 0:
        avg_rating = round(user[0] / user[1], 1)
        await callback.message.answer(f"⭐ **Твой рейтинг:** {avg_rating} из 5\n📊 Оценок: {user[1]}")
    else:
        await callback.message.answer("У тебя пока нет оценок. Пообщайся с кем-нибудь!")
    await callback.answer()

# --- ПОИСК ---
async def start_search(user_id, message_obj):
    if user_id in active_chats:
        await message_obj.answer("Ты уже в чате! Заверши его, чтобы искать нового.")
        return
    if user_id in waiting_users:
        await message_obj.answer("🔍 Уже ищу... подожди.")
        return
    waiting_users.append(user_id)
    if len(waiting_users) >= 2:
        user1 = waiting_users.pop(0)
        user2 = waiting_users.pop(0)
        active_chats[user1] = user2
        active_chats[user2] = user1
        text = "✅ **Собеседник найден!**\nОбщайтесь анонимно. Можете кидать фото, стикеры и текст.\n\nКогда надоест, нажмите 'Следующий' или 'Завершить'."
        try:
            await bot.send_message(user1, text, reply_markup=get_chat_menu())
            await bot.send_message(user2, text, reply_markup=get_chat_menu())
        except:
            pass
    else:
        await message_obj.answer("🔍 Ищу собеседника... Как только кто-то появится, я вас соединю.")

@dp.message(F.text == "🔍 Найти собеседника")
async def find_partner_btn(message: types.Message):
    await start_search(message.from_user.id, message)

# --- ЗАВЕРШЕНИЕ ЧАТА ---
async def end_current_chat(uid):
    if uid in active_chats:
        partner = active_chats[uid]
        del active_chats[uid]
        if partner in active_chats:
            del active_chats[partner]
        return partner
    return None

@dp.callback_query(F.data == "end_chat")
async def end_chat_callback(callback: CallbackQuery):
    partner = await end_current_chat(callback.from_user.id)
    if partner:
        await callback.message.edit_text("Чат завершен. Оцените собеседника:", reply_markup=get_rating_menu(partner))
        try:
            await bot.send_message(partner, "Собеседник завершил чат. Оцените общение:", reply_markup=get_rating_menu(callback.from_user.id))
        except:
            pass
    else:
        await callback.message.edit_text("Ты не был в чате.")
    await callback.answer()

@dp.callback_query(F.data == "next_partner")
async def next_partner_callback(callback: CallbackQuery):
    partner = await end_current_chat(callback.from_user.id)
    if partner:
        try:
            await bot.send_message(partner, "Собеседник переключился на нового. Оцените общение:", reply_markup=get_rating_menu(callback.from_user.id))
        except:
            pass
    await callback.message.edit_text("⏭ Ищем нового собеседника...")
    await start_search(callback.from_user.id, callback.message)
    await callback.answer()

@dp.callback_query(F.data == "skip_rate")
async def skip_rate_callback(callback: CallbackQuery):
    await callback.message.edit_text("Жми '🔍 Найти собеседника' в меню!")
    await callback.answer()

# --- СИМПАТИИ ---
@dp.callback_query(F.data.startswith("like_"))
async def like_partner_callback(callback: CallbackQuery):
    partner_id = int(callback.data.split("_")[1])
    uid = callback.from_user.id
    async with aiosqlite.connect("bot_database.db") as db:
        await db.execute("INSERT OR IGNORE INTO likes (from_id, to_id) VALUES (?, ?)", (uid, partner_id))
        await db.commit()
        async with db.execute("SELECT 1 FROM likes WHERE from_id = ? AND to_id = ?", (partner_id, uid)) as cursor:
            if await cursor.fetchone():
                await callback.message.edit_text("🎉 **Взаимная симпатия!** Вы понравились друг другу. Вот твой контакт для связи:")
                try:
                    await bot.send_message(partner_id, f"🎉 **Взаимная симпатия!** Вы понравились друг другу. Твой собеседник: @{callback.from_user.username or 'скрыт'}")
                except:
                    pass
                my_username = callback.from_user.username or "скрыт"
                await bot.send_message(partner_id, f"Его юзернейм: @{my_username}")
                return
    await callback.message.edit_text("❤️ Ты поставил симпатию! Если собеседник ответит взаимностью, я вас познакомлю.")
    await callback.answer()

# --- ЖАЛОБЫ ---
@dp.callback_query(F.data == "complaint_start")
async def start_complaint(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in active_chats:
        await callback.answer("Ты не в чате!", show_alert=True)
        return
    await callback.message.answer("🚨 Напиши причину жалобы:")
    await state.set_state(UserStates.waiting_for_complaint_reason)
    await callback.answer()

@dp.message(UserStates.waiting_for_complaint_reason)
async def process_complaint(message: types.Message, state: FSMContext):
    partner_id = active_chats.get(message.from_user.id, 0)
    async with aiosqlite.connect("bot_database.db") as db:
        await db.execute("INSERT INTO complaints (from_user_id, against_user_id, reason) VALUES (?, ?, ?)",
                         (message.from_user.id, partner_id, message.text))
        await db.commit()
    await message.answer("✅ Жалоба отправлена администратору.", reply_markup=get_chat_menu())
    await state.clear()


# ==========================================
# ⚠️ АДМИН ПАНЕЛЬ (ДОЛЖНА БЫТЬ ВЫШЕ ПЕРЕСЫЛКИ!) ⚠️
# ==========================================
@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id != ADMIN_ID: 
        return
    await message.answer("🛡 **Админ-панель**", reply_markup=get_admin_menu())

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    async with aiosqlite.connect("bot_database.db") as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            users_count = (await cursor.fetchone())[0]
    await callback.message.edit_text(f"📊 Пользователей: {users_count}", reply_markup=get_admin_menu())
    await callback.answer()

@dp.callback_query(F.data == "admin_complaints")
async def admin_complaints(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    async with aiosqlite.connect("bot_database.db") as db:
        async with db.execute("SELECT from_user_id, against_user_id, reason FROM complaints ORDER BY id DESC LIMIT 5") as cursor:
            complaints = await cursor.fetchall()
    if not complaints:
        text = "Жалоб нет."
    else:
        text = "⚠️ **Последние жалобы:**\n\n"
        for c in complaints:
            text += f"От: {c[0]} | На: {c[1]}\nПричина: {c[2]}\n\n"
    await callback.message.edit_text(text, reply_markup=get_admin_menu())
    await callback.answer()

@dp.callback_query(F.data == "admin_ban_start")
async def admin_ban_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await callback.message.answer("Напиши ID пользователя, которого нужно забанить:")
    await state.set_state(UserStates.waiting_for_ban_id)
    await callback.answer()

@dp.message(UserStates.waiting_for_ban_id)
async def process_ban(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    try:
        ban_id = int(message.text)
        async with aiosqlite.connect("bot_database.db") as db:
            await db.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (ban_id,))
            await db.commit()
        await message.answer(f"🚫 Пользователь {ban_id} забанен.")
    except:
        await message.answer("Ошибка: ID должен быть числом.")
    await state.clear()


# ==========================================
# ПЕРЕСЫЛКА СООБЩЕНИЙ (ДОЛЖНА БЫТЬ В САМОМ КОНЦЕ!)
# ==========================================
@dp.message()
async def forward_message(message: types.Message):
    uid = message.from_user.id
    
    # 🔥 ВАЖНО: Пропускаем команды, чтобы они не застревали в пересылке
    if message.text and message.text.startswith('/'):
        return

    if uid in active_chats:
        partner = active_chats[uid]
        try:
            await bot.copy_message(chat_id=partner, from_chat_id=uid, message_id=message.message_id)
        except Exception:
            await message.answer("Не удалось отправить. Собеседник заблокировал бота.")
    else:
        if message.text not in ["👤 Мой профиль", "🔍 Найти собеседника", "⚙️ Настройки"]:
            await message.answer("Ты не в чате. Нажми '🔍 Найти собеседника' чтобы начать общение.")

# --- ЗАПУСК ---
async def main():
    keep_alive.keep_alive()
    await init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
