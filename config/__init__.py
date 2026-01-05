# -*- coding: utf-8 -*-
"""
ماژول تنظیمات ربات
اولویت: config.local > config
"""

import os
import sys

# اضافه کردن مسیر پدر به sys.path برای import
_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_current_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

# بارگذاری تنظیمات
try:
    # اول سعی می‌کنیم از config.local بارگذاری کنیم
    from .local import *
    print("✅ تنظیمات از config.local بارگذاری شد")
except ImportError:
    try:
        # اگر config.local موجود نبود، از config بارگذاری می‌کنیم
        from .config import *
        print("⚠️ تنظیمات از config.py بارگذاری شد (برای توسعه)")
    except ImportError:
        print("❌ فایل تنظیمات یافت نشد!")
        sys.exit(1)

# بررسی تنظیمات ضروری (فقط چک کردن وجود مقدار)
required_settings = ['BOT_TOKEN', 'SUDO_ADMIN_ID', 'PANEL_URL', 'PANEL_PASSWORD']

for setting in required_settings:
    value = globals().get(setting)
    if not value or str(value).strip() == '':
        print(f"❌ تنظیم {setting} خالی است")
        print("لطفاً فایل config/local.py را ویرایش کنید.")
        sys.exit(1)

print("✅ تنظیمات با موفقیت بارگذاری شد")