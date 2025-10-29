from .moderation import setup_moderation
from .group_guard import setup_group_guard

def register_handlers(dp):
    setup_moderation(dp)
    setup_group_guard(dp)
