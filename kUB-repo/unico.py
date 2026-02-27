# modules/unico.py
"""
🐱 Unico Cat — случайное медиа из канала Unico
author: @Hairpin00, idea: @uzhasn1y (конвертировано для kazhurkeUserBot)
version: 1.4.0
"""

import random
import asyncio
import logging

from telethon.tl.types import (
    InputMessagesFilterPhotoVideo,
    InputMessagesFilterGif,
    InputMessagesFilterVideo,
)

logger = logging.getLogger("KUB.unico")

UNICO_CHANNEL = "unico_1213213213"


def setup(bot):
    import sys
    main = sys.modules["__main__"]
    Module, Command = main.Module, main.Command
    mc = main.module_config
    client = bot.client
    p = bot.config.prefix

    mod = Module(
        name="unico",
        description="Случайное медиа Unico 🐱",
        author="@Hairpin00 & @uzhasn1y",
        version="1.4.0",
        settings_schema=[
            {
                "key": "language",
                "label": "Язык / Language",
                "type": "str",
                "default": "ru",
                "description": "ru / en",
            },
            {
                "key": "channel",
                "label": "Канал-источник",
                "type": "str",
                "default": UNICO_CHANNEL,
                "description": "Username или ID канала",
            },
            {
                "key": "fetch_limit",
                "label": "Лимит загрузки",
                "type": "int",
                "default": "50",
                "description": "Сколько медиа загружать за раз",
            },
        ],
    )

    STRINGS = {
        "ru": {
            "searching": "🔍 Ищу Unico...",
            "no_media": "❌ Не найдено медиа. Попробуйте позже.",
            "send_error": "❌ Не удалось отправить.",
            "error": "❌ Ошибка: {}",
        },
        "en": {
            "searching": "🔍 Searching for Unico...",
            "no_media": "❌ No media found. Try later.",
            "send_error": "❌ Failed to send.",
            "error": "❌ Error: {}",
        },
    }

    def get_strings():
        lang = mc(bot, "unico", "language", "ru")
        return STRINGS.get(lang, STRINGS["ru"])

    async def get_media(filter_type=None, limit=50):
        """Получить медиа из канала."""
        channel = mc(bot, "unico", "channel", UNICO_CHANNEL)
        try:
            messages = []
            async for msg in client.iter_messages(channel, limit=limit, filter=filter_type):
                if msg.media:
                    messages.append(msg)
            return messages
        except Exception as e:
            logger.error(f"fetch: {e}")
            return []

    async def send_copy(event, source):
        """Отправляет медиа как копию (без пересылки)."""
        try:
            media = source.media
            if not media:
                return False

            caption = source.text or source.message or ""
            file = None
            attributes = None

            if hasattr(source, "video") and source.video:
                file = source.video
                attributes = source.video.attributes
            elif hasattr(source, "document") and source.document:
                file = source.document
                attributes = source.document.attributes

            if file:
                await client.send_file(
                    event.chat_id, file,
                    caption=caption,
                    attributes=attributes,
                    supports_streaming=True,
                    silent=True,
                )
                return True

            # Фото
            if hasattr(source, "photo") and source.photo:
                await client.send_file(
                    event.chat_id, source.photo,
                    caption=caption, silent=True,
                )
                return True

            return False
        except Exception as e:
            logger.error(f"send: {e}")
            return False

    async def cmd_unico(event):
        """Случайное медиа Unico."""
        s = get_strings()
        limit = mc(bot, "unico", "fetch_limit", 50)

        msg = await event.edit(s["searching"])

        try:
            all_media = []

            # Собираем разные типы медиа
            for filt in [InputMessagesFilterGif, InputMessagesFilterVideo, InputMessagesFilterPhotoVideo]:
                media = await get_media(filt, limit=limit)
                all_media.extend(media)

            # Убираем дубликаты по ID
            unique = {}
            for m in all_media:
                unique[m.id] = m
            media_list = list(unique.values())

            if not media_list:
                await msg.edit(s["no_media"])
                return

            chosen = random.choice(media_list)
            await msg.delete()

            success = await send_copy(event, chosen)
            if not success:
                await client.send_message(event.chat_id, s["send_error"])

        except Exception as e:
            logger.error(f"unico: {e}")
            try:
                await msg.edit(s["error"].format(str(e)[:100]))
            except Exception:
                pass

    mod.commands = {
        "unico": Command("unico", cmd_unico, "Случайный Unico 🐱", "unico", f"{p}unico"),
    }

    bot.module_manager.register_module(mod)
    bot.register_commands(mod)
