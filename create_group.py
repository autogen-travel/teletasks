import json
import asyncio
import logging
import argparse
from telethon import TelegramClient
from telethon.errors import UserPrivacyRestrictedError, UsernameNotOccupiedError
from telethon.tl.functions.contacts import ResolveUsernameRequest
from telethon.tl.functions.channels import CreateChannelRequest, InviteToChannelRequest, EditAdminRequest
from telethon.tl.types import ChatAdminRights

from telethon.tl.functions.messages import ExportChatInviteRequest

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('group_creator.log'),
        logging.StreamHandler()
    ]
)

# Загрузка API-ключей
with open('api_keys.json', 'r') as f:
    api_keys = json.load(f)

api_id = api_keys['api_id']
api_hash = api_keys['api_hash']
phone_number = api_keys['phone_number']
user_username = api_keys['user_username']
bot_username = api_keys['bot_username']
default_group_title = api_keys['group_title']
default_group_about = api_keys['group_about']

# Инициализация клиента
client = TelegramClient(phone_number, api_id, api_hash, device_model='iPhone 13 Pro', system_version='4.16.30-vxCUSTOM')

# Проверка существования группы
async def group_exists(client, group_title):
    dialogs = await client.get_dialogs()
    return any(dialog.name == group_title for dialog in dialogs)

async def main(group_title_override=None, group_about_override=None, raw_user_list=None):
    await client.start()
    logging.info("✅ Авторизация прошла успешно")

    group_title = group_title_override or default_group_title
    logging.info(f"🔍 Проверяем существование группы '{group_title}'...")
    await asyncio.sleep(2)

    if await group_exists(client, group_title):
        logging.warning(f"⚠️ Группа '{group_title}' уже существует. Операция отменена.")
        return

    # Получение пользователя
    try:
        user = (await client(ResolveUsernameRequest(user_username))).users[0]
        logging.info(f"👤 Пользователь @{user_username} найден.")
    except UsernameNotOccupiedError:
        logging.error(f"❌ Пользователь @{user_username} не найден.")
        return
    await asyncio.sleep(2)

    # Получение бота
    try:
        bot = (await client(ResolveUsernameRequest(bot_username))).users[0]
        logging.info(f"🤖 Бот @{bot_username} найден.")
    except UsernameNotOccupiedError:
        logging.error(f"❌ Бот @{bot_username} не найден.")
        return
    await asyncio.sleep(2)

    # Создание группы
    logging.info("🚀 Создаём супергруппу...")
    result = await client(CreateChannelRequest(
        title=group_title,
        about=group_about_override or default_group_about,
        megagroup=True
    ))
    channel = result.chats[0]
    logging.info(f"✅ Группа '{group_title}' создана.")
    await asyncio.sleep(3)

    # Добавление основного пользователя и бота
    for participant in [user, bot]:
        try:
            await client(InviteToChannelRequest(channel=channel, users=[participant]))
            logging.info(f"➕ Участник {getattr(participant, 'username', participant.id)} добавлен.")
            await asyncio.sleep(2)
        except UserPrivacyRestrictedError:
            logging.warning(f"⚠️ {getattr(participant, 'username', participant.id)} запретил добавление в группы.")
        except Exception as e:
            logging.error(f"❌ Ошибка при добавлении {participant.id}: {e}")

    # Назначение бота админом
    rights = ChatAdminRights(
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
    )
    try:
        await client(EditAdminRequest(
            channel=channel,
            user_id=bot,
            admin_rights=rights,
            rank='Бот'
        ))
        logging.info(f"🛡 Бот @{bot_username} назначен администратором.")
    except Exception as e:
        logging.warning(f"⚠️ Не удалось назначить бота админом: {e}")
    await asyncio.sleep(2)

    # Обработка дополнительных пользователей
    if raw_user_list:
        for entry in raw_user_list:
            entry = entry.strip()
            try:
                if entry.isdigit():
                    entity = await client.get_entity(int(entry))
                else:
                    entity = await client.get_entity(entry)
                await client(InviteToChannelRequest(channel=channel, users=[entity]))
                logging.info(f"✅ {getattr(entity, 'username', entity.id)} добавлен в группу.")
                await asyncio.sleep(2)
            except UserPrivacyRestrictedError:
                logging.warning(f"🚫 {entry} запретил добавление в группы.")
            except Exception as e:
                logging.error(f"❌ Ошибка при добавлении {entry}: {e}")

    # Получение ссылки-приглашения
    invite = await client(ExportChatInviteRequest(peer=channel))
    print(invite.link)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Создание Telegram-группы через Telethon')
    parser.add_argument('--group', help='Название создаваемой группы (переопределяет config)', type=str)
    parser.add_argument('--users', help='Список пользователей через запятую: username или ID', type=str)
    parser.add_argument('--about', help='Описание для группы', type=str)
    args = parser.parse_args()

    users = args.users.split(',') if args.users else []
    asyncio.run(main(group_title_override=args.group, group_about_override=args.about, raw_user_list=users))