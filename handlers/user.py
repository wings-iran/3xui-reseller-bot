# هندلرهای کاربران عادی

import time
import uuid
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from config import MESSAGES, SUDO_ADMIN_ID, DEFAULT_TRAFFIC_LIMIT_GB
from database import (
    get_user, add_user, get_user_configs, get_config,
    add_config, delete_config, extend_config,
    get_user_total_traffic, get_user_remaining_traffic,
    is_user_blocked, update_config_traffic
)
from api import Panel3XUI
from keyboards import (
    get_main_menu_keyboard, get_back_keyboard, get_cancel_keyboard,
    get_inbound_selection_keyboard, get_traffic_amount_keyboard,
    get_expiry_time_keyboard, get_configs_list_keyboard,
    get_config_detail_keyboard, get_confirm_delete_keyboard,
    get_extend_traffic_keyboard, get_extend_time_keyboard, get_extend_confirm_keyboard
)


# حالت‌های مکالمه
(
    SELECTING_INBOUND,
    ENTERING_USERNAME,
    SELECTING_TRAFFIC,
    ENTERING_CUSTOM_TRAFFIC,
    SELECTING_EXPIRY,
    ENTERING_CUSTOM_EXPIRY,
    CONFIRMING_CREATE,
    # حالت‌های تمدید
    EXTEND_ENTERING_TRAFFIC,
    EXTEND_ENTERING_TIME,
) = range(9)


async def check_user_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """بررسی دسترسی کاربر"""
    telegram_id = update.effective_user.id
    
    # بررسی اینکه کاربر وجود دارد
    user = await get_user(telegram_id)
    
    if not user:
        # اگر سودو ادمین است، اتوماتیک اضافه شود
        if telegram_id == SUDO_ADMIN_ID:
            await add_user(telegram_id, is_admin=True, is_sudo=True, traffic_limit_gb=99999)
            return True
        
        # کاربر وجود ندارد
        if update.callback_query:
            await update.callback_query.answer(MESSAGES["not_authorized"], show_alert=True)
        else:
            await update.message.reply_text(MESSAGES["not_authorized"])
        return False
    
    # بررسی مسدود بودن
    if user.get("is_blocked"):
        if update.callback_query:
            await update.callback_query.answer(MESSAGES["blocked"], show_alert=True)
        else:
            await update.message.reply_text(MESSAGES["blocked"])
        return False
    
    return True


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر دستور /start"""
    if not await check_user_access(update, context):
        return
    
    telegram_id = update.effective_user.id
    user = await get_user(telegram_id)
    
    is_admin = user.get("is_admin", False) if user else False
    is_sudo = user.get("is_sudo", False) if user else False
    
    await update.message.reply_text(
        MESSAGES["welcome"],
        reply_markup=get_main_menu_keyboard(is_admin, is_sudo)
    )


async def back_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بازگشت به منوی اصلی"""
    query = update.callback_query
    await query.answer()
    
    if not await check_user_access(update, context):
        return ConversationHandler.END
    
    telegram_id = update.effective_user.id
    user = await get_user(telegram_id)
    
    is_admin = user.get("is_admin", False) if user else False
    is_sudo = user.get("is_sudo", False) if user else False
    
    await query.edit_message_text(
        MESSAGES["welcome"],
        reply_markup=get_main_menu_keyboard(is_admin, is_sudo)
    )
    
    # پاک کردن داده‌های موقت
    context.user_data.clear()
    return ConversationHandler.END


async def cancel_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو عملیات"""
    query = update.callback_query
    await query.answer("عملیات لغو شد")
    
    context.user_data.clear()
    
    telegram_id = update.effective_user.id
    user = await get_user(telegram_id)
    
    is_admin = user.get("is_admin", False) if user else False
    is_sudo = user.get("is_sudo", False) if user else False
    
    await query.edit_message_text(
        MESSAGES["welcome"],
        reply_markup=get_main_menu_keyboard(is_admin, is_sudo)
    )
    
    return ConversationHandler.END


# ==================== ساخت کانفیگ ====================

async def create_config_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع ساخت کانفیگ"""
    query = update.callback_query
    await query.answer()
    
    if not await check_user_access(update, context):
        return ConversationHandler.END
    
    telegram_id = update.effective_user.id
    user = await get_user(telegram_id)
    
    # بررسی حد ترافیک
    remaining = await get_user_remaining_traffic(telegram_id)
    if remaining <= 0 and not user.get("is_sudo"):
        await query.edit_message_text(
            MESSAGES["traffic_limit_reached"],
            reply_markup=get_back_keyboard()
        )
        return ConversationHandler.END
    
    # دریافت لیست inbound ها
    async with Panel3XUI() as panel:
        inbounds = await panel.get_inbounds()
    
    if not inbounds:
        await query.edit_message_text(
            "❌ خطا در دریافت لیست سرورها. لطفاً دوباره تلاش کنید.",
            reply_markup=get_back_keyboard()
        )
        return ConversationHandler.END
    
    await query.edit_message_text(
        "🔹 لطفاً سرور مورد نظر را انتخاب کنید:",
        reply_markup=get_inbound_selection_keyboard(inbounds)
    )
    
    return SELECTING_INBOUND


