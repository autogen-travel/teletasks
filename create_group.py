import json
import asyncio
import logging
import argparse
from telethon import TelegramClient
from telethon.errors import UserPrivacyRestrictedError, UsernameNotOccupiedError
from telethon.tl.functions.contacts import ResolveUsernameRequest
from telethon.tl.functions.channels import CreateChannelRequest, InviteToChannelRequest, EditAdminRequest
from telethon.tl.functions.messages import ExportChatInviteRequest, SendMessageRequest
from telethon.tl.types import ChatAdminRights

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('group_creator.log'),
        logging.StreamHandler()
    ]
)

with open('api_keys.json', 'r') as f:
    api_keys = json.load(f)

api_id = api_keys['api_id']
api_hash = api_keys['api_hash']
phone_number = api_keys['phone_number']
user_username = api_keys['user_username']
bot_username = api_keys['bot_username']
default_group_title = api_keys['group_title']
default_group_about = api_keys['group_about']

client = TelegramClient(phone_number, api_id, api_hash, device_model='iPhone 13 Pro', system_version='4.16.30-vxCUSTOM')


async def group_exists(client, group_title):
    dialogs = await client.get_dialogs()
    return any(dialog.name == group_title for dialog in dialogs)


async def main(group_title_override=None, group_about_override=None, raw_user_list=None, author_username=None, first_post=None):
    await client.start()
    logging.info("✅ Авторизация прошла успешно")

    group_title = group_title_override or default_group_title
    if await group_exists(client, group_title):
        logging.warning(f"⚠️ Группа '{group_title}' уже существует.")
        return

    try:
        user = (await client(ResolveUsernameRequest(user_username))).users[0]
    except UsernameNotOccupiedError:
        logging.error(f"❌ Пользователь @{user_username} не найден.")
        return

    try:
        bot = (await client(ResolveUsernameRequest(bot_username))).users[0]
    except UsernameNotOccupiedError:
        logging.error(f"❌ Бот @{bot_username} не найден.")
        return

    result = await client(CreateChannelRequest(
        title=group_title,
        about=group_about_override or default_group_about,
        megagroup=True
    ))
    channel = result.chats[0]
    logging.info(f"✅ Группа '{group_title}' создана.")

    for participant in [user, bot]:
        try:
            await client(InviteToChannelRequest(channel=channel, users=[participant]))
            logging.info(f"➕ {participant.username} добавлен.")
            await asyncio.sleep(2)
        except Exception as e:
            logging.warning(f"⚠️ Ошибка добавления {participant.username}: {e}")

    try:
        await client(EditAdminRequest(
            channel=channel,
            user_id=bot,
            admin_rights=ChatAdminRights(
                change_info=False,
                post_messages=True,
                edit_messages=True,
                delete_messages=True,
                ban_users=True,
                invite_users=True,
                pin_messages=True,
                add_admins=False,
                manage_call=True,
                anonymous=False,
                manage_topics=True
            ),
            rank='Бот'
        ))
        logging.info(f"🛡 Бот назначен админом.")
    except Exception as e:
        logging.warning(f"⚠️ Не удалось назначить бота админом: {e}")

    # Добавляем автора поста и назначаем админом
    if author_username:
        try:
            author = await client.get_entity(author_username)
            await client(InviteToChannelRequest(channel=channel, users=[author]))
            await asyncio.sleep(2)
            await client(EditAdminRequest(
                channel=channel,
                user_id=author,
                admin_rights=ChatAdminRights(
                    change_info=False,
                    post_messages=True,
                    edit_messages=True,
                    delete_messages=True,
                    ban_users=True,
                    invite_users=True,
                    pin_messages=True,
                    add_admins=False,
                    manage_call=True,
                    anonymous=False,
                    manage_topics=True
                ),
                rank='Автор поста'
            ))
            logging.info(f"👑 Автор @{author_username} назначен администратором.")
        except Exception as e:
            logging.warning(f"⚠️ Не удалось добавить/назначить автора: {e}")

    # Отправка первого сообщения
    if first_post:
        try:
            await client.send_message(channel, message=first_post)
            logging.info("📩 Первое сообщение отправлено в группу.")
        except Exception as e:
            logging.warning(f"⚠️ Ошибка при отправке первого сообщения: {e}")

    # Получение и вывод ссылки
    invite = await client(ExportChatInviteRequest(peer=channel))
    print(invite.link)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Создание Telegram-группы через Telethon')
    parser.add_argument('--group', help='Название создаваемой группы', type=str)
    parser.add_argument('--users', help='Список пользователей через запятую', type=str)
    parser.add_argument('--about', help='Описание группы', type=str)
    parser.add_argument('--author', help='Автор поста (username)', type=str)
    parser.add_argument('--first-post', help='Текст первого сообщения', type=str)
    args = parser.parse_args()

    users = args.users.split(',') if args.users else []
    asyncio.run(main(
        group_title_override=args.group,
        group_about_override=args.about,
        raw_user_list=users,
        author_username=args.author,
        first_post=args.first_post
    ))