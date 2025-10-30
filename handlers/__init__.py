# handler/__init__.py

from aiogram import Dispatcher
from .moderation import router as moderation_router
from .group_guard import router as group_guard_router
from .admin_tag import router as admin_tag_router
from .welcome import router as welcome_router
from .filters import router as filters_router

def register_all_handlers(dp: Dispatcher):
    """
    Registers all modular routers with the main dispatcher.
    Order is crucial: Guards/Filters first, then commands, then passive handlers.
    """
    
    # 1. GUARDS/FILTERS (Highest Priority for deletion/restriction)
    dp.include_router(group_guard_router) # Flood Control
    dp.include_router(filters_router)     # Content Filter

    # 2. COMMANDS (Medium Priority)
    dp.include_router(moderation_router)
    dp.include_router(admin_tag_router)

    # 3. PASSIVE/OTHER UPDATES (Low Priority)
    dp.include_router(welcome_router) # Chat Member Updates/Set Welcome Command
