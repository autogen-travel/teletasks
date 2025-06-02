import json
import logging
import subprocess
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# 🔧 Загрузка конфигурации
with open("api_keys.json", "r") as f:
    config = json.load(f)

BOT_TOKEN = config["bot_token"]
SCRIPT_PATH = "/root/teletasks/create_group.py"  # укажи путь к своему скрипту

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# 📩 Обработка новых постов в каналах
async def handle_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    post = update.channel_post
    text = post.text or ""

    logging.info(f"📬 Новый пост в канале: {text[:60]}")

    try:
        result = subprocess.run(
            ["python3", SCRIPT_PATH, text],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        logging.info(f"✅ Скрипт выполнен:\n{result.stdout}")
    except Exception as e:
        logging.error(f"❌ Ошибка при запуске скрипта: {e}")

# 🚀 Запуск бота
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST, handle_channel_post))

    logging.info("🤖 Бот запущен (polling)...")
    app.run_polling()