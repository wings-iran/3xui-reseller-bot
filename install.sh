#!/bin/bash

# تنظیمات رنگ برای خروجی
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# تابع برای نمایش پیام
print_message() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# تشخیص کاربر فعلی
CURRENT_USER=${SUDO_USER:-$USER}
if [[ -z "$CURRENT_USER" ]]; then
    CURRENT_USER=$(whoami)
fi

# اگر با root اجرا شده، از root استفاده می‌کنیم
if [[ $EUID -eq 0 ]]; then
    CURRENT_USER="root"
    SUDO_CMD=""
else
    SUDO_CMD="sudo"
fi

# گرفتن مسیر اسکریپت و پروژه
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"

# چک کردن آیا python3 نصب است
if ! command -v python3 &> /dev/null; then
    print_error "Python3 نصب نیست. لطفاً ابتدا Python3 را نصب کنید:"
    if [[ $EUID -eq 0 ]]; then
        echo "apt update && apt install python3 python3-pip -y"
    else
        echo "sudo apt update && sudo apt install python3 python3-pip -y"
    fi
    exit 1
fi

echo ""
echo "======================================"
echo "    نصب ربات تلگرام مدیریت پنل 3X-UI"
echo "======================================"
echo ""

# رفتن به پوشه پروژه
cd "$SCRIPT_DIR"

# ایجاد فایل تنظیمات محلی
print_message "آماده‌سازی فایل تنظیمات..."

CONFIG_DIR="$SCRIPT_DIR/config"
LOCAL_CONFIG="$CONFIG_DIR/local.py"
SAMPLE_CONFIG="$CONFIG_DIR/config.py"

# اطمینان از وجود پوشه config
if [[ ! -d "$CONFIG_DIR" ]]; then
    print_error "پوشه config یافت نشد!"
    exit 1
fi

if [[ ! -f "$SAMPLE_CONFIG" ]]; then
    print_error "فایل config/config.py یافت نشد!"
    exit 1
fi

# ایجاد فایل local.py از نمونه
if [[ ! -f "$LOCAL_CONFIG" ]]; then
    print_message "کپی کردن فایل تنظیمات نمونه..."
    cp "$SAMPLE_CONFIG" "$LOCAL_CONFIG"
    print_success "فایل config/local.py ایجاد شد"
else
    print_warning "فایل config/local.py از قبل وجود دارد"
    read -p "آیا می‌خواهید آن را بازنویسی کنید؟ (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cp "$SAMPLE_CONFIG" "$LOCAL_CONFIG"
        print_success "فایل config/local.py بازنویسی شد"
    fi
fi

echo ""
echo "⚠️  مرحله مهم: تنظیم فایل config/local.py"
echo ""

# دریافت اطلاعات از کاربر
print_message "دریافت اطلاعات مورد نیاز..."

# دریافت توکن ربات (از متغیر محیطی یا از کاربر)
if [[ -n "$BOT_TOKEN" ]]; then
    print_message "استفاده از توکن از متغیر محیطی"
else
    read -p "توکن ربات تلگرام (از @BotFather): " BOT_TOKEN
fi
if [[ -z "$BOT_TOKEN" ]]; then
    print_error "توکن ربات نمی‌تواند خالی باشد!"
    exit 1
fi

# دریافت آیدی ادمین (از متغیر محیطی یا از کاربر)
if [[ -n "$ADMIN_ID" ]]; then
    print_message "استفاده از آیدی ادمین از متغیر محیطی"
else
    read -p "آیدی عددی ادمین تلگرام: " ADMIN_ID
fi
if [[ -z "$ADMIN_ID" ]] || ! [[ "$ADMIN_ID" =~ ^[0-9]+$ ]]; then
    print_error "آیدی ادمین باید یک عدد باشد!"
    exit 1
fi

# دریافت آدرس پنل (از متغیر محیطی یا از کاربر)
if [[ -n "$PANEL_URL" ]]; then
    print_message "استفاده از آدرس پنل از متغیر محیطی"
else
    read -p "آدرس پنل 3X-UI (مثال: https://panel.example.com:2053): " PANEL_URL
fi
if [[ -z "$PANEL_URL" ]]; then
    print_error "آدرس پنل نمی‌تواند خالی باشد!"
    exit 1
fi

# دریافت نام کاربری پنل (از متغیر محیطی یا از کاربر)
if [[ -n "$PANEL_USERNAME" ]]; then
    print_message "استفاده از نام کاربری پنل از متغیر محیطی"
else
    read -p "نام کاربری پنل (پیش‌فرض: admin): " PANEL_USERNAME
    PANEL_USERNAME=${PANEL_USERNAME:-admin}
fi
PANEL_USERNAME=${PANEL_USERNAME:-admin}

# دریافت رمز عبور پنل (از متغیر محیطی یا از کاربر)
if [[ -n "$PANEL_PASSWORD" ]]; then
    print_message "استفاده از رمز عبور پنل از متغیر محیطی"
else
    read -sp "رمز عبور پنل: " PANEL_PASSWORD
    echo ""
fi
if [[ -z "$PANEL_PASSWORD" ]]; then
    print_error "رمز عبور پنل نمی‌تواند خالی باشد!"
    exit 1
fi

# به‌روزرسانی فایل config/local.py
print_message "به‌روزرسانی فایل تنظیمات..."

# محاسبه مسیر نسبی دیتابیس
DB_PATH="$SCRIPT_DIR/data.db"

