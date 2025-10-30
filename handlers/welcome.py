from aiogram import Dispatcher
from aiogram.types import ChatMemberUpdated, Message
from aiogram.filters import Command
from utils import delete_later, get_welcome_message, set_welcome_message, is_admin

def setup_welcome(dp: Dispatcher):
    
    # 1. COMMAND: Set Custom Welcome Message
    @dp.message(Command("setwelcome"))
    async def cmd_set_welcome(message: Message):
        if not await is_admin(message.chat, message.from_user.id):
            return await message.reply("⚠️ Only admins can set the welcome message.")

        new_message = message.text.split(maxsplit=1)[1].strip() if len(message.text.split()) > 1 else None

        if not new_message:
            return await message.reply("Usage: /setwelcome <Your message here>. Use {user_name} for the user's name.")

        await set_welcome_message(message.chat.id, new_message)
        await message.reply(f"✅ Welcome message saved! New message:\n\n{new_message}")
        await delete_later(message, 10)


    # 2. HANDLER: Send Welcome Message on Join
    @dp.chat_member()
    async def on_user_join(event: ChatMemberUpdated):
        new = event.new_chat_member
        
        # Only greet if the user changed status to 'member' or 'restricted' (and can send messages)
        if new.status in ('member', 'restricted') and new.user.id != event.bot.id:
            
            # Fetch custom message from DB (or get default)
            custom_msg = await get_welcome_message(event.chat.id)

            # Format the message
            user_name = new.user.first_name or 'there'
            final_msg = custom_msg.replace('{user_name}', user_name)

            # Send and schedule deletion
            sent = await event.chat.send_message(final_msg)
            await delete_later(sent, 10)