async def select_inbound(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """انتخاب inbound"""
    query = update.callback_query
    await query.answer()
    
    # استخراج inbound_id از callback_data
    inbound_id = int(query.data.split("_")[-1])
    context.user_data["inbound_id"] = inbound_id
    
    await query.edit_message_text(
        "📝 لطفاً نام کاربری برای کانفیگ وارد کنید:\n"
        "(فقط حروف انگلیسی و اعداد)",
        reply_markup=get_cancel_keyboard()
    )
    
    return ENTERING_USERNAME


async def enter_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """وارد کردن نام کاربری"""
    username = update.message.text.strip()
    
    # اعتبارسنجی نام کاربری
    if not username.replace("_", "").replace("-", "").isalnum():
        await update.message.reply_text(
            "❌ نام کاربری نامعتبر است.\n"
            "فقط از حروف انگلیسی، اعداد و _ استفاده کنید.",
            reply_markup=get_cancel_keyboard()
        )
        return ENTERING_USERNAME
    
    # ایجاد ایمیل یکتا
    telegram_id = update.effective_user.id
    email = f"{username}_{telegram_id}_{int(time.time())}"
    context.user_data["email"] = email
    context.user_data["display_name"] = username
    
    await update.message.reply_text(
        "📊 حجم ترافیک را انتخاب کنید:",
        reply_markup=get_traffic_amount_keyboard()
    )
    
    return SELECTING_TRAFFIC


async def select_traffic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """انتخاب حجم ترافیک"""
    query = update.callback_query
    await query.answer()
    
    # بررسی اینکه آیا گزینه دلخواه انتخاب شده
    if query.data == "traffic_custom":
        await query.edit_message_text(
            "📊 حجم ترافیک را به گیگابایت وارد کنید:\n"
            "(مثال: 15 یا 25.5)",
            reply_markup=get_cancel_keyboard()
        )
        return ENTERING_CUSTOM_TRAFFIC
    
    # استخراج مقدار ترافیک
    traffic_gb = int(query.data.split("_")[-1])
    context.user_data["traffic_gb"] = traffic_gb
    
    await query.edit_message_text(
        "⏰ مدت زمان اعتبار را انتخاب کنید:",
        reply_markup=get_expiry_time_keyboard()
    )
    
    return SELECTING_EXPIRY


async def enter_custom_traffic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """وارد کردن حجم دلخواه"""
    try:
        traffic_gb = float(update.message.text.strip())
        if traffic_gb < 0:
            raise ValueError("Negative value")
    except ValueError:
        await update.message.reply_text(
            "❌ مقدار نامعتبر. لطفاً یک عدد مثبت وارد کنید.\n"
            "(مثال: 15 یا 25.5)",
            reply_markup=get_cancel_keyboard()
        )
        return ENTERING_CUSTOM_TRAFFIC
    
    context.user_data["traffic_gb"] = traffic_gb
    
    await update.message.reply_text(
        "⏰ مدت زمان اعتبار را انتخاب کنید:",
        reply_markup=get_expiry_time_keyboard()
    )
    
    return SELECTING_EXPIRY


async def select_expiry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """انتخاب زمان انقضا"""
    query = update.callback_query
    await query.answer()
    
    # بررسی اینکه آیا گزینه دلخواه انتخاب شده
    if query.data == "expiry_custom":
        await query.edit_message_text(
            "⏰ مدت زمان اعتبار را به روز وارد کنید:\n"
            "(مثال: 45 برای 45 روز)",
            reply_markup=get_cancel_keyboard()
        )
        return ENTERING_CUSTOM_EXPIRY
    
    # استخراج تعداد روز
    days = int(query.data.split("_")[-1])
    
    return await _process_expiry(update, context, days)


async def enter_custom_expiry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """وارد کردن زمان دلخواه"""
    try:
        days = int(update.message.text.strip())
        if days < 0:
            raise ValueError("Negative value")
    except ValueError:
        await update.message.reply_text(
            "❌ مقدار نامعتبر. لطفاً یک عدد صحیح مثبت وارد کنید.\n"
            "(مثال: 45 برای 45 روز)",
            reply_markup=get_cancel_keyboard()
        )
        return ENTERING_CUSTOM_EXPIRY
    
    return await _process_expiry(update, context, days, is_message=True)


async def _process_expiry(update: Update, context: ContextTypes.DEFAULT_TYPE, days: int, is_message: bool = False):
    """پردازش زمان انقضا و نمایش خلاصه"""
    if days > 0:
        expiry_time = int(time.time()) + (days * 24 * 60 * 60)
    else:
        expiry_time = 0  # نامحدود
    
    context.user_data["expiry_time"] = expiry_time
    context.user_data["expiry_days"] = days
    
    # نمایش خلاصه و تأیید
    traffic = context.user_data.get("traffic_gb", 0)
    traffic_text = f"{traffic} GB" if traffic > 0 else "نامحدود"
    expiry_text = f"{days} روز" if days > 0 else "نامحدود"
    
    summary = (
        f"📋 خلاصه کانفیگ:\n\n"
        f"👤 نام: {context.user_data.get('display_name')}\n"
        f"📊 حجم: {traffic_text}\n"
        f"⏰ اعتبار: {expiry_text}\n\n"
        f"آیا تأیید می‌کنید؟"
    )
    
    from keyboards import get_yes_no_keyboard
    
    if is_message:
        await update.message.reply_text(
            summary,
            reply_markup=get_yes_no_keyboard("confirm_create", "cancel")
        )
    else:
        query = update.callback_query
        await query.edit_message_text(
            summary,
            reply_markup=get_yes_no_keyboard("confirm_create", "cancel")
        )
    
    return CONFIRMING_CREATE


async def confirm_create_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تأیید ساخت کانفیگ"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    
    # دریافت داده‌ها
    inbound_id = context.user_data.get("inbound_id")
    email = context.user_data.get("email")
    traffic_gb = context.user_data.get("traffic_gb", 0)
    expiry_time = context.user_data.get("expiry_time", 0)
    
    await query.edit_message_text("⏳ در حال ساخت کانفیگ...")
    
    try:
        # ساخت کانفیگ در پنل
        async with Panel3XUI() as panel:
            result = await panel.add_client(
                inbound_id=inbound_id,
                email=email,
                total_gb=traffic_gb,
                expiry_time=expiry_time
            )
            
            if not result.get("success"):
                await query.edit_message_text(
                    f"❌ خطا در ساخت کانفیگ:\n{result.get('msg', 'Unknown error')}",
                    reply_markup=get_back_keyboard()
                )
                return ConversationHandler.END
            
            # ذخیره در دیتابیس
            config_id = await add_config(
                owner_telegram_id=telegram_id,
                panel_client_email=email,
                inbound_id=inbound_id,
                traffic_limit_gb=traffic_gb,
                expiry_time=expiry_time
            )
            
            # دریافت لینک‌ها
            sub_link = await panel.get_subscription_link(inbound_id, email)
            config_link = await panel.get_config_link(inbound_id, email)
        
        # نمایش نتیجه
        traffic_text = f"{traffic_gb} GB" if traffic_gb > 0 else "نامحدود"
        days = context.user_data.get("expiry_days", 0)
        expiry_text = f"{days} روز" if days > 0 else "نامحدود"
        
        message = (
            f"✅ کانفیگ با موفقیت ساخته شد!\n\n"
            f"👤 نام: {context.user_data.get('display_name')}\n"
            f"📧 ایمیل: {email}\n"
            f"📊 حجم: {traffic_text}\n"
            f"⏰ اعتبار: {expiry_text}\n"
        )
        
        if config_link:
            message += f"\n📱 لینک کانفیگ:\n`{config_link}`"
        
        if sub_link:
            message += f"\n\n🔗 لینک اشتراک:\n`{sub_link}`"
        
        await query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=get_back_keyboard()
        )
        
    except Exception as e:
        await query.edit_message_text(
            f"❌ خطا: {str(e)}",
            reply_markup=get_back_keyboard()
        )
    
    context.user_data.clear()
    return ConversationHandler.END


