# هندلرهای ادمین

from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from config import SUDO_ADMIN_ID, DEFAULT_TRAFFIC_LIMIT_GB
from database import (
    get_user, add_user, get_all_users, update_user,
    block_user, set_traffic_limit, is_user_admin, is_user_sudo,
    get_user_configs, get_overall_stats, get_user_total_traffic,
    get_user_remaining_traffic, get_all_active_configs, update_config_traffic
)
from api import Panel3XUI
from keyboards import (
    get_admin_panel_keyboard, get_admin_users_list_keyboard,
    get_admin_user_detail_keyboard, get_traffic_limit_keyboard,
    get_back_keyboard, get_cancel_keyboard, get_configs_list_keyboard
)


# حالت‌های مکالمه
(
    WAITING_USER_ID,
    WAITING_TRAFFIC_LIMIT,
    WAITING_MANUAL_LIMIT,
) = range(10, 13)


async def check_admin_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """بررسی دسترسی ادمین"""
    telegram_id = update.effective_user.id
    
    # بررسی سودو
    if telegram_id == SUDO_ADMIN_ID:
        return True
    
    # بررسی ادمین
    if await is_user_admin(telegram_id):
        return True
    
    if update.callback_query:
        await update.callback_query.answer("⛔️ شما دسترسی ادمین ندارید!", show_alert=True)
    else:
        await update.message.reply_text("⛔️ شما دسترسی ادمین ندارید!")
    
    return False


# ==================== پنل ادمین ====================

async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش پنل ادمین"""
    query = update.callback_query
    await query.answer()
    
    if not await check_admin_access(update, context):
        return
    
    await query.edit_message_text(
        "👨‍💼 پنل مدیریت\n\n"
        "یک گزینه را انتخاب کنید:",
        reply_markup=get_admin_panel_keyboard()
    )


# ==================== مدیریت کاربران ====================

async def show_users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش لیست کاربران"""
    query = update.callback_query
    await query.answer()
    
    if not await check_admin_access(update, context):
        return
    
    users = await get_all_users()
    
    if not users:
        await query.edit_message_text(
            "📭 هیچ کاربری وجود ندارد.",
            reply_markup=get_back_keyboard()
        )
        return
    
    await query.edit_message_text(
        f"👥 لیست کاربران ({len(users)} نفر):\n\n"
        "👑 = سودو  |  👨‍💼 = ادمین  |  👤 = کاربر\n"
        "✅ = فعال  |  🚫 = مسدود",
        reply_markup=get_admin_users_list_keyboard(users)
    )


async def users_page_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """صفحه‌بندی لیست کاربران"""
    query = update.callback_query
    await query.answer()
    
    page = int(query.data.split("_")[-1])
    users = await get_all_users()
    
    await query.edit_message_reply_markup(
        reply_markup=get_admin_users_list_keyboard(users, page)
    )


async def show_user_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش جزئیات یک کاربر"""
    query = update.callback_query
    await query.answer()
    
    if not await check_admin_access(update, context):
        return
    
    telegram_id = int(query.data.split("_")[-1])
    user = await get_user(telegram_id)
    
    if not user:
        await query.answer("کاربر یافت نشد!", show_alert=True)
        return
    
    # دریافت آمار
    total_used = await get_user_total_traffic(telegram_id)
    remaining = await get_user_remaining_traffic(telegram_id)
    configs = await get_user_configs(telegram_id)
    
    role = "👑 سودو" if user.get("is_sudo") else "👨‍💼 ادمین" if user.get("is_admin") else "👤 کاربر"
    status = "🚫 مسدود" if user.get("is_blocked") else "✅ فعال"
    
    message = (
        f"📋 اطلاعات کاربر:\n\n"
        f"🆔 آیدی: `{telegram_id}`\n"
        f"👤 نقش: {role}\n"
        f"📊 وضعیت: {status}\n"
        f"📈 سقف ترافیک: {user.get('traffic_limit_gb', 0)} GB\n"
        f"📉 مصرفی: {total_used:.2f} GB\n"
        f"📊 باقیمانده: {remaining:.2f} GB\n"
        f"📋 تعداد کانفیگ: {len(configs)}"
    )
    
    await query.edit_message_text(
        message,
        parse_mode="Markdown",
        reply_markup=get_admin_user_detail_keyboard(telegram_id, user.get("is_blocked", False))
    )


# ==================== مسدود/رفع مسدودی ====================

async def block_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مسدود کردن کاربر"""
    query = update.callback_query
    await query.answer()
    
    if not await check_admin_access(update, context):
        return
    
    telegram_id = int(query.data.split("_")[-1])
    
    # نمی‌توان سودو را مسدود کرد
    if telegram_id == SUDO_ADMIN_ID:
        await query.answer("❌ امکان مسدود کردن ادمین اصلی وجود ندارد!", show_alert=True)
        return
    
    await block_user(telegram_id, True)
    await query.answer("✅ کاربر مسدود شد", show_alert=True)
    
    # رفرش صفحه
    user = await get_user(telegram_id)
    await query.edit_message_reply_markup(
        reply_markup=get_admin_user_detail_keyboard(telegram_id, True)
    )


