#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ربات تلگرام مدیریت پنل 3X-UI
"""

import asyncio
import logging
import sys
import os

# اضافه کردن مسیر پروژه به path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram import Update
from telegram.ext import Application, ContextTypes

from config import *
from database import init_db, add_user
from handlers.user import get_user_handlers
from handlers.admin import get_admin_handlers
from scheduler import init_scheduler, stop_scheduler


# تنظیم logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر خطاها"""
    logger.error(f"Exception while handling an update: {context.error}")
    
    if update and update.effective_user:
        try:
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text="❌ خطایی رخ داد. لطفاً دوباره تلاش کنید."
            )
        except Exception:
            pass


async def post_init(application: Application):
    """اجرا بعد از راه‌اندازی"""
    logger.info("Initializing database...")
    await init_db()
    
    # افزودن ادمین اصلی اگر وجود نداشته باشد
    await add_user(SUDO_ADMIN_ID, is_admin=True, is_sudo=True, traffic_limit_gb=99999)
    
    logger.info("Initializing scheduler...")
    init_scheduler(application.bot)
    
    logger.info("Bot is ready!")
    
    # ارسال پیام به ادمین
    try:
        await application.bot.send_message(
            chat_id=SUDO_ADMIN_ID,
            text="✅ ربات با موفقیت راه‌اندازی شد!\n\n"
                 "برای شروع دستور /start را ارسال کنید."
        )
    except Exception as e:
        logger.warning(f"Could not send startup message to admin: {e}")


async def post_shutdown(application: Application):
    """اجرا قبل از خاموش شدن"""
    logger.info("Shutting down scheduler...")
    stop_scheduler()
    logger.info("Bot shutdown complete.")


def main():
    """تابع اصلی"""
    logger.info("Starting bot...")
    
    # ساخت application
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    
    # ثبت هندلرهای کاربر
    for handler in get_user_handlers():
        application.add_handler(handler)
    
    # ثبت هندلرهای ادمین
    for handler in get_admin_handlers():
        application.add_handler(handler)
    
    # ثبت هندلر خطا
    application.add_error_handler(error_handler)
    
    # اجرای ربات
    logger.info("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