# ==================== مشاهده کانفیگ‌ها ====================

async def show_my_configs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش لیست کانفیگ‌های کاربر"""
    query = update.callback_query
    await query.answer()
    
    if not await check_user_access(update, context):
        return
    
    telegram_id = update.effective_user.id
    configs = await get_user_configs(telegram_id)
    
    if not configs:
        await query.edit_message_text(
            "📭 شما هنوز کانفیگی نساخته‌اید.",
            reply_markup=get_back_keyboard()
        )
        return
    
    await query.edit_message_text(
        f"📋 کانفیگ‌های شما ({len(configs)} عدد):\n\n"
        "یک کانفیگ را انتخاب کنید:",
        reply_markup=get_configs_list_keyboard(configs)
    )


async def view_config_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش جزئیات یک کانفیگ"""
    query = update.callback_query
    await query.answer()
    
    config_id = int(query.data.split("_")[-1])
    config = await get_config(config_id)
    
    if not config:
        await query.edit_message_text(
            "❌ کانفیگ یافت نشد.",
            reply_markup=get_back_keyboard()
        )
        return
    
    # دریافت ترافیک از پنل
    async with Panel3XUI() as panel:
        traffic_data = await panel.get_client_traffic(config["panel_client_email"])
    
    # بروزرسانی ترافیک در دیتابیس
    if traffic_data.get("success"):
        await update_config_traffic(config_id, traffic_data.get("total_gb", 0))
        used_gb = traffic_data.get("total_gb", 0)
    else:
        used_gb = config.get("traffic_used_gb", 0)
    
    # محاسبه اطلاعات
    limit_gb = config.get("traffic_limit_gb", 0)
    remaining_gb = max(0, limit_gb - used_gb) if limit_gb > 0 else "∞"
    
    expiry = config.get("expiry_time", 0)
    if expiry > 0:
        remaining_time = expiry - int(time.time())
        if remaining_time > 0:
            days = remaining_time // (24 * 60 * 60)
            hours = (remaining_time % (24 * 60 * 60)) // 3600
            expiry_text = f"{days} روز و {hours} ساعت"
        else:
            expiry_text = "❌ منقضی شده"
    else:
        expiry_text = "♾ نامحدود"
    
    limit_text = f"{limit_gb} GB" if limit_gb > 0 else "♾ نامحدود"
    remaining_text = format_traffic(remaining_gb) if isinstance(remaining_gb, float) else remaining_gb
    
    message = (
        f"📄 جزئیات کانفیگ:\n\n"
        f"📧 ایمیل: `{config['panel_client_email']}`\n"
        f"📊 حجم کل: {limit_text}\n"
        f"📉 مصرفی: {format_traffic(used_gb)}\n"
        f"📈 باقیمانده: {remaining_text}\n"
        f"⏰ اعتبار: {expiry_text}\n"
    )
    
    await query.edit_message_text(
        message,
        parse_mode="Markdown",
        reply_markup=get_config_detail_keyboard(config_id)
    )


