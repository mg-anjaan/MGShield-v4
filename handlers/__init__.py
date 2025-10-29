from aiogram import Dispatcher
from . import group_guard, moderation, admin_tag, welcome

def register_handlers(dp: Dispatcher):
    group_guard.setup_group_guard(dp)
    moderation.setup_moderation(dp)
    admin_tag.setup_admin_tag(dp)
    welcome.setup_welcome(dp)