async def unblock_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رفع مسدودی کاربر"""
    query = update.callback_query
    await query.answer()
    
    if not await check_admin_access(update, context):
        return
    
    telegram_id = int(query.data.split("_")[-1])
    
    await block_user(telegram_id, False)
    await query.answer("✅ مسدودی کاربر برداشته شد", show_alert=True)
    
    await query.edit_message_reply_markup(
        reply_markup=get_admin_user_detail_keyboard(telegram_id, False)
    )


# ==================== تغییر حد ترافیک ====================

async def change_traffic_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش گزینه‌های تغییر حد ترافیک"""
    query = update.callback_query
    await query.answer()
    
    if not await check_admin_access(update, context):
        return
    
    telegram_id = int(query.data.split("_")[-1])
    context.user_data["editing_user_id"] = telegram_id
    
    await query.edit_message_text(
        "📊 حد ترافیک جدید را انتخاب کنید:",
        reply_markup=get_traffic_limit_keyboard(telegram_id)
    )


async def set_traffic_limit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنظیم حد ترافیک"""
    query = update.callback_query
    await query.answer()
    
    if not await check_admin_access(update, context):
        return
    
    parts = query.data.split("_")
    telegram_id = int(parts[2])
    limit_gb = float(parts[3])
    
    await set_traffic_limit(telegram_id, limit_gb)
    await query.answer(f"✅ حد ترافیک به {limit_gb} GB تغییر یافت", show_alert=True)
    
    # بازگشت به صفحه کاربر
    user = await get_user(telegram_id)
    total_used = await get_user_total_traffic(telegram_id)
    remaining = await get_user_remaining_traffic(telegram_id)
    configs = await get_user_configs(telegram_id)
    
    role = "👑 سودو" if user.get("is_sudo") else "👨‍💼 ادمین" if user.get("is_admin") else "👤 کاربر"
    status = "🚫 مسدود" if user.get("is_blocked") else "✅ فعال"
    
    message = (
        f"📋 اطلاعات کاربر:\n\n"
        f"🆔 آیدی: `{telegram_id}`\n"
        f"👤 نقش: {role}\n"
        f"📊 وضعیت: {status}\n"
        f"📈 سقف ترافیک: {limit_gb} GB\n"
        f"📉 مصرفی: {total_used:.2f} GB\n"
        f"📊 باقیمانده: {remaining:.2f} GB\n"
        f"📋 تعداد کانفیگ: {len(configs)}"
    )
    
    await query.edit_message_text(
        message,
        parse_mode="Markdown",
        reply_markup=get_admin_user_detail_keyboard(telegram_id, user.get("is_blocked", False))
    )


async def manual_limit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع وارد کردن دستی حد ترافیک"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = int(query.data.split("_")[-1])
    context.user_data["editing_user_id"] = telegram_id
    
    await query.edit_message_text(
        "📝 مقدار حد ترافیک را به گیگابایت وارد کنید:\n"
        "(فقط عدد وارد کنید)",
        reply_markup=get_cancel_keyboard()
    )
    
    return WAITING_MANUAL_LIMIT


async def receive_manual_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت مقدار دستی حد ترافیک"""
    try:
        limit_gb = float(update.message.text.strip())
        if limit_gb < 0:
            raise ValueError("Negative value")
    except ValueError:
        await update.message.reply_text(
            "❌ مقدار نامعتبر. لطفاً یک عدد مثبت وارد کنید.",
            reply_markup=get_cancel_keyboard()
        )
        return WAITING_MANUAL_LIMIT
    
    telegram_id = context.user_data.get("editing_user_id")
    
    await set_traffic_limit(telegram_id, limit_gb)
    
    await update.message.reply_text(
        f"✅ حد ترافیک کاربر {telegram_id} به {limit_gb} GB تغییر یافت.",
        reply_markup=get_back_keyboard()
    )
    
    context.user_data.clear()
    return ConversationHandler.END