async def show_config_traffic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش ترافیک کانفیگ"""
    query = update.callback_query
    await query.answer()
    
    config_id = int(query.data.split("_")[-1])
    config = await get_config(config_id)
    
    if not config:
        await query.answer("کانفیگ یافت نشد", show_alert=True)
        return
    
    async with Panel3XUI() as panel:
        traffic_data = await panel.get_client_traffic(config["panel_client_email"])
    
    if traffic_data.get("success"):
        message = (
            f"📊 آمار ترافیک:\n\n"
            f"⬆️ آپلود: {traffic_data.get('upload_gb', 0):.3f} GB\n"
            f"⬇️ دانلود: {traffic_data.get('download_gb', 0):.3f} GB\n"
            f"📈 کل: {traffic_data.get('total_gb', 0):.3f} GB"
        )
    else:
        message = "❌ خطا در دریافت آمار ترافیک"
    
    await query.answer(message, show_alert=True)


async def copy_config_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """کپی لینک کانفیگ"""
    query = update.callback_query
    await query.answer()
    
    config_id = int(query.data.split("_")[-1])
    config = await get_config(config_id)
    
    if not config:
        await query.answer("کانفیگ یافت نشد", show_alert=True)
        return
    
    async with Panel3XUI() as panel:
        config_link = await panel.get_config_link(
            config["inbound_id"], 
            config["panel_client_email"]
        )
        sub_link = await panel.get_subscription_link(
            config["inbound_id"],
            config["panel_client_email"]
        )
    
    message = f"📱 لینک کانفیگ:\n`{config_link}`"
    
    if sub_link:
        message += f"\n\n🔗 لینک اشتراک:\n`{sub_link}`"
    
    await query.edit_message_text(
        message,
        parse_mode="Markdown",
        reply_markup=get_back_keyboard()
    )


# ==================== حذف کانفیگ ====================

async def delete_config_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تأیید حذف کانفیگ"""
    query = update.callback_query
    await query.answer()
    
    config_id = int(query.data.split("_")[-1])
    
    await query.edit_message_text(
        "⚠️ آیا مطمئن هستید که می‌خواهید این کانفیگ را حذف کنید?\n\n"
        "توجه: حجم مصرفی این کانفیگ در سقف مصرفی شما باقی می‌ماند.",
        reply_markup=get_confirm_delete_keyboard(config_id)
    )


