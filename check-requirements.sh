#!/bin/bash

# تنظیمات رنگ
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "======================================"
echo "    بررسی نیازمندی‌های سیستم"
echo "======================================"
echo ""

# چک کردن Python3
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo -e "${GREEN}✅${NC} Python3 نصب است: $PYTHON_VERSION"
else
    echo -e "${RED}❌${NC} Python3 نصب نیست"
    echo "   نصب: sudo apt update && sudo apt install python3 python3-pip -y"
fi

# چک کردن pip3
if command -v pip3 &> /dev/null; then
    echo -e "${GREEN}✅${NC} pip3 نصب است"
else
    echo -e "${RED}❌${NC} pip3 نصب نیست"
    echo "   نصب: sudo apt update && sudo apt install python3-pip -y"
fi

# چک کردن git
if command -v git &> /dev/null; then
    echo -e "${GREEN}✅${NC} Git نصب است"
else
    echo -e "${RED}❌${NC} Git نصب نیست"
    echo "   نصب: sudo apt update && sudo apt install git -y"
fi

# چک کردن دسترسی sudo
if sudo -n true 2>/dev/null; then
    echo -e "${GREEN}✅${NC} دسترسی sudo موجود است"
else
    echo -e "${YELLOW}⚠️${NC}  دسترسی sudo نیاز است (برای نصب سرویس systemd)"
fi

# چک کردن پورت‌های باز (اختیاری)
echo ""
echo -e "${BLUE}ℹ️${NC}  یادآوری: مطمئن شوید پنل 3X-UI شما قابل دسترسی است"
echo -e "${BLUE}ℹ️${NC}  و ربات تلگرام شما توسط @BotFather ساخته شده"

echo ""
if [[ -f "install.sh" ]]; then
    echo -e "${GREEN}✅${NC} فایل install.sh موجود است"
    echo -e "${BLUE}💡${NC} برای شروع نصب: ./install.sh"
else
    echo -e "${RED}❌${NC} فایل install.sh یافت نشد"
fi

echo ""
echo "======================================"