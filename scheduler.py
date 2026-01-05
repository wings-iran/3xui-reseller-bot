# تسک‌های زمان‌بندی شده

import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from telegram import Bot

from config import (
    BOT_TOKEN, SUDO_ADMIN_ID, TRAFFIC_CHECK_INTERVAL_HOURS,
    ALERT_THRESHOLD_PERCENT, MESSAGES
)
from database import (
    get_all_active_configs, update_config_traffic,
    get_all_users, get_user_total_traffic, get_users_near_limit,
    get_user
)
from api import Panel3XUI


# نگهداری bot instance
bot: Bot = None
scheduler: AsyncIOScheduler = None


def init_scheduler(bot_instance: Bot):
    """راه‌اندازی scheduler"""
    global bot, scheduler
    
    bot = bot_instance
    scheduler = AsyncIOScheduler()
    
    # اضافه کردن job چک ترافیک
    scheduler.add_job(
        check_all_traffic,
        IntervalTrigger(hours=TRAFFIC_CHECK_INTERVAL_HOURS),
        id="traffic_check",
        name="Traffic Check Job",
        replace_existing=True
    )
    
    scheduler.start()
    print(f"✅ Scheduler started. Traffic check every {TRAFFIC_CHECK_INTERVAL_HOURS} hours.")


async def check_all_traffic():
    """بررسی ترافیک همه کانفیگ‌ها"""
    print(f"[{datetime.now()}] Starting traffic check...")
    
    try:
        async with Panel3XUI() as panel:
            # دریافت ترافیک همه کلاینت‌ها
            all_traffic = await panel.get_all_clients_traffic()
            
            # ساخت دیکشنری برای دسترسی سریع
            traffic_by_email = {t["email"]: t for t in all_traffic}
            
            # بروزرسانی ترافیک در دیتابیس
            configs = await get_all_active_configs()
            
            for config in configs:
                email = config.get("panel_client_email")
                if email in traffic_by_email:
                    traffic_gb = traffic_by_email[email].get("total_gb", 0)
                    await update_config_traffic(config["id"], traffic_gb)
        
        print(f"[{datetime.now()}] Updated traffic for {len(configs)} configs.")
        
        # بررسی کاربران نزدیک به حد مجاز
        await check_users_near_limit()
        
    except Exception as e:
        print(f"[{datetime.now()}] Error in traffic check: {e}")


async def check_users_near_limit():
    """بررسی و هشدار کاربران نزدیک به حد مجاز"""
    users_near_limit = await get_users_near_limit(ALERT_THRESHOLD_PERCENT)
    
    for user_data in users_near_limit:
        telegram_id = user_data["telegram_id"]
        percent = user_data["percent"]
        used_gb = user_data["used_gb"]
        limit_gb = user_data["limit_gb"]
        
        try:
            # ارسال هشدار به کاربر
            user_message = MESSAGES["alert_near_limit"].format(
                percent=percent,
                used=used_gb,
                limit=limit_gb
            )
            
            await bot.send_message(
                chat_id=telegram_id,
                text=user_message
            )
            
            # ارسال هشدار به ادمین اصلی
            admin_message = MESSAGES["admin_alert"].format(
                user_id=telegram_id,
                percent=percent
            )
            
            await bot.send_message(
                chat_id=SUDO_ADMIN_ID,
                text=admin_message
            )
            
            print(f"[{datetime.now()}] Alert sent to user {telegram_id} ({percent}%)")
            
        except Exception as e:
            print(f"[{datetime.now()}] Failed to send alert to {telegram_id}: {e}")


async def manual_traffic_sync():
    """همگام‌سازی دستی ترافیک (برای فراخوانی از ادمین)"""
    await check_all_traffic()
    return True


def stop_scheduler():
    """توقف scheduler"""
    global scheduler
    if scheduler:
        scheduler.shutdown()
        print("Scheduler stopped.")
