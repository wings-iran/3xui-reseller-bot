# مدیریت دیتابیس SQLite

import aiosqlite
from datetime import datetime
from config import DATABASE_PATH


async def init_db():
    """ایجاد جداول دیتابیس"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # جدول کاربران
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                is_admin BOOLEAN DEFAULT 0,
                is_sudo BOOLEAN DEFAULT 0,
                traffic_limit_gb REAL DEFAULT 50,
                is_blocked BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # جدول کانفیگ‌ها
        await db.execute("""
            CREATE TABLE IF NOT EXISTS configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_telegram_id INTEGER NOT NULL,
                panel_client_email TEXT NOT NULL,
                inbound_id INTEGER NOT NULL,
                traffic_limit_gb REAL NOT NULL,
                traffic_used_gb REAL DEFAULT 0,
                expiry_time INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_deleted BOOLEAN DEFAULT 0,
                deleted_traffic_gb REAL DEFAULT 0,
                FOREIGN KEY (owner_telegram_id) REFERENCES users(telegram_id)
            )
        """)
        
        # جدول تنظیمات
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        await db.commit()


# ==================== توابع مربوط به کاربران ====================

async def add_user(telegram_id: int, is_admin: bool = False, is_sudo: bool = False, 
                   traffic_limit_gb: float = 50) -> bool:
    """افزودن کاربر جدید"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            await db.execute("""
                INSERT OR IGNORE INTO users (telegram_id, is_admin, is_sudo, traffic_limit_gb)
                VALUES (?, ?, ?, ?)
            """, (telegram_id, is_admin, is_sudo, traffic_limit_gb))
            await db.commit()
            return True
        except Exception as e:
            print(f"Error adding user: {e}")
            return False


async def get_user(telegram_id: int) -> dict | None:
    """دریافت اطلاعات کاربر"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None


