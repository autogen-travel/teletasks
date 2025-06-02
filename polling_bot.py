import logging
import subprocess
import json
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# Настройка логгирования
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Загрузка токена и пути к скрипту
with open("api_keys.json", "r") as f:
    config = json.load(f)

BOT_TOKEN = config["bot_token"]
SCRIPT_PATH = os.path.abspath("create_group.py")

# Основной хендлер новых постов в канале
async def handle_new_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.channel_post:
        text = update.channel_post.text.strip()
        logging.info(f"📬 Новый пост в канале: {text}")

        try:
            # Запуск скрипта создания группы
            result = subprocess.run(
                ["python3", SCRIPT_PATH, "--group", text],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=60
            )
            logging.info("✅ Скрипт выполнен:\n" + result.stdout)

            # Извлечение ссылки на группу из вывода
            lines = result.stdout.strip().splitlines()
            invite_link = next((line for line in lines if line.startswith("https://t.me/")), None)

            if invite_link:
                # Редактирование поста — добавление ссылки
                original_text = update.channel_post.text
                new_text = f"{original_text}\n\n🔗 [Обсудить задачу]({invite_link})"

                await context.bot.edit_message_text(
                    chat_id=update.channel_post.chat_id,
                    message_id=update.channel_post.message_id,
                    text=new_text,
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
                logging.info("✏️ Пост отредактирован с ссылкой на группу.")
            else:
                logging.warning("⚠️ Ссылка на группу не найдена в выводе скрипта.")

        except subprocess.TimeoutExpired:
            logging.error("⏳ Скрипт превысил лимит времени выполнения.")
        except Exception as e:
            logging.error(f"❌ Ошибка при обработке поста: {e}")

# Инициализация и запуск бота
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST, handle_new_post))
    logging.info("🤖 Бот запущен (polling)...")
    app.run_polling()