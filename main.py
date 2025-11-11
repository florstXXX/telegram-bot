import sqlite3
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# === НАСТРОЙКИ ===
TOKEN = "8261991852:AAGerWdoke_aiKGQYeAsduJfowGlVxpRs4Q"
CHANNEL_ID = "-1003105686811"

# === СОЗДАНИЕ БАЗЫ ДАННЫХ ===
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    login TEXT,
    password TEXT
)
""")
conn.commit()

# === СОСТОЯНИЯ ===
user_states = {}

# === /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["🟢 Войти / Зарегистрироваться", "📄 Профиль"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "👋 Привет!\n\n"
        "Этот бот поможет тебе отправить просьбу ментору.\n"
        "Выбери действие ниже 👇",
        reply_markup=reply_markup
    )

# === Вход / Регистрация ===
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_states[user_id] = "waiting_for_login"
    await update.message.reply_text(
        "Введите своё имя, фамилию, класс:\n\n📘 *Пример:*\n`Анур_Есенгельды_9С`",
        parse_mode="Markdown"
    )

# === Профиль ===
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cursor.execute("SELECT login, password FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    if user:
        keyboard = [
            ["✉️ Отправить просьбу"],
            ["🔙 Назад в меню"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            f"👤 Ваш профиль:\n"
            f"Логин: {user[0]}\nПароль: {user[1]}\n\n"
            f"Можете отправить просьбу 👇",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text("⚠️ Вы ещё не вошли. Нажмите '🟢 Войти / Зарегистрироваться'.")

# === Отправка просьбы ===
async def request_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cursor.execute("SELECT login FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    if not user:
        await update.message.reply_text("⚠️ Сначала войдите через '🟢 Войти / Зарегистрироваться'.")
        return

    user_states[user_id] = "waiting_for_request"
    await update.message.reply_text("📝 Напиши свою просьбу (например: 'Нужна помощь с задачей по алгебре'):")

# === Обработка сообщений ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    state = user_states.get(user_id)

    # Обработка кнопок
    if text == "🟢 Войти / Зарегистрироваться":
        await login(update, context)
        return
    elif text == "📄 Профиль":
        await profile(update, context)
        return
    elif text == "✉️ Отправить просьбу":
        await request_message(update, context)
        return
    elif text == "🔙 Назад в меню":
        await start(update, context)
        return

    # Ввод данных
    if state == "waiting_for_login":
        context.user_data["login"] = text
        user_states[user_id] = "waiting_for_password"
        await update.message.reply_text("Теперь введите пароль:")

    elif state == "waiting_for_password":
        login_value = context.user_data.get("login")
        password = text

        cursor.execute("SELECT password FROM users WHERE user_id = ?", (user_id,))
        existing_user = cursor.fetchone()

        if existing_user:
            if existing_user[0] == password:
                await update.message.reply_text("✅ Добро пожаловать обратно!")
            else:
                await update.message.reply_text("❌ Неверный пароль. Попробуй снова.")
                return
        else:
            cursor.execute(
                "INSERT INTO users (user_id, login, password) VALUES (?, ?, ?)",
                (user_id, login_value, password)
            )
            conn.commit()
            await update.message.reply_text(f"✅ Вы успешно зарегистрированы!\nЛогин: {login_value}")

        user_states.pop(user_id, None)
        context.user_data.clear()
        await start(update, context)

    elif state == "waiting_for_request":
        cursor.execute("SELECT login FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        user_states.pop(user_id, None)

        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"📩 *Новая просьба от {user[0]}:*\n\n{text}",
            parse_mode="Markdown"
        )
        await update.message.reply_text("✅ Ваша просьба успешно отправлена!")
        await start(update, context)

    else:
        await update.message.reply_text("Используй кнопки ниже 👇")

# === ЗАПУСК ===
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("login", login))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Бот запущен! Ожидаю сообщения...")
    app.run_polling()

if __name__ == "__main__":
    main()
