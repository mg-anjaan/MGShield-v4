from .moderation import setup_moderation
from .group_guard import setup_group_guard
from .admin_tag import setup_admin_tag
from .welcome import setup_welcome
from .filters import setup_filters

def register_all_handlers(dp):
    # 1. Filters and Guards FIRST (These delete/restrict messages)
    setup_filters(dp)       
    setup_group_guard(dp)
    
    # 2. Command Handlers and Specific Updates (These handle commands)
    setup_moderation(dp)    
    setup_admin_tag(dp)
    setup_welcome(dp)