async def delete_config_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حذف نهایی کانفیگ"""
    query = update.callback_query
    await query.answer()
    
    config_id = int(query.data.split("_")[-1])
    config = await get_config(config_id)
    
    if not config:
        await query.edit_message_text(
            "❌ کانفیگ یافت نشد.",
            reply_markup=get_back_keyboard()
        )
        return
    
    # دریافت ترافیک فعلی
    async with Panel3XUI() as panel:
        traffic_data = await panel.get_client_traffic(config["panel_client_email"])
        final_traffic = traffic_data.get("total_gb", 0) if traffic_data.get("success") else 0
        
        # پیدا کردن uuid کلاینت
        client_info = await panel.get_client_by_email(config["panel_client_email"])
        
        if client_info.get("success"):
            uuid_str = client_info["client"].get("id")
            # حذف از پنل
            await panel.delete_client(config["inbound_id"], uuid_str)
    
    # حذف نرم از دیتابیس (حفظ ترافیک مصرفی)
    await delete_config(config_id, final_traffic)
    
    await query.edit_message_text(
        "✅ کانفیگ با موفقیت حذف شد.\n"
        f"📊 حجم مصرفی ({final_traffic:.2f} GB) در سقف مصرفی شما محاسبه می‌شود.",
        reply_markup=get_back_keyboard()
    )


# ==================== تمدید کانفیگ ====================

async def extend_config_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع تمدید - پرسیدن حجم اضافی"""
    query = update.callback_query
    await query.answer()
    
    config_id = int(query.data.split("_")[-1])
    config = await get_config(config_id)
    
    if not config:
        await query.edit_message_text(
            "❌ کانفیگ یافت نشد.",
            reply_markup=get_back_keyboard()
        )
        return
    
    context.user_data["extend_config_id"] = config_id
    context.user_data["extend_traffic_gb"] = 0
    context.user_data["extend_days"] = 0
    
    current_limit = config.get("traffic_limit_gb", 0)
    limit_text = f"{current_limit} GB" if current_limit > 0 else "نامحدود"
    
    await query.edit_message_text(
        f"📊 تمدید کانفیگ\n\n"
        f"حجم فعلی: {limit_text}\n\n"
        f"چقدر حجم اضافه شود؟",
        reply_markup=get_extend_traffic_keyboard(config_id)
    )


async def extend_select_traffic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """انتخاب حجم اضافی برای تمدید"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    config_id = int(parts[2])
    traffic_value = parts[3]
    
    if traffic_value == "custom":
        context.user_data["extend_config_id"] = config_id
        await query.edit_message_text(
            "📊 مقدار حجم اضافی را به گیگابایت وارد کنید:\n"
            "(مثال: 15)",
            reply_markup=get_cancel_keyboard()
        )
        return EXTEND_ENTERING_TRAFFIC
    
    traffic_gb = float(traffic_value)
    context.user_data["extend_config_id"] = config_id
    context.user_data["extend_traffic_gb"] = traffic_gb
    
    config = await get_config(config_id)
    current_expiry = config.get("expiry_time", 0)
    
    if current_expiry > 0:
        remaining = current_expiry - int(time.time())
        if remaining > 0:
            days = remaining // (24 * 60 * 60)
            expiry_text = f"{days} روز باقیمانده"
        else:
            expiry_text = "منقضی شده"
    else:
        expiry_text = "نامحدود"
    
    await query.edit_message_text(
        f"⏰ تمدید کانفیگ\n\n"
        f"زمان فعلی: {expiry_text}\n\n"
        f"چند روز اضافه شود؟",
        reply_markup=get_extend_time_keyboard(config_id)
    )


async def extend_enter_custom_traffic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """وارد کردن حجم دلخواه برای تمدید"""
    try:
        traffic_gb = float(update.message.text.strip())
        if traffic_gb < 0:
            raise ValueError()
    except ValueError:
        await update.message.reply_text(
            "❌ مقدار نامعتبر. لطفاً یک عدد مثبت وارد کنید.",
            reply_markup=get_cancel_keyboard()
        )
        return EXTEND_ENTERING_TRAFFIC
    
    config_id = context.user_data.get("extend_config_id")
    context.user_data["extend_traffic_gb"] = traffic_gb
    
    config = await get_config(config_id)
    current_expiry = config.get("expiry_time", 0)
    
    if current_expiry > 0:
        remaining = current_expiry - int(time.time())
        if remaining > 0:
            days = remaining // (24 * 60 * 60)
            expiry_text = f"{days} روز باقیمانده"
        else:
            expiry_text = "منقضی شده"
    else:
        expiry_text = "نامحدود"
    
    await update.message.reply_text(
        f"⏰ تمدید کانفیگ\n\n"
        f"زمان فعلی: {expiry_text}\n\n"
        f"چند روز اضافه شود؟",
        reply_markup=get_extend_time_keyboard(config_id)
    )
    
    return ConversationHandler.END


async def extend_select_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """انتخاب زمان اضافی برای تمدید"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    config_id = int(parts[2])
    time_value = parts[3]
    
    if time_value == "custom":
        context.user_data["extend_config_id"] = config_id
        await query.edit_message_text(
            "⏰ تعداد روز اضافی را وارد کنید:\n"
            "(مثال: 45)",
            reply_markup=get_cancel_keyboard()
        )
        return EXTEND_ENTERING_TIME
    
    days = int(time_value)
    context.user_data["extend_days"] = days
    
    # نمایش خلاصه
    return await show_extend_summary(update, context, config_id)