# ==================== افزودن کاربر ====================

async def add_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع افزودن کاربر جدید"""
    query = update.callback_query
    await query.answer()
    
    if not await check_admin_access(update, context):
        return ConversationHandler.END
    
    await query.edit_message_text(
        "👤 آیدی عددی تلگرام کاربر جدید را وارد کنید:",
        reply_markup=get_cancel_keyboard()
    )
    
    return WAITING_USER_ID


async def receive_new_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت آیدی کاربر جدید"""
    try:
        telegram_id = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(
            "❌ آیدی نامعتبر. لطفاً یک عدد وارد کنید.",
            reply_markup=get_cancel_keyboard()
        )
        return WAITING_USER_ID
    
    # بررسی اینکه کاربر وجود نداشته باشد
    existing = await get_user(telegram_id)
    if existing:
        await update.message.reply_text(
            "❌ این کاربر قبلاً در سیستم وجود دارد.",
            reply_markup=get_back_keyboard()
        )
        return ConversationHandler.END
    
    context.user_data["new_user_id"] = telegram_id
    
    await update.message.reply_text(
        f"📊 حد ترافیک کاربر {telegram_id} را به گیگابایت وارد کنید:\n"
        f"(پیش‌فرض: {DEFAULT_TRAFFIC_LIMIT_GB} GB)",
        reply_markup=get_cancel_keyboard()
    )
    
    return WAITING_TRAFFIC_LIMIT


async def receive_new_user_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت حد ترافیک کاربر جدید"""
    text = update.message.text.strip()
    
    try:
        if text:
            limit_gb = float(text)
        else:
            limit_gb = DEFAULT_TRAFFIC_LIMIT_GB
    except ValueError:
        await update.message.reply_text(
            "❌ مقدار نامعتبر. لطفاً یک عدد وارد کنید.",
            reply_markup=get_cancel_keyboard()
        )
        return WAITING_TRAFFIC_LIMIT
    
    telegram_id = context.user_data.get("new_user_id")
    
    await add_user(telegram_id, is_admin=False, is_sudo=False, traffic_limit_gb=limit_gb)
    
    await update.message.reply_text(
        f"✅ کاربر جدید افزوده شد:\n\n"
        f"🆔 آیدی: {telegram_id}\n"
        f"📊 حد ترافیک: {limit_gb} GB",
        reply_markup=get_back_keyboard()
    )
    
    context.user_data.clear()
    return ConversationHandler.END


# ==================== آمار کلی ====================

async def show_overall_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش آمار کلی"""
    query = update.callback_query
    await query.answer()
    
    if not await check_admin_access(update, context):
        return
    
    stats = await get_overall_stats()
    users = await get_all_users()
    
    # محاسبه آمار بیشتر
    blocked_users = sum(1 for u in users if u.get("is_blocked"))
    admin_users = sum(1 for u in users if u.get("is_admin") or u.get("is_sudo"))
    
    message = (
        f"📊 آمار کلی سیستم:\n\n"
        f"👥 تعداد کاربران: {stats['total_users']}\n"
        f"👨‍💼 ادمین‌ها: {admin_users}\n"
        f"🚫 مسدود شده: {blocked_users}\n\n"
        f"📋 کانفیگ‌های فعال: {stats['active_configs']}\n"
        f"📈 کل ترافیک مصرفی: {stats['total_traffic_gb']} GB"
    )
    
    await query.edit_message_text(
        message,
        reply_markup=get_back_keyboard()
    )


# ==================== مصرف کاربر ====================