# جایگزینی مقادیر در فایل config
sed -i "s|BOT_TOKEN = \".*\"|BOT_TOKEN = \"$BOT_TOKEN\"|g" "$LOCAL_CONFIG"
sed -i "s|SUDO_ADMIN_ID = .*|SUDO_ADMIN_ID = $ADMIN_ID|g" "$LOCAL_CONFIG"
sed -i "s|PANEL_URL = \".*\"|PANEL_URL = \"$PANEL_URL\"|g" "$LOCAL_CONFIG"
sed -i "s|PANEL_USERNAME = \".*\"|PANEL_USERNAME = \"$PANEL_USERNAME\"|g" "$LOCAL_CONFIG"
sed -i "s|PANEL_PASSWORD = \".*\"|PANEL_PASSWORD = \"$PANEL_PASSWORD\"|g" "$LOCAL_CONFIG"
sed -i "s|DATABASE_PATH = \".*\"|DATABASE_PATH = \"$DB_PATH\"|g" "$LOCAL_CONFIG"

print_success "فایل تنظیمات به‌روزرسانی شد"

# چک کردن پر بودن تنظیمات مهم
if grep -q "BOT_TOKEN.*YOUR_BOT_TOKEN" "$LOCAL_CONFIG" || grep -q "BOT_TOKEN.*=\"\"" "$LOCAL_CONFIG"; then
    print_error "BOT_TOKEN تنظیم نشده است!"
    exit 1
fi

if grep -q "SUDO_ADMIN_ID.*123456789" "$LOCAL_CONFIG"; then
    print_error "SUDO_ADMIN_ID تنظیم نشده است!"
    exit 1
fi

if grep -q "PANEL_URL.*your-panel.com" "$LOCAL_CONFIG" || grep -q "PANEL_URL.*=\"\"" "$LOCAL_CONFIG"; then
    print_error "PANEL_URL تنظیم نشده است!"
    exit 1
fi

if grep -q "PANEL_PASSWORD.*YOUR_PANEL_PASSWORD" "$LOCAL_CONFIG" || grep -q "PANEL_PASSWORD.*=\"\"" "$LOCAL_CONFIG"; then
    print_error "PANEL_PASSWORD تنظیم نشده است!"
    exit 1
fi

print_success "فایل تنظیمات تأیید شد"

# نصب وابستگی‌های پایتون
print_message "نصب وابستگی‌های پایتون..."
if [[ $EUID -eq 0 ]]; then
    pip3 install -r requirements.txt
else
    pip3 install --user -r requirements.txt || pip3 install -r requirements.txt
fi

if [[ $? -ne 0 ]]; then
    print_error "خطا در نصب وابستگی‌ها!"
    exit 1
fi

print_success "وابستگی‌ها با موفقیت نصب شدند"

# ایجاد سرویس systemd
print_message "ایجاد سرویس systemd..."

SERVICE_FILE="/etc/systemd/system/3xui-bot.service"

# تعیین دستور sudo
if [[ $EUID -eq 0 ]]; then
    SUDO_PREFIX=""
else
    SUDO_PREFIX="sudo"
fi

cat > /tmp/3xui-bot.service << EOF
[Unit]
Description=3X-UI Telegram Bot
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$SCRIPT_DIR
ExecStart=$(which python3) $SCRIPT_DIR/bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

$SUDO_PREFIX mv /tmp/3xui-bot.service "$SERVICE_FILE"
$SUDO_PREFIX chmod 644 "$SERVICE_FILE"

print_success "سرویس systemd ایجاد شد"

# فعال‌سازی و شروع سرویس
print_message "فعال‌سازی سرویس..."
$SUDO_PREFIX systemctl daemon-reload
$SUDO_PREFIX systemctl enable 3xui-bot.service

# تست اجرای ربات قبل از شروع سرویس
print_message "تست اجرای ربات..."
timeout 5 python3 bot.py > /tmp/bot_test.log 2>&1 &
TEST_PID=$!
sleep 3
if ps -p $TEST_PID > /dev/null; then
    kill $TEST_PID 2>/dev/null
    print_success "تست اجرا موفق بود"
else
    print_warning "تست اجرا مشکل داشت، اما ادامه می‌دهیم..."
    cat /tmp/bot_test.log 2>/dev/null || true
fi

# شروع سرویس
print_message "شروع سرویس..."
$SUDO_PREFIX systemctl start 3xui-bot.service

# چک کردن وضعیت
sleep 3
if $SUDO_PREFIX systemctl is-active --quiet 3xui-bot.service; then
    print_success "ربات با موفقیت نصب و اجرا شد!"
    echo ""
    echo "======================================"
    echo "✅ نصب تکمیل شد!"
    echo ""
    echo "🔧 دستورات مفید:"
    if [[ $EUID -eq 0 ]]; then
        echo "  systemctl status 3xui-bot    # وضعیت ربات"
        echo "  systemctl restart 3xui-bot   # ریستارت ربات"
        echo "  systemctl stop 3xui-bot      # توقف ربات"
        echo "  journalctl -u 3xui-bot -f    # مشاهده لاگ زنده"
    else
        echo "  sudo systemctl status 3xui-bot    # وضعیت ربات"
        echo "  sudo systemctl restart 3xui-bot   # ریستارت ربات"
        echo "  sudo systemctl stop 3xui-bot      # توقف ربات"
        echo "  sudo journalctl -u 3xui-bot -f     # مشاهده لاگ زنده"
    fi
    echo ""
    echo "📊 آمار:"
    $SUDO_PREFIX systemctl status 3xui-bot.service --no-pager | grep -E "(Active|Main PID|Memory|CPU)" || true
    echo ""
    echo "======================================"
else
    print_error "ربات اجرا نشد. لطفاً لاگ‌ها را چک کنید:"
    if [[ $EUID -eq 0 ]]; then
        echo "journalctl -u 3xui-bot -n 20"
    else
        echo "sudo journalctl -u 3xui-bot -n 20"
    fi
    exit 1
fi
