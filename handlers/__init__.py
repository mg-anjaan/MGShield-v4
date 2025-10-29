from .moderation import setup_moderation
from .filters import setup_filters
from .group_guard import setup_group_guard

def register_handlers(dp):
    setup_moderation(dp)
    setup_filters(dp)
    setup_group_guard(dp)
