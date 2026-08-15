"""
🔗 NOVA PAY — Общий модуль JSONBin API
Используется ОБОИМИ ботами
"""

import os
import asyncio
import random
import string
import hashlib
import logging
import aiohttp
from datetime import datetime, timedelta
from typing import Optional

log = logging.getLogger("NovaAPI")

# ═══════════════════════════════════════════════════════════════
# 🔑 КЛЮЧИ — читаются из переменных окружения
# ═══════════════════════════════════════════════════════════════

JSONBIN_KEY  = os.environ["JSONBIN_API_KEY"]
BIN_USERS    = os.environ["BIN_USERS"]
BIN_CARDS    = os.environ["BIN_CARDS"]
BIN_TX       = os.environ["BIN_TRANSACTIONS"]
BIN_CHECKS   = os.environ["BIN_CHECKS"]
BIN_PENDING  = os.environ["BIN_PENDING"]
BIN_ORDERS   = os.environ["BIN_ORDERS_SYNC"]
BIN_NOTIFY   = os.environ["BIN_NOTIFICATIONS"]

HEADERS = {
    "X-Master-Key":     JSONBIN_KEY,
    "Content-Type":     "application/json",
    "X-Bin-Versioning": "false"
}

# ═══════════════════════════════════════════════════════════════
# 🌐 BASE API
# ═══════════════════════════════════════════════════════════════

_cache:      dict = {}
_cache_time: dict = {}
CACHE_TTL = 5  # секунд