async def extend_enter_custom_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """وارد کردن زمان دلخواه برای تمدید"""
    try:
        days = int(update.message.text.strip())
        if days < 0:
            raise ValueError()
    except ValueError:
        await update.message.reply_text(
            "❌ مقدار نامعتبر. لطفاً یک عدد صحیح مثبت وارد کنید.",
            reply_markup=get_cancel_keyboard()
        )
        return EXTEND_ENTERING_TIME
    
    config_id = context.user_data.get("extend_config_id")
    context.user_data["extend_days"] = days
    
    # نمایش خلاصه
    return await show_extend_summary(update, context, config_id, is_message=True)


async def show_extend_summary(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                              config_id: int, is_message: bool = False):
    """نمایش خلاصه تمدید"""
    config = await get_config(config_id)
    
    traffic_gb = context.user_data.get("extend_traffic_gb", 0)
    days = context.user_data.get("extend_days", 0)
    
    current_limit = config.get("traffic_limit_gb", 0)
    new_limit = current_limit + traffic_gb
    
    current_expiry = config.get("expiry_time", 0)
    if current_expiry > 0 and current_expiry > int(time.time()):
        new_expiry = current_expiry + (days * 24 * 60 * 60)
    else:
        new_expiry = int(time.time()) + (days * 24 * 60 * 60) if days > 0 else 0
    
    # محاسبه روزهای باقیمانده جدید
    if new_expiry > 0:
        new_remaining_days = (new_expiry - int(time.time())) // (24 * 60 * 60)
        new_expiry_text = f"{new_remaining_days} روز"
    else:
        new_expiry_text = "نامحدود"
    
    traffic_text = f"+{traffic_gb} GB" if traffic_gb > 0 else "بدون تغییر"
    time_text = f"+{days} روز" if days > 0 else "بدون تغییر"
    
    summary = (
        f"📋 خلاصه تمدید:\n\n"
        f"📊 حجم: {current_limit} GB → {new_limit} GB ({traffic_text})\n"
        f"⏰ زمان: {new_expiry_text} ({time_text})\n\n"
        f"آیا تأیید می‌کنید؟"
    )
    
    if is_message:
        await update.message.reply_text(
            summary,
            reply_markup=get_extend_confirm_keyboard(config_id)
        )
    else:
        query = update.callback_query
        await query.edit_message_text(
            summary,
            reply_markup=get_extend_confirm_keyboard(config_id)
        )
    
    return ConversationHandler.END


