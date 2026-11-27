import telebot
from telebot import types
import keep_alive

# ⚠️ ВСТАВЬ СВОЙ ТОКЕН
TOKEN = '9199104364:AAFKfPe2d5tw3nmlu010CwjfPm9bH8tXlPQ'
# ⚠️ ВСТАВЬ СВОЙ ID (цифры от @userinfobot)
ADMIN_ID = 6835078005

bot = telebot.TeleBot(TOKEN)

# Хранилища
users = {}          # id: {"name": "...", "interests": "..."}
waiting = []        # очередь ожидания
chats = {}          # id: partner_id

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if uid in users:
        bot.send_message(uid, "Ты уже зарегистрирован. Пиши /find чтобы искать собеседника.")
        return
    msg = bot.send_message(uid, "Привет! Давай знакомиться анонимно.\n\nКак тебя называть? (придумай ник)")
    bot.register_next_step_handler(msg, ask_name)

def ask_name(message):
    uid = message.from_user.id
    users[uid] = {"name": message.text, "id": uid}
    msg = bot.send_message(uid, f"Приятно познакомиться, {message.text}!\n\nЧто тебе интересно? (кино, музыка, игры, спорт — пиши через запятую)")
    bot.register_next_step_handler(msg, ask_interests)

def ask_interests(message):
    uid = message.from_user.id
    users[uid]["interests"] = message.text
    bot.send_message(uid, "Готово! Теперь нажми /find чтобы найти анонимного собеседника.")

@bot.message_handler(commands=['find'])
def find(message):
    uid = message.from_user.id
    if uid not in users:
        bot.send_message(uid, "Сначала напиши /start")
        return
    if uid in chats:
        bot.send_message(uid, "Ты уже в чате. Напиши /stop чтобы выйти.")
        return
    if uid in waiting:
        bot.send_message(uid, "Уже ищу... подожди.")
        return

    waiting.append(uid)
    if len(waiting) >= 2:
        user1 = waiting.pop(0)
        user2 = waiting.pop(0)
        chats[user1] = user2
        chats[user2] = user1
        bot.send_message(user1, "✅ Собеседник найден!\n/find — новый\n/stop — завершить")
        bot.send_message(user2, "✅ Собеседник найден!\n/find — новый\n/stop — завершить")
    else:
        bot.send_message(uid, "🔍 Ищу собеседника...")

@bot.message_handler(commands=['stop'])
def stop(message):
    uid = message.from_user.id
    if uid in chats:
        partner = chats[uid]
        del chats[uid]
        if partner in chats:
            del chats[partner]
            bot.send_message(partner, "Собеседник завершил чат. Напиши /find чтобы найти нового.")
        bot.send_message(uid, "Чат завершён.")
    elif uid in waiting:
        waiting.remove(uid)
        bot.send_message(uid, "Поиск отменён.")

# === АДМИН ПАНЕЛЬ ===
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "У тебя нет доступа к этой команде.")
        return
    
    markup = types.InlineKeyboardMarkup()
    btn_stats = types.InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")
    btn_users = types.InlineKeyboardButton("👥 Пользователи", callback_data="admin_users")
    btn_broadcast = types.InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")
    markup.add(btn_stats, btn_users, btn_broadcast)
    
    bot.send_message(message.chat.id, "🛡️ Админ-панель\nВыбери действие:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def admin_actions(call):
    if call.from_user.id != ADMIN_ID:
        return
    
    if call.data == "admin_stats":
        text = f"📊 Статистика:\n\nВсего пользователей: {len(users)}\nВ чатах сейчас: {len(chats)//2}\nВ поиске: {len(waiting)}"
        bot.send_message(call.message.chat.id, text)
        
    elif call.data == "admin_users":
        if not users:
            bot.send_message(call.message.chat.id, "Пока нет пользователей.")
            return
        text = "👥 Список пользователей:\n\n"
        for uid, info in users.items():
            text += f"ID: {uid} | Ник: {info.get('name')}\n"
        bot.send_message(call.message.chat.id, text[:4000]) # обрезаем если слишком длинно
        
    elif call.data == "admin_broadcast":
        msg = bot.send_message(call.message.chat.id, "Напиши текст для рассылки (он уйдет всем пользователям):")
        bot.register_next_step_handler(msg, do_broadcast)

def do_broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return
    text = message.text
    count = 0
    for uid in users.keys():
        try:
            bot.send_message(uid, f"📢 Сообщение от админа:\n\n{text}")
            count += 1
        except:
            pass
    bot.send_message(ADMIN_ID, f"✅ Рассылка завершена. Отправлено: {count} пользователям.")

# ====================

@bot.message_handler(content_types=['text'])
def forward(message):
    uid = message.from_user.id
    if uid in chats:
        partner = chats[uid]
        try:
            bot.send_message(partner, f"💬 {message.text}")
        except:
            bot.send_message(uid, "Не удалось отправить.")
    else:
        bot.send_message(uid, "Ты не в чате. Напиши /
@bot.message_handler(commands=['menu'])
def show_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Кнопка 1")
    btn2 = types.KeyboardButton("Кнопка 2")
    markup.add(btn1, btn2)
    bot.send_message(message.chat.id, "Меню:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "Кнопка 1")
def btn1_click(message):
    bot.send_message(message.chat.id, "Ты нажал Кнопку 1")                

keep_alive.keep_alive()
print("Бот запущен...")
bot.infinity_polling()
