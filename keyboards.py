# کیبوردهای اینلاین ربات

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup


# ==================== کیبوردهای اصلی ====================

def get_main_menu_keyboard(is_admin: bool = False, is_sudo: bool = False) -> InlineKeyboardMarkup:
    """کیبورد منوی اصلی"""
    keyboard = [
        [
            InlineKeyboardButton("➕ ساخت کانفیگ", callback_data="create_config"),
            InlineKeyboardButton("📋 کانفیگ‌های من", callback_data="my_configs"),
        ],
        [
            InlineKeyboardButton("📊 وضعیت ترافیک", callback_data="traffic_status"),
            InlineKeyboardButton("🔄 بروزرسانی", callback_data="refresh_my_traffic"),
        ],
        [
            InlineKeyboardButton("ℹ️ راهنما", callback_data="help"),
        ],
    ]
    
    if is_admin or is_sudo:
        keyboard.append([
            InlineKeyboardButton("👨‍💼 پنل مدیریت", callback_data="admin_panel")
        ])
    
    return InlineKeyboardMarkup(keyboard)


def get_back_keyboard() -> InlineKeyboardMarkup:
    """کیبورد بازگشت"""
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]]
    return InlineKeyboardMarkup(keyboard)


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """کیبورد لغو"""
    keyboard = [[InlineKeyboardButton("❌ لغو", callback_data="cancel")]]
    return InlineKeyboardMarkup(keyboard)


# ==================== کیبوردهای ساخت کانفیگ ====================

