# modules/autoreact.py
"""
🎭 AutoReact — автоматические реакции на сообщения по триггерам
author: @kozhura_ubezhishe_player_fly (конвертировано для kazhurkeUserBot)
version: 1.2.1 (fix)
"""

import logging
import re
import asyncio
import json
import os
import random
import time as _time

from telethon import events
from telethon.tl.types import ReactionEmoji, ReactionCustomEmoji
from telethon.tl.functions.messages import SendReactionRequest

logger = logging.getLogger("KUB.autoreact")

TRIGGERS_FILE = "autoreact_triggers.json"
REACTIONS_FILE = "autoreact_reactions.json"
IGNORED_CHATS_FILE = "autoreact_ignored_chats.json"


def setup(bot):
    import sys
    main = sys.modules["__main__"]
    Module, Command = main.Module, main.Command
    mc = main.module_config
    mc_set = main.module_config_set
    client = bot.client
    p = bot.config.prefix

    mod = main.Module(
        name="autoreact",
        description="Авто-реакции по триггер-словам",
        author="@kozhura_ubezhishe_player_fly",
        version="1.2.1",
        settings_schema=[
            {"key": "enabled", "label": "Включено", "type": "bool", "default": "true",
             "description": "Включить/выключить модуль"},
            {"key": "mode", "label": "Режим", "type": "str", "default": "random",
             "description": "random / first / all"},
            {"key": "cooldown", "label": "Кулдаун (сек)", "type": "int", "default": "0",
             "description": "Пауза между реакциями от одного юзера"},
            {"key": "on_own", "label": "На свои", "type": "bool", "default": "false",
             "description": "Реагировать на свои сообщения"},
            {"key": "on_bot", "label": "На ботов", "type": "bool", "default": "true",
             "description": "Реагировать на сообщения ботов"},
            {"key": "ignore_channels", "label": "Игнор каналов", "type": "bool", "default": "true",
             "description": "Игнорировать каналы (не группы)"},
        ],
    )

    # ─── Безопасное чтение настроек с приведением типов ───

    def cfg_bool(key, default=True):
        """Безопасно читает bool из конфига."""
        val = mc(bot, "autoreact", key, default)
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ("true", "1", "yes", "да", "on")
        return bool(val)

    def cfg_int(key, default=0):
        """Безопасно читает int из конфига."""
        val = mc(bot, "autoreact", key, default)
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    def cfg_str(key, default=""):
        """Безопасно читает str из конфига."""
        val = mc(bot, "autoreact", key, default)
        return str(val) if val is not None else default

    # ─── Хранилище ───

    triggers = {}
    reactions_list = []
    user_cooldowns = {}
    ignored_chats = set()  # set of int

    def load_triggers():
        nonlocal triggers
        try:
            if os.path.exists(TRIGGERS_FILE):
                with open(TRIGGERS_FILE, "r", encoding="utf-8") as f:
                    triggers = json.load(f)
        except Exception as e:
            logger.error(f"load triggers: {e}")
            triggers = {}

    def save_triggers():
        try:
            with open(TRIGGERS_FILE, "w", encoding="utf-8") as f:
                json.dump(triggers, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"save triggers: {e}")

    def load_reactions():
        nonlocal reactions_list
        try:
            if os.path.exists(REACTIONS_FILE):
                with open(REACTIONS_FILE, "r", encoding="utf-8") as f:
                    reactions_list = json.load(f)
        except Exception as e:
            logger.error(f"load reactions: {e}")
            reactions_list = ["👍", "❤️", "🔥"]

    def save_reactions():
        try:
            with open(REACTIONS_FILE, "w", encoding="utf-8") as f:
                json.dump(reactions_list, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"save reactions: {e}")

    def load_ignored_chats():
        nonlocal ignored_chats
        try:
            if os.path.exists(IGNORED_CHATS_FILE):
                with open(IGNORED_CHATS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Принудительно int — JSON может хранить как строки
                    ignored_chats = set(int(x) for x in data.get("chats", []))
        except Exception as e:
            logger.error(f"load ignored: {e}")
            ignored_chats = set()

    def save_ignored_chats():
        try:
            with open(IGNORED_CHATS_FILE, "w", encoding="utf-8") as f:
                # Сохраняем как int
                json.dump({"chats": [int(x) for x in ignored_chats]}, f, indent=2)
        except Exception as e:
            logger.error(f"save ignored: {e}")

    load_triggers()
    load_reactions()
    load_ignored_chats()

    # ─── Утилиты ───

    def parse_trigger_string(text):
        text = text.strip()
        if text.startswith('"') and text.endswith('"'):
            return "exact", text[1:-1].lower()
        if text.startswith("/") and text.endswith("/"):
            pattern = text[1:-1]
            try:
                re.compile(pattern, re.IGNORECASE)
                return "regex", pattern
            except re.error:
                return None, None
        return "contains", text.lower()

    def is_custom_emoji_id(value):
        return isinstance(value, str) and value.isdigit() and len(value) >= 13

    def check_cooldown(user_id):
        cd = cfg_int("cooldown", 0)
        if cd <= 0:
            return True
        last = user_cooldowns.get(user_id, 0.0)
        now = _time.time()
        if now - last >= cd:
            user_cooldowns[user_id] = now
            return True
        return False

    def get_reactions_for_message(text):
        if not text:
            return []
        matched = []
        text_lower = text.lower()
        for key, reacts in triggers.items():
            ttype, trigger = key.split("::", 1)
            if ttype == "exact" and text_lower == trigger:
                matched.extend(reacts)
            elif ttype == "contains" and trigger in text_lower:
                matched.extend(reacts)
            elif ttype == "regex":
                try:
                    if re.search(trigger, text, re.IGNORECASE):
                        matched.extend(reacts)
                except re.error:
                    continue
        return matched

    async def apply_reactions(message, reactions):
        if not reactions:
            return
        try:
            mode = cfg_str("mode", "random")
            formatted = []
            for r in reactions:
                if is_custom_emoji_id(r):
                    formatted.append(ReactionCustomEmoji(document_id=int(r)))
                else:
                    formatted.append(ReactionEmoji(emoticon=r))

            if mode == "random":
                chosen = [random.choice(formatted)]
            elif mode == "first":
                chosen = [formatted[0]]
            else:  # all
                chosen = formatted

            await client(SendReactionRequest(
                peer=message.chat_id, msg_id=message.id, reaction=chosen
            ))
        except Exception as e:
            logger.error(f"react error: {e}")

    # ─── Обработчик входящих ───

    async def _autoreact_handler(event):
        try:
            if not cfg_bool("enabled", True):
                return

            msg = event.message
            if not msg or not msg.text:
                return

            # int сравнение — оба int
            chat_id = int(event.chat_id)
            if chat_id in ignored_chats:
                return

            if msg.out and not cfg_bool("on_own", False):
                return

            sender = msg.sender
            if sender and getattr(sender, "bot", False) and not cfg_bool("on_bot", True):
                return

            if cfg_bool("ignore_channels", True) and event.is_channel and not event.is_group:
                return

            sender_id = msg.sender_id
            if sender_id and not check_cooldown(int(sender_id)):
                return

            reacts = get_reactions_for_message(msg.text)
            if reacts:
                await apply_reactions(msg, reacts)
        except Exception as e:
            logger.error(f"autoreact handler: {e}")

    client.add_event_handler(_autoreact_handler, events.NewMessage())
    mod.handlers.append(_autoreact_handler)

    # ─── Команды ───

    async def cmd_addreact(event):
        args = event.text.split(maxsplit=2)
        if len(args) < 3:
            await event.edit(
                f"❌ `{p}addreact <триггер> <реакция>`\n\n"
                f"**Триггеры:**\n"
                f'  `"точное"` — точное совпадение\n'
                f"  `текст` — вхождение\n"
                f"  `/regex/` — регулярка\n\n"
                f"**Реакция:** эмодзи или ID кастомного\n"
                f"ID через `{p}emojiid`"
            )
            return
        ttype, trigger = parse_trigger_string(args[1].strip())
        if not ttype:
            await event.edit("❌ Неверный триггер")
            return
        reaction = args[2].strip()
        key = f"{ttype}::{trigger}"
        if key not in triggers:
            triggers[key] = []
        if reaction not in triggers[key]:
            triggers[key].append(reaction)
            save_triggers()
        rtype = "кастомный" if is_custom_emoji_id(reaction) else "обычный"
        await event.edit(
            f"✅ {rtype} `{reaction}` → `{args[1].strip()}`\n"
            f"Все реакции: {' '.join(triggers[key])}"
        )

    async def cmd_removereact(event):
        args = event.text.split(maxsplit=2)
        if len(args) < 2:
            await event.edit(f"❌ `{p}removereact <триггер> [реакция]`")
            return
        ttype, trigger = parse_trigger_string(args[1].strip())
        if not ttype:
            await event.edit("❌ Неверный триггер")
            return
        key = f"{ttype}::{trigger}"
        if key not in triggers:
            await event.edit("❌ Триггер не найден")
            return
        if len(args) > 2:
            reaction = args[2].strip()
            if reaction in triggers[key]:
                triggers[key].remove(reaction)
                if not triggers[key]:
                    del triggers[key]
                save_triggers()
                await event.edit(f"✅ Реакция `{reaction}` удалена")
            else:
                await event.edit("❌ Реакция не найдена")
        else:
            del triggers[key]
            save_triggers()
            await event.edit("✅ Триггер удалён")

    async def cmd_listreact(event):
        if not triggers:
            await event.edit("📭 Нет триггеров")
            return
        text = "📋 **Триггеры и реакции:**\n━━━━━━━━━━━━━━━━━━━━━\n\n"
        for key, reacts in triggers.items():
            ttype, trigger = key.split("::", 1)
            if ttype == "exact":
                disp = f'"{trigger}"'
            elif ttype == "regex":
                disp = f"/{trigger}/"
            else:
                disp = trigger
            rdisp = []
            for r in reacts:
                if is_custom_emoji_id(r):
                    rdisp.append(f"[…{r[-6:]}]")
                else:
                    rdisp.append(r)
            text += f"`{disp}` → {' '.join(rdisp)}\n"
        await event.edit(main.truncate(text))

    async def cmd_emojiid(event):
        reply = await event.get_reply_message()
        if not reply:
            await event.edit("❌ Ответьте на сообщение с кастомным эмодзи")
            return
        found = []
        if reply.entities:
            for ent in reply.entities:
                if hasattr(ent, "document_id"):
                    eid = str(ent.document_id)
                    char = reply.text[ent.offset:ent.offset + ent.length]
                    found.append((char, eid))
        if found:
            text = "✅ **Кастомные эмодзи:**\n\n"
            for char, eid in found:
                text += f"{char} → `{eid}`\n"
            text += f"\nПример: `{p}addreact привет {found[0][1]}`"
            await event.edit(text)
        else:
            await event.edit("❌ Кастомных эмодзи не найдено")

    async def cmd_testreact(event):
        args = event.text.split(maxsplit=1)
        if len(args) < 2:
            await event.edit(f"❌ `{p}testreact <реакция>`")
            return
        reaction = args[1].strip()
        test_msg = await event.reply("🧪 Тест...")
        try:
            if is_custom_emoji_id(reaction):
                robj = ReactionCustomEmoji(document_id=int(reaction))
                rtype = "кастомный"
            else:
                robj = ReactionEmoji(emoticon=reaction)
                rtype = "обычный"
            await client(SendReactionRequest(
                peer=test_msg.chat_id, msg_id=test_msg.id, reaction=[robj]
            ))
            await event.edit(f"✅ {rtype} `{reaction}` работает!")
        except Exception as e:
            await event.edit(f"❌ Ошибка: {e}")

    async def cmd_addreaction(event):
        args = event.text.split(maxsplit=1)
        if len(args) < 2:
            await event.edit(f"❌ `{p}addreaction <эмодзи>`")
            return
        reaction = args[1].strip()
        if reaction not in reactions_list:
            reactions_list.append(reaction)
            save_reactions()
            await event.edit(f"✅ `{reaction}` добавлен в общий список")
        else:
            await event.edit("ℹ️ Уже в списке")

    async def cmd_removereaction(event):
        args = event.text.split(maxsplit=1)
        if len(args) < 2:
            await event.edit(f"❌ `{p}removereaction <эмодзи>`")
            return
        reaction = args[1].strip()
        if reaction in reactions_list:
            reactions_list.remove(reaction)
            save_reactions()
            await event.edit("✅ Удалена")
        else:
            await event.edit("❌ Не найдена")

    async def cmd_ignorechat(event):
        args = event.text.split(maxsplit=1)
        try:
            chat_id = int(args[1].strip()) if len(args) > 1 else int(event.chat_id)
        except (ValueError, TypeError):
            await event.edit("❌ Неверный ID")
            return
        ignored_chats.add(chat_id)
        save_ignored_chats()
        try:
            ch = await client.get_entity(chat_id)
            name = getattr(ch, "title", getattr(ch, "username", str(chat_id)))
        except Exception:
            name = str(chat_id)
        await event.edit(f"✅ `{name}` (`{chat_id}`) в игноре")

    async def cmd_unignorechat(event):
        args = event.text.split(maxsplit=1)
        try:
            chat_id = int(args[1].strip()) if len(args) > 1 else int(event.chat_id)
        except (ValueError, TypeError):
            await event.edit("❌ Неверный ID")
            return
        if chat_id in ignored_chats:
            ignored_chats.remove(chat_id)
            save_ignored_chats()
            await event.edit(f"✅ `{chat_id}` убран из игнора")
        else:
            await event.edit("❌ Не в игноре")

    async def cmd_listignored(event):
        if not ignored_chats:
            await event.edit("📭 Нет игнорируемых чатов")
            return
        text = "🚫 **Игнорируемые:**\n━━━━━━━━━━━━━━━━━━━━━\n\n"
        for cid in ignored_chats:
            try:
                ch = await client.get_entity(int(cid))
                name = getattr(ch, "title", getattr(ch, "username", "?"))
                ctype = "📢" if getattr(ch, "broadcast", False) else "💬"
            except Exception:
                name, ctype = "?", "❓"
            text += f"{ctype} **{name}**\n  `{cid}` | `{p}unignorechat {cid}`\n\n"
        await event.edit(main.truncate(text))

    async def cmd_reactconfig(event):
        text = (
            f"⚙️ **AutoReact Config**\n━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{'✅' if cfg_bool('enabled', True) else '❌'} Статус\n"
            f"🎯 Режим: `{cfg_str('mode', 'random')}`\n"
            f"⏱ Кулдаун: `{cfg_int('cooldown', 0)}с`\n"
            f"👤 На свои: {'✅' if cfg_bool('on_own', False) else '❌'}\n"
            f"🤖 На ботов: {'✅' if cfg_bool('on_bot', True) else '❌'}\n"
            f"📢 Игнор каналов: {'✅' if cfg_bool('ignore_channels', True) else '❌'}\n"
            f"🚫 Игнор чатов: {len(ignored_chats)}\n\n"
            f"Настройки через `{p}settings` → inline\n"
            f"или `{p}ignorechat` / `{p}unignorechat`"
        )
        await event.edit(text)

    async def cmd_helpreact(event):
        await event.edit(
            f"🎭 **AutoReact v1.2.1**\n━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"**Триггеры:**\n"
            f"  `{p}addreact <триггер> <реакция>`\n"
            f"  `{p}removereact <триггер> [реакция]`\n"
            f"  `{p}listreact`\n\n"
            f"**Кастомные эмодзи:**\n"
            f"  `{p}emojiid` (ответ на msg)\n"
            f"  `{p}testreact <ID>`\n\n"
            f"**Общий список:**\n"
            f"  `{p}addreaction` / `{p}removereaction`\n\n"
            f"**Игнор:**\n"
            f"  `{p}ignorechat` / `{p}unignorechat`\n"
            f"  `{p}listignored`\n\n"
            f"**Конфиг:** `{p}reactconfig` или inline ⚙️"
        )

    # ─── Регистрация ───

    mod.commands = {
        "addreact": Command("addreact", cmd_addreact, "Добавить реакцию", "autoreact", f"{p}addreact <trigger> <react>"),
        "removereact": Command("removereact", cmd_removereact, "Удалить реакцию", "autoreact", f"{p}removereact <trigger> [react]"),
        "listreact": Command("listreact", cmd_listreact, "Список триггеров", "autoreact", f"{p}listreact"),
        "emojiid": Command("emojiid", cmd_emojiid, "ID эмодзи", "autoreact", f"{p}emojiid"),
        "testreact": Command("testreact", cmd_testreact, "Тест реакции", "autoreact", f"{p}testreact <react>"),
        "addreaction": Command("addreaction", cmd_addreaction, "В общий список", "autoreact", f"{p}addreaction <emoji>"),
        "removereaction": Command("removereaction", cmd_removereaction, "Из списка", "autoreact", f"{p}removereaction <emoji>"),
        "ignorechat": Command("ignorechat", cmd_ignorechat, "Игнорировать чат", "autoreact", f"{p}ignorechat [id]"),
        "unignorechat": Command("unignorechat", cmd_unignorechat, "Убрать из игнора", "autoreact", f"{p}unignorechat [id]"),
        "listignored": Command("listignored", cmd_listignored, "Список игнора", "autoreact", f"{p}listignored"),
        "reactconfig": Command("reactconfig", cmd_reactconfig, "Конфиг", "autoreact", f"{p}reactconfig"),
        "helpreact": Command("helpreact", cmd_helpreact, "Помощь", "autoreact", f"{p}helpreact"),
    }

    def _unload():
        try:
            client.remove_event_handler(_autoreact_handler)
        except Exception:
            pass

    mod.on_unload = _unload

    bot.module_manager.register_module(mod)
    bot.register_commands(mod)
