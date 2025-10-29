from aiogram import Dispatcher
from aiogram.types import ChatMemberUpdated
from utils import delete_later

def setup_welcome(dp: Dispatcher):
    @dp.chat_member()
    async def on_user_join(event: ChatMemberUpdated):
        # Trigger when a user becomes a member
        new = event.new_chat_member
        if new is None:
            return
        # Only greet if they are a member (not left)
        try:
            status = new.status
        except:
            return
        # Compose welcome with first name only
        first = new.user.first_name or 'there'
        sent = await event.chat.send_message(f"👋 Welcome {first}! Please follow the group rules.")
        # schedule deletion
        await delete_later(sent, 10)
