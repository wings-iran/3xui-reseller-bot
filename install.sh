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

# چک کردن اینکه آیا اسکریپت با sudo اجرا شده
if [[ $EUID -eq 0 ]]; then
   print_error "این اسکریپت نباید با sudo اجرا شود"
   exit 1
fi

# گرفتن مسیر اسکریپت و پروژه
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# چک کردن آیا python3 نصب است
if ! command -v python3 &> /dev/null; then
    print_error "Python3 نصب نیست. لطفاً ابتدا Python3 را نصب کنید:"
    echo "sudo apt update && sudo apt install python3 python3-pip -y"
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

if [[ ! -f "config.local.py" ]]; then
    print_message "کپی کردن فایل تنظیمات نمونه..."
    cp config.py config.local.py
    print_success "فایل config.local.py ایجاد شد"
else
    print_warning "فایل config.local.py از قبل وجود دارد"
fi

echo ""
echo "⚠️  مرحله مهم: تنظیم فایل config.local.py"
echo ""
echo "لطفاً فایل config.local.py را با تنظیمات خود ویرایش کنید:"
echo "  nano config.local.py"
echo ""
echo "تنظیمات مورد نیاز:"
echo "  • BOT_TOKEN: توکن ربات از @BotFather"
echo "  • SUDO_ADMIN_ID: آیدی عددی ادمین"
echo "  • PANEL_URL: آدرس پنل 3X-UI"
echo "  • PANEL_USERNAME: نام کاربری پنل"
echo "  • PANEL_PASSWORD: رمز عبور پنل"
echo ""

# پرسیدن از کاربر برای ادامه
while true; do
    read -p "آیا فایل config.local.py را ویرایش کرده‌اید؟ (y/N): " -n 1 -r
    echo ""
    case $REPLY in
        [Yy]* ) break;;
        [Nn]* ) echo "لطفاً ابتدا فایل را ویرایش کنید."; exit 1;;
        "" ) echo "لطفاً ابتدا فایل را ویرایش کنید."; exit 1;;
        * ) echo "لطفاً y یا n وارد کنید.";;
    esac
done

echo ""
print_message "شروع نصب..."
# چک کردن وجود فایل تنظیمات
if [[ ! -f "config.local.py" ]]; then
    print_error "فایل config.local.py یافت نشد! لطفاً ابتدا آن را ایجاد کنید."
    exit 1
fi

# چک کردن پر بودن تنظیمات مهم
if ! grep -q "BOT_TOKEN.*=" config.local.py || grep -q "BOT_TOKEN.*YOUR_BOT_TOKEN" config.local.py; then
    print_error "BOT_TOKEN تنظیم نشده است. لطفاً config.local.py را ویرایش کنید."
    exit 1
fi

if ! grep -q "SUDO_ADMIN_ID.*=" config.local.py || grep -q "SUDO_ADMIN_ID.*123456789" config.local.py; then
    print_error "SUDO_ADMIN_ID تنظیم نشده است. لطفاً config.local.py را ویرایش کنید."
    exit 1
fi

if ! grep -q "PANEL_URL.*=" config.local.py || grep -q "PANEL_URL.*your-panel.com" config.local.py; then
    print_error "PANEL_URL تنظیم نشده است. لطفاً config.local.py را ویرایش کنید."
    exit 1
fi

if ! grep -q "PANEL_PASSWORD.*=" config.local.py || grep -q "PANEL_PASSWORD.*YOUR_PANEL_PASSWORD" config.local.py; then
    print_error "PANEL_PASSWORD تنظیم نشده است. لطفاً config.local.py را ویرایش کنید."
    exit 1
fi

print_success "فایل تنظیمات تأیید شد"

# نصب وابستگی‌های پایتون
print_message "نصب وابستگی‌های پایتون..."
pip3 install -r requirements.txt

# ایجاد سرویس systemd
print_message "ایجاد سرویس systemd..."
sudo tee /etc/systemd/system/3xui-bot.service > /dev/null << EOF
[Unit]
Description=3X-UI Telegram Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
ExecStart=$(which python3) $(pwd)/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# فعال‌سازی و شروع سرویس
print_message "فعال‌سازی سرویس..."
sudo systemctl daemon-reload
sudo systemctl enable 3xui-bot.service
sudo systemctl start 3xui-bot.service

# چک کردن وضعیت
sleep 3
if sudo systemctl is-active --quiet 3xui-bot.service; then
    print_success "ربات با موفقیت نصب و اجرا شد!"
    echo ""
    echo "======================================"
    echo "✅ نصب تکمیل شد!"
    echo ""
    echo "🔧 دستورات مفید:"
    echo "  systemctl status 3xui-bot    # وضعیت ربات"
    echo "  systemctl restart 3xui-bot   # ریستارت ربات"
    echo "  systemctl stop 3xui-bot      # توقف ربات"
    echo "  journalctl -u 3xui-bot -f    # مشاهده لاگ زنده"
    echo ""
    echo "📊 آمار:"
    sudo systemctl status 3xui-bot.service --no-pager | grep -E "(Active|Main PID|Memory|CPU)"
    echo ""
    echo "======================================"
else
    print_error "ربات اجرا نشد. لطفاً لاگ‌ها را چک کنید:"
    echo "journalctl -u 3xui-bot -n 20"
fi