"""
Модуль: KsenonAFK
Описание: Универсальный AFK модуль с поддержкой кастомного сообщения,
          лимитов ответов и управления через настройки.
Автор: @kmodules / @MeKsenon (оригинал для Hikka), портирование для KUB
Версия: 1.0.6
"""

import time
import datetime
import logging
import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Callable, Any, Optional

from telethon import events
from telethon.tl import types, functions


# ─── Dataclass-ы ───

@dataclass
class Command:
    name: str
    handler: Callable
    description: str = ""
    module: str = ""
    usage: str = ""
    category: str = "misc"


@dataclass
class Module:
    name: str
    description: str = ""
    author: str = "Unknown"
    version: str = "1.0"
    commands: Dict[str, Command] = field(default_factory=dict)
    handlers: List[Any] = field(default_factory=list)
    on_load: Optional[Callable] = None
    on_unload: Optional[Callable] = None
    settings: Dict[str, Any] = field(default_factory=dict)
    settings_schema: List[Dict] = field(default_factory=list)
    requirements: List[str] = field(default_factory=list)


# ─── Константы ───

MOD_NAME = "ksenonafk"
logger = logging.getLogger(MOD_NAME)

STRINGS = {
    "gone": (
        "✋ **Сейчас я в AFK режиме**\n"
        "👤 **Был в сети:** Только что\n"
        "⏰ **Ушёл по причине:** _{reason}_"
    ),
    "gone_with_time": (
        "✋ **Сейчас я в AFK режиме**\n"
        "👤 **Был в сети:** Только что\n"
        "🎤 **Приду в:** **{come_time}**\n"
        "⏰ **Ушёл по причине:** _{reason}_"
    ),
    "back": "👤 **Больше не в режиме AFK.**",
    "afk_notify": (
        "✋ **Сейчас я в AFK режиме**\n"
        "👤 **Был в сети:** {was_online} назад\n"
        "{reason_line}"
        "{come_line}"
    ),
    "reason_line": "⏰ **Ушёл по причине:** _{reason}_\n",
    "come_line": "🎤 **Приду в:** **{come_time}**\n",
    "preview_header": (
        "😀 **AFK режим включён!**\n"
        "✈️ **KsenonAFK будет отвечать этим сообщением:**\n\n"
    ),
    "no_reason": "Нету",
    "ignore_set": "✅ Установлено ограничение: {limit} сообщений за {minutes} минут в одном чате",
    "time_limit_set": "✅ Установлено ограничение: {max_msgs} сообщений за {minutes} минут (ЛС: {pm_limit} сообщений)",
}


# ─── Состояние ───

class AFKState:
    def __init__(self):
        self.is_afk: bool = False
        self.reason: Optional[str] = None
        self.gone_time: Optional[float] = None
        self.return_time: Optional[str] = None
        self.answered_users: set = set()
        self.chat_messages: Dict[int, List[float]] = defaultdict(list)
        self.ignore_limit: Optional[int] = None
        self.ignore_time: Optional[int] = None
        self.pm_limit: Optional[int] = None
        self.chat_limit: Optional[int] = None
        self.time_interval: Optional[int] = None
        self.old_emoji_status: Any = None

    def reset(self):
        self.is_afk = False
        self.reason = None
        self.gone_time = None
        self.return_time = None
        self.answered_users.clear()
        self.chat_messages.clear()


_state = AFKState()


# ─── Утилиты ───

def _format_timedelta(td: datetime.timedelta) -> str:
    total = int(td.total_seconds())
    if total < 0:
        total = 0
    days, remainder = divmod(total, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days}д")
    if hours:
        parts.append(f"{hours}ч")
    if minutes:
        parts.append(f"{minutes}м")
    parts.append(f"{seconds}с")
    return " ".join(parts)


def _build_afk_response(was_online_str, reason, come_time, custom_template):
    reason_line = ""
    if reason and reason != STRINGS["no_reason"]:
        reason_line = STRINGS["reason_line"].format(reason=reason)

    come_line = ""
    if come_time:
        come_line = STRINGS["come_line"].format(come_time=come_time)

    default_message = STRINGS["afk_notify"].format(
        was_online=was_online_str,
        reason_line=reason_line,
        come_line=come_line,
    )

    if custom_template == "{default}":
        return default_message

    try:
        return custom_template.format(
            was_online=was_online_str,
            reason=reason if reason else STRINGS["no_reason"],
            come_time=come_time if come_time else "",
            default=default_message,
        )
    except (KeyError, IndexError, ValueError):
        return default_message


def _check_limits(chat_id, is_pm):
    current_time = time.time()

    if _state.ignore_limit and _state.ignore_time:
        _state.chat_messages[chat_id] = [
            t for t in _state.chat_messages[chat_id]
            if current_time - t < _state.ignore_time
        ]
        if len(_state.chat_messages[chat_id]) >= _state.ignore_limit:
            return False

    if _state.time_interval:
        limit = _state.pm_limit if is_pm else _state.chat_limit
        if limit is not None:
            recent = [
                t for t in _state.chat_messages[chat_id]
                if current_time - t < _state.time_interval
            ]
            if len(recent) >= limit:
                return False
            _state.chat_messages[chat_id] = recent

    _state.chat_messages[chat_id].append(current_time)
    return True