async def get_all_users() -> list:
    """دریافت لیست همه کاربران"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def update_user(telegram_id: int, **kwargs) -> bool:
    """بروزرسانی اطلاعات کاربر"""
    if not kwargs:
        return False
    
    set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
    values = list(kwargs.values()) + [telegram_id]
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            await db.execute(
                f"UPDATE users SET {set_clause} WHERE telegram_id = ?", values
            )
            await db.commit()
            return True
        except Exception as e:
            print(f"Error updating user: {e}")
            return False


async def block_user(telegram_id: int, blocked: bool = True) -> bool:
    """مسدود/فعال کردن کاربر"""
    return await update_user(telegram_id, is_blocked=blocked)


async def set_traffic_limit(telegram_id: int, limit_gb: float) -> bool:
    """تنظیم حد ترافیک کاربر"""
    return await update_user(telegram_id, traffic_limit_gb=limit_gb)


async def is_user_blocked(telegram_id: int) -> bool:
    """بررسی مسدود بودن کاربر"""
    user = await get_user(telegram_id)
    return user.get("is_blocked", False) if user else True


async def is_user_admin(telegram_id: int) -> bool:
    """بررسی ادمین بودن کاربر"""
    user = await get_user(telegram_id)
    return user.get("is_admin", False) or user.get("is_sudo", False) if user else False


async def is_user_sudo(telegram_id: int) -> bool:
    """بررسی سودو بودن کاربر"""
    user = await get_user(telegram_id)
    return user.get("is_sudo", False) if user else False


# ==================== توابع مربوط به کانفیگ‌ها ====================

async def add_config(owner_telegram_id: int, panel_client_email: str, inbound_id: int,
                     traffic_limit_gb: float, expiry_time: int) -> int | None:
    """افزودن کانفیگ جدید"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            cursor = await db.execute("""
                INSERT INTO configs (owner_telegram_id, panel_client_email, inbound_id, 
                                     traffic_limit_gb, expiry_time)
                VALUES (?, ?, ?, ?, ?)
            """, (owner_telegram_id, panel_client_email, inbound_id, traffic_limit_gb, expiry_time))
            await db.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"Error adding config: {e}")
            return None


async def get_config(config_id: int) -> dict | None:
    """دریافت اطلاعات یک کانفیگ"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM configs WHERE id = ?", (config_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None


async def get_config_by_email(email: str) -> dict | None:
    """دریافت کانفیگ با ایمیل"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM configs WHERE panel_client_email = ?", (email,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None


async def get_user_configs(telegram_id: int, include_deleted: bool = False) -> list:
    """دریافت کانفیگ‌های یک کاربر"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        if include_deleted:
            query = "SELECT * FROM configs WHERE owner_telegram_id = ?"
        else:
            query = "SELECT * FROM configs WHERE owner_telegram_id = ? AND is_deleted = 0"
        
        async with db.execute(query, (telegram_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_all_active_configs() -> list:
    """دریافت همه کانفیگ‌های فعال"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM configs WHERE is_deleted = 0"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def update_config(config_id: int, **kwargs) -> bool:
    """بروزرسانی کانفیگ"""
    if not kwargs:
        return False
    
    set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
    values = list(kwargs.values()) + [config_id]
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            await db.execute(
                f"UPDATE configs SET {set_clause} WHERE id = ?", values
            )
            await db.commit()
            return True
        except Exception as e:
            print(f"Error updating config: {e}")
            return False


async def update_config_traffic(config_id: int, traffic_used_gb: float) -> bool:
    """بروزرسانی حجم مصرفی کانفیگ"""
    return await update_config(config_id, traffic_used_gb=traffic_used_gb)


async def delete_config(config_id: int, final_traffic_gb: float) -> bool:
    """حذف کانفیگ (نرم) - حفظ حجم مصرفی"""
    return await update_config(
        config_id, 
        is_deleted=True, 
        deleted_traffic_gb=final_traffic_gb
    )


async def extend_config(config_id: int, new_expiry_time: int, 
                        additional_traffic_gb: float = 0) -> bool:
    """تمدید کانفیگ"""
    config = await get_config(config_id)
    if not config:
        return False
    
    new_traffic = config["traffic_limit_gb"] + additional_traffic_gb
    return await update_config(
        config_id,
        expiry_time=new_expiry_time,
        traffic_limit_gb=new_traffic
    )


# ==================== توابع آماری ====================

async def get_user_total_traffic(telegram_id: int) -> float:
    """محاسبه کل ترافیک مصرفی یک کاربر"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # جمع ترافیک کانفیگ‌های فعال
        async with db.execute("""
            SELECT COALESCE(SUM(traffic_used_gb), 0) as active_traffic
            FROM configs 
            WHERE owner_telegram_id = ? AND is_deleted = 0
        """, (telegram_id,)) as cursor:
            row = await cursor.fetchone()
            active_traffic = row[0] if row else 0
        
        # جمع ترافیک کانفیگ‌های حذف شده
        async with db.execute("""
            SELECT COALESCE(SUM(deleted_traffic_gb), 0) as deleted_traffic
            FROM configs 
            WHERE owner_telegram_id = ? AND is_deleted = 1
        """, (telegram_id,)) as cursor:
            row = await cursor.fetchone()
            deleted_traffic = row[0] if row else 0
        
        return active_traffic + deleted_traffic


async def get_user_remaining_traffic(telegram_id: int) -> float:
    """محاسبه ترافیک باقیمانده کاربر"""
    user = await get_user(telegram_id)
    if not user:
        return 0
    
    total_used = await get_user_total_traffic(telegram_id)
    return max(0, user["traffic_limit_gb"] - total_used)


async def get_overall_stats() -> dict:
    """دریافت آمار کلی"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # تعداد کاربران
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            total_users = (await cursor.fetchone())[0]
        
        # تعداد کانفیگ‌های فعال
        async with db.execute(
            "SELECT COUNT(*) FROM configs WHERE is_deleted = 0"
        ) as cursor:
            active_configs = (await cursor.fetchone())[0]
        
        # کل ترافیک مصرفی
        async with db.execute("""
            SELECT COALESCE(SUM(traffic_used_gb), 0) + 
                   COALESCE((SELECT SUM(deleted_traffic_gb) FROM configs WHERE is_deleted = 1), 0)
            FROM configs WHERE is_deleted = 0
        """) as cursor:
            total_traffic = (await cursor.fetchone())[0]
        
        return {
            "total_users": total_users,
            "active_configs": active_configs,
            "total_traffic_gb": round(total_traffic, 2)
        }


async def get_users_near_limit(threshold_percent: float = 80) -> list:
    """یافتن کاربرانی که نزدیک حد مجاز هستند"""
    users = await get_all_users()
    near_limit = []
    
    for user in users:
        if user["is_blocked"]:
            continue
            
        total_used = await get_user_total_traffic(user["telegram_id"])
        limit = user["traffic_limit_gb"]
        
        if limit > 0:
            percent = (total_used / limit) * 100
            if percent >= threshold_percent:
                near_limit.append({
                    "telegram_id": user["telegram_id"],
                    "used_gb": round(total_used, 2),
                    "limit_gb": limit,
                    "percent": round(percent, 1)
                })
    
    return near_limit