async def show_user_usage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش جزئیات مصرف کاربر"""
    query = update.callback_query
    await query.answer()
    
    if not await check_admin_access(update, context):
        return
    
    telegram_id = int(query.data.split("_")[-1])
    configs = await get_user_configs(telegram_id, include_deleted=True)
    
    if not configs:
        await query.answer("این کاربر کانفیگی ندارد", show_alert=True)
        return
    
    message = f"📊 جزئیات مصرف کاربر {telegram_id}:\n\n"
    
    total_used = 0
    for config in configs:
        status = "🗑" if config.get("is_deleted") else "✅"
        used = config.get("deleted_traffic_gb", 0) if config.get("is_deleted") else config.get("traffic_used_gb", 0)
        total_used += used
        
        email = config.get("panel_client_email", "")[:15]
        message += f"{status} {email}... : {used:.2f} GB\n"
    
    message += f"\n📈 مجموع: {total_used:.2f} GB"
    
    await query.edit_message_text(
        message,
        reply_markup=get_back_keyboard()
    )


# ==================== کانفیگ‌های کاربر ====================

async def show_user_configs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش کانفیگ‌های یک کاربر"""
    query = update.callback_query
    await query.answer()
    
    if not await check_admin_access(update, context):
        return
    
    telegram_id = int(query.data.split("_")[-1])
    configs = await get_user_configs(telegram_id)
    
    if not configs:
        await query.answer("این کاربر کانفیگی ندارد", show_alert=True)
        return
    
    await query.edit_message_text(
        f"📋 کانفیگ‌های کاربر {telegram_id}:",
        reply_markup=get_configs_list_keyboard(configs)
    )


# ==================== همه کانفیگ‌ها ====================

async def show_all_configs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش همه کانفیگ‌های فعال"""
    query = update.callback_query
    await query.answer()
    
    if not await check_admin_access(update, context):
        return
    
    configs = await get_all_active_configs()
    
    if not configs:
        await query.edit_message_text(
            "📭 هیچ کانفیگ فعالی وجود ندارد.",
            reply_markup=get_back_keyboard()
        )
        return
    
    # گروه‌بندی بر اساس کاربر
    by_user = {}
    for config in configs:
        owner = config.get("owner_telegram_id")
        if owner not in by_user:
            by_user[owner] = []
        by_user[owner].append(config)
    
    message = f"📋 کانفیگ‌های فعال ({len(configs)} عدد):\n\n"
    
    for user_id, user_configs in by_user.items():
        message += f"👤 {user_id}: {len(user_configs)} کانفیگ\n"
    
    await query.edit_message_text(
        message,
        reply_markup=get_back_keyboard()
    )


# ==================== جستجو ====================

async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع جستجو"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🔍 آیدی تلگرام یا ایمیل کانفیگ را وارد کنید:",
        reply_markup=get_cancel_keyboard()
    )
    
    context.user_data["searching"] = True


# ==================== همگام‌سازی ترافیک ====================

def format_traffic(gb: float) -> str:
    """فرمت ترافیک - نمایش MB برای مقادیر کوچک"""
    if gb < 0.01:  # کمتر از 10 MB
        return f"{gb * 1024:.1f} MB"
    elif gb < 1:
        return f"{gb * 1024:.0f} MB"
    else:
        return f"{gb:.2f} GB"


async def sync_traffic_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """همگام‌سازی دستی ترافیک از پنل"""
    query = update.callback_query
    await query.answer()
    
    if not await check_admin_access(update, context):
        return
    
    await query.edit_message_text(
        "⏳ در حال همگام‌سازی ترافیک...\n"
        "لطفاً صبر کنید..."
    )
    
    try:
        async with Panel3XUI() as panel:
            # دریافت ترافیک همه کلاینت‌ها
            all_traffic = await panel.get_all_clients_traffic()
            
            # ساخت دیکشنری برای دسترسی سریع
            traffic_by_email = {t["email"]: t for t in all_traffic}
            
            # بروزرسانی ترافیک در دیتابیس
            configs = await get_all_active_configs()
            updated_count = 0
            
            for config in configs:
                email = config.get("panel_client_email")
                if email in traffic_by_email:
                    traffic_gb = traffic_by_email[email].get("total_gb", 0)
                    await update_config_traffic(config["id"], traffic_gb)
                    updated_count += 1
        
        # دریافت آمار بعد از بروزرسانی
        stats = await get_overall_stats()
        users = await get_all_users()
        
        # محاسبه مصرف کل کاربران
        users_usage = []
        for user in users:
            if not user.get("is_blocked"):
                total_used = await get_user_total_traffic(user["telegram_id"])
                if total_used > 0:
                    users_usage.append({
                        "id": user["telegram_id"],
                        "used": total_used,
                        "limit": user.get("traffic_limit_gb", 0)
                    })
        
        # مرتب‌سازی بر اساس مصرف
        users_usage.sort(key=lambda x: x["used"], reverse=True)
        
        message = (
            f"✅ همگام‌سازی با موفقیت انجام شد!\n\n"
            f"📊 آمار:\n"
            f"• کانفیگ‌های بروزرسانی شده: {updated_count}\n"
            f"• کل ترافیک مصرفی: {format_traffic(stats['total_traffic_gb'])}\n\n"
        )
        
        if users_usage:
            message += "👥 مصرف کاربران:\n"
            for i, u in enumerate(users_usage[:10], 1):
                percent = (u["used"] / u["limit"] * 100) if u["limit"] > 0 else 0
                message += f"{i}. `{u['id']}`: {format_traffic(u['used'])}/{u['limit']} GB ({percent:.0f}%)\n"
        
        await query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=get_back_keyboard()
        )
        
    except Exception as e:
        await query.edit_message_text(
            f"❌ خطا در همگام‌سازی:\n{str(e)}",
            reply_markup=get_back_keyboard()
        )


# ==================== لغو عملیات ادمین ====================

async def cancel_admin_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو عملیات ادمین"""
    query = update.callback_query
    await query.answer("لغو شد")
    
    context.user_data.clear()
    
    await query.edit_message_text(
        "👨‍💼 پنل مدیریت\n\n"
        "یک گزینه را انتخاب کنید:",
        reply_markup=get_admin_panel_keyboard()
    )
    
    return ConversationHandler.END