def get_inbound_selection_keyboard(inbounds: list) -> InlineKeyboardMarkup:
    """کیبورد انتخاب inbound"""
    keyboard = []
    
    for inbound in inbounds:
        inbound_id = inbound.get("id")
        remark = inbound.get("remark", f"Inbound {inbound_id}")
        protocol = inbound.get("protocol", "").upper()
        
        keyboard.append([
            InlineKeyboardButton(
                f"🔹 {remark} ({protocol})",
                callback_data=f"select_inbound_{inbound_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("❌ لغو", callback_data="cancel")])
    
    return InlineKeyboardMarkup(keyboard)


def get_traffic_amount_keyboard() -> InlineKeyboardMarkup:
    """کیبورد انتخاب حجم ترافیک"""
    keyboard = [
        [
            InlineKeyboardButton("5 GB", callback_data="traffic_5"),
            InlineKeyboardButton("10 GB", callback_data="traffic_10"),
            InlineKeyboardButton("20 GB", callback_data="traffic_20"),
        ],
        [
            InlineKeyboardButton("30 GB", callback_data="traffic_30"),
            InlineKeyboardButton("50 GB", callback_data="traffic_50"),
            InlineKeyboardButton("100 GB", callback_data="traffic_100"),
        ],
        [
            InlineKeyboardButton("♾ نامحدود", callback_data="traffic_0"),
            InlineKeyboardButton("✏️ دلخواه", callback_data="traffic_custom"),
        ],
        [InlineKeyboardButton("❌ لغو", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_expiry_time_keyboard() -> InlineKeyboardMarkup:
    """کیبورد انتخاب زمان انقضا"""
    keyboard = [
        [
            InlineKeyboardButton("1 هفته", callback_data="expiry_7"),
            InlineKeyboardButton("2 هفته", callback_data="expiry_14"),
        ],
        [
            InlineKeyboardButton("1 ماه", callback_data="expiry_30"),
            InlineKeyboardButton("2 ماه", callback_data="expiry_60"),
        ],
        [
            InlineKeyboardButton("3 ماه", callback_data="expiry_90"),
            InlineKeyboardButton("6 ماه", callback_data="expiry_180"),
        ],
        [
            InlineKeyboardButton("♾ نامحدود", callback_data="expiry_0"),
            InlineKeyboardButton("✏️ دلخواه", callback_data="expiry_custom"),
        ],
        [InlineKeyboardButton("❌ لغو", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)


# ==================== کیبوردهای لیست کانفیگ ====================

def get_configs_list_keyboard(configs: list) -> InlineKeyboardMarkup:
    """کیبورد لیست کانفیگ‌ها"""
    keyboard = []
    
    for config in configs:
        config_id = config.get("id")
        email = config.get("panel_client_email", "Unknown")
        
        # کوتاه کردن نام اگر طولانی است
        display_name = email[:20] + "..." if len(email) > 20 else email
        
        keyboard.append([
            InlineKeyboardButton(
                f"📄 {display_name}",
                callback_data=f"view_config_{config_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")])
    
    return InlineKeyboardMarkup(keyboard)


def get_config_detail_keyboard(config_id: int) -> InlineKeyboardMarkup:
    """کیبورد جزئیات کانفیگ"""
    keyboard = [
        [
            InlineKeyboardButton("📋 کپی کانفیگ", callback_data=f"copy_config_{config_id}"),
            InlineKeyboardButton("📊 ترافیک", callback_data=f"config_traffic_{config_id}"),
        ],
        [
            InlineKeyboardButton("⏰ تمدید", callback_data=f"extend_config_{config_id}"),
            InlineKeyboardButton("🗑 حذف", callback_data=f"delete_config_{config_id}"),
        ],
        [InlineKeyboardButton("🔙 بازگشت به لیست", callback_data="my_configs")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_confirm_delete_keyboard(config_id: int) -> InlineKeyboardMarkup:
    """کیبورد تأیید حذف"""
    keyboard = [
        [
            InlineKeyboardButton("✅ بله، حذف شود", callback_data=f"confirm_delete_{config_id}"),
            InlineKeyboardButton("❌ انصراف", callback_data=f"view_config_{config_id}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_extend_traffic_keyboard(config_id: int) -> InlineKeyboardMarkup:
    """کیبورد انتخاب حجم اضافی برای تمدید"""
    keyboard = [
        [
            InlineKeyboardButton("5 GB", callback_data=f"ext_traffic_{config_id}_5"),
            InlineKeyboardButton("10 GB", callback_data=f"ext_traffic_{config_id}_10"),
            InlineKeyboardButton("20 GB", callback_data=f"ext_traffic_{config_id}_20"),
        ],
        [
            InlineKeyboardButton("30 GB", callback_data=f"ext_traffic_{config_id}_30"),
            InlineKeyboardButton("50 GB", callback_data=f"ext_traffic_{config_id}_50"),
        ],
        [
            InlineKeyboardButton("بدون تغییر", callback_data=f"ext_traffic_{config_id}_0"),
            InlineKeyboardButton("✏️ دلخواه", callback_data=f"ext_traffic_{config_id}_custom"),
        ],
        [InlineKeyboardButton("❌ لغو", callback_data=f"view_config_{config_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_extend_time_keyboard(config_id: int) -> InlineKeyboardMarkup:
    """کیبورد انتخاب زمان اضافی برای تمدید"""
    keyboard = [
        [
            InlineKeyboardButton("1 هفته", callback_data=f"ext_time_{config_id}_7"),
            InlineKeyboardButton("2 هفته", callback_data=f"ext_time_{config_id}_14"),
        ],
        [
            InlineKeyboardButton("1 ماه", callback_data=f"ext_time_{config_id}_30"),
            InlineKeyboardButton("2 ماه", callback_data=f"ext_time_{config_id}_60"),
        ],
        [
            InlineKeyboardButton("بدون تغییر", callback_data=f"ext_time_{config_id}_0"),
            InlineKeyboardButton("✏️ دلخواه", callback_data=f"ext_time_{config_id}_custom"),
        ],
        [InlineKeyboardButton("❌ لغو", callback_data=f"view_config_{config_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_extend_confirm_keyboard(config_id: int) -> InlineKeyboardMarkup:
    """کیبورد تأیید تمدید"""
    keyboard = [
        [
            InlineKeyboardButton("✅ تأیید و تمدید", callback_data=f"ext_confirm_{config_id}"),
            InlineKeyboardButton("❌ انصراف", callback_data=f"view_config_{config_id}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


# ==================== کیبوردهای ادمین ====================

def get_admin_panel_keyboard() -> InlineKeyboardMarkup:
    """کیبورد پنل ادمین"""
    keyboard = [
        [
            InlineKeyboardButton("👥 مدیریت کاربران", callback_data="admin_users"),
            InlineKeyboardButton("📊 آمار کلی", callback_data="admin_stats"),
        ],
        [
            InlineKeyboardButton("➕ افزودن کاربر", callback_data="admin_add_user"),
            InlineKeyboardButton("🔍 جستجو", callback_data="admin_search"),
        ],
        [
            InlineKeyboardButton("📋 همه کانفیگ‌ها", callback_data="admin_all_configs"),
        ],
        [
            InlineKeyboardButton("🔄 همگام‌سازی ترافیک", callback_data="admin_sync_traffic"),
        ],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_admin_users_list_keyboard(users: list, page: int = 0, per_page: int = 10) -> InlineKeyboardMarkup:
    """کیبورد لیست کاربران برای ادمین"""
    keyboard = []
    
    start = page * per_page
    end = start + per_page
    page_users = users[start:end]
    
    for user in page_users:
        telegram_id = user.get("telegram_id")
        status = "🚫" if user.get("is_blocked") else "✅"
        role = "👑" if user.get("is_sudo") else "👨‍💼" if user.get("is_admin") else "👤"
        
        keyboard.append([
            InlineKeyboardButton(
                f"{role} {status} {telegram_id}",
                callback_data=f"admin_user_{telegram_id}"
            )
        ])
    
    # دکمه‌های صفحه‌بندی
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"users_page_{page-1}"))
    if end < len(users):
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"users_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(keyboard)


def get_admin_user_detail_keyboard(telegram_id: int, is_blocked: bool) -> InlineKeyboardMarkup:
    """کیبورد جزئیات کاربر برای ادمین"""
    block_text = "🔓 رفع مسدودی" if is_blocked else "🔒 مسدود کردن"
    block_action = "unblock" if is_blocked else "block"
    
    keyboard = [
        [
            InlineKeyboardButton(block_text, callback_data=f"admin_{block_action}_{telegram_id}"),
            InlineKeyboardButton("📊 مصرف", callback_data=f"admin_usage_{telegram_id}"),
        ],
        [
            InlineKeyboardButton("📝 تغییر حد ترافیک", callback_data=f"admin_limit_{telegram_id}"),
            InlineKeyboardButton("📋 کانفیگ‌ها", callback_data=f"admin_configs_{telegram_id}"),
        ],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_users")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_traffic_limit_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    """کیبورد تنظیم حد ترافیک"""
    keyboard = [
        [
            InlineKeyboardButton("25 GB", callback_data=f"set_limit_{telegram_id}_25"),
            InlineKeyboardButton("50 GB", callback_data=f"set_limit_{telegram_id}_50"),
            InlineKeyboardButton("100 GB", callback_data=f"set_limit_{telegram_id}_100"),
        ],
        [
            InlineKeyboardButton("200 GB", callback_data=f"set_limit_{telegram_id}_200"),
            InlineKeyboardButton("500 GB", callback_data=f"set_limit_{telegram_id}_500"),
            InlineKeyboardButton("1 TB", callback_data=f"set_limit_{telegram_id}_1000"),
        ],
        [
            InlineKeyboardButton("📝 وارد کردن دستی", callback_data=f"manual_limit_{telegram_id}"),
        ],
        [InlineKeyboardButton("🔙 بازگشت", callback_data=f"admin_user_{telegram_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)


# ==================== کیبورد Yes/No ====================

def get_yes_no_keyboard(yes_callback: str, no_callback: str) -> InlineKeyboardMarkup:
    """کیبورد بله/خیر"""
    keyboard = [
        [
            InlineKeyboardButton("✅ بله", callback_data=yes_callback),
            InlineKeyboardButton("❌ خیر", callback_data=no_callback),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
