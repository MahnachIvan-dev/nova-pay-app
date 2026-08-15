"""
🌃 NOVA CREATIVE STUDIO — Бот заказов
Подключён к JSONBin для синхронизации с Nova Pay и сайтом
"""

import os
import sys
import asyncio
import sqlite3
import logging
import html
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict

# Добавляем путь к shared_api
sys.path.append(str(Path(__file__).parent.parent))
import shared_api as JB

from aiogram.fsm.storage.base import StorageKey
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ═══════════════════════════════════════════════════════════════
# 🔧 КОНФИГУРАЦИЯ
# ═══════════════════════════════════════════════════════════════

BOT_TOKEN       = os.environ["BOT_TOKEN"]
OWNER_ID        = int(os.getenv("OWNER_ID",           "7969709802"))
ADMIN_GROUP_ID  = int(os.getenv("ADMIN_GROUP_ID",     "-1004380423059"))
STORAGE_CHANNEL = int(os.getenv("STORAGE_CHANNEL_ID", "-1003977995290"))
NOVAPAY_BOT     = os.getenv("NOVAPAY_BOT",            "NOVACreativePay_bot")

DATA_DIR = Path("./order_data")
DB_PATH  = DATA_DIR / "orders.db"
DATA_DIR.mkdir(exist_ok=True)

AUTO_CLOSE_HOURS = 48

# Платные услуги (цены в NVC)
PAID_SERVICES = {
    "music_track":    150,
    "design_sticker": 100,
    "video_anim":     200,
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("OrdersBot")

bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())

# ═══════════════════════════════════════════════════════════════
# 🗂 КАТЕГОРИИ
# ═══════════════════════════════════════════════════════════════

CATEGORIES = {
    "🎨 Дизайн и графика": "design",
    "🎧 Музыка и звук":    "music",
    "📝 Контент":          "content",
    "🎬 Видео и анимация": "video",
}

SUBCATEGORIES = {
    "design": {
        "🖼 Аватары и иконки":                "design_avatar",
        "🎯 Баннеры, шапки и обложки":        "design_banner",
        "📢 Постеры и рекламные изображения": "design_poster",
        "🎨 Арты и иллюстрации":              "design_art",
        "😄 Стикер-паки":                     "design_sticker",
    },
    "music": {
        "🎵 Авторские музыкальные треки":     "music_track",
        "🎙 Интро и аутро":                   "music_intro",
        "🌊 Атмосферные фоновые композиции":  "music_ambient",
        "🎼 Музыкальное оформление проектов": "music_project",
    },
    "content": {
        "📱 Посты для Telegram": "content_post",
        "🎉 Поздравления":       "content_congrats",
        "📖 Истории и сценарии": "content_story",
        "📋 Описания проектов":  "content_desc",
        "🎤 Тексты для дикторов":"content_voice",
        "💡 Идеи и концепции":   "content_idea",
    },
    "video": {
        "🎬 Монтаж видео":     "video_edit",
        "✨ Анимация и моушн": "video_anim",
        "🎞 Клипы и ролики":   "video_clip",
        "📺 Слайд-шоу":        "video_slide",
    },
}