async def extend_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تأیید نهایی تمدید"""
    query = update.callback_query
    await query.answer()
    
    config_id = int(query.data.split("_")[-1])
    config = await get_config(config_id)
    
    if not config:
        await query.edit_message_text(
            "❌ کانفیگ یافت نشد.",
            reply_markup=get_back_keyboard()
        )
        return
    
    traffic_gb = context.user_data.get("extend_traffic_gb", 0)
    days = context.user_data.get("extend_days", 0)
    
    # محاسبه مقادیر جدید
    current_limit = config.get("traffic_limit_gb", 0)
    new_limit = current_limit + traffic_gb
    
    current_expiry = config.get("expiry_time", 0)
    if current_expiry > 0 and current_expiry > int(time.time()):
        new_expiry = current_expiry + (days * 24 * 60 * 60)
    else:
        new_expiry = int(time.time()) + (days * 24 * 60 * 60) if days > 0 else current_expiry
    
    await query.edit_message_text("⏳ در حال تمدید...")
    
    try:
        # بروزرسانی در پنل
        async with Panel3XUI() as panel:
            client_info = await panel.get_client_by_email(config["panel_client_email"])
            
            if client_info.get("success"):
                uuid_str = client_info["client"].get("id")
                await panel.update_client(
                    inbound_id=config["inbound_id"],
                    uuid_str=uuid_str,
                    email=config["panel_client_email"],
                    total_gb=new_limit,
                    expiry_time=new_expiry
                )
        
        # بروزرسانی در دیتابیس
        await extend_config(config_id, new_expiry, traffic_gb)
        
        traffic_text = f"+{traffic_gb} GB" if traffic_gb > 0 else ""
        time_text = f"+{days} روز" if days > 0 else ""
        
        await query.edit_message_text(
            f"✅ کانفیگ با موفقیت تمدید شد!\n\n"
            f"📊 حجم جدید: {new_limit} GB {traffic_text}\n"
            f"⏰ زمان اضافه شده: {time_text}",
            reply_markup=get_back_keyboard()
        )
        
    except Exception as e:
        await query.edit_message_text(
            f"❌ خطا در تمدید: {str(e)}",
            reply_markup=get_back_keyboard()
        )
    
    context.user_data.clear()


# ==================== وضعیت ترافیک ====================

def format_traffic(gb: float) -> str:
    """فرمت ترافیک - نمایش MB برای مقادیر کوچک"""
    if gb < 0.01:  # کمتر از 10 MB
        return f"{gb * 1024:.1f} MB"
    elif gb < 1:
        return f"{gb * 1024:.0f} MB"
    else:
        return f"{gb:.2f} GB"


async def show_traffic_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش وضعیت ترافیک کاربر"""
    query = update.callback_query
    await query.answer()
    
    if not await check_user_access(update, context):
        return
    
    telegram_id = update.effective_user.id
    user = await get_user(telegram_id)
    
    total_used = await get_user_total_traffic(telegram_id)
    remaining = await get_user_remaining_traffic(telegram_id)
    limit = user.get("traffic_limit_gb", 0)
    
    percent = (total_used / limit * 100) if limit > 0 else 0
    
    # نوار پیشرفت
    filled = int(percent / 10)
    progress_bar = "▓" * filled + "░" * (10 - filled)
    
    configs = await get_user_configs(telegram_id)
    
    message = (
        f"📊 وضعیت ترافیک شما:\n\n"
        f"📈 سقف مجاز: {limit} GB\n"
        f"📉 مصرفی: {format_traffic(total_used)}\n"
        f"📊 باقیمانده: {format_traffic(remaining)}\n\n"
        f"[{progress_bar}] {percent:.1f}%\n\n"
        f"📋 تعداد کانفیگ‌ها: {len(configs)}"
    )
    
    await query.edit_message_text(
        message,
        reply_markup=get_back_keyboard()
    )


