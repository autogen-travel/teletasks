import json
import logging
import asyncio
import subprocess
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Читаем токен из api_keys.json
with open('api_keys.json', 'r') as f:
    keys = json.load(f)
BOT_TOKEN = keys['bot_token']


async def animate_edit(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int):
    """Анимация с циклом 'создание группы...', редактирование сообщения с интервалом"""
    states = [
        "создание группы",
        "создание группы.",
        "создание группы..",
        "создание группы...",
    ]
    for _ in range(3):  # повторим анимацию 3 раза
        for state in states:
            try:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=state
                )
                await asyncio.sleep(0.7)
            except Exception as e:
                logging.warning(f"Ошибка при редактировании сообщения анимации: {e}")
                return


async def handle_new_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.channel_post
    if not message or not message.text:
        logging.info("Пост без текста, пропускаем")
        return

    post_text = message.text.strip()
    chat_id = message.chat.id
    message_id = message.message_id

    logging.info(f"📬 Новый пост в канале: {post_text}")

    # Запускаем анимацию в фоне, редактируя тот же пост
    animation_task = asyncio.create_task(animate_edit(context, chat_id, message_id))

    # Запускаем create_group.py как subprocess
    try:
        # Передаем заголовок группы - например, тот же, что и пост
        process = await asyncio.create_subprocess_exec(
            'python3', 'create_group.py', '--group', post_text,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        animation_task.cancel()  # Прекращаем анимацию после завершения скрипта

        if process.returncode != 0:
            logging.error(f"create_group.py завершился с ошибкой:\n{stderr.decode()}")
            # Восстанавливаем исходный текст поста
            await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=post_text)
            return

        output = stdout.decode()
        logging.info(f"✅ Скрипт выполнен:\n{output}")

        # Вытаскиваем ссылку на группу из вывода (пример)
        import re
        link_match = re.search(r'(https?://t\.me/[\w\+\-]+)', output)
        if not link_match:
            logging.warning("⚠️ Ссылка на группу не найдена в выводе скрипта.")
            # Просто восстанавливаем исходный пост
            await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=post_text)
            return

        invite_link = link_match.group(1)

        # Редактируем пост с добавлением ссылки
        new_text = f"{post_text}\n\n👉 [Ссылка на группу]({invite_link})"
        await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=new_text, parse_mode="Markdown")

    except asyncio.CancelledError:
        logging.info("Анимация отменена.")
    except Exception as e:
        logging.error(f"Ошибка в обработчике нового поста: {e}")
        # Восстанавливаем исходный пост
        await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=post_text)


if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Фильтр: новые посты в канале с текстом
    post_filter = filters.UpdateType.CHANNEL_POST & filters.TEXT

    application.add_handler(MessageHandler(post_filter, handle_new_post))

    logging.info("🤖 Бот запущен. Ожидание новых постов...")
    application.run_polling()