"""
💜 NOVA PAY BOT
Использует shared_api.py для общего JSONBin
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta

sys.path.append(str(Path(__file__).parent.parent))
import shared_api as JB

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    WebAppInfo
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ═══════════════════════════════════════════════════════════════
# 🔧 КОНФИГУРАЦИЯ
# ═══════════════════════════════════════════════════════════════

NOVAPAY_TOKEN = os.environ["NOVAPAY_TOKEN"]
OWNER_ID      = int(os.getenv("OWNER_ID",   "7969709802"))
WEBAPP_URL    = os.getenv("WEBAPP_URL",     "https://nova-pay-app.vercel.app")
ORDERS_BOT    = os.getenv("ORDERS_BOT",    "Nova_creativestudiobot")
CHANNEL_ID    = os.getenv("CHANNEL_ID",    "NOVA_creators")

WEEKLY_BONUS      = 20
REFERRAL_BONUS    = 50
CHANNEL_SUB_BONUS = 30

STARS_RATES = [
    {"stars": 50,  "nvc": 50,  "label": ""},
    {"stars": 100, "nvc": 110, "label": ""},
    {"stars": 250, "nvc": 300, "label": "🔥 Выгодно"},
    {"stars": 500, "nvc": 650, "label": "👑 Лучший"},
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("NovaPay")

bot = Bot(token=NOVAPAY_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())


# ═══════════════════════════════════════════════════════════════
# 📝 FSM
# ═══════════════════════════════════════════════════════════════

class NPState(StatesGroup):
    transfer_to     = State()
    transfer_amount = State()


# ═══════════════════════════════════════════════════════════════
# 🎹 КЛАВИАТУРЫ
# ═══════════════════════════════════════════════════════════════

def main_kb(uid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="💳 Открыть Nova Pay",
            web_app=WebAppInfo(url=f"{WEBAPP_URL}?uid={uid}")
        )],
        [
            InlineKeyboardButton(
                text="💰 Баланс", callback_data="np_balance"
            ),
            InlineKeyboardButton(
                text="📋 История", callback_data="np_history"
            ),
        ],
        [
            InlineKeyboardButton(
                text="📤 Перевести", callback_data="np_transfer"
            ),
            InlineKeyboardButton(
                text="🎁 Бонусы", callback_data="np_bonuses"
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔗 Реферал", callback_data="np_referral"
            ),
            InlineKeyboardButton(
                text="💳 Карточки", callback_data="np_cards"
            ),
        ],
        [InlineKeyboardButton(
            text="💫 Купить NVC", callback_data="np_buy"
        )],
    ])


def back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="np_menu")]
    ])


# ═══════════════════════════════════════════════════════════════
# /start
# ═══════════════════════════════════════════════════════════════

@dp.message(Command("start"))
async def cmd_start(msg: types.Message, state: FSMContext):
    await state.clear()
    uid      = msg.from_user.id
    username = msg.from_user.username or ""
    fname    = (msg.from_user.first_name or "") + " " + (msg.from_user.last_name or "")
    fname    = fname.strip() or str(uid)

    parts = msg.text.split(maxsplit=1)
    param = parts[1] if len(parts) > 1 else ""

    user   = await JB.get_user(uid)
    is_new = user is None

    if is_new:
        anim = await msg.answer("⚡ Создаём аккаунт Nova Pay...")
        await asyncio.sleep(0.8)
        await anim.edit_text("💳 Выпускаем карточку Starter...")
        await asyncio.sleep(0.8)

        user = await JB.register_user(uid, username, fname)

        if param.startswith("REF-"):
            await JB.process_referral(uid, param)

        if param.startswith("check_"):
            check_id = param.replace("check_", "")
            await anim.delete()
            return await _activate_check(msg, uid, check_id)

        await anim.edit_text(
            f"✅ <b>Добро пожаловать в Nova Pay!</b>\n\n"
            f"💳 Карточка: <b>Starter</b>\n"
            f"💰 Стартовый баланс: <b>20 NVC</b>\n"
            f"🆔 Telegram ID: <code>{uid}</code>",
            parse_mode="HTML"
        )
        await asyncio.sleep(0.8)
        await msg.answer(
            "🎨 Хотите персонализировать карточку?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="📝 Привязать никнейм",
                    callback_data="np_link_nick"
                )],
                [InlineKeyboardButton(
                    text="⏭ Пропустить",
                    callback_data="np_menu"
                )],
            ])
        )
        return

    if param.startswith("check_"):
        return await _activate_check(msg, uid, param.replace("check_",""))

    await msg.answer(
        f"👋 <b>С возвращением!</b>\n\n"
        f"💰 Баланс: <b>{user.get('balance',0)} NVC</b>\n"
        f"💳 Карточка: <b>{user.get('card_tier','starter').capitalize()}</b>",
        parse_mode="HTML",
        reply_markup=main_kb(uid)
    )


async def _activate_check(msg: types.Message, uid: int, check_id: str):
    result = await JB.activate_check(check_id, uid)
    errors = {
        "not_found": "❌ Чек не найден",
        "used":      "❌ Чек уже использован",
        "expired":   "❌ Срок действия истёк",
        "own_check": "❌ Нельзя активировать свой чек"
    }
    if not result.get("ok"):
        return await msg.answer(
            errors.get(result.get("error",""), "❌ Ошибка"),
            reply_markup=main_kb(uid)
        )
    await msg.answer(
        f"🎉 <b>Чек активирован!</b>\n\n"
        f"💰 +{result['amount']} NVC\n"
        f"💳 Баланс: <b>{result['new_balance']} NVC</b>",
        parse_mode="HTML",
        reply_markup=main_kb(uid)
    )


# ═══════════════════════════════════════════════════════════════
# CALLBACKS
# ═══════════════════════════════════════════════════════════════

@dp.callback_query(F.data == "np_menu")
async def cb_menu(call: types.CallbackQuery):
    uid  = call.from_user.id
    user = await JB.get_user(uid)
    if not user:
        return await call.answer("Сначала /start", show_alert=True)
    try:
        await call.message.edit_text(
            f"💳 <b>Nova Pay</b>\n\n"
            f"👤 {call.from_user.full_name}\n"
            f"💰 Баланс: <b>{user.get('balance',0)} NVC</b>\n"
            f"💳 Карточка: <b>{user.get('card_tier','starter').capitalize()}</b>",
            parse_mode="HTML",
            reply_markup=main_kb(uid)
        )
    except Exception:
        pass
    await call.answer()


@dp.callback_query(F.data == "np_balance")
async def cb_balance(call: types.CallbackQuery):
    user = await JB.get_user(call.from_user.id)
    if not user:
        return await call.answer("Сначала /start", show_alert=True)
    await call.message.edit_text(
        f"💰 <b>Баланс Nova Pay</b>\n\n"
        f"🪙 Текущий: <b>{user.get('balance',0)} NVC</b>\n"
        f"📈 Получено всего: <b>{user.get('total_earned',0)} NVC</b>\n"
        f"📉 Потрачено всего: <b>{user.get('total_spent',0)} NVC</b>",
        parse_mode="HTML",
        reply_markup=back_kb()
    )


@dp.callback_query(F.data == "np_history")
async def cb_history(call: types.CallbackQuery):
    uid  = call.from_user.id
    txs  = await JB.get_user_transactions(uid)
    last = txs[:10]

    if not last:
        text = "📋 <b>История</b>\n\n<i>Пока пусто</i>"
    else:
        icons = {
            "bonus":"🎁","transfer":"💸",
            "payment":"🛒","check":"🎰"
        }
        text = "📋 <b>Последние транзакции</b>\n\n"
        for t in last:
            inc  = t.get("to_id") == uid
            sign = "+" if inc else "−"
            icon = "📥" if inc else "📤"
            text += (
                f"{icon} {sign}{t['amount']} NVC\n"
                f"   {t.get('description','')}\n"
                f"   {JB.fmt_dt(t.get('created_at',''))}\n\n"
            )

    await call.message.edit_text(
        text, parse_mode="HTML", reply_markup=back_kb()
    )


@dp.callback_query(F.data == "np_referral")
async def cb_referral(call: types.CallbackQuery):
    uid  = call.from_user.id
    user = await JB.get_user(uid)
    if not user:
        return await call.answer("Сначала /start", show_alert=True)

    me   = await bot.get_me()
    link = f"https://t.me/{me.username}?start={user.get('referral_code','')}"

    await call.message.edit_text(
        f"🔗 <b>Реферальная программа</b>\n\n"
        f"💰 Вы получаете: <b>{REFERRAL_BONUS} NVC</b> за каждого\n"
        f"💰 Друг получает: <b>20 NVC</b>\n\n"
        f"👥 Приглашено: <b>{user.get('referral_count',0)}</b>\n\n"
        f"🔗 Ваша ссылка:\n<code>{link}</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📤 Поделиться",
                url=f"https://t.me/share/url?url={link}"
                    f"&text=Присоединяйся к Nova Pay!"
            )],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="np_menu")]
        ])
    )


@dp.callback_query(F.data == "np_bonuses")
async def cb_bonuses(call: types.CallbackQuery):
    uid  = call.from_user.id
    user = await JB.get_user(uid)
    if not user:
        return await call.answer("Сначала /start", show_alert=True)

    last   = datetime.fromisoformat(
        user.get("last_weekly_bonus", "2000-01-01T00:00:00")
    )
    next_b = last + timedelta(days=7)
    can    = datetime.now() >= next_b
    days   = max(0, (next_b - datetime.now()).days)

    rows = []
    if can:
        rows.append([InlineKeyboardButton(
            text=f"🎁 Получить {WEEKLY_BONUS} NVC",
            callback_data="np_claim_weekly"
        )])
    if CHANNEL_ID and not user.get("subscribed_channel"):
        rows.append([InlineKeyboardButton(
            text=f"📢 Подписаться (+{CHANNEL_SUB_BONUS} NVC)",
            callback_data="np_check_sub"
        )])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="np_menu")])

    await call.message.edit_text(
        f"🎁 <b>Бонусы</b>\n\n"
        f"🗓 Еженедельный: <b>{WEEKLY_BONUS} NVC</b>\n"
        f"   {'✅ Доступен!' if can else f'⏳ Через {days} дн.'}\n\n"
        f"👥 За реферала: <b>{REFERRAL_BONUS} NVC</b>\n"
        f"📢 За подписку: <b>{CHANNEL_SUB_BONUS} NVC</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )


@dp.callback_query(F.data == "np_claim_weekly")
async def cb_claim(call: types.CallbackQuery):
    uid  = call.from_user.id
    user = await JB.get_user(uid)
    if not user:
        return await call.answer("Сначала /start", show_alert=True)

    last   = datetime.fromisoformat(
        user.get("last_weekly_bonus","2000-01-01T00:00:00")
    )
    next_b = last + timedelta(days=7)
    if datetime.now() < next_b:
        return await call.answer(
            f"⏳ Через {(next_b-datetime.now()).days} дн.",
            show_alert=True
        )

    await JB.update_user_field(
        uid, "last_weekly_bonus", datetime.now().isoformat()
    )
    new_bal = await JB.update_balance(uid, WEEKLY_BONUS, "Еженедельный бонус")
    await call.answer(f"🎉 +{WEEKLY_BONUS} NVC! Баланс: {new_bal}", show_alert=True)
    await cb_bonuses(call)


@dp.callback_query(F.data == "np_check_sub")
async def cb_check_sub(call: types.CallbackQuery):
    uid = call.from_user.id
    if not CHANNEL_ID:
        return await call.answer("Канал не настроен", show_alert=True)
    try:
        m = await bot.get_chat_member(CHANNEL_ID, uid)
        ok = m.status not in ("left","kicked")
    except Exception:
        ok = False

    if not ok:
        return await call.answer(
            "❌ Подпишитесь сначала!", show_alert=True
        )

    user = await JB.get_user(uid)
    if user and user.get("subscribed_channel"):
        return await call.answer("✅ Бонус уже получен!", show_alert=True)

    await JB.update_user_field(uid, "subscribed_channel", True)
    new_bal = await JB.update_balance(uid, CHANNEL_SUB_BONUS, "Подписка на канал")
    await call.answer(
        f"🎉 +{CHANNEL_SUB_BONUS} NVC! Баланс: {new_bal}", show_alert=True
    )


@dp.callback_query(F.data == "np_cards")
async def cb_cards(call: types.CallbackQuery):
    uid  = call.from_user.id
    user = await JB.get_user(uid)
    if not user:
        return await call.answer("Сначала /start", show_alert=True)

    tiers = {
        "starter":  {"emoji":"🟣","price":0,   "name":"Starter"},
        "creative": {"emoji":"💜","price":200,  "name":"Creative"},
        "elite":    {"emoji":"👑","price":500,  "name":"Nova Elite"},
    }
    cur  = user.get("card_tier","starter")
    text = "💳 <b>Тарифы карточек</b>\n\n"
    rows = []

    for key, info in tiers.items():
        is_cur = cur == key
        price  = "Бесплатно" if info["price"]==0 else f"{info['price']} NVC"
        text  += f"{info['emoji']} <b>{info['name']}</b> — {price}"
        text  += " ✅\n" if is_cur else "\n"
        if not is_cur and info["price"] > 0:
            rows.append([InlineKeyboardButton(
                text=f"Купить {info['name']} — {info['price']} NVC",
                callback_data=f"np_buy_card:{key}"
            )])

    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="np_menu")])
    await call.message.edit_text(
        text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )


@dp.callback_query(F.data.startswith("np_buy_card:"))
async def cb_buy_card(call: types.CallbackQuery):
    uid  = call.from_user.id
    tier = call.data.split(":")[1]
    prices = {"starter":0,"creative":200,"elite":500}
    price  = prices.get(tier,0)

    user = await JB.get_user(uid)
    if not user:
        return await call.answer("Сначала /start", show_alert=True)
    if user.get("balance",0) < price:
        return await call.answer(
            f"❌ Нужно {price} NVC, у вас {user.get('balance',0)}",
            show_alert=True
        )

    await JB.upgrade_card_tier(uid, tier)
    await call.answer(f"✅ Карточка {tier} активирована!", show_alert=True)
    await cb_cards(call)


@dp.callback_query(F.data == "np_buy")
async def cb_buy(call: types.CallbackQuery):
    rates = "\n".join(
        f"⭐ {r['stars']} Stars → <b>{r['nvc']} NVC</b>"
        + (f" {r['label']}" if r['label'] else "")
        for r in STARS_RATES
    )
    await call.message.edit_text(
        f"💫 <b>Купить NVC за Stars</b>\n\n{rates}\n\n"
        f"Выберите пакет:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            *[[InlineKeyboardButton(
                text=f"⭐ {r['stars']} → {r['nvc']} NVC {r['label']}",
                callback_data=f"np_rate:{r['stars']}:{r['nvc']}"
            )] for r in STARS_RATES],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="np_menu")]
        ])
    )


@dp.callback_query(F.data.startswith("np_rate:"))
async def cb_rate(call: types.CallbackQuery):
    uid   = call.from_user.id
    parts = call.data.split(":")
    stars = int(parts[1])
    nvc   = int(parts[2])

    user = await JB.get_user(uid)
    if not user:
        return await call.answer("Сначала /start", show_alert=True)

    req = await JB.create_pending(
        uid, user.get("username",""),
        user.get("full_name", str(uid)),
        stars, nvc
    )

    # Уведомляем владельца
    try:
        await bot.send_message(
            OWNER_ID,
            f"💳 <b>Новая заявка</b>\n\n"
            f"👤 {JB.html_esc(user.get('full_name',''))} "
            f"(@{user.get('username','—')})\n"
            f"🆔 <code>{uid}</code>\n"
            f"⭐ {stars} Stars → 💰 {nvc} NVC\n\n"
            f"ID: <code>{req['req_id']}</code>\n"
            f"/approve {req['req_id']}\n"
            f"/decline {req['req_id']}",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await call.message.edit_text(
        f"✅ <b>Заявка создана!</b>\n\n"
        f"🔢 <code>{req['req_id']}</code>\n"
        f"⭐ {stars} Stars → 💰 {nvc} NVC\n\n"
        f"Отправьте Stars владельцу студии и укажите "
        f"ID заявки. Баланс пополнится в течение часа.",
        parse_mode="HTML",
        reply_markup=back_kb()
    )


@dp.callback_query(F.data == "np_transfer")
async def cb_transfer(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(NPState.transfer_to)
    await call.message.edit_text(
        "📤 <b>Перевод NVC</b>\n\nВведите Telegram ID получателя:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="np_menu")]
        ])
    )


@dp.message(NPState.transfer_to)
async def fsm_transfer_to(msg: types.Message, state: FSMContext):
    try:
        to_id = int(msg.text.strip())
    except ValueError:
        return await msg.answer("❌ Введите числовой ID")
    if to_id == msg.from_user.id:
        return await msg.answer("❌ Нельзя переводить себе")
    to_user = await JB.get_user(to_id)
    if not to_user:
        return await msg.answer("❌ Пользователь не найден в Nova Pay")

    await state.update_data(to_id=to_id, to_name=to_user.get("full_name",""))
    await state.set_state(NPState.transfer_amount)
    await msg.answer(
        f"📤 → <b>{to_user.get('full_name','')}</b>\n\nВведите сумму NVC:",
        parse_mode="HTML"
    )


@dp.message(NPState.transfer_amount)
async def fsm_transfer_amount(msg: types.Message, state: FSMContext):
    uid = msg.from_user.id
    try:
        amount = int(msg.text.strip())
        if amount <= 0:
            raise ValueError
    except ValueError:
        return await msg.answer("❌ Введите положительное число")

    user = await JB.get_user(uid)
    if not user or user.get("balance",0) < amount:
        return await msg.answer(
            f"❌ Недостаточно NVC. Баланс: {user.get('balance',0) if user else 0}"
        )

    data    = await state.get_data()
    to_id   = data["to_id"]
    to_name = data["to_name"]

    # Перевод через JSONBin
    d = await JB.jget(JB.BIN_USERS, force=True)
    d["users"][str(uid)]["balance"]    -= amount
    d["users"][str(uid)]["total_spent"] = d["users"][str(uid)].get("total_spent",0) + amount
    d["users"][str(to_id)]["balance"]  += amount
    d["users"][str(to_id)]["total_earned"] = d["users"][str(to_id)].get("total_earned",0) + amount
    await JB.jput(JB.BIN_USERS, d)

    await JB.add_transaction(
        uid, to_id, amount, "transfer", f"Перевод → {to_name}"
    )
    await JB.push_notification(
        to_id,
        f"💰 Получен перевод +{amount} NVC от {msg.from_user.full_name}",
        "success"
    )

    await state.clear()
    await msg.answer(
        f"✅ <b>Переведено!</b>\n\n"
        f"📤 → {to_name}\n💰 {amount} NVC",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Меню", callback_data="np_menu")]
        ])
    )
    try:
        await bot.send_message(
            to_id,
            f"💰 <b>Получен перевод!</b>\n\n"
            f"📥 От: {msg.from_user.full_name}\n"
            f"💰 Сумма: <b>{amount} NVC</b>",
            parse_mode="HTML"
        )
    except Exception:
        pass


@dp.callback_query(F.data == "np_link_nick")
async def cb_link_nick(call: types.CallbackQuery):
    uid   = call.from_user.id
    uname = call.from_user.username
    if not uname:
        return await call.answer(
            "❌ Установите username в настройках Telegram",
            show_alert=True
        )
    await JB.update_user_field(uid, "username", uname)
    await JB.update_user_field(uid, "nickname_linked", True)
    await call.answer(f"✅ @{uname} привязан!", show_alert=True)
    await cb_menu(call)


# ═══════════════════════════════════════════════════════════════
# 👑 КОМАНДЫ ВЛАДЕЛЬЦА
# ═══════════════════════════════════════════════════════════════

@dp.message(Command("approve"), F.from_user.id == OWNER_ID)
async def cmd_approve(msg: types.Message):
    parts = msg.text.split()
    if len(parts) < 2:
        return await msg.reply("/approve REQ-XXXXXX")
    req_id = parts[1].upper()

    req = await JB.approve_pending(req_id, OWNER_ID)
    if not req:
        return await msg.reply(f"❌ Заявка {req_id} не найдена или уже обработана")

    await msg.reply(
        f"✅ <b>Подтверждено!</b>\n\n"
        f"👤 {JB.html_esc(req.get('full_name',''))}\n"
        f"💰 Начислено: <b>{req['nvc']} NVC</b>",
        parse_mode="HTML"
    )
    try:
        await bot.send_message(
            req["uid"],
            f"✅ <b>Баланс пополнен!</b>\n\n"
            f"💰 +{req['nvc']} NVC\n\n"
            f"<i>Спасибо, что используете Nova Pay! 💜</i>",
            parse_mode="HTML"
        )
    except Exception:
        pass


@dp.message(Command("decline"), F.from_user.id == OWNER_ID)
async def cmd_decline(msg: types.Message):
    parts = msg.text.split(maxsplit=2)
    if len(parts) < 2:
        return await msg.reply("/decline REQ-XXXXXX [причина]")
    req_id = parts[1].upper()
    reason = parts[2] if len(parts) > 2 else "Оплата не найдена"

    d   = await JB.jget(JB.BIN_PENDING, force=True)
    req = d.get("pending",{}).get(req_id)
    if not req:
        return await msg.reply("❌ Не найдена")

    await JB.reject_pending(req_id, OWNER_ID)
    await msg.reply(f"❌ Заявка {req_id} отклонена.")
    try:
        await bot.send_message(
            req["uid"],
            f"❌ Заявка {req_id} отклонена.\n"
            f"Причина: {JB.html_esc(reason)}",
            parse_mode="HTML"
        )
    except Exception:
        pass


@dp.message(Command("give"), F.from_user.id == OWNER_ID)
async def cmd_give(msg: types.Message):
    parts = msg.text.split(maxsplit=3)
    if len(parts) < 3:
        return await msg.reply("/give USER_ID СУММА [причина]")
    try:
        uid    = int(parts[1])
        amount = int(parts[2])
    except ValueError:
        return await msg.reply("❌ Неверные параметры")
    reason  = parts[3] if len(parts) > 3 else "Начисление от администратора"
    user    = await JB.get_user(uid)
    if not user:
        return await msg.reply(f"❌ Пользователь {uid} не найден")

    new_bal = await JB.update_balance(uid, amount, reason)
    await msg.reply(
        f"✅ +{amount} NVC → <code>{uid}</code>\n"
        f"Баланс: <b>{new_bal} NVC</b>",
        parse_mode="HTML"
    )
    try:
        await bot.send_message(
            uid,
            f"💰 <b>Начисление!</b>\n\n+{amount} NVC\n{JB.html_esc(reason)}",
            parse_mode="HTML"
        )
    except Exception:
        pass


@dp.message(Command("check"), F.from_user.id == OWNER_ID)
async def cmd_check(msg: types.Message):
    parts = msg.text.split(maxsplit=2)
    if len(parts) < 3:
        return await msg.reply("/check СУММА ОПИСАНИЕ")
    try:
        amount = int(parts[1])
    except ValueError:
        return await msg.reply("❌ Неверная сумма")

    check = await JB.create_check(amount, parts[2], OWNER_ID)
    me    = await bot.get_me()
    link  = f"https://t.me/{me.username}?start=check_{check['check_id']}"

    await msg.reply(
        f"✅ <b>Чек создан!</b>\n\n"
        f"🔢 <code>{check['check_id']}</code>\n"
        f"💰 <b>{amount} NVC</b>\n"
        f"📝 {JB.html_esc(parts[2])}\n\n"
        f"🔗 <code>{link}</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📤 Поделиться",
                url=f"https://t.me/share/url?url={link}"
                    f"&text=💰 Чек на {amount} NVC!"
            )]
        ])
    )


@dp.message(Command("pending"), F.from_user.id == OWNER_ID)
async def cmd_pending(msg: types.Message):
    d    = await JB.get_pending()
    reqs = [r for r in d.values() if r.get("status")=="pending"]
    if not reqs:
        return await msg.reply("📭 Новых заявок нет.")
    text = f"💳 <b>Заявки ({len(reqs)}):</b>\n\n"
    for r in reqs[-10:]:
        text += (
            f"🔢 <code>{r['req_id']}</code>\n"
            f"👤 {JB.html_esc(r.get('full_name',''))}\n"
            f"⭐ {r['stars']} → 💰 {r['nvc']} NVC\n\n"
        )
    text += "/approve REQ-ID | /decline REQ-ID"
    await msg.reply(text, parse_mode="HTML")


@dp.message(Command("npstats"), F.from_user.id == OWNER_ID)
async def cmd_stats(msg: types.Message):
    users   = await JB.get_all_users()
    checks  = await JB.get_all_checks()
    pending = await JB.get_pending()

    total_nvc = sum(u.get("balance",0) for u in users.values())
    act_checks= sum(1 for c in checks.values() if not c.get("is_used"))
    pend_cnt  = sum(1 for r in pending.values() if r.get("status")=="pending")

    await msg.reply(
        f"📊 <b>Nova Pay Stats</b>\n\n"
        f"👥 Пользователей: <b>{len(users)}</b>\n"
        f"💰 NVC в обороте: <b>{total_nvc}</b>\n"
        f"🎰 Активных чеков: <b>{act_checks}</b>\n"
        f"💳 Заявок на рассмотрении: <b>{pend_cnt}</b>",
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════
# 🎯 MAIN
# ═══════════════════════════════════════════════════════════════

async def main():
    log.info("💜 Nova Pay Bot запущен!")
    log.info(f"👑 Owner:  {OWNER_ID}")
    log.info(f"🌐 WebApp: {WEBAPP_URL}")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())