"""
Модуль для массовой отправки сообщений
Автор: Unknown
Версия: 1.0.0
"""
# requires:

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Callable, Any, Optional

logger = logging.getLogger(__name__)

# ==================== ДАТАКЛАССЫ ====================
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

# ==================== SETUP ====================
def setup(bot):
    """Точка входа модуля согласно документации"""

    MOD_NAME = "spammer"

    # Создаём модуль
    mod = Module(
        name=MOD_NAME,
        description="Массовая отправка сообщений",
        author="Unknown",
        version="1.0.0",
    )

    p = bot.config.prefix

    # Схема настроек
    mod.settings_schema = [
        {
            "key": "max_limit",
            "label": "Максимум сообщений",
            "type": "int",
            "default": 100,
            "description": "Максимальное количество за один вызов",
        },
        {
            "key": "delay",
            "label": "Задержка (сек)",
            "type": "float",
            "default": 0.1,
            "description": "Задержка между отправками",
        },
        {
            "key": "auto_delete",
            "label": "Автоудаление",
            "type": "bool",
            "default": True,
            "description": "Удалять команду и подтверждение",
        },
    ]

    # ==================== КОМАНДЫ ====================

    async def cmd_spam(event):
        """Спам сообщениями"""
        args = event.raw_text.split(maxsplit=2)

        if len(args) < 3:
            await event.edit(
                f"❌ **Использование:**\n"
                f"`{p}spam <кол-во> <текст>`\n\n"
                f"**Пример:**\n"
                f"`{p}spam 5 Привет!`"
            )
            return

        try:
            count = int(args[1])
        except ValueError:
            await event.edit("❌ Количество должно быть числом")
            return

        text = args[2]

        if count <= 0:
            await event.edit("❌ Количество должно быть > 0")
            return

        if not text.strip():
            await event.edit("❌ Текст не может быть пустым")
            return

        # Читаем настройки
        max_limit = module_config(MOD_NAME, "max_limit", 100)
        delay = module_config(MOD_NAME, "delay", 0.1)
        auto_del = module_config(MOD_NAME, "auto_delete", True)

        if count > max_limit:
            await event.edit(f"❌ Лимит: {max_limit} сообщений")
            return

        status = await event.edit(f"🚀 Отправка {count} сообщений...")

        try:
            chat_id = event.chat_id

            for i in range(count):
                await bot.client.send_message(chat_id, text)

                # Обновляем прогресс каждые 10 сообщений
                if (i + 1) % 10 == 0:
                    try:
                        await status.edit(f"🚀 Отправка: {i+1}/{count}...")
                    except:
                        pass

                await asyncio.sleep(delay)

            # Завершение
            if auto_del:
                await status.delete()
                confirm = await event.respond(f"✅ Отправлено **{count}** сообщений")
                await asyncio.sleep(3)
                try:
                    await confirm.delete()
                except:
                    pass
            else:
                await status.edit(f"✅ Отправлено **{count}** сообщений")

        except Exception as e:
            logger.error(f"Spam error: {e}")
            await status.edit(f"❌ Ошибка: {e}")

    async def cmd_rspam(event):
        """Спам ответами на сообщение"""
        reply = await event.get_reply_message()

        if not reply:
            await event.edit("❌ Ответьте на сообщение")
            return

        args = event.raw_text.split(maxsplit=2)

        if len(args) < 3:
            await event.edit(
                f"❌ **Использование:**\n"
                f"`{p}rspam <кол-во> <текст>`\n\n"
                f"Ответьте на сообщение этой командой"
            )
            return

        try:
            count = int(args[1])
        except ValueError:
            await event.edit("❌ Количество должно быть числом")
            return

        text = args[2]

        if count <= 0:
            await event.edit("❌ Количество должно быть > 0")
            return

        if not text.strip():
            await event.edit("❌ Текст не может быть пустым")
            return

        max_limit = module_config(MOD_NAME, "max_limit", 100)
        delay = module_config(MOD_NAME, "delay", 0.1)
        auto_del = module_config(MOD_NAME, "auto_delete", True)

        if count > max_limit:
            await event.edit(f"❌ Лимит: {max_limit}")
            return

        status = await event.edit(f"🚀 Отправка {count} ответов...")

        try:
            for i in range(count):
                await reply.reply(text)

                if (i + 1) % 10 == 0:
                    try:
                        await status.edit(f"🚀 Отправка: {i+1}/{count}...")
                    except:
                        pass

                await asyncio.sleep(delay)

            if auto_del:
                await status.delete()
                confirm = await event.respond(f"✅ Отправлено **{count}** ответов")
                await asyncio.sleep(3)
                try:
                    await confirm.delete()
                except:
                    pass
            else:
                await status.edit(f"✅ Отправлено **{count}** ответов")

        except Exception as e:
            logger.error(f"Reply spam error: {e}")
            await status.edit(f"❌ Ошибка: {e}")

    async def cmd_delayspam(event):
        """Спам с большой задержкой"""
        args = event.raw_text.split(maxsplit=3)

        if len(args) < 4:
            await event.edit(
                f"❌ **Использование:**\n"
                f"`{p}delayspam <кол-во> <секунд> <текст>`\n\n"
                f"**Пример:**\n"
                f"`{p}delayspam 3 60 Напоминание`"
            )
            return

        try:
            count = int(args[1])
            delay_sec = float(args[2])
        except ValueError:
            await event.edit("❌ Некорректные параметры")
            return

        text = args[3]

        if count <= 0 or delay_sec < 0:
            await event.edit("❌ Некорректные параметры")
            return

        if not text.strip():
            await event.edit("❌ Текст не может быть пустым")
            return

        max_limit = module_config(MOD_NAME, "max_limit", 100)
        auto_del = module_config(MOD_NAME, "auto_delete", True)

        if count > max_limit:
            await event.edit(f"❌ Лимит: {max_limit}")
            return

        # Вычисляем время
        total_sec = count * delay_sec
        hours = int(total_sec // 3600)
        minutes = int((total_sec % 3600) // 60)
        seconds = int(total_sec % 60)

        time_str = ""
        if hours > 0:
            time_str += f"{hours}ч "
        if minutes > 0:
            time_str += f"{minutes}м "
        if seconds > 0:
            time_str += f"{seconds}с"

        status = await event.edit(
            f"⏳ Отправка {count} сообщений с задержкой {delay_sec}с\n"
            f"Общее время: ~{time_str.strip()}"
        )

        try:
            chat_id = event.chat_id

            for i in range(count):
                await bot.client.send_message(chat_id, text)

                try:
                    await status.edit(
                        f"⏳ Отправлено: {i+1}/{count}\n"
                        f"Следующее через: {delay_sec}с"
                    )
                except:
                    pass

                if i < count - 1:
                    await asyncio.sleep(delay_sec)

            if auto_del:
                await status.delete()
                confirm = await event.respond(f"✅ Завершено: {count} сообщений")
                await asyncio.sleep(3)
                try:
                    await confirm.delete()
                except:
                    pass
            else:
                await status.edit(f"✅ Завершено: {count} сообщений")

        except Exception as e:
            logger.error(f"Delay spam error: {e}")
            await status.edit(f"❌ Ошибка: {e}")

    # ==================== РЕГИСТРАЦИЯ ====================

    mod.commands = {
        "spam": Command(
            "spam", cmd_spam,
            "Спам сообщениями", MOD_NAME,
            f"{p}spam <кол-во> <текст>", "tools"
        ),
        "rspam": Command(
            "rspam", cmd_rspam,
            "Спам ответами", MOD_NAME,
            f"{p}rspam <кол-во> <текст>", "tools"
        ),
        "delayspam": Command(
            "delayspam", cmd_delayspam,
            "Спам с задержкой", MOD_NAME,
            f"{p}delayspam <кол-во> <сек> <текст>", "tools"
        ),
    }

    # ==================== LIFECYCLE ====================

    async def on_unload():
        logger.info(f"{MOD_NAME}: выгружен")

    mod.on_unload = on_unload

    # ==================== РЕГИСТРАЦИЯ ====================

    bot.module_manager.register_module(mod)
    bot.register_commands(mod)

    logger.info(f"{MOD_NAME}: загружен")