# ==================== ثبت هندلرها ====================

def get_admin_handlers():
    """برگرداندن هندلرهای ادمین"""
    
    # مکالمه افزودن کاربر
    add_user_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_user_start, pattern="^admin_add_user$")],
        states={
            WAITING_USER_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_user_id),
            ],
            WAITING_TRAFFIC_LIMIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_user_limit),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_admin_operation, pattern="^cancel$"),
        ],
        per_message=False,
    )
    
    # مکالمه تغییر دستی حد ترافیک
    manual_limit_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(manual_limit_start, pattern="^manual_limit_")],
        states={
            WAITING_MANUAL_LIMIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_manual_limit),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_admin_operation, pattern="^cancel$"),
        ],
        per_message=False,
    )
    
    handlers = [
        add_user_conv,
        manual_limit_conv,
        CallbackQueryHandler(show_admin_panel, pattern="^admin_panel$"),
        CallbackQueryHandler(show_users_list, pattern="^admin_users$"),
        CallbackQueryHandler(users_page_navigation, pattern="^users_page_"),
        CallbackQueryHandler(show_user_detail, pattern="^admin_user_\\d+$"),
        CallbackQueryHandler(block_user_handler, pattern="^admin_block_"),
        CallbackQueryHandler(unblock_user_handler, pattern="^admin_unblock_"),
        CallbackQueryHandler(change_traffic_limit, pattern="^admin_limit_"),
        CallbackQueryHandler(set_traffic_limit_handler, pattern="^set_limit_"),
        CallbackQueryHandler(show_overall_stats, pattern="^admin_stats$"),
        CallbackQueryHandler(show_user_usage, pattern="^admin_usage_"),
        CallbackQueryHandler(show_user_configs, pattern="^admin_configs_"),
        CallbackQueryHandler(show_all_configs, pattern="^admin_all_configs$"),
        CallbackQueryHandler(search_start, pattern="^admin_search$"),
        CallbackQueryHandler(sync_traffic_handler, pattern="^admin_sync_traffic$"),
    ]
    
    return handlers
