import telebot
from telebot import types
import keep_alive  # <-- Важно, чтобы Render видел веб-сервер

# ⚠️ ВСТАВЬ СВОЙ ТОКЕН МЕЖДУ КАВЫЧКАМИ
TOKEN = '9199104364:AAFKfPe2d5tw3nmlu010CwjfPm9bH8tXlPQ'
bot = telebot.TeleBot(TOKEN)

# Хранилища
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
    users[uid] = {"name": message.text}
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
        bot.send_message(user1, "✅ Собеседник найден! Вы общаетесь анонимно.\n/find — искать нового\n/stop — завершить")
        bot.send_message(user2, "✅ Собеседник найден! Вы общаетесь анонимно.\n/find — искать нового\n/stop — завершить")
    else:
        bot.send_message(uid, "🔍 Ищу собеседника... Как только кто-то появится, я вас соединю.")

@bot.message_handler(commands=['stop'])
def stop(message):
    uid = message.from_user.id
    if uid in chats:
        partner = chats[uid]
        del chats[uid]
        if partner in chats:
            del chats[partner]
            bot.send_message(partner, "Собеседник завершил чат. Напиши /find чтобы найти нового.")
        bot.send_message(uid, "Чат завершён. Напиши /find чтобы найти нового.")
    elif uid in waiting:
        waiting.remove(uid)
        bot.send_message(uid, "Поиск отменён.")
    else:
        bot.send_message(uid, "Ты не в чате.")

@bot.message_handler(content_types=['text'])
def forward(message):
    uid = message.from_user.id
    if uid in chats:
        partner = chats[uid]
        try:
            bot.send_message(partner, f"💬 {message.text}")
        except:
            bot.send_message(uid, "Не удалось отправить. Возможно, собеседник заблокировал бота.")
    else:
        bot.send_message(uid, "Ты не в чате. Напиши /find чтобы найти собеседника.")

# Запуск веб-сервера и бота
keep_alive.keep_alive()
print("Бот запущен...")
bot.infinity_polling()