async def jget(bin_id: str, force: bool = False) -> dict:
    """Получить данные из JSONBin с кэшированием"""
    now = datetime.now().timestamp()
    if (not force
            and bin_id in _cache
            and (now - _cache_time.get(bin_id, 0)) < CACHE_TTL):
        return _cache[bin_id]

    for attempt in range(3):
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(
                    f"https://api.jsonbin.io/v3/b/{bin_id}/latest",
                    headers=HEADERS,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as r:
                    if r.status == 200:
                        d = await r.json()
                        result = d.get("record", {})
                        _cache[bin_id]      = result
                        _cache_time[bin_id] = now
                        return result
                    else:
                        log.error(f"jget({bin_id}) HTTP {r.status}")
        except Exception as e:
            log.error(f"jget attempt {attempt+1}: {e}")
            if attempt < 2:
                await asyncio.sleep(1)

    return _cache.get(bin_id, {})


async def jput(bin_id: str, data: dict) -> bool:
    """Сохранить данные в JSONBin"""
    _cache[bin_id]      = data
    _cache_time[bin_id] = datetime.now().timestamp()

    for attempt in range(3):
        try:
            async with aiohttp.ClientSession() as s:
                async with s.put(
                    f"https://api.jsonbin.io/v3/b/{bin_id}",
                    headers=HEADERS,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as r:
                    if r.status == 200:
                        return True
                    log.error(f"jput({bin_id}) HTTP {r.status}")
        except Exception as e:
            log.error(f"jput attempt {attempt+1}: {e}")
            if attempt < 2:
                await asyncio.sleep(1)
    return False


def invalidate(bin_id: str):
    """Сбросить кэш конкретного бина"""
    _cache.pop(bin_id, None)
    _cache_time.pop(bin_id, None)


# ═══════════════════════════════════════════════════════════════
# 🛠 ГЕНЕРАТОРЫ
# ═══════════════════════════════════════════════════════════════

def gen_id(prefix: str, length: int = 6) -> str:
    chars = string.ascii_uppercase + string.digits
    return prefix + "-" + "".join(random.choices(chars, k=length))

def gen_card_number() -> str:
    return " ".join(str(random.randint(1000, 9999)) for _ in range(4))

def gen_ref_code(uid: int) -> str:
    h = hashlib.md5(str(uid).encode()).hexdigest()[:6].upper()
    return f"REF-{h}"

def mask_card(num: str) -> str:
    if not num:
        return "•••• •••• •••• ••••"
    p = num.split(" ")
    if len(p) < 4:
        return num
    return f"{p[0]} •••• •••• {p[3]}"

def html_esc(text: str) -> str:
    return (text or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def fmt_date(iso: str) -> str:
    if not iso:
        return "—"
    try:
        return datetime.fromisoformat(iso).strftime("%d.%m.%Y")
    except Exception:
        return iso[:10]

def fmt_dt(iso: str) -> str:
    if not iso:
        return "—"
    try:
        return datetime.fromisoformat(iso).strftime("%d.%m %H:%M")
    except Exception:
        return iso[:16]


# ═══════════════════════════════════════════════════════════════
# 👤 USERS
# ═══════════════════════════════════════════════════════════════

async def get_user(uid: int) -> Optional[dict]:
    d = await jget(BIN_USERS)
    return d.get("users", {}).get(str(uid))

async def get_all_users() -> dict:
    d = await jget(BIN_USERS)
    return d.get("users", {})

async def save_user(uid: int, user: dict):
    d = await jget(BIN_USERS)
    if "users" not in d:
        d["users"] = {}
    d["users"][str(uid)] = user
    await jput(BIN_USERS, d)

async def update_user_field(uid: int, field: str, value):
    d = await jget(BIN_USERS)
    if str(uid) in d.get("users", {}):
        d["users"][str(uid)][field] = value
        await jput(BIN_USERS, d)

async def update_balance(uid: int, delta: int,
                         desc: str = "") -> Optional[int]:
    d    = await jget(BIN_USERS, force=True)
    user = d.get("users", {}).get(str(uid))
    if not user:
        return None

    new_bal = max(0, (user.get("balance", 0) + delta))
    d["users"][str(uid)]["balance"] = new_bal

    if delta > 0:
        d["users"][str(uid)]["total_earned"] = (
            user.get("total_earned", 0) + delta
        )
    else:
        d["users"][str(uid)]["total_spent"] = (
            user.get("total_spent", 0) + abs(delta)
        )

    await jput(BIN_USERS, d)

    await add_transaction(
        from_id     = int(uid) if delta < 0 else 0,
        to_id       = int(uid) if delta > 0 else 0,
        amount      = abs(delta),
        tx_type     = "bonus" if delta > 0 else "payment",
        description = desc
    )
    return new_bal


async def register_user(uid: int, username: str,
                         full_name: str) -> dict:
    existing = await get_user(uid)
    if existing:
        return existing

    card_id  = gen_id("CARD")
    card_num = gen_card_number()
    ref_code = gen_ref_code(uid)

    # Создаём карточку
    cards_d = await jget(BIN_CARDS)
    if "cards" not in cards_d:
        cards_d["cards"] = {}
    cards_d["cards"][card_id] = {
        "card_id":       card_id,
        "card_number":   card_num,
        "owner_id":      int(uid),
        "tier":          "starter",
        "created_at":    datetime.now().isoformat(),
        "is_active":     True,
        "avatar_linked": False,
        "nickname_linked": bool(username),
        "nickname":      username or None
    }
    await jput(BIN_CARDS, cards_d)

    # Создаём пользователя
    user = {
        "telegram_id":        int(uid),
        "username":           username or "",
        "full_name":          full_name or str(uid),
        "balance":            20,
        "referral_code":      ref_code,
        "referred_by":        None,
        "referral_count":     0,
        "card_tier":          "starter",
        "card_id":            card_id,
        "registered_at":      datetime.now().isoformat(),
        "last_weekly_bonus":  (
            datetime.now() - timedelta(days=8)
        ).isoformat(),
        "total_earned":       20,
        "total_spent":        0,
        "subscribed_channel": False,
        "is_banned":          False,
        "avatar_url":         None,
        "nickname_linked":    bool(username)
    }
    await save_user(uid, user)

    await add_transaction(
        from_id=0, to_id=int(uid), amount=20,
        tx_type="bonus",
        description="Стартовый бонус при регистрации"
    )
    return user


async def process_referral(new_uid: int, ref_code: str) -> bool:
    d = await jget(BIN_USERS, force=True)
    for u_id, u_data in d.get("users", {}).items():
        if (u_data.get("referral_code") == ref_code
                and int(u_id) != new_uid):
            d["users"][u_id]["referral_count"] = (
                u_data.get("referral_count", 0) + 1
            )
            d["users"][str(new_uid)]["referred_by"] = int(u_id)
            await jput(BIN_USERS, d)
            await update_balance(
                int(u_id), 50,
                f"Реферал: пользователь {new_uid}"
            )
            return True
    return False


# ═══════════════════════════════════════════════════════════════
# 💳 CARDS
# ═══════════════════════════════════════════════════════════════

async def get_card(card_id: str) -> Optional[dict]:
    d = await jget(BIN_CARDS)
    return d.get("cards", {}).get(card_id)

async def upgrade_card_tier(uid: int, new_tier: str):
    user = await get_user(uid)
    if not user:
        return

    prices = {"starter": 0, "creative": 200, "elite": 500}
    price  = prices.get(new_tier, 0)

    if price > 0:
        await update_balance(uid, -price, f"Покупка карточки {new_tier}")

    # Обновляем тир пользователя и карточки
    d = await jget(BIN_USERS)
    d["users"][str(uid)]["card_tier"] = new_tier
    await jput(BIN_USERS, d)

    cd = await jget(BIN_CARDS)
    if user.get("card_id") in cd.get("cards", {}):
        cd["cards"][user["card_id"]]["tier"] = new_tier
        await jput(BIN_CARDS, cd)


# ═══════════════════════════════════════════════════════════════
# 💸 TRANSACTIONS
# ═══════════════════════════════════════════════════════════════

async def add_transaction(from_id: int, to_id: int,
                           amount: int, tx_type: str,
                           description: str = ""):
    d = await jget(BIN_TX)
    if "transactions" not in d:
        d["transactions"] = []

    d["transactions"].append({
        "tx_id":       gen_id("TX", 8),
        "from_id":     from_id,
        "to_id":       to_id,
        "amount":      amount,
        "currency":    "NVC",
        "type":        tx_type,
        "description": description,
        "status":      "completed",
        "created_at":  datetime.now().isoformat()
    })

    # Держим последние 2000
    if len(d["transactions"]) > 2000:
        d["transactions"] = d["transactions"][-2000:]

    await jput(BIN_TX, d)

async def get_user_transactions(uid: int) -> list:
    d = await jget(BIN_TX)
    return [
        t for t in d.get("transactions", [])
        if t.get("from_id") == uid or t.get("to_id") == uid
    ][::-1]

async def get_all_transactions() -> list:
    d = await jget(BIN_TX)
    return d.get("transactions", [])[::-1]


# ═══════════════════════════════════════════════════════════════
# 🎰 CHECKS
# ═══════════════════════════════════════════════════════════════

async def get_check(check_id: str) -> Optional[dict]:
    d = await jget(BIN_CHECKS)
    return d.get("checks", {}).get(check_id)

async def get_all_checks() -> dict:
    d = await jget(BIN_CHECKS)
    return d.get("checks", {})

async def create_check(amount: int, description: str,
                        created_by: int,
                        expiry_days: int = 30) -> dict:
    check_id = gen_id("CHK")
    d = await jget(BIN_CHECKS)
    if "checks" not in d:
        d["checks"] = {}

    check = {
        "check_id":    check_id,
        "amount":      amount,
        "currency":    "NVC",
        "created_by":  created_by,
        "description": description,
        "is_used":     False,
        "used_by":     None,
        "used_at":     None,
        "created_at":  datetime.now().isoformat(),
        "expires_at":  (
            datetime.now() + timedelta(days=expiry_days)
        ).isoformat()
    }
    d["checks"][check_id] = check
    await jput(BIN_CHECKS, d)
    return check

async def activate_check(check_id: str,
                          uid: int) -> dict:
    d     = await jget(BIN_CHECKS, force=True)
    check = d.get("checks", {}).get(check_id)

    if not check:
        return {"ok": False, "error": "not_found"}
    if check.get("is_used"):
        return {"ok": False, "error": "used"}
    if datetime.fromisoformat(
        check.get("expires_at", "2000-01-01")
    ) < datetime.now():
        return {"ok": False, "error": "expired"}
    if check.get("created_by") == uid:
        return {"ok": False, "error": "own_check"}

    d["checks"][check_id]["is_used"] = True
    d["checks"][check_id]["used_by"] = int(uid)
    d["checks"][check_id]["used_at"] = datetime.now().isoformat()
    await jput(BIN_CHECKS, d)

    new_bal = await update_balance(
        uid, check["amount"],
        f"Чек {check_id}: {check['description']}"
    )
    return {"ok": True, "amount": check["amount"], "new_balance": new_bal}


# ═══════════════════════════════════════════════════════════════
# 💳 PENDING (заявки на покупку NVC)
# ═══════════════════════════════════════════════════════════════

async def get_pending() -> dict:
    d = await jget(BIN_PENDING)
    return d.get("pending", {})

async def create_pending(uid: int, username: str,
                          full_name: str, stars: int,
                          nvc: int) -> dict:
    req_id = gen_id("REQ")
    d = await jget(BIN_PENDING)
    if "pending" not in d:
        d["pending"] = {}

    req = {
        "req_id":      req_id,
        "uid":         int(uid),
        "username":    username or "",
        "full_name":   full_name or str(uid),
        "stars":       stars,
        "nvc":         nvc,
        "status":      "pending",
        "created_at":  datetime.now().isoformat(),
        "approved_at": None,
        "approved_by": None
    }
    d["pending"][req_id] = req
    await jput(BIN_PENDING, d)
    return req

async def approve_pending(req_id: str,
                           admin_uid: int) -> Optional[dict]:
    d   = await jget(BIN_PENDING, force=True)
    req = d.get("pending", {}).get(req_id)
    if not req or req.get("status") != "pending":
        return None

    d["pending"][req_id]["status"]      = "approved"
    d["pending"][req_id]["approved_at"] = datetime.now().isoformat()
    d["pending"][req_id]["approved_by"] = admin_uid
    await jput(BIN_PENDING, d)

    await update_balance(
        req["uid"], req["nvc"],
        f"Покупка NVC: {req['stars']} Stars (заявка {req_id})"
    )
    return req

async def reject_pending(req_id: str, admin_uid: int) -> bool:
    d = await jget(BIN_PENDING, force=True)
    if req_id not in d.get("pending", {}):
        return False
    d["pending"][req_id]["status"]      = "rejected"
    d["pending"][req_id]["approved_at"] = datetime.now().isoformat()
    d["pending"][req_id]["approved_by"] = admin_uid
    await jput(BIN_PENDING, d)
    return True


# ═══════════════════════════════════════════════════════════════
# 📦 ORDERS SYNC (синхронизация заказов с сайтом)
# ═══════════════════════════════════════════════════════════════

async def sync_order_to_json(order_num: str, user_id: int,
                              category: str, service: str,
                              service_key: str, status: str,
                              is_paid: bool = False,
                              paid_amount: int = 0):
    """Синхронизирует заказ из SQLite в JSONBin для сайта"""
    d = await jget(BIN_ORDERS)
    if "orders" not in d:
        d["orders"] = {}

    d["orders"][order_num] = {
        "order_num":   order_num,
        "user_id":     user_id,
        "category":    category,
        "service":     service,
        "service_key": service_key,
        "status":      status,
        "is_paid":     is_paid,
        "paid_amount": paid_amount,
        "created_at":  datetime.now().isoformat()
    }

    # Держим последние 200 заказов
    if len(d["orders"]) > 200:
        sorted_orders = sorted(
            d["orders"].items(),
            key=lambda x: x[1].get("created_at", ""),
            reverse=True
        )
        d["orders"] = dict(sorted_orders[:200])

    await jput(BIN_ORDERS, d)

async def update_order_status_json(order_num: str, status: str):
    d = await jget(BIN_ORDERS)
    if order_num in d.get("orders", {}):
        d["orders"][order_num]["status"] = status
        await jput(BIN_ORDERS, d)


# ═══════════════════════════════════════════════════════════════
# 🔔 NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════

async def push_notification(uid: int, text: str, notif_type: str = "info"):
    """Пуш-уведомление через JSONBin (сайт читает их)"""
    d = await jget(BIN_NOTIFY)
    if "notifications" not in d:
        d["notifications"] = []

    d["notifications"].append({
        "id":         gen_id("N", 8),
        "uid":        uid,
        "text":       text,
        "type":       notif_type,
        "read":       False,
        "created_at": datetime.now().isoformat()
    })

    # Держим последние 500
    d["notifications"] = d["notifications"][-500:]
    await jput(BIN_NOTIFY, d)

async def get_user_notifications(uid: int) -> list:
    d = await jget(BIN_NOTIFY)
    return [
        n for n in d.get("notifications", [])
        if n.get("uid") == uid and not n.get("read")
    ]

async def mark_notifications_read(uid: int):
    d = await jget(BIN_NOTIFY, force=True)
    changed = False
    for i, n in enumerate(d.get("notifications", [])):
        if n.get("uid") == uid and not n.get("read"):
            d["notifications"][i]["read"] = True
            changed = True
    if changed:
        await jput(BIN_NOTIFY, d)