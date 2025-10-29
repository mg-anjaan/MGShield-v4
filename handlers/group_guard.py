from aiogram import Dispatcher, types
from utils import delete_later

user_message_count = {}

def setup_group_guard(dp: Dispatcher):
    @dp.message()
    async def group_protection(message: types.Message):
        if message.chat.type not in ["group", "supergroup"]:
            return

        # CRITICAL FIX: Skip messages that ARE commands!
        if message.text and message.text.startswith('/'):
            # Allow the message to pass to the next handler (the command handlers)
            return
            
        # Skip admins (to prevent them from being flood-muted)
        # Assuming you have 'is_admin' imported in this file or handled elsewhere
        # if await is_admin(message.chat, message.from_user.id):
        #     return

        user_id = message.from_user.id
        chat_id = message.chat.id

        # 🛡 Flood control logic...
        key = (chat_id, user_id)
        if key not in user_message_count:
            user_message_count[key] = []
        
        current_time = message.date.timestamp()
        user_message_count[key].append(current_time)
        user_message_count[key] = [t for t in user_message_count[key] if current_time - t <= 10]

        if len(user_message_count[key]) > 5:
            # Action: Mute the user
            await message.chat.restrict(
                user_id, 
                permissions=types.ChatPermissions(can_send_messages=False), 
                until_date=60
            )
            
            # Action: Send warning and schedule deletion
            warn = await message.reply("🤖 Flood detected! User muted for 1 minute.")
            await delete_later(warn, 10)
            
            return # Stop processing after mute
        
        return # Allow the message to continue to the next handler

