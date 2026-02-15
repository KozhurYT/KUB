# modules/sourcetrigger.py
"""
📡 SourceTrigger — пересылка медиа/текста из канала по триггерам
authors: @YouRooni, @Hairpin00, @kozhura_ubezhishe_player_fly
version: 1.1.0
"""

import logging
import re
import asyncio
import json
import os

from telethon import events

logger = logging.getLogger("KUB.sourcetrigger")

TRIGGERS_FILE = "sourcetrigger_triggers.json"
BATCH_SIZE = 200


def setup(bot):
    import sys
    main = sys.modules["__main__"]
    Module, Command = main.Module, main.Command
    mc = main.module_config
    mc_set = main.module_config_set
    client = bot.client
    p = bot.config.prefix

    mod = Module(
        name="sourcetrigger",
        description="Пересылка из канала по триггерам",
        author="@YouRooni & @Hairpin00 & @kozhura_ubezhishe_player_fly",
        version="1.1.0",
        settings_schema=[
            {
                "key": "channel_id",
                "label": "ID канала-источника",
                "type": "int",
                "default": "0",
                "description": "ID канала откуда брать контент (числовой)",
            },
            {
                "key": "auto_parse",
                "label": "Авто-парсинг",
                "type": "bool",
                "default": "true",
                "description": "Автоматически индексировать при загрузке",
            },
        ],
    )

    triggers = {}

    # ─── Хранилище ───

    def save_triggers():
        try:
            with open(TRIGGERS_FILE, "w", encoding="utf-8") as f:
                json.dump(triggers, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"save triggers: {e}")

    def load_triggers():
        nonlocal triggers
        try:
            if os.path.exists(TRIGGERS_FILE):
                with open(TRIGGERS_FILE, "r", encoding="utf-8") as f:
                    triggers = json.load(f)
        except Exception as e:
            logger.error(f"load triggers: {e}")
            triggers = {}

    load_triggers()

    # ─── Утилиты ───

    def get_source_id():
        val = mc(bot, "sourcetrigger", "channel_id", 0)
        try:
            return int(val) if val else 0
        except (ValueError, TypeError):
            return 0

    async def process_message_for_triggers(msg):
        """Парсит сообщение канала и извлекает триггер."""
        if not msg or not getattr(msg, "text", None):
            return None

        content_msg = msg
        if msg.is_reply:
            replied = await msg.get_reply_message()
            if replied:
                content_msg = replied
            else:
                return None

        text = msg.text.strip()
        first_line = text.split("\n", 1)[0].strip()
        ttype, trigger = None, None

        if re.match(r"^~{1,3}", first_line):
            if first_line.startswith("~~~"):
                after = first_line[3:].lstrip()
                if after.startswith("|"):
                    pattern = after[1:].strip()
                    if pattern:
                        try:
                            re.compile(pattern, re.IGNORECASE)
                            ttype, trigger = "regex_delete", pattern
                        except re.error:
                            pass
                else:
                    ttype, trigger = "exact_delete", after.strip().lower()
            elif first_line.startswith("~~"):
                ttype, trigger = "contains", first_line[2:].strip().lower()
            elif first_line.startswith("~"):
                after = first_line[1:].lstrip()
                if after.startswith("|"):
                    pattern = after[1:].strip()
                    if pattern:
                        try:
                            re.compile(pattern, re.IGNORECASE)
                            ttype, trigger = "regex", pattern
                        except re.error:
                            pass
                else:
                    ttype, trigger = "exact", after.strip().lower()

        if ttype and trigger:
            return ttype, trigger, content_msg.id
        return None

    def parse_trigger_string(text):
        """Парсит строку триггера из команды."""
        text = text.strip()
        if text.startswith("~~~"):
            after = text[3:].lstrip()
            if after.startswith("|"):
                pattern = after[1:].strip()
                if pattern:
                    try:
                        re.compile(pattern, re.IGNORECASE)
                        return "regex_delete", pattern
                    except re.error:
                        return None, None
            else:
                return "exact_delete", after.strip().lower()
        elif text.startswith("~~"):
            return "contains", text[2:].strip().lower()
        elif text.startswith("~"):
            after = text[1:].lstrip()
            if after.startswith("|"):
                pattern = after[1:].strip()
                if pattern:
                    try:
                        re.compile(pattern, re.IGNORECASE)
                        return "regex", pattern
                    except re.error:
                        return None, None
            else:
                return "exact", after.strip().lower()
        return None, None

    # ─── Парсер канала ───

    async def run_parser(event=None):
        source_id = get_source_id()
        if not source_id:
            if event:
                await event.edit(f"❌ Источник не настроен\n`{p}stsource <channel_id>`")
            return

        if event:
            status_msg = await event.edit("💎 Индексация...")
        else:
            status_msg = None

        triggers.clear()
        counts = {"exact": 0, "contains": 0, "exact_delete": 0, "regex": 0, "regex_delete": 0}

        try:
            entity = await client.get_entity(source_id)
            tasks = []
            processed = 0

            async for msg in client.iter_messages(entity, limit=None):
                tasks.append(asyncio.create_task(process_message_for_triggers(msg)))
                processed += 1

                if len(tasks) >= BATCH_SIZE:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for result in results:
                        if isinstance(result, Exception) or not result:
                            continue
                        ttype, trigger, msg_id = result
                        key = f"{ttype}::{trigger}"
                        if key not in triggers:
                            triggers[key] = []
                        if msg_id not in triggers[key]:
                            triggers[key].append(msg_id)
                        counts[ttype] += 1
                    tasks.clear()

                    if status_msg and processed % (BATCH_SIZE * 5) == 0:
                        try:
                            await status_msg.edit(f"💎 Обработано {processed}...")
                        except Exception:
                            pass

            # Остаток
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, Exception) or not result:
                        continue
                    ttype, trigger, msg_id = result
                    key = f"{ttype}::{trigger}"
                    if key not in triggers:
                        triggers[key] = []
                    if msg_id not in triggers[key]:
                        triggers[key].append(msg_id)
                    counts[ttype] += 1

            save_triggers()

            if event:
                total = sum(counts.values())
                await status_msg.edit(
                    f"✅ **Индексация завершена!**\n━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"📊 Всего: **{total}** триггеров\n"
                    f"  🎯 Точных: {counts['exact']}\n"
                    f"  🔍 По вхождению: {counts['contains']}\n"
                    f"  🎯🗑 Точных+удалить: {counts['exact_delete']}\n"
                    f"  📐 Regex: {counts['regex']}\n"
                    f"  📐🗑 Regex+удалить: {counts['regex_delete']}\n"
                    f"  📝 Сообщений обработано: {processed}"
                )
        except Exception as e:
            logger.error(f"parse error: {e}")
            if event:
                await event.edit(f"❌ Ошибка: {str(e)[:200]}")

    # ─── Авто-парсинг при загрузке ───

    if mc(bot, "sourcetrigger", "auto_parse", True) and get_source_id():
        async def _auto_parse():
            await asyncio.sleep(5)
            logger.info("sourcetrigger: auto-parse started")
            await run_parser()
            logger.info(f"sourcetrigger: auto-parse done, {len(triggers)} triggers")

        asyncio.get_event_loop().create_task(_auto_parse())

    # ─── Обработчики событий ───

    async def _source_watcher(event):
        """Следит за новыми сообщениями в канале-источнике."""
        try:
            source_id = get_source_id()
            if not source_id or event.chat_id != source_id:
                return
            result = await process_message_for_triggers(event.message)
            if not result:
                return
            ttype, trigger, msg_id = result
            key = f"{ttype}::{trigger}"
            if key not in triggers:
                triggers[key] = []
            if msg_id not in triggers[key]:
                triggers[key].append(msg_id)
            save_triggers()
        except Exception as e:
            logger.error(f"source watcher: {e}")

    async def _trigger_watcher(event):
        """Следит за исходящими — срабатывание триггеров."""
        try:
            if not event.out or not event.text:
                return

            source_id = get_source_id()
            if not source_id:
                return

            text = event.text
            low = text.strip().lower()
            matched_key = None

            # Приоритет: regex_delete → exact_delete → regex → exact → contains
            for key in triggers:
                if key.startswith("regex_delete::"):
                    pattern = key.split("::", 1)[1]
                    try:
                        if re.fullmatch(pattern, text, re.IGNORECASE):
                            matched_key = key
                            break
                    except re.error:
                        continue

            if not matched_key:
                k = f"exact_delete::{low}"
                if k in triggers:
                    matched_key = k

            if not matched_key:
                for key in triggers:
                    if key.startswith("regex::"):
                        pattern = key.split("::", 1)[1]
                        try:
                            if re.fullmatch(pattern, text, re.IGNORECASE):
                                matched_key = key
                                break
                        except re.error:
                            continue

            if not matched_key:
                k = f"exact::{low}"
                if k in triggers:
                    matched_key = k

            if not matched_key:
                for key in triggers:
                    if key.startswith("contains::"):
                        trigger = key.split("::", 1)[1]
                        if trigger in text.lower():
                            matched_key = key
                            break

            if not matched_key:
                return

            msg_ids = triggers[matched_key]
            if not msg_ids:
                return

            should_delete = "delete" in matched_key.split("::", 1)[0]
            reply_to = event.reply_to_msg_id if event.is_reply else None

            for msg_id in msg_ids:
                try:
                    source_msg = await client.get_messages(source_id, ids=msg_id)
                    if source_msg:
                        await client.send_message(
                            event.chat_id, source_msg, reply_to=reply_to
                        )
                except Exception as e:
                    logger.error(f"forward {msg_id}: {e}")

            if should_delete and event.out:
                await event.delete()

        except Exception as e:
            logger.error(f"trigger watcher: {e}")

    client.add_event_handler(_source_watcher, events.NewMessage())
    client.add_event_handler(_trigger_watcher, events.NewMessage(outgoing=True))
    mod.handlers.extend([_source_watcher, _trigger_watcher])

    # ─── Команды ───

    async def cmd_stsource(event):
        """Установить канал-источник."""
        args = event.text.split(maxsplit=1)
        if len(args) < 2:
            cur = get_source_id()
            if cur:
                try:
                    ch = await client.get_entity(cur)
                    name = getattr(ch, "title", str(cur))
                except Exception:
                    name = "?"
                await event.edit(
                    f"📡 **Источник:** `{name}` (`{cur}`)\n\n"
                    f"`{p}stsource <ID>` — сменить\n"
                    f"`{p}stparse` — переиндексировать"
                )
            else:
                await event.edit(
                    f"❌ Источник не настроен\n\n"
                    f"`{p}stsource <channel_id>`\n"
                    f"ID можно узнать через `{p}id` в канале"
                )
            return

        try:
            cid = int(args[1].strip())
        except ValueError:
            await event.edit("❌ Укажите числовой ID")
            return

        mc_set(bot, "sourcetrigger", "channel_id", str(cid))
        try:
            ch = await client.get_entity(cid)
            name = getattr(ch, "title", str(cid))
            await event.edit(f"✅ Источник: **{name}** (`{cid}`)\n\nИндексация: `{p}stparse`")
        except Exception:
            await event.edit(f"✅ Источник: `{cid}` (не удалось получить имя)\n`{p}stparse`")

    async def cmd_stparse(event):
        """Индексировать канал-источник."""
        await run_parser(event)

    async def cmd_staddtrigger(event):
        """Добавить триггер (ответ на контент + текст триггера)."""
        reply = await event.get_reply_message()
        if not reply:
            await event.edit(
                f"❌ Ответьте на сообщение с контентом\n\n"
                f"**Формат:** `{p}staddtrigger <триггер>`\n"
                f"  `~текст` — точное\n"
                f"  `~~текст` — вхождение\n"
                f"  `~~~текст` — точное + удалить\n"
                f"  `~|regex` — регулярка\n"
                f"  `~~~|regex` — регулярка + удалить"
            )
            return

        args = event.text.split(maxsplit=1)
        if len(args) < 2:
            await event.edit(f"❌ Укажите триггер: `{p}staddtrigger ~привет`")
            return

        trigger_text = args[1].strip()
        ttype, trigger = parse_trigger_string(trigger_text)
        if not ttype or not trigger:
            await event.edit("❌ Неверный формат триггера")
            return

        source_id = get_source_id()
        if not source_id:
            await event.edit(f"❌ Источник не настроен: `{p}stsource <id>`")
            return

        await event.edit("⏳ Добавляю...")

        try:
            content_msg = await client.send_file(source_id, reply)
            await client.send_message(source_id, trigger_text, reply_to=content_msg.id)

            key = f"{ttype}::{trigger}"
            if key not in triggers:
                triggers[key] = []
            if content_msg.id not in triggers[key]:
                triggers[key].append(content_msg.id)
            save_triggers()

            type_names = {
                "exact": "🎯 точное",
                "contains": "🔍 вхождение",
                "exact_delete": "🎯🗑 точное+удаление",
                "regex": "📐 regex",
                "regex_delete": "📐🗑 regex+удаление",
            }
            await event.edit(
                f"✅ **Триггер добавлен!**\n\n"
                f"Тип: {type_names.get(ttype, ttype)}\n"
                f"Триггер: `{trigger_text}`\n"
                f"Контент ID: `{content_msg.id}`"
            )
        except Exception as e:
            await event.edit(f"❌ Ошибка: {str(e)[:200]}")

    async def cmd_stlist(event):
        """Список всех триггеров."""
        if not triggers:
            await event.edit("📭 Нет триггеров\nИндексация: `{p}stparse`")
            return

        text = f"📋 **Триггеры SourceTrigger** ({len(triggers)})\n━━━━━━━━━━━━━━━━━━━━━\n\n"

        type_icons = {
            "exact": "🎯",
            "contains": "🔍",
            "exact_delete": "🎯🗑",
            "regex": "📐",
            "regex_delete": "📐🗑",
        }

        for key, msg_ids in triggers.items():
            ttype, trigger = key.split("::", 1)
            icon = type_icons.get(ttype, "❓")
            disp = trigger[:40] + ("..." if len(trigger) > 40 else "")
            text += f"{icon} `{disp}` → {len(msg_ids)} msg\n"

        text += f"\n📊 Всего: {len(triggers)} триггеров"
        await event.edit(main.truncate(text))

    async def cmd_stinfo(event):
        """Информация о модуле."""
        source_id = get_source_id()
        auto = mc(bot, "sourcetrigger", "auto_parse", True)

        type_counts = {}
        for key in triggers:
            ttype = key.split("::", 1)[0]
            type_counts[ttype] = type_counts.get(ttype, 0) + 1

        source_name = "не настроен"
        if source_id:
            try:
                ch = await client.get_entity(source_id)
                source_name = getattr(ch, "title", str(source_id))
            except Exception:
                source_name = str(source_id)

        text = (
            f"📡 **SourceTrigger v1.1.0**\n━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📺 Источник: **{source_name}**\n"
            f"🔄 Авто-парсинг: {'✅' if auto else '❌'}\n"
            f"📋 Триггеров: **{len(triggers)}**\n"
        )
        if type_counts:
            text += "\n**По типам:**\n"
            names = {"exact": "🎯 Точные", "contains": "🔍 Вхождение",
                     "exact_delete": "🎯🗑 Точные+удал", "regex": "📐 Regex",
                     "regex_delete": "📐🗑 Regex+удал"}
            for t, c in type_counts.items():
                text += f"  {names.get(t, t)}: {c}\n"

        text += (
            f"\n**Команды:**\n"
            f"  `{p}stsource <id>` — источник\n"
            f"  `{p}stparse` — индексация\n"
            f"  `{p}staddtrigger <~триггер>` — добавить\n"
            f"  `{p}stlist` — список\n"
            f"  `{p}stinfo` — эта справка\n"
            f"\n**Синтаксис триггеров:**\n"
            f"  `~текст` — точное совпадение\n"
            f"  `~~текст` — вхождение в текст\n"
            f"  `~~~текст` — точное + удалить\n"
            f"  `~|regex` — регулярное выражение\n"
            f"  `~~~|regex` — regex + удалить"
        )
        await event.edit(text)

    # ─── Регистрация ───

    mod.commands = {
        "stsource": Command("stsource", cmd_stsource, "Канал-источник", "sourcetrigger", f"{p}stsource [id]"),
        "stparse": Command("stparse", cmd_stparse, "Индексировать канал", "sourcetrigger", f"{p}stparse"),
        "staddtrigger": Command("staddtrigger", cmd_staddtrigger, "Добавить триггер", "sourcetrigger", f"{p}staddtrigger <~trigger>"),
        "stlist": Command("stlist", cmd_stlist, "Список триггеров", "sourcetrigger", f"{p}stlist"),
        "stinfo": Command("stinfo", cmd_stinfo, "Инфо и справка", "sourcetrigger", f"{p}stinfo"),
    }

    def _unload():
        try:
            client.remove_event_handler(_source_watcher)
            client.remove_event_handler(_trigger_watcher)
        except Exception:
            pass

    mod.on_unload = _unload

    bot.module_manager.register_module(mod)
    bot.register_commands(mod)
