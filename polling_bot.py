import json
import logging
import asyncio
import re
import subprocess
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Загрузка токена из api_keys.json
with open('api_keys.json', 'r') as f:
    keys = json.load(f)
BOT_TOKEN = keys['bot_token']

async def handle_new_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat_id = message.chat_id

    # Получаем текст из message.text или из message.caption (для медиа)
    task_title = (message.text or message.caption or "Без названия").strip()

    logging.info(f"📬 Новый пост в канале: {task_title}")

    stop_animation = asyncio.Event()

    async def animate_group_creation():
        dots = ["", ".", "..", "..."]
        i = 0
        while not stop_animation.is_set():
            try:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message.message_id,
                    text=f"Создание группы{dots[i % 4]}"
                )
            except Exception as e:
                logging.warning(f"⚠️ Не удалось обновить сообщение: {e}")
            await asyncio.sleep(0.5)
            i += 1

    # Запускаем анимацию
    animation_task = asyncio.create_task(animate_group_creation())

    try:
        # Запускаем скрипт создания группы, передавая название группы
        result = subprocess.run(
            ["python3", "create_group.py", "--group", task_title],
            capture_output=True,
            text=True,
            check=True
        )
        logging.info(f"✅ Скрипт выполнен:\n{result.stdout}")
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Ошибка при выполнении скрипта: {e.stderr}")
        stop_animation.set()
        await animation_task
        return

    # Останавливаем анимацию
    stop_animation.set()
    await animation_task

    # Ищем ссылку на группу в выводе скрипта
    link_match = re.search(r'(https://t\.me/\S+)', result.stdout)
    if link_match:
        invite_link = link_match.group(1)
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message.message_id,
                text=f"{task_title}\n\n📎 Ссылка на группу: {invite_link}"
            )
        except Exception as e:
            logging.warning(f"⚠️ Не удалось отредактировать сообщение с ссылкой: {e}")
    else:
        logging.warning("⚠️ Ссылка на группу не найдена в выводе скрипта.")

async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Фильтр сообщений — только новые посты в канале (с текстом или caption)
    post_filter = filters.UpdateType.CHANNEL_POST & (filters.TEXT | filters.Caption())

    application.add_handler(MessageHandler(post_filter, handle_new_post))

    logging.info("🤖 Бот запущен. Ожидание новых постов...")
    await application.run_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())