# ─── Точка входа ───

def setup(bot):
    mod = Module(
        name=MOD_NAME,
        description="Универсальный AFK модуль с кастом-сообщением и лимитами",
        author="@kmodules / @MeKsenon (порт для KUB)",
        version="1.0.6",
    )

    p = bot.config.prefix

    # ─────────────────────────────────────────────────
    # ВАЖНО: внедрённые module_config / module_config_set
    # уже содержат bot внутри (лямбда в _load_file),
    # поэтому вызываем БЕЗ bot:
    #
    #   module_config(MOD_NAME, "key", default)
    #   module_config_set(MOD_NAME, "key", value)
    #
    # НЕ: module_config(bot, MOD_NAME, "key", default)
    # ─────────────────────────────────────────────────

    mod.settings_schema = [
        {
            "key": "always_answer",
            "label": "Отвечать всегда",
            "type": "bool",
            "default": False,
            "description": (
                "True — отвечает на каждое упоминание/ЛС. "
                "False — каждому пользователю только один раз."
            ),
        },
        {
            "key": "set_premium_status",
            "label": "Менять премиум-статус",
            "type": "bool",
            "default": False,
            "description": "Ставить emoji-статус при AFK (нужен Premium).",
        },
        {
            "key": "custom_emoji_status_id",
            "label": "ID emoji-статуса",
            "type": "int",
            "default": 4969889971700761796,
            "description": "Document ID кастомного emoji для премиум-статуса.",
        },
        {
            "key": "custom_message",
            "label": "Кастомное AFK-сообщение",
            "type": "str",
            "default": "{default}",
            "description": (
                "Шаблон ответа. Переменные: "
                "{was_online}, {reason}, {come_time}, {default}"
            ),
        },
    ]

    # ─── .afk ───

    async def cmd_afk(event):
        args = event.raw_text.split(maxsplit=1)
        raw_args = args[1].strip() if len(args) > 1 else ""

        reason = None
        time_val = None

        if raw_args:
            parts = raw_args.split(" ", 1)
            reason = parts[0]
            if len(parts) > 1:
                time_val = parts[1].strip()
            if reason.lower() in ("нету", "none", "-"):
                reason = None

        # Премиум-статус
        set_premium = module_config(MOD_NAME, "set_premium_status", False)
        if set_premium:
            try:
                me = await bot.client.get_me()
                if hasattr(me, "emoji_status") and me.emoji_status:
                    _state.old_emoji_status = me.emoji_status
                emoji_id = module_config(MOD_NAME, "custom_emoji_status_id", 4969889971700761796)
                await bot.client(functions.account.UpdateEmojiStatusRequest(
                    emoji_status=types.EmojiStatus(document_id=int(emoji_id))
                ))
            except Exception as e:
                logger.error(f"Не удалось установить emoji-статус: {e}")

        _state.is_afk = True
        _state.reason = reason
        _state.gone_time = time.time()
        _state.return_time = time_val
        _state.answered_users.clear()
        _state.chat_messages.clear()

        custom_tpl = module_config(MOD_NAME, "custom_message", "{default}")
        preview = _build_afk_response("Только что", reason, time_val, custom_tpl)

        await event.edit(STRINGS["preview_header"] + preview)

    # ─── .unafk ───

    async def cmd_unafk(event):
        if not _state.is_afk:
            await event.edit("ℹ️ AFK режим не был включён.")
            return

        # Восстановление статуса (до reset!)
        set_premium = module_config(MOD_NAME, "set_premium_status", False)
        if set_premium and _state.old_emoji_status:
            try:
                await bot.client(functions.account.UpdateEmojiStatusRequest(
                    emoji_status=_state.old_emoji_status
                ))
            except Exception as e:
                logger.error(f"Не удалось восстановить emoji-статус: {e}")

        _state.old_emoji_status = None
        _state.reset()

        await event.edit(STRINGS["back"])

    # ─── .ignorusers ───

    async def cmd_ignorusers(event):
        args = event.raw_text.split()
        if len(args) != 3:
            await event.edit(
                f"❌ Использование: `{p}ignorusers <кол-во> <минуты>`\n"
                f"Пример: `{p}ignorusers 3 5`"
            )
            return
        try:
            msg_limit = int(args[1])
            time_limit = int(args[2])
        except ValueError:
            await event.edit("❌ Аргументы должны быть числами.")
            return
        if msg_limit < 1 or time_limit < 1:
            await event.edit("❌ Значения должны быть положительными.")
            return

        _state.ignore_limit = msg_limit
        _state.ignore_time = time_limit * 60

        await event.edit(
            STRINGS["ignore_set"].format(limit=msg_limit, minutes=time_limit)
        )

    # ─── .timeafk ───

    async def cmd_timeafk(event):
        args = event.raw_text.split()
        if len(args) != 3:
            await event.edit(
                f"❌ Использование: `{p}timeafk <минуты> <макс_сообщений>`\n"
                f"Пример: `{p}timeafk 10 5`"
            )
            return
        try:
            interval = int(args[1])
            max_msgs = int(args[2])
        except ValueError:
            await event.edit("❌ Аргументы должны быть числами.")
            return
        if interval < 1 or max_msgs < 1:
            await event.edit("❌ Значения должны быть положительными.")
            return

        _state.time_interval = interval * 60
        _state.pm_limit = 2
        _state.chat_limit = max_msgs

        await event.edit(
            STRINGS["time_limit_set"].format(max_msgs=max_msgs, minutes=interval, pm_limit=2)
        )

    # ─── .afkstatus ───

    async def cmd_afkstatus(event):
        if not _state.is_afk:
            await event.edit("ℹ️ AFK режим **выключен**.")
            return

        elapsed = datetime.timedelta(seconds=int(time.time() - _state.gone_time))
        elapsed_str = _format_timedelta(elapsed)
        reason_str = _state.reason or STRINGS["no_reason"]
        return_str = _state.return_time or "—"
        answered_count = len(_state.answered_users)

        always = module_config(MOD_NAME, "always_answer", False)
        premium = module_config(MOD_NAME, "set_premium_status", False)

        limits_text = ""
        if _state.ignore_limit:
            limits_text += f"├ 🚫 Лимит чата: {_state.ignore_limit} за {(_state.ignore_time or 0) // 60}м\n"
        if _state.time_interval:
            limits_text += (
                f"├ ⏱ Лимит времени: {_state.chat_limit} за {(_state.time_interval or 0) // 60}м"
                f" (ЛС: {_state.pm_limit})\n"
            )

        await event.edit(
            f"✋ **AFK Статус**\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"├ 🟢 Режим: **Включён**\n"
            f"├ ⏱ Время в AFK: **{elapsed_str}**\n"
            f"├ 💬 Причина: _{reason_str}_\n"
            f"├ 🕐 Приду в: **{return_str}**\n"
            f"├ 📩 Ответили: **{answered_count}** пользователям\n"
            f"{limits_text}"
            f"├ 🔄 Отвечать всегда: {'✅' if always else '❌'}\n"
            f"└ ⭐ Премиум-статус: {'✅' if premium else '❌'}\n"
        )

    # ─── Watcher ───

    async def watcher_handler(event):
        if event.out:
            return
        if not _state.is_afk:
            return

        message = event.message
        if not isinstance(message, types.Message):
            return

        me = await bot.client.get_me()
        is_mentioned = message.mentioned
        is_pm = event.is_private

        if not is_pm and not is_mentioned:
            return

        sender = await event.get_sender()
        if not sender:
            return
        if hasattr(sender, "bot") and sender.bot:
            return
        if hasattr(sender, "verified") and sender.verified:
            return
        if sender.id == me.id:
            return

        always_answer = module_config(MOD_NAME, "always_answer", False)
        if not always_answer and sender.id in _state.answered_users:
            return

        chat_id = sender.id if is_pm else event.chat_id
        if not _check_limits(chat_id, is_pm):
            return

        if not always_answer:
            _state.answered_users.add(sender.id)

        now = datetime.datetime.now().replace(microsecond=0)
        gone = datetime.datetime.fromtimestamp(_state.gone_time).replace(microsecond=0)
        diff = now - gone
        diff_str = _format_timedelta(diff)

        custom_tpl = module_config(MOD_NAME, "custom_message", "{default}")
        response = _build_afk_response(diff_str, _state.reason, _state.return_time, custom_tpl)

        try:
            await event.reply(response)
        except Exception as e:
            logger.error(f"Ошибка при отправке AFK-ответа: {e}")

    handler = bot.client.on(events.NewMessage(incoming=True))(watcher_handler)
    mod.handlers.append(handler)

    # ─── on_unload ───

    async def on_unload():
        if _state.is_afk:
            set_premium = module_config(MOD_NAME, "set_premium_status", False)
            if set_premium and _state.old_emoji_status:
                try:
                    await bot.client(functions.account.UpdateEmojiStatusRequest(
                        emoji_status=_state.old_emoji_status
                    ))
                except Exception:
                    pass
            _state.reset()

    mod.on_unload = on_unload

    # ─── Регистрация ───

    mod.commands = {
        "afk": Command("afk", cmd_afk, "Включить AFK режим", MOD_NAME, f"{p}afk [причина] [время]"),
        "unafk": Command("unafk", cmd_unafk, "Выйти из AFK", MOD_NAME, f"{p}unafk"),
        "ignorusers": Command("ignorusers", cmd_ignorusers, "Лимит ответов на чат", MOD_NAME, f"{p}ignorusers <кол-во> <мин>"),
        "timeafk": Command("timeafk", cmd_timeafk, "Временной лимит", MOD_NAME, f"{p}timeafk <мин> <макс>"),
        "afkstatus": Command("afkstatus", cmd_afkstatus, "Статус AFK", MOD_NAME, f"{p}afkstatus"),
    }

    bot.module_manager.register_module(mod)
    bot.register_commands(mod)
