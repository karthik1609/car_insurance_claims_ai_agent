# src/api/routes_update.py

from src.routes.telegram_bot import router as telegram_router

def update_routes(router):
    """Update the main API router to include the Telegram bot"""
    router.include_router(telegram_router, prefix="/telegram", tags=["Telegram"])
    return router