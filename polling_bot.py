from telegram.ext import Updater, MessageHandler, Filters
import json
import subprocess
import logging
import os

with open('api_keys.json', 'r') as f:
    api_keys = json.load(f)

# Вставь токен своего бота
BOT_TOKEN = api_keys['bot_token']

# Путь к вызываемому скрипту
SCRIPT_PATH = "/create_group.py"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_channel_post(update, context):
    post = update.channel_post
    text = post.text or ""

    logger.info(f"Новый пост в канале: {text[:50]}")

    try:
        result = subprocess.run(
            ["python3", SCRIPT_PATH, text],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        logger.info(f"Результат запуска скрипта:\n{result.stdout}")
    except Exception as e:
        logger.error(f"Ошибка при запуске скрипта: {e}")

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(MessageHandler(Filters.update.channel_posts, handle_channel_post))

    logger.info("Бот запущен, ожидание новых постов в канале...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()