# ═══════════════════════════════════════════════════════════════
# 💾 ЛОКАЛЬНАЯ БД (SQLite)
# ═══════════════════════════════════════════════════════════════

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id    INTEGER PRIMARY KEY,
                username   TEXT,
                full_name  TEXT,
                is_banned  INTEGER DEFAULT 0,
                warn_count INTEGER DEFAULT 0,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS orders (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER,
                category     TEXT,
                category_key TEXT,
                service      TEXT,
                service_key  TEXT,
                details      TEXT,
                status       TEXT DEFAULT 'pending',
                admin_id     INTEGER,
                topic_id     INTEGER,
                created_at   TEXT,
                accepted_at  TEXT,
                closed_at    TEXT,
                close_reason TEXT,
                order_num    TEXT UNIQUE,
                is_paid      INTEGER DEFAULT 0,
                paid_amount  INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS order_media (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id       INTEGER,
                file_id        TEXT,
                file_type      TEXT,
                channel_msg_id INTEGER,
                direction      TEXT DEFAULT 'from_user'
            );
            CREATE TABLE IF NOT EXISTS order_chat (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id   INTEGER,
                user_id    INTEGER,
                role       TEXT,
                text       TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS reviews (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id   INTEGER,
                user_id    INTEGER,
                text       TEXT,
                rating     INTEGER,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS admins (
                user_id  INTEGER PRIMARY KEY,
                username TEXT,
                added_at TEXT
            );
        """)
    log.info("💾 БД инициализирована")


def db():
    return sqlite3.connect(DB_PATH)


def gen_order_num() -> str:
    import random, string
    return "NCS-" + "".join(
        random.choices(string.ascii_uppercase + string.digits, k=4)
    )


def upsert_user(uid: int, username: str, full_name: str):
    with db() as conn:
        conn.execute(
            "INSERT INTO users(user_id,username,full_name,created_at) "
            "VALUES(?,?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET "
            "username=excluded.username,full_name=excluded.full_name",
            (uid, username, full_name, datetime.now().isoformat())
        )


def is_banned_local(uid: int) -> bool:
    with db() as conn:
        r = conn.execute(
            "SELECT is_banned FROM users WHERE user_id=?", (uid,)
        ).fetchone()
    return bool(r and r[0])


def is_admin_user(uid: int) -> bool:
    if uid == OWNER_ID:
        return True
    with db() as conn:
        r = conn.execute(
            "SELECT user_id FROM admins WHERE user_id=?", (uid,)
        ).fetchone()
    return bool(r)


def is_admin_chat(msg: types.Message) -> bool:
    if msg.chat.id == ADMIN_GROUP_ID:
        return True
    if msg.chat.type == "private" and msg.from_user.id == OWNER_ID:
        return True
    return False


def get_order(order_id: int):
    with db() as conn:
        return conn.execute(
            "SELECT * FROM orders WHERE id=?", (order_id,)
        ).fetchone()


def get_order_by_num(num: str):
    with db() as conn:
        return conn.execute(
            "SELECT * FROM orders WHERE order_num=?", (num,)
        ).fetchone()


def get_user_active_order(uid: int):
    with db() as conn:
        return conn.execute(
            "SELECT * FROM orders WHERE user_id=? "
            "AND status IN ('pending','accepted') "
            "ORDER BY id DESC LIMIT 1",
            (uid,)
        ).fetchone()


def get_user_local(uid: int):
    with db() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE user_id=?", (uid,)
        ).fetchone()


def all_users_local():
    with db() as conn:
        return conn.execute("SELECT * FROM users").fetchall()


# ═══════════════════════════════════════════════════════════════
# 🔗 СИНХРОНИЗАЦИЯ JSONBin
# ═══════════════════════════════════════════════════════════════

async def sync_user_to_jb(uid: int, username: str, full_name: str):
    """Регистрирует/обновляет пользователя в JSONBin"""
    existing = await JB.get_user(uid)
    if not existing:
        await JB.register_user(uid, username, full_name)
        log.info(f"👤 Новый пользователь в JSONBin: {uid}")

async def check_nvc_balance(uid: int, required: int) -> bool:
    """Проверяет баланс NVC через JSONBin"""
    user = await JB.get_user(uid)
    if not user:
        return False
    return user.get("balance", 0) >= required

async def deduct_nvc(uid: int, amount: int, desc: str) -> Optional[int]:
    """Списывает NVC через JSONBin"""
    return await JB.update_balance(uid, -amount, desc)

async def sync_order(order_num: str, user_id: int,
                     category: str, service: str,
                     service_key: str, status: str,
                     is_paid: bool = False,
                     paid_amount: int = 0):
    """Синхронизирует заказ в JSONBin"""
    await JB.sync_order_to_json(
        order_num, user_id, category, service,
        service_key, status, is_paid, paid_amount
    )


# ═══════════════════════════════════════════════════════════════
# 🎹 КЛАВИАТУРЫ
# ═══════════════════════════════════════════════════════════════

WELCOME_TEXT = """🌃 <b>Добро пожаловать в бот NOVA CREATIVE STUDIO!</b> 💜

Здесь вы можете оформить заказ на творческие услуги.

💳 Некоторые услуги доступны за <b>NVC</b>
(Nova Creative Currency) — получить в @{novapay}

<i>Спасибо, что выбираете NOVA CREATIVE STUDIO! 🚀💜</i>"""

INFO_SERVICES = """📖 <b>Список услуг NOVA CREATIVE STUDIO</b>

🎨 <b>Дизайн и графика</b>
• Аватары и иконки
• Баннеры, шапки и обложки
• Постеры и рекламные изображения
• Арты и иллюстрации
• Стикер-паки 💳 <i>100 NVC</i>

🎧 <b>Музыка и звук</b>
• Авторские музыкальные треки 💳 <i>150 NVC</i>
• Интро и аутро
• Атмосферные фоновые композиции
• Музыкальное оформление проектов

📝 <b>Контент</b>
• Посты для Telegram
• Поздравления
• Истории и сценарии
• Описания проектов
• Тексты для дикторов
• Идеи и концепции

🎬 <b>Видео и анимация</b>
• Монтаж видео
• Анимация и моушн 💳 <i>200 NVC</i>
• Клипы и ролики
• Слайд-шоу"""

INFO_RULES = """📜 <b>Правила NOVA CREATIVE STUDIO</b>

1️⃣ Уважение — общайтесь вежливо
2️⃣ Описание заказа — чем подробнее тем лучше
3️⃣ Сроки — обговариваются при принятии
4️⃣ Оплата — бесплатно или в NVC
5️⃣ Автозакрытие — если не принят за 48ч"""


def welcome_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🛒 Оформить заказ", callback_data="new_order"
        )],
        [
            InlineKeyboardButton(
                text="📖 Услуги", callback_data="info:services"
            ),
            InlineKeyboardButton(
                text="📜 Правила", callback_data="info:rules"
            ),
        ],
        [InlineKeyboardButton(
            text="💳 Nova Pay — получить NVC",
            url=f"https://t.me/{NOVAPAY_BOT}"
        )],
    ])


def categories_kb() -> ReplyKeyboardMarkup:
    rows = []
    cats = list(CATEGORIES.keys())
    for i in range(0, len(cats), 2):
        row = [KeyboardButton(text=cats[i])]
        if i + 1 < len(cats):
            row.append(KeyboardButton(text=cats[i + 1]))
        rows.append(row)
    rows.append([KeyboardButton(text="❌ Отмена")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def subcategories_kb(category_key: str) -> ReplyKeyboardMarkup:
    subs = list(SUBCATEGORIES.get(category_key, {}).keys())
    rows = []
    for i in range(0, len(subs), 2):
        row = [KeyboardButton(text=subs[i])]
        if i + 1 < len(subs):
            row.append(KeyboardButton(text=subs[i + 1]))
        rows.append(row)
    rows.append([
        KeyboardButton(text="◀️ Назад"),
        KeyboardButton(text="❌ Отмена")
    ])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )


def chat_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Статус заказа")],
            [KeyboardButton(text="❌ Отмена заказа")],
        ],
        resize_keyboard=True
    )


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def accept_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Принять", callback_data=f"accept:{order_id}"
        )],
        [InlineKeyboardButton(
            text="❌ Отклонить", callback_data=f"reject:{order_id}"
        )],
    ])


def admin_order_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Завершить", callback_data=f"complete:{order_id}"
        )],
        [InlineKeyboardButton(
            text="🔒 Закрыть", callback_data=f"close:{order_id}"
        )],
    ])


def pay_kb(order_id: int, price: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"💳 Оплатить {price} NVC в Nova Pay",
            url=f"https://t.me/{NOVAPAY_BOT}"
        )],
        [InlineKeyboardButton(
            text="✅ Я оплатил — продолжить",
            callback_data=f"paid_confirm:{order_id}"
        )],
        [InlineKeyboardButton(
            text="❌ Отмена", callback_data="cancel_paid"
        )],
    ])


def rating_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="⭐", callback_data=f"rate:{order_id}:1"
            ),
            InlineKeyboardButton(
                text="⭐⭐", callback_data=f"rate:{order_id}:2"
            ),
            InlineKeyboardButton(
                text="⭐⭐⭐", callback_data=f"rate:{order_id}:3"
            ),
        ],
        [
            InlineKeyboardButton(
                text="⭐⭐⭐⭐", callback_data=f"rate:{order_id}:4"
            ),
            InlineKeyboardButton(
                text="⭐⭐⭐⭐⭐", callback_data=f"rate:{order_id}:5"
            ),
        ],
        [InlineKeyboardButton(
            text="⏭ Пропустить", callback_data=f"rate:{order_id}:0"
        )],
    ])


# ═══════════════════════════════════════════════════════════════
# 🛠 ХЕЛПЕРЫ
# ═══════════════════════════════════════════════════════════════

async def safe_delete(chat_id: int, msg_id: int):
    try:
        await bot.delete_message(chat_id, msg_id)
    except Exception:
        pass


async def store_media(file_id: str, file_type: str,
                      order_id: int, direction: str = "from_user"):
    ch_id = None
    if STORAGE_CHANNEL:
        try:
            send_fn = {
                "photo":    bot.send_photo,
                "audio":    bot.send_audio,
                "video":    bot.send_video,
                "voice":    bot.send_voice,
            }.get(file_type, bot.send_document)
            m     = await send_fn(
                STORAGE_CHANNEL, file_id,
                caption=f"📦 #{order_id} | {direction}"
            )
            ch_id = m.message_id
        except Exception as e:
            log.error(f"store_media: {e}")

    with db() as conn:
        conn.execute(
            "INSERT INTO order_media("
            "order_id,file_id,file_type,channel_msg_id,direction"
            ") VALUES(?,?,?,?,?)",
            (order_id, file_id, file_type, ch_id, direction)
        )


async def create_topic(order_num: str, service: str) -> Optional[int]:
    try:
        topic = await bot.create_forum_topic(
            ADMIN_GROUP_ID,
            name=f"#{order_num} {service[:25]}"
        )
        return topic.message_thread_id
    except Exception as e:
        log.error(f"create_topic: {e}")
        return None


async def notify_admins(order_id: int, order_num: str,
                         category: str, service: str,
                         details: str, user_id: int,
                         username: str, full_name: str,
                         topic_id: int, is_paid: bool = False,
                         paid_amount: int = 0):
    paid_tag = (
        f"\n💳 <b>Оплачено:</b> {paid_amount} NVC" if is_paid else ""
    )
    text = (
        f"🆕 <b>Новый заказ NOVA CREATIVE STUDIO</b>\n\n"
        f"🔢 Номер: <code>{order_num}</code>\n"
        f"📂 {category}\n"
        f"🛠 <b>{service}</b>{paid_tag}\n\n"
        f"👤 {JB.html_esc(full_name)} "
        f"(@{username or '—'}) "
        f"<code>{user_id}</code>\n\n"
        f"📝 {JB.html_esc(details)}\n\n"
        f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )
    try:
        await bot.send_message(
            ADMIN_GROUP_ID, text,
            message_thread_id=topic_id,
            reply_markup=accept_kb(order_id),
            parse_mode="HTML"
        )
    except Exception as e:
        log.error(f"notify_admins: {e}")


async def forward_to_topic(order_id: int, text: str = None,
                            from_name: str = "Клиент",
                            media_msg: types.Message = None):
    order = get_order(order_id)
    if not order or not order[9]:
        return
    try:
        if media_msg:
            await media_msg.forward(
                ADMIN_GROUP_ID,
                message_thread_id=order[9]
            )
        elif text:
            await bot.send_message(
                ADMIN_GROUP_ID,
                f"💬 <b>{JB.html_esc(from_name)}:</b>\n"
                f"{JB.html_esc(text)}",
                message_thread_id=order[9],
                parse_mode="HTML"
            )
    except Exception as e:
        log.error(f"forward_to_topic: {e}")


async def send_to_user(order_id: int, text: str = None,
                        media_msg: types.Message = None):
    order = get_order(order_id)
    if not order:
        return
    try:
        if media_msg:
            await media_msg.copy_to(order[1])
        elif text:
            await bot.send_message(
                order[1],
                f"💬 <b>Сообщение от NOVA CREATIVE STUDIO:</b>\n\n"
                f"{JB.html_esc(text)}",
                parse_mode="HTML"
            )
    except Exception as e:
        log.error(f"send_to_user: {e}")


async def send_media_to_user(order_id: int,
                              msg: types.Message) -> bool:
    order = get_order(order_id)
    if not order:
        return False
    for fattr, ftype in [
        ("photo","photo"), ("document","document"),
        ("audio","audio"), ("video","video"),
        ("voice","voice"), ("video_note","video_note"),
    ]:
        media = getattr(msg, fattr, None)
        if media:
            fid = (media[-1].file_id
                   if fattr == "photo" else media.file_id)
            await store_media(fid, ftype, order_id, "result")
            await send_to_user(order_id, media_msg=msg)
            return True
    return False


# ═══════════════════════════════════════════════════════════════
# 📝 FSM
# ═══════════════════════════════════════════════════════════════

class OrderFSM(StatesGroup):
    choosing_category    = State()
    choosing_subcategory = State()
    entering_details     = State()
    waiting_payment      = State()
    in_chat              = State()
    waiting_review       = State()


class AdminFSM(StatesGroup):
    completing_order = State()
    entering_check   = State()
    closing_order    = State()


# ═══════════════════════════════════════════════════════════════
# 🤖 КОМАНДЫ
# ═══════════════════════════════════════════════════════════════

@dp.message(Command("start"), F.chat.type == "private")
async def cmd_start(msg: types.Message, state: FSMContext):
    await state.clear()
    uid      = msg.from_user.id
    username = msg.from_user.username or ""
    fname    = msg.from_user.full_name or str(uid)

    if is_banned_local(uid):
        return await msg.answer("🚫 Вы заблокированы.")

    # Локальная БД
    upsert_user(uid, username, fname)

    # JSONBin — регистрация/синхронизация
    asyncio.create_task(sync_user_to_jb(uid, username, fname))

    active = get_user_active_order(uid)
    if active:
        await msg.answer(
            f"👋 <b>С возвращением!</b>\n\n"
            f"Активный заказ: <code>{active[14]}</code>\n"
            f"📂 {active[2]}\n🛠 {active[4]}\n\n"
            f"💬 Пиши сюда — всё дойдёт до администратора.",
            parse_mode="HTML",
            reply_markup=chat_kb()
        )
        await state.set_state(OrderFSM.in_chat)
        await state.update_data(order_id=active[0])
        return

    welcome = WELCOME_TEXT.format(novapay=NOVAPAY_BOT)
    await msg.answer(
        welcome, parse_mode="HTML", reply_markup=welcome_kb()
    )


@dp.callback_query(F.data.startswith("info:"))
async def cb_info(call: types.CallbackQuery):
    texts = {"services": INFO_SERVICES, "rules": INFO_RULES}
    text  = texts.get(call.data.split(":")[1], "—")
    try:
        await call.message.edit_text(
            text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="◀️ Назад", callback_data="back_welcome"
                )]
            ])
        )
    except Exception:
        pass


@dp.callback_query(F.data == "back_welcome")
async def cb_back(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    welcome = WELCOME_TEXT.format(novapay=NOVAPAY_BOT)
    try:
        await call.message.edit_text(
            welcome, parse_mode="HTML", reply_markup=welcome_kb()
        )
    except Exception:
        await call.message.answer(
            welcome, parse_mode="HTML", reply_markup=welcome_kb()
        )


@dp.callback_query(F.data == "new_order")
async def cb_new_order(call: types.CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    if is_banned_local(uid):
        return await call.answer("🚫 Заблокированы", show_alert=True)
    if get_user_active_order(uid):
        return await call.answer(
            "⚠️ У вас уже есть активный заказ!", show_alert=True
        )
    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await call.message.answer(
        "🛒 <b>Оформление заказа</b>\n\nВыбери категорию 👇",
        parse_mode="HTML",
        reply_markup=categories_kb()
    )
    await state.set_state(OrderFSM.choosing_category)


@dp.message(OrderFSM.choosing_category, F.chat.type == "private")
async def fsm_category(msg: types.Message, state: FSMContext):
    text = msg.text or ""
    if text == "❌ Отмена":
        await state.clear()
        await msg.answer("❌ Отменено.", reply_markup=remove_kb())
        welcome = WELCOME_TEXT.format(novapay=NOVAPAY_BOT)
        return await msg.answer(
            welcome, parse_mode="HTML", reply_markup=welcome_kb()
        )
    if text not in CATEGORIES:
        await safe_delete(msg.chat.id, msg.message_id)
        return

    cat_key = CATEGORIES[text]
    await state.update_data(category=text, category_key=cat_key)
    await state.set_state(OrderFSM.choosing_subcategory)
    await msg.answer(
        f"📂 <b>{text}</b>\n\nВыбери услугу 👇",
        parse_mode="HTML",
        reply_markup=subcategories_kb(cat_key)
    )


@dp.message(OrderFSM.choosing_subcategory, F.chat.type == "private")
async def fsm_subcategory(msg: types.Message, state: FSMContext):
    text = msg.text or ""
    data = await state.get_data()

    if text == "❌ Отмена":
        await state.clear()
        await msg.answer("❌ Отменено.", reply_markup=remove_kb())
        welcome = WELCOME_TEXT.format(novapay=NOVAPAY_BOT)
        return await msg.answer(
            welcome, parse_mode="HTML", reply_markup=welcome_kb()
        )
    if text == "◀️ Назад":
        await state.set_state(OrderFSM.choosing_category)
        return await msg.answer(
            "📂 Выбери категорию:", reply_markup=categories_kb()
        )

    cat_key = data.get("category_key", "")
    subs    = SUBCATEGORIES.get(cat_key, {})
    if text not in subs:
        await safe_delete(msg.chat.id, msg.message_id)
        return

    svc_key = subs[text]
    price   = PAID_SERVICES.get(svc_key, 0)
    price_note = (
        f"\n💳 <b>Платная услуга: {price} NVC</b>"
        if price else ""
    )

    await state.update_data(service=text, service_key=svc_key)
    await state.set_state(OrderFSM.entering_details)
    await msg.answer(
        f"✅ Услуга: <b>{text}</b>{price_note}\n\n"
        f"📝 <b>Опиши свой заказ:</b>\n"
        f"• Что сделать\n• Пожелания по стилю\n"
        f"• Примеры / дедлайн\n\n"
        f"<i>Можно прикрепить фото/файлы 📎</i>",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )


@dp.message(OrderFSM.entering_details, F.chat.type == "private")
async def fsm_details(msg: types.Message, state: FSMContext):
    text = msg.text or msg.caption or ""
    data = await state.get_data()

    if text == "❌ Отмена":
        await state.clear()
        await msg.answer("❌ Отменено.", reply_markup=remove_kb())
        welcome = WELCOME_TEXT.format(novapay=NOVAPAY_BOT)
        return await msg.answer(
            welcome, parse_mode="HTML", reply_markup=welcome_kb()
        )

    if not text.strip() and not any([
        msg.photo, msg.document, msg.audio
    ]):
        return

    details     = text.strip() or "Детали в прикреплённых файлах"
    category    = data.get("category", "—")
    cat_key     = data.get("category_key", "—")
    service     = data.get("service", "—")
    svc_key     = data.get("service_key", "—")
    price       = PAID_SERVICES.get(svc_key, 0)
    uid         = msg.from_user.id

    # Генерируем номер заказа
    order_num = gen_order_num()
    while get_order_by_num(order_num):
        order_num = gen_order_num()

    # Сохраняем в SQLite
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO orders("
            "user_id,category,category_key,service,service_key,"
            "details,created_at,order_num,is_paid,paid_amount"
            ") VALUES(?,?,?,?,?,?,?,?,?,?)",
            (uid, category, cat_key, service, svc_key,
             details, datetime.now().isoformat(),
             order_num, 0, price)
        )
        order_id = cur.lastrowid

    # Медиа
    if msg.photo:
        await store_media(msg.photo[-1].file_id, "photo", order_id)
    elif msg.document:
        await store_media(msg.document.file_id, "document", order_id)
    elif msg.audio:
        await store_media(msg.audio.file_id, "audio", order_id)

    # Синхронизируем в JSONBin
    asyncio.create_task(sync_order(
        order_num, uid, category, service,
        svc_key, "pending", False, price
    ))

    if price > 0:
        # Проверяем баланс NVC
        has_nvc = await check_nvc_balance(uid, price)

        await state.update_data(
            order_id=order_id, order_num=order_num
        )
        await state.set_state(OrderFSM.waiting_payment)

        nvc_hint = (
            "✅ У вас достаточно NVC! Нажмите «Я оплатил» после оплаты в Nova Pay."
            if has_nvc
            else f"❌ Недостаточно NVC. Пополните баланс в @{NOVAPAY_BOT}"
        )

        return await msg.answer(
            f"✅ <b>Заказ создан!</b>\n\n"
            f"🔢 Номер: <code>{order_num}</code>\n"
            f"🛠 <b>{service}</b>\n\n"
            f"💳 Требуется оплата: <b>{price} NVC</b>\n"
            f"{nvc_hint}\n\n"
            f"1. Открой бот @{NOVAPAY_BOT}\n"
            f"2. Оплати {price} NVC\n"
            f"3. Вернись и нажми «✅ Я оплатил»",
            parse_mode="HTML",
            reply_markup=pay_kb(order_id, price)
        )

    # Бесплатная услуга
    await _finalize_order(
        msg, state, order_id, order_num,
        category, service, details, uid,
        msg.from_user.username or "",
        msg.from_user.full_name or str(uid)
    )


async def _finalize_order(msg_or_call, state, order_id,
                           order_num, category, service,
                           details, uid, username, full_name,
                           is_paid=False, paid_amount=0):
    topic_id = await create_topic(order_num, service)

    if topic_id:
        with db() as conn:
            conn.execute(
                "UPDATE orders SET topic_id=? WHERE id=?",
                (topic_id, order_id)
            )
        await notify_admins(
            order_id, order_num, category, service,
            details, uid, username, full_name, topic_id,
            is_paid, paid_amount
        )

    if is_paid:
        with db() as conn:
            conn.execute(
                "UPDATE orders SET is_paid=1 WHERE id=?",
                (order_id,)
            )
        asyncio.create_task(sync_order(
            order_num, uid, category, service,
            "", "pending", True, paid_amount
        ))
        # Пуш-уведомление через JSONBin
        asyncio.create_task(JB.push_notification(
            uid,
            f"✅ Заказ {order_num} оформлен и оплачен ({paid_amount} NVC)",
            "success"
        ))

    await state.update_data(order_id=order_id)
    await state.set_state(OrderFSM.in_chat)

    paid_note = f"\n💳 Оплачено: {paid_amount} NVC" if is_paid else ""

    answer_fn = (
        msg_or_call.message.answer
        if isinstance(msg_or_call, types.CallbackQuery)
        else msg_or_call.answer
    )

    await answer_fn(
        f"✅ <b>Заказ оформлен!</b>\n\n"
        f"🔢 <code>{order_num}</code>\n"
        f"📂 {category}\n🛠 {service}{paid_note}\n"
        f"📊 <b>⏳ Ожидает принятия</b>\n\n"
        f"💬 Пиши сюда — сообщения идут администратору.\n\n"
        f"<i>NOVA CREATIVE STUDIO 💜</i>",
        parse_mode="HTML",
        reply_markup=chat_kb()
    )
    log.info(f"🆕 Заказ #{order_id} ({order_num}) от {uid}")


@dp.callback_query(F.data.startswith("paid_confirm:"))
async def cb_paid_confirm(call: types.CallbackQuery, state: FSMContext):
    order_id = int(call.data.split(":")[1])
    order    = get_order(order_id)
    if not order:
        return await call.answer("❌ Не найден", show_alert=True)

    uid      = call.from_user.id
    price    = order[16]

    # Проверяем баланс в JSONBin
    has_nvc = await check_nvc_balance(uid, price)
    if not has_nvc:
        return await call.answer(
            f"❌ Недостаточно NVC!\n"
            f"Нужно {price} NVC.\n"
            f"Пополни в @{NOVAPAY_BOT}",
            show_alert=True
        )

    # Списываем NVC через JSONBin
    new_bal = await deduct_nvc(
        uid, price, f"Оплата заказа {order[14]}: {order[4]}"
    )
    if new_bal is None:
        return await call.answer(
            "❌ Ошибка списания. Попробуйте позже.", show_alert=True
        )

    await call.message.edit_reply_markup(reply_markup=None)
    await call.answer("✅ NVC списаны! Оформляем заказ...")

    await _finalize_order(
        call, state, order_id, order[14],
        order[2], order[4], order[6],
        uid, call.from_user.username or "",
        call.from_user.full_name or str(uid),
        is_paid=True, paid_amount=price
    )


@dp.callback_query(F.data == "cancel_paid")
async def cb_cancel_paid(call: types.CallbackQuery, state: FSMContext):
    data     = await state.get_data()
    order_id = data.get("order_id")
    if order_id:
        order = get_order(order_id)
        with db() as conn:
            conn.execute(
                "UPDATE orders SET status='closed',"
                "close_reason='Отменён до оплаты' WHERE id=?",
                (order_id,)
            )
        if order:
            asyncio.create_task(
                JB.update_order_status_json(order[14], "closed")
            )
    await state.clear()
    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer("❌ Заказ отменён.", reply_markup=remove_kb())
    welcome = WELCOME_TEXT.format(novapay=NOVAPAY_BOT)
    await call.message.answer(
        welcome, parse_mode="HTML", reply_markup=welcome_kb()
    )


@dp.message(OrderFSM.in_chat, F.chat.type == "private")
async def fsm_chat(msg: types.Message, state: FSMContext):
    uid  = msg.from_user.id
    text = msg.text or msg.caption or ""
    data = await state.get_data()
    oid  = data.get("order_id")

    if not oid:
        await state.clear()
        return await msg.answer("❌ Ошибка. /start")

    order = get_order(oid)
    if not order:
        await state.clear()
        return await msg.answer("❌ Заказ не найден. /start")

    if text == "📋 Статус заказа":
        sm = {"pending":"⏳ Ожидает","accepted":"🔄 В работе"}
        return await msg.answer(
            f"📋 <code>{order[14]}</code>\n"
            f"📂 {order[2]}\n🛠 {order[4]}\n"
            f"📊 {sm.get(order[7],order[7])}",
            parse_mode="HTML"
        )

    if text == "❌ Отмена заказа":
        if order[7] == "accepted":
            return await msg.answer("⚠️ Заказ в работе. Обратитесь к администратору.")
        with db() as conn:
            conn.execute(
                "UPDATE orders SET status='closed',"
                "close_reason='Отменён пользователем' WHERE id=?", (oid,)
            )
        asyncio.create_task(
            JB.update_order_status_json(order[14], "closed")
        )
        await state.clear()
        await msg.answer("❌ Заказ отменён.", reply_markup=remove_kb())
        if order[9]:
            try:
                await bot.send_message(
                    ADMIN_GROUP_ID,
                    f"❌ Клиент отменил <code>{order[14]}</code>",
                    message_thread_id=order[9],
                    parse_mode="HTML"
                )
            except Exception:
                pass
        welcome = WELCOME_TEXT.format(novapay=NOVAPAY_BOT)
        return await msg.answer(
            welcome, parse_mode="HTML", reply_markup=welcome_kb()
        )

    if order[7] not in ("pending","accepted"):
        await state.clear()
        return await msg.answer("⚠️ Заказ закрыт. /start")

    fname = msg.from_user.full_name or str(uid)

    for fattr, ftype in [
        ("photo","photo"),("document","document"),
        ("audio","audio"),("voice","voice"),("video","video"),
    ]:
        media = getattr(msg, fattr, None)
        if media:
            fid = media[-1].file_id if fattr=="photo" else media.file_id
            await store_media(fid, ftype, oid)
            await forward_to_topic(oid, from_name=fname, media_msg=msg)
            return await msg.answer("✅ Отправлено.")

    if text:
        await forward_to_topic(oid, text=text, from_name=fname)
        with db() as conn:
            conn.execute(
                "INSERT INTO order_chat("
                "order_id,user_id,role,text,created_at) "
                "VALUES(?,?,?,?,?)",
                (oid, uid, "user", text, datetime.now().isoformat())
            )
        return await msg.answer("✅ Отправлено.")


# ═══════════════════════════════════════════════════════════════
# 🔘 CALLBACKS ЗАКАЗОВ
# ═══════════════════════════════════════════════════════════════

@dp.callback_query(F.data.startswith("accept:"))
async def cb_accept(call: types.CallbackQuery):
    if not is_admin_user(call.from_user.id):
        return await call.answer("⚠️ Нет прав", show_alert=True)

    oid   = int(call.data.split(":")[1])
    order = get_order(oid)
    if not order or order[7] != "pending":
        return await call.answer("⚠️ Уже обработан", show_alert=True)

    with db() as conn:
        conn.execute(
            "UPDATE orders SET status='accepted',"
            "admin_id=?,accepted_at=? WHERE id=?",
            (call.from_user.id, datetime.now().isoformat(), oid)
        )

    asyncio.create_task(
        JB.update_order_status_json(order[14], "accepted")
    )
    asyncio.create_task(JB.push_notification(
        order[1],
        f"🎉 Ваш заказ {order[14]} принят и передан в работу!",
        "success"
    ))

    try:
        await call.message.edit_reply_markup(
            reply_markup=admin_order_kb(oid)
        )
        await bot.send_message(
            ADMIN_GROUP_ID,
            f"✅ Заказ принят — {JB.html_esc(call.from_user.full_name)}",
            message_thread_id=order[9],
            parse_mode="HTML"
        )
    except Exception:
        pass

    try:
        await bot.send_message(
            order[1],
            f"🎉 <b>Заказ принят!</b>\n\n"
            f"🔢 <code>{order[14]}</code>\n"
            f"💬 Пиши прямо в бота — всё дойдёт.\n\n"
            f"<i>NOVA CREATIVE STUDIO 💜</i>",
            parse_mode="HTML",
            reply_markup=chat_kb()
        )
    except Exception:
        pass
    await call.answer("✅")


@dp.callback_query(F.data.startswith("reject:"))
async def cb_reject(call: types.CallbackQuery):
    if not is_admin_user(call.from_user.id):
        return await call.answer("⚠️ Нет прав", show_alert=True)

    oid   = int(call.data.split(":")[1])
    order = get_order(oid)
    if not order or order[7] != "pending":
        return await call.answer("⚠️ Нельзя", show_alert=True)

    with db() as conn:
        conn.execute(
            "UPDATE orders SET status='closed',"
            "close_reason='Отклонён' WHERE id=?", (oid,)
        )
    asyncio.create_task(
        JB.update_order_status_json(order[14], "closed")
    )

    try:
        await call.message.edit_reply_markup(reply_markup=None)
        await bot.send_message(
            order[1],
            f"❌ <b>Заказ отклонён</b>\n\n"
            f"Попробуйте позже: /start\n\n"
            f"<i>NOVA CREATIVE STUDIO 💜</i>",
            parse_mode="HTML",
            reply_markup=remove_kb()
        )
    except Exception:
        pass
    await call.answer("❌")


@dp.callback_query(F.data.startswith("complete:"))
async def cb_complete(call: types.CallbackQuery):
    if not is_admin_user(call.from_user.id):
        return await call.answer("⚠️ Нет прав", show_alert=True)

    oid   = int(call.data.split(":")[1])
    order = get_order(oid)
    if not order or order[7] != "accepted":
        return await call.answer("⚠️ Не в работе", show_alert=True)

    aid = call.from_user.id
    key = StorageKey(bot_id=bot.id, chat_id=aid, user_id=aid)
    adm_state = FSMContext(storage=dp.storage, key=key)
    await adm_state.update_data(order_id=oid)
    await adm_state.set_state(AdminFSM.completing_order)

    try:
        await bot.send_message(
            aid,
            f"📦 <b>Завершение заказа {order[14]}</b>\n\n"
            f"Отправь результаты работы.\n"
            f"Когда всё — напиши <code>/done_result</code>",
            parse_mode="HTML"
        )
        await call.answer("Проверь личку!")
    except Exception:
        await adm_state.clear()
        await call.answer("❌ Напиши боту /start в личку!", show_alert=True)


@dp.callback_query(F.data.startswith("close:"))
async def cb_close(call: types.CallbackQuery):
    if not is_admin_user(call.from_user.id):
        return await call.answer("⚠️ Нет прав", show_alert=True)

    oid   = int(call.data.split(":")[1])
    order = get_order(oid)
    if not order:
        return await call.answer("❌ Не найден", show_alert=True)

    aid = call.from_user.id
    key = StorageKey(bot_id=bot.id, chat_id=aid, user_id=aid)
    adm_state = FSMContext(storage=dp.storage, key=key)
    await adm_state.update_data(order_id=oid)
    await adm_state.set_state(AdminFSM.closing_order)

    try:
        await bot.send_message(
            aid,
            f"🔒 <b>Закрытие {order[14]}</b>\n\nУкажи причину или <code>-</code>",
            parse_mode="HTML"
        )
        await call.answer("Проверь личку!")
    except Exception:
        await adm_state.clear()
        await call.answer("❌ Напиши боту /start в личку!", show_alert=True)


@dp.callback_query(F.data.startswith("rate:"))
async def cb_rate(call: types.CallbackQuery, state: FSMContext):
    parts = call.data.split(":")
    oid   = int(parts[1])
    rat   = int(parts[2])

    if rat == 0:
        try:
            await call.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await call.answer("💜 Спасибо!")
        welcome = WELCOME_TEXT.format(novapay=NOVAPAY_BOT)
        return await bot.send_message(
            call.from_user.id, welcome,
            parse_mode="HTML", reply_markup=welcome_kb()
        )

    await state.update_data(order_id=oid, rating=rat)
    await state.set_state(OrderFSM.waiting_review)
    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await bot.send_message(
        call.from_user.id,
        f"{'⭐'*rat} Оставь комментарий:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="⏭ Пропустить")]],
            resize_keyboard=True
        )
    )


@dp.message(OrderFSM.waiting_review, F.chat.type == "private")
async def fsm_review(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    oid  = data.get("order_id")
    rat  = data.get("rating", 5)
    text = msg.text or ""

    if text in ("⏭ Пропустить", "/skip"):
        await state.clear()
        await msg.answer("💜 Спасибо!", reply_markup=remove_kb())
        welcome = WELCOME_TEXT.format(novapay=NOVAPAY_BOT)
        return await msg.answer(
            welcome, parse_mode="HTML", reply_markup=welcome_kb()
        )

    with db() as conn:
        conn.execute(
            "INSERT INTO reviews("
            "order_id,user_id,text,rating,created_at) "
            "VALUES(?,?,?,?,?)",
            (oid, msg.from_user.id, text, rat,
             datetime.now().isoformat())
        )

    await state.clear()
    await msg.answer(f"💜 Спасибо!\n{'⭐'*rat}", reply_markup=remove_kb())
    welcome = WELCOME_TEXT.format(novapay=NOVAPAY_BOT)
    await msg.answer(welcome, parse_mode="HTML", reply_markup=welcome_kb())

    order = get_order(oid)
    if order and order[9]:
        try:
            await bot.send_message(
                ADMIN_GROUP_ID,
                f"⭐ <b>Отзыв</b> <code>{order[14]}</code>\n"
                f"{'⭐'*rat}\n{JB.html_esc(text)}",
                message_thread_id=order[9],
                parse_mode="HTML"
            )
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════
# 👮 ADMIN FSM
# ═══════════════════════════════════════════════════════════════

@dp.message(AdminFSM.completing_order, F.chat.type == "private")
async def adm_result(msg: types.Message, state: FSMContext):
    if not is_admin_user(msg.from_user.id):
        return
    if msg.text == "/done_result":
        await state.set_state(AdminFSM.entering_check)
        return await msg.answer(
            "📋 Опиши что было сделано:"
        )
    data  = await state.get_data()
    order = get_order(data.get("order_id"))
    if not order:
        return
    sent = await send_media_to_user(order[0], msg)
    if sent:
        return await msg.answer("✅ Файл отправлен клиенту")
    if msg.text:
        await send_to_user(order[0], text=msg.text)
        return await msg.answer("✅ Сообщение отправлено")


@dp.message(AdminFSM.entering_check, F.chat.type == "private")
async def adm_check(msg: types.Message, state: FSMContext):
    if not is_admin_user(msg.from_user.id):
        return

    data     = await state.get_data()
    order_id = data.get("order_id")
    order    = get_order(order_id)
    if not order:
        await state.clear()
        return

    with db() as conn:
        conn.execute(
            "UPDATE orders SET status='done',closed_at=? WHERE id=?",
            (datetime.now().isoformat(), order_id)
        )
        media = conn.execute(
            "SELECT file_type,COUNT(*) FROM order_media "
            "WHERE order_id=? AND direction='result' "
            "GROUP BY file_type", (order_id,)
        ).fetchall()

    asyncio.create_task(
        JB.update_order_status_json(order[14], "done")
    )
    asyncio.create_task(JB.push_notification(
        order[1],
        f"✅ Ваш заказ {order[14]} выполнен! Оставьте отзыв.",
        "success"
    ))

    icons = {"photo":"📸","audio":"🎵","video":"🎬","document":"📎"}
    media_lines = "\n".join(
        f"{icons.get(ft,'📄')} {ft}: {cnt}"
        for ft, cnt in media
    )

    paid_note = f"💳 Оплачено: {order[16]} NVC\n" if order[15] else ""
    check_text = msg.text or "—"

    check_msg = (
        f"🧾 <b>ЧЕК ЗАКАЗА — NOVA CREATIVE STUDIO</b>\n\n"
        f"🔢 <code>{order[14]}</code>\n"
        f"📂 {order[2]}\n🛠 {order[4]}\n"
        f"{paid_note}"
        f"✅ {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        f"<b>Результат:</b>\n{media_lines or '—'}\n\n"
        f"<b>Детали:</b>\n{JB.html_esc(check_text)}\n\n"
        f"Спасибо, что выбрали NOVA CREATIVE STUDIO! 💜"
    )

    try:
        await bot.send_message(
            order[1], check_msg,
            parse_mode="HTML", reply_markup=remove_kb()
        )
        await bot.send_message(
            order[1], "⭐ <b>Оцените работу!</b>",
            parse_mode="HTML",
            reply_markup=rating_kb(order_id)
        )
    except Exception as e:
        log.error(f"send check: {e}")

    if order[9]:
        try:
            await bot.send_message(
                ADMIN_GROUP_ID,
                f"✅ <b>Заказ {order[14]} завершён!</b>",
                message_thread_id=order[9],
                parse_mode="HTML"
            )
            await bot.close_forum_topic(ADMIN_GROUP_ID, order[9])
        except Exception:
            pass

    await msg.answer("✅ Заказ завершён! Чек отправлен клиенту. 💜")
    await state.clear()


@dp.message(AdminFSM.closing_order, F.chat.type == "private")
async def adm_close(msg: types.Message, state: FSMContext):
    if not is_admin_user(msg.from_user.id):
        return

    data     = await state.get_data()
    order_id = data.get("order_id")
    order    = get_order(order_id)
    reason   = (
        msg.text.strip()
        if msg.text and msg.text.strip() != "-"
        else "Закрыт администратором"
    )

    if not order:
        await state.clear()
        return

    with db() as conn:
        conn.execute(
            "UPDATE orders SET status='closed',"
            "closed_at=?,close_reason=? WHERE id=?",
            (datetime.now().isoformat(), reason, order_id)
        )

    asyncio.create_task(
        JB.update_order_status_json(order[14], "closed")
    )

    try:
        await bot.send_message(
            order[1],
            f"🔒 <b>Заказ закрыт</b>\n\n"
            f"🔢 <code>{order[14]}</code>\n"
            f"Причина: {JB.html_esc(reason)}\n\n"
            f"Новый заказ: /start",
            parse_mode="HTML",
            reply_markup=remove_kb()
        )
    except Exception:
        pass

    if order[9]:
        try:
            await bot.send_message(
                ADMIN_GROUP_ID,
                f"🔒 {order[14]} закрыт.\n{JB.html_esc(reason)}",
                message_thread_id=order[9],
                parse_mode="HTML"
            )
            await bot.close_forum_topic(ADMIN_GROUP_ID, order[9])
        except Exception:
            pass

    await msg.answer(f"✅ Заказ {order[14]} закрыт.")
    await state.clear()


# ═══════════════════════════════════════════════════════════════
# 📨 ГРУППА → ПОЛЬЗОВАТЕЛЬ
# ═══════════════════════════════════════════════════════════════

@dp.message(F.chat.id == ADMIN_GROUP_ID)
async def handle_group(msg: types.Message):
    if msg.text and msg.text.startswith("/"):
        return
    if not msg.message_thread_id:
        return
    if not is_admin_user(msg.from_user.id):
        return

    with db() as conn:
        order = conn.execute(
            "SELECT * FROM orders WHERE topic_id=? "
            "AND status IN ('pending','accepted')",
            (msg.message_thread_id,)
        ).fetchone()

    if not order:
        return

    try:
        if msg.text:
            await bot.send_message(
                order[1],
                f"💬 <b>NOVA CREATIVE STUDIO:</b>\n\n"
                f"{JB.html_esc(msg.text)}",
                parse_mode="HTML"
            )
        else:
            for fattr, ftype in [
                ("photo","photo"),("document","document"),
                ("audio","audio"),("video","video"),("voice","voice"),
            ]:
                if getattr(msg, fattr, None):
                    await msg.copy_to(order[1])
                    break
    except Exception as e:
        log.error(f"group→user: {e}")


# ═══════════════════════════════════════════════════════════════
# 🔐 КОМАНДЫ АДМИНА
# ═══════════════════════════════════════════════════════════════

@dp.message(Command("help"))
async def cmd_help(msg: types.Message):
    if not is_admin_chat(msg) or not is_admin_user(msg.from_user.id):
        return
    await msg.reply(
        "📖 <b>Команды</b>\n\n"
        "/orders — активные заказы\n"
        "/stats — статистика\n"
        "/user ID — инфо о пользователе\n"
        "/ban ID — заблокировать\n"
        "/unban ID — разблокировать\n"
        "/warn ID — предупреждение\n"
        "/dm ID Текст — написать пользователю\n"
        "/broadcast Текст — рассылка\n"
        "/addadmin ID — добавить администратора\n"
        "/removeadmin ID — удалить администратора",
        parse_mode="HTML"
    )


@dp.message(Command("stats"))
async def cmd_stats(msg: types.Message):
    if not is_admin_chat(msg) or not is_admin_user(msg.from_user.id):
        return
    with db() as conn:
        tu   = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        ban  = conn.execute("SELECT COUNT(*) FROM users WHERE is_banned=1").fetchone()[0]
        to   = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        pend = conn.execute("SELECT COUNT(*) FROM orders WHERE status='pending'").fetchone()[0]
        acc  = conn.execute("SELECT COUNT(*) FROM orders WHERE status='accepted'").fetchone()[0]
        done = conn.execute("SELECT COUNT(*) FROM orders WHERE status='done'").fetchone()[0]

    await msg.reply(
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Пользователей: <b>{tu}</b>\n"
        f"🚫 Забанено: <b>{ban}</b>\n\n"
        f"📋 Заказов: <b>{to}</b>\n"
        f"⏳ Ожидают: <b>{pend}</b>\n"
        f"🔄 В работе: <b>{acc}</b>\n"
        f"✅ Завершено: <b>{done}</b>",
        parse_mode="HTML"
    )


@dp.message(Command("orders"))
async def cmd_orders(msg: types.Message):
    if not is_admin_chat(msg) or not is_admin_user(msg.from_user.id):
        return
    with db() as conn:
        orders = conn.execute(
            "SELECT order_num,category,service,status,user_id,created_at "
            "FROM orders WHERE status IN ('pending','accepted') "
            "ORDER BY created_at DESC LIMIT 15"
        ).fetchall()
    if not orders:
        return await msg.reply("📭 Активных заказов нет.")
    text = f"📋 <b>Активные заказы ({len(orders)}):</b>\n\n"
    for o in orders:
        icon = "⏳" if o[3]=="pending" else "🔄"
        text += (
            f"{icon} <code>{o[0]}</code>\n"
            f"   {o[1]} → {o[2][:20]}\n"
            f"   <code>{o[4]}</code>\n\n"
        )
    await msg.reply(text, parse_mode="HTML")


@dp.message(Command("ban"))
async def cmd_ban(msg: types.Message):
    if not is_admin_chat(msg) or not is_admin_user(msg.from_user.id):
        return
    parts = msg.text.split(maxsplit=2)
    if len(parts) < 2:
        return await msg.reply("/ban USER_ID [причина]")
    try:
        uid = int(parts[1])
    except ValueError:
        return await msg.reply("❌ Неверный ID")
    if uid == OWNER_ID:
        return await msg.reply("⚠️ Нельзя!")
    reason = parts[2] if len(parts) > 2 else "Нарушение правил"
    with db() as conn:
        conn.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (uid,))
    try:
        await bot.send_message(
            uid,
            f"🚫 <b>Вы заблокированы</b>\nПричина: {JB.html_esc(reason)}",
            parse_mode="HTML"
        )
    except Exception:
        pass
    await msg.reply(
        f"🚫 <code>{uid}</code> заблокирован.", parse_mode="HTML"
    )


@dp.message(Command("unban"))
async def cmd_unban(msg: types.Message):
    if not is_admin_chat(msg) or not is_admin_user(msg.from_user.id):
        return
    parts = msg.text.split()
    if len(parts) < 2:
        return await msg.reply("/unban USER_ID")
    try:
        uid = int(parts[1])
    except ValueError:
        return await msg.reply("❌ Неверный ID")
    with db() as conn:
        conn.execute(
            "UPDATE users SET is_banned=0,warn_count=0 WHERE user_id=?",
            (uid,)
        )
    try:
        await bot.send_message(uid, "✅ Вы разблокированы. 💜")
    except Exception:
        pass
    await msg.reply(f"✅ <code>{uid}</code> разблокирован.", parse_mode="HTML")


@dp.message(Command("warn"))
async def cmd_warn(msg: types.Message):
    if not is_admin_chat(msg) or not is_admin_user(msg.from_user.id):
        return
    parts = msg.text.split(maxsplit=2)
    if len(parts) < 2:
        return await msg.reply("/warn USER_ID [причина]")
    try:
        uid = int(parts[1])
    except ValueError:
        return await msg.reply("❌ Неверный ID")
    reason = parts[2] if len(parts) > 2 else "Предупреждение"
    with db() as conn:
        conn.execute(
            "UPDATE users SET warn_count=warn_count+1 WHERE user_id=?",
            (uid,)
        )
        wc = conn.execute(
            "SELECT warn_count FROM users WHERE user_id=?", (uid,)
        ).fetchone()
    wc = wc[0] if wc else 1
    try:
        await bot.send_message(
            uid,
            f"⚠️ <b>Предупреждение</b>\n"
            f"Причина: {JB.html_esc(reason)}\n"
            f"Предупреждений: {wc}/3",
            parse_mode="HTML"
        )
    except Exception:
        pass
    await msg.reply(f"⚠️ {uid} — {wc}/3", parse_mode="HTML")
    if wc >= 3:
        with db() as conn:
            conn.execute(
                "UPDATE users SET is_banned=1 WHERE user_id=?", (uid,)
            )
        await msg.reply(f"🚫 <code>{uid}</code> автозабанен.", parse_mode="HTML")


@dp.message(Command("dm"))
async def cmd_dm(msg: types.Message):
    if not is_admin_chat(msg) or not is_admin_user(msg.from_user.id):
        return
    parts = msg.text.split(maxsplit=2)
    if len(parts) < 3:
        return await msg.reply("/dm USER_ID Сообщение")
    try:
        uid = int(parts[1])
    except ValueError:
        return await msg.reply("❌ Неверный ID")
    try:
        await bot.send_message(
            uid,
            f"📩 <b>Уведомление от NOVA CREATIVE STUDIO</b>\n\n"
            f"{JB.html_esc(parts[2])}",
            parse_mode="HTML"
        )
        await msg.reply(f"✅ Отправлено → <code>{uid}</code>", parse_mode="HTML")
    except Exception as e:
        await msg.reply(f"❌ {e}")


@dp.message(Command("broadcast"))
async def cmd_broadcast(msg: types.Message):
    if not is_admin_chat(msg) or not is_admin_user(msg.from_user.id):
        return
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        return await msg.reply("/broadcast Текст")
    text   = parts[1]
    status = await msg.reply("⏳ Рассылаю...")
    ok = fail = 0
    for u in all_users_local():
        if u[3]:
            continue
        try:
            await bot.send_message(u[0], text)
            ok += 1
            await asyncio.sleep(0.05)
        except Exception:
            fail += 1
    await status.edit_text(f"📢 Готово! ✅{ok} ❌{fail}")


@dp.message(Command("addadmin"))
async def cmd_addadmin(msg: types.Message):
    if not is_admin_chat(msg) or msg.from_user.id != OWNER_ID:
        return
    parts = msg.text.split()
    if len(parts) < 2:
        return await msg.reply("/addadmin USER_ID")
    try:
        uid = int(parts[1])
    except ValueError:
        return await msg.reply("❌ Неверный ID")
    with db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO admins(user_id,added_at) VALUES(?,?)",
            (uid, datetime.now().isoformat())
        )
    await msg.reply(f"🛡 <code>{uid}</code> добавлен как администратор.", parse_mode="HTML")
    try:
        await bot.send_message(
            uid,
            "🛡 <b>Вы назначены администратором NOVA CREATIVE STUDIO!</b>",
            parse_mode="HTML"
        )
    except Exception:
        pass


@dp.message(Command("removeadmin"))
async def cmd_removeadmin(msg: types.Message):
    if not is_admin_chat(msg) or msg.from_user.id != OWNER_ID:
        return
    parts = msg.text.split()
    if len(parts) < 2:
        return await msg.reply("/removeadmin USER_ID")
    try:
        uid = int(parts[1])
    except ValueError:
        return await msg.reply("❌ Неверный ID")
    with db() as conn:
        conn.execute("DELETE FROM admins WHERE user_id=?", (uid,))
    await msg.reply(f"❌ <code>{uid}</code> удалён.", parse_mode="HTML")


# ═══════════════════════════════════════════════════════════════
# ⏰ АВТОЗАКРЫТИЕ
# ═══════════════════════════════════════════════════════════════

async def auto_close():
    while True:
        try:
            cutoff = (
                datetime.now() - timedelta(hours=AUTO_CLOSE_HOURS)
            ).isoformat()
            with db() as conn:
                expired = conn.execute(
                    "SELECT * FROM orders WHERE status='pending' "
                    "AND created_at<?", (cutoff,)
                ).fetchall()

            for o in expired:
                with db() as conn:
                    conn.execute(
                        "UPDATE orders SET status='closed',"
                        "close_reason=? WHERE id=?",
                        (f"Автозакрытие {AUTO_CLOSE_HOURS}ч", o[0])
                    )
                asyncio.create_task(
                    JB.update_order_status_json(o[14], "closed")
                )
                try:
                    await bot.send_message(
                        o[1],
                        f"⚠️ Заказ <code>{o[14]}</code> "
                        f"автоматически закрыт ({AUTO_CLOSE_HOURS}ч).\n"
                        f"Попробуйте снова: /start",
                        parse_mode="HTML",
                        reply_markup=remove_kb()
                    )
                except Exception:
                    pass
                if o[9]:
                    try:
                        await bot.send_message(
                            ADMIN_GROUP_ID,
                            f"⏰ <code>{o[14]}</code> автозакрыт.",
                            message_thread_id=o[9],
                            parse_mode="HTML"
                        )
                        await bot.close_forum_topic(ADMIN_GROUP_ID, o[9])
                    except Exception:
                        pass

        except Exception as e:
            log.error(f"auto_close: {e}")

        await asyncio.sleep(1800)


# ═══════════════════════════════════════════════════════════════
# 🎯 MAIN
# ═══════════════════════════════════════════════════════════════

async def main():
    init_db()
    log.info("🌃 NOVA Orders Bot запущен")
    log.info(f"👑 Owner:   {OWNER_ID}")
    log.info(f"👥 Group:   {ADMIN_GROUP_ID}")
    log.info(f"📦 Storage: {STORAGE_CHANNEL}")
    asyncio.create_task(auto_close())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())