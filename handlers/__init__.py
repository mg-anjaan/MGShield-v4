from .group_guard import setup_group_guard
from .moderation import setup_moderation
from .admin_tag import setup_admin_tag
from .welcome import setup_welcome

def register_handlers(dp):
    setup_group_guard(dp)
    setup_moderation(dp)
    setup_admin_tag(dp)
    setup_welcome(dp)
