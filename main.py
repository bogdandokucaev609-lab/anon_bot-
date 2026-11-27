import telebot
from telebot import types
import keep_alive

TOKEN = '9199104364:AAFKfPe2d5tw3nmlu010CwjfPm9bH8tXlPQ'
ADMIN_ID = 6835078005

bot = telebot.TeleBot(TOKEN)

users = {}
waiting = []
chats = {}

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
    msg = bot.send_message(uid, f"Приятно познакомиться, {message.text}!\n\nЧто тебе интересно?")
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

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"))
    bot.send_message(message.chat.id, "🛡️ Админ-панель", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'admin_stats')
def admin_stats(call):
    if call.from_user.id == ADMIN_ID:
        bot.send_message(call.message.chat.id, f"📊 Пользователей: {len(users)}\nВ чатах: {len(chats)//2}")

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
        bot.send_message(uid, "Ты не в чате. Напиши /find")

keep_alive.keep_alive()
print("Бот запущен...")
bot.infinity_polling()
