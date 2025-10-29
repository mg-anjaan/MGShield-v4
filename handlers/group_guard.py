from aiogram import Dispatcher, types
from utils import delete_later

user_message_count = {}

def setup_group_guard(dp: Dispatcher):
    @dp.message()
    async def group_protection(message: types.Message):
        if message.chat.type not in ["group", "supergroup"]:
            return

        user_id = message.from_user.id
        chat_id = message.chat.id

        # 🛡 Flood control (more than 5 msgs in 10 sec)
        key = (chat_id, user_id)
        if key not in user_message_count:
            user_message_count[key] = []
        user_message_count[key].append(message.date.timestamp())
        user_message_count[key] = [t for t in user_message_count[key] if message.date.timestamp() - t <= 10]

        if len(user_message_count[key]) > 5:
            await message.chat.restrict(user_id, permissions=types.ChatPermissions(can_send_messages=False), until_date=60)
            warn = await message.reply("🤖 Flood detected! User muted for 1 minute.")
            await delete_later(warn, 10)


