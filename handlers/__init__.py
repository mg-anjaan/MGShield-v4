# handlers/__init__.py

from .moderation import setup_moderation
from .group_guard import setup_group_guard
from .admin_tag import setup_admin_tag
from .welcome import setup_welcome
from .filters import setup_filters  # <--- MUST BE PRESENT NOW

def register_all_handlers(dp):
    setup_moderation(dp)
    setup_group_guard(dp)
    setup_admin_tag(dp)
    setup_welcome(dp)
    setup_filters(dp) # <--- MUST BE PRESENT NOW