async def refresh_my_traffic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بروزرسانی ترافیک کاربر از پنل"""
    query = update.callback_query
    await query.answer("⏳ در حال بروزرسانی...")
    
    if not await check_user_access(update, context):
        return
    
    telegram_id = update.effective_user.id
    
    # دریافت کانفیگ‌های کاربر
    configs = await get_user_configs(telegram_id)
    
    if not configs:
        await query.answer("شما کانفیگی ندارید", show_alert=True)
        return
    
    try:
        async with Panel3XUI() as panel:
            for config in configs:
                traffic_data = await panel.get_client_traffic(config["panel_client_email"])
                if traffic_data.get("success"):
                    await update_config_traffic(config["id"], traffic_data.get("total_gb", 0))
        
        # نمایش وضعیت بروز شده
        user = await get_user(telegram_id)
        total_used = await get_user_total_traffic(telegram_id)
        remaining = await get_user_remaining_traffic(telegram_id)
        limit = user.get("traffic_limit_gb", 0)
        
        percent = (total_used / limit * 100) if limit > 0 else 0
        filled = int(percent / 10)
        progress_bar = "▓" * filled + "░" * (10 - filled)
        
        message = (
            f"✅ بروزرسانی انجام شد!\n\n"
            f"📊 وضعیت ترافیک شما:\n\n"
            f"📈 سقف مجاز: {limit} GB\n"
            f"📉 مصرفی: {format_traffic(total_used)}\n"
            f"📊 باقیمانده: {format_traffic(remaining)}\n\n"
            f"[{progress_bar}] {percent:.1f}%\n\n"
            f"📋 تعداد کانفیگ‌ها: {len(configs)}"
        )
        
        await query.edit_message_text(
            message,
            reply_markup=get_back_keyboard()
        )
        
    except Exception as e:
        await query.answer(f"خطا: {str(e)}", show_alert=True)


# ==================== راهنما ====================

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش راهنما"""
    query = update.callback_query
    await query.answer()
    
    help_text = (
        "📖 راهنمای استفاده از ربات:\n\n"
        "➕ **ساخت کانفیگ:**\n"
        "برای ساخت کانفیگ جدید، سرور، نام، حجم و زمان را انتخاب کنید.\n\n"
        "📋 **کانفیگ‌های من:**\n"
        "لیست کانفیگ‌های ساخته شده را مشاهده کنید.\n\n"
        "📊 **وضعیت ترافیک:**\n"
        "مصرف کلی و باقیمانده ترافیک خود را ببینید.\n\n"
        "⏰ **تمدید:**\n"
        "زمان اعتبار کانفیگ را افزایش دهید.\n\n"
        "🗑 **حذف:**\n"
        "کانفیگ حذف می‌شود اما حجم مصرفی در سقف شما باقی می‌ماند.\n\n"
        "⚠️ **توجه:**\n"
        "وقتی به 80% سقف ترافیک رسیدید، هشدار دریافت می‌کنید."
    )
    
    await query.edit_message_text(
        help_text,
        parse_mode="Markdown",
        reply_markup=get_back_keyboard()
    )


# ==================== ثبت هندلرها ====================

def get_user_handlers():
    """برگرداندن هندلرهای کاربر"""
    
    # مکالمه ساخت کانفیگ
    create_config_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(create_config_start, pattern="^create_config$")],
        states={
            SELECTING_INBOUND: [
                CallbackQueryHandler(select_inbound, pattern="^select_inbound_"),
            ],
            ENTERING_USERNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_username),
            ],
            SELECTING_TRAFFIC: [
                CallbackQueryHandler(select_traffic, pattern="^traffic_"),
            ],
            ENTERING_CUSTOM_TRAFFIC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_custom_traffic),
            ],
            SELECTING_EXPIRY: [
                CallbackQueryHandler(select_expiry, pattern="^expiry_"),
            ],
            ENTERING_CUSTOM_EXPIRY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_custom_expiry),
            ],
            CONFIRMING_CREATE: [
                CallbackQueryHandler(confirm_create_config, pattern="^confirm_create$"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_operation, pattern="^cancel$"),
            CallbackQueryHandler(back_to_main_menu, pattern="^back_main$"),
        ],
        per_message=False,
    )
    
    # مکالمه تمدید کانفیگ
    extend_config_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(extend_select_traffic, pattern="^ext_traffic_\\d+_custom$"),
            CallbackQueryHandler(extend_select_time, pattern="^ext_time_\\d+_custom$"),
        ],
        states={
            EXTEND_ENTERING_TRAFFIC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, extend_enter_custom_traffic),
            ],
            EXTEND_ENTERING_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, extend_enter_custom_time),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_operation, pattern="^cancel$"),
        ],
        per_message=False,
    )
    
    handlers = [
        CommandHandler("start", start_command),
        create_config_conv,
        extend_config_conv,
        CallbackQueryHandler(back_to_main_menu, pattern="^back_main$"),
        CallbackQueryHandler(show_my_configs, pattern="^my_configs$"),
        CallbackQueryHandler(view_config_detail, pattern="^view_config_"),
        CallbackQueryHandler(copy_config_link, pattern="^copy_config_"),
        CallbackQueryHandler(show_config_traffic, pattern="^config_traffic_"),
        CallbackQueryHandler(delete_config_confirm, pattern="^delete_config_"),
        CallbackQueryHandler(delete_config_final, pattern="^confirm_delete_"),
        # تمدید کانفیگ
        CallbackQueryHandler(extend_config_start, pattern="^extend_config_"),
        CallbackQueryHandler(extend_select_traffic, pattern="^ext_traffic_"),
        CallbackQueryHandler(extend_select_time, pattern="^ext_time_"),
        CallbackQueryHandler(extend_confirm, pattern="^ext_confirm_"),
        # سایر
        CallbackQueryHandler(show_traffic_status, pattern="^traffic_status$"),
        CallbackQueryHandler(refresh_my_traffic, pattern="^refresh_my_traffic$"),
        CallbackQueryHandler(show_help, pattern="^help$"),
    ]
    
    return handlers
