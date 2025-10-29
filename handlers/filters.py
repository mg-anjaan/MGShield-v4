from aiogram import types

def setup_filters(dp):
    @dp.message()
    async def handle_all(message: types.Message):
        # No filtering logic yet; just a placeholder to prevent import errors
        return

