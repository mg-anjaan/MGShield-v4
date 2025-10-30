from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message, ChatPermissions
from aiogram.exceptions import TelegramBadRequest
from datetime import datetime, timedelta

# Import utilities
from utils import is_admin, extract_target_user, delete_later, warn_user, get_warn_count, parse_time
router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.reply("🤖 GroupGuardian active! Use /help for commands.")
    await delete_later(message, 10)

@router.message(Command("mute"))
async def cmd_mute(message: Message, bot: Bot):
    if not await is_admin(bot, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ You must be an admin to use this.")
    
    target = extract_target_user(message)
    if not target:
        return await message.reply("Usage: `/mute @user 10m` (or reply to a user)", parse_mode="Markdown")
    
    user_id, until_date_timestamp = target
    
    if await is_admin(bot, message.chat.id, user_id):
        return await message.reply("⚠️ I cannot mute an admin.")
    
    try:
        await bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=user_id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_date_timestamp
        )
        await message.reply("🔇 User muted.")
    except TelegramBadRequest as e:
        await message.reply(f"❌ Failed to mute user. Error: {e.message}")
        
    await delete_later(message, 10)

@router.message(Command("unmute"))
async def cmd_unmute(message: Message, bot: Bot):
    if not await is_admin(bot, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ You must be an admin to use this.")
    
    target = extract_target_user(message)
    if not target:
        return await message.reply("Usage: `/unmute @user` (or reply to a user)", parse_mode="Markdown")
    
    user_id, _ = target
    
    try:
        # Restore default permissions
        await bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=user_id,
            permissions=ChatPermissions(
                can_send_messages=True, 
                can_send_media_messages=True, 
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )
        await message.reply("🔊 User unmuted.")
    except TelegramBadRequest as e:
        await message.reply(f"❌ Failed to unmute user. Error: {e.message}")

    await delete_later(message, 10)

@router.message(Command("ban"))
async def cmd_ban(message: Message, bot: Bot):
    if not await is_admin(bot, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ You must be an admin to use this.")
    
    target = extract_target_user(message)
    if not target:
        return await message.reply("Usage: `/ban @user` (or reply to a user)", parse_mode="Markdown")
    
    user_id, _ = target
    
    if await is_admin(bot, message.chat.id, user_id):
        return await message.reply("⚠️ I cannot ban an admin.")
    
    try:
        # Permanent ban
        await bot.ban_chat_member(message.chat.id, user_id)
        # Clear all warnings when banning
        await warn_user(message.chat.id, user_id, reset=True) 
        await message.reply("⛔ User banned and warnings cleared.")
    except TelegramBadRequest as e:
        await message.reply(f"❌ Failed to ban user. Error: {e.message}")
        
    await delete_later(message, 10)

@router.message(Command("unban"))
async def cmd_unban(message: Message, bot: Bot):
    if not await is_admin(bot, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ You must be an admin to use this.")
    
    target = extract_target_user(message)
    if not target:
        return await message.reply("Usage: `/unban @user` (or reply to a user)", parse_mode="Markdown")
    
    user_id, _ = target
    
    try:
        await bot.unban_chat_member(message.chat.id, user_id)
        await message.reply("✅ User unbanned.")
    except TelegramBadRequest as e:
        await message.reply(f"❌ Failed to unban user. Error: {e.message}")

    await delete_later(message, 10)

@router.message(Command("warn"))
async def cmd_warn(message: Message, bot: Bot):
    if not await is_admin(bot, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ You must be an admin to use this.")
    
    target = extract_target_user(message)
    if not target:
        return await message.reply("Usage: `/warn @user` (or reply to a user)", parse_mode="Markdown")
    
    user_id, _ = target
    chat_id = message.chat.id

    if await is_admin(bot, chat_id, user_id):
        return await message.reply("⚠️ I cannot warn an admin.")

    try:
        # Increment warning count
        warns = await warn_user(chat_id, user_id) 
        
        if warns >= 3:
            # KICK: Temporary ban for 1 minute to ensure kick
            kick_until = datetime.now() + timedelta(minutes=1)
            await bot.ban_chat_member(chat_id, user_id, until_date=kick_until)
            await bot.unban_chat_member(chat_id, user_id) # Allow rejoin
            await warn_user(chat_id, user_id, reset=True)
            await message.reply(f"❗ **{message.from_user.full_name}** KICKED the user after **{warns}/3** warns.")
        else:
            await message.reply(f"⚠️ User warned. Current warnings: **{warns}/3**.")
            
    except TelegramBadRequest as e:
        await message.reply(f"❌ Failed to warn/kick user. Error: {e.message}")
        
    await delete_later(message, 10)

@router.message(Command("checkwarns"))
async def cmd_check_warns(message: Message, bot: Bot):
    if not await is_admin(bot, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ You must be an admin to use this.")
    
    target = extract_target_user(message)
    if not target:
        return await message.reply("Usage: `/checkwarns @user` (or reply to a user)", parse_mode="Markdown")
    
    user_id, _ = target
    
    warns = await get_warn_count(message.chat.id, user_id)
    await message.reply(f"✅ User ID `{user_id}` has **{warns}/3** warnings.", parse_mode="Markdown")
    
    await delete_later(message, 10)

