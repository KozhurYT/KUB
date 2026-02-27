"""
Grid 3x3 for stories.

Splits a photo into a 3x3 grid and posts each part as a pinned story.

Author: @ke_mods (fixed for KUB)
Version: 1.1.1
License: CC BY-ND 4.0
"""
# requires: pillow

__requires__ = ["pillow"]

import io
import asyncio
import math
from dataclasses import dataclass, field
from typing import Dict, List, Callable, Any, Optional
from telethon import functions, types, errors

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


def setup(bot):
    MOD_NAME = "photostories"
    mod = Module(
        name=MOD_NAME,
        description="Grid 3x3 for stories — splits a photo into 9 parts and posts them as pinned stories",
        author="@ke_mods (fixed)",
        version="1.1.1",
        requirements=["pillow"],
    )
    p = bot.config.prefix

    mod.settings_schema = [
        {
            "key": "language",
            "label": "Language",
            "type": "str",
            "default": "ru",
            "description": "Interface language: ru or en",
        },
        {
            "key": "delay",
            "label": "Delay (sec)",
            "type": "int",
            "default": 2,
            "description": "Delay between uploads to prevent FloodWait",
        }
    ]

    strings = {
        "ru": {
            "no_rep": "❗️ Ответьте на изображение!",
            "work": "🕔 Обрабатываю и нарезаю...",
            "uploading": "📤 Загрузка истории {}/9...",
            "flood": "⏳ Жду {}с из-за флуда...",
            "done": "✅ Готово! Сетка 3x3 опубликована в профиле.",
            "err": "❌ Ошибка: {}",
        },
        "en": {
            "no_rep": "❗️ Reply to an image!",
            "work": "🕔 Processing and slicing...",
            "uploading": "📤 Uploading story {}/9...",
            "flood": "⏳ Waiting {}s due to flood...",
            "done": "✅ Done! 3x3 grid posted to profile.",
            "err": "❌ Error: {}",
        },
    }

    async def cmd_pts(event):
        """Split a photo into a 3x3 grid and post as pinned stories."""
        from PIL import Image

        # ИСПРАВЛЕНО: Убран аргумент 'bot' из вызова module_config
        lang = module_config(MOD_NAME, "language", "ru")
        delay = module_config(MOD_NAME, "delay", 2)

        t = strings.get(lang, strings["en"])

        reply = await event.get_reply_message()
        if not reply or not reply.media:
            await event.edit(t["no_rep"])
            return

        try:
            await event.edit(t["work"])
            photo_bytes = await reply.download_media(bytes)
            img = Image.open(io.BytesIO(photo_bytes))
        except Exception as e:
            await event.edit(t["err"].format(str(e)))
            return

        w, h = img.size

        # Корректируем размер, если нужно (используем безопасный доступ к Resampling)
        target_aspect = 0.8
        if abs(w / h - target_aspect) > 0.05:
            new_h = int(w / target_aspect)
            resample = getattr(Image, "Resampling", Image).LANCZOS
            try:
                img = img.resize((w, new_h), resample)
            except Exception:
                img = img.resize((w, new_h), Image.LANCZOS)
            w, h = img.size

        parts = []
        piece_w = w / 3
        piece_h = h / 3

        for r in range(3):
            for c in range(3):
                left = math.floor(c * piece_w)
                upper = math.floor(r * piece_h)
                right = math.floor((c + 1) * piece_w) if c < 2 else w
                lower = math.floor((r + 1) * piece_h) if r < 2 else h

                parts.append(img.crop((left, upper, right, lower)))

        parts.reverse()

        total = len(parts)
        for i, part in enumerate(parts):
            await event.edit(t["uploading"].format(i + 1))

            out = io.BytesIO()
            part.save(out, "JPEG", quality=95)
            out.seek(0)

            try:
                uploaded_file = await bot.client.upload_file(out, file_name=f"story_{i}.jpg")

                result = await bot.client(functions.stories.SendStoryRequest(
                    peer=types.InputPeerSelf(),
                    media=types.InputMediaUploadedPhoto(uploaded_file),
                    privacy_rules=[types.InputPrivacyValueAllowAll()],
                    period=86400,
                ))

                story_id = None
                if result.updates:
                    for update in result.updates:
                        if isinstance(update, types.UpdateStory):
                            story_id = update.story.id
                            break
                        elif isinstance(update, types.UpdateStoryID):
                            story_id = update.id
                            break

                if story_id:
                    try:
                        await bot.client(functions.stories.TogglePinnedRequest(
                            peer=types.InputPeerSelf(),
                            id=[story_id],
                            pinned=True,
                        ))
                    except Exception:
                        pass

                if i < total - 1:
                    await asyncio.sleep(delay)

            except errors.FloodWaitError as e:
                await event.edit(t["flood"].format(e.seconds))
                await asyncio.sleep(e.seconds + 1)
                await event.edit(t["err"].format("FloodWait."))
                return
            except Exception as e:
                await event.edit(t["err"].format(str(e)))
                return

        await event.edit(t["done"])

    mod.commands = {
        "pts": Command(
            "pts",
            cmd_pts,
            "Stories 3x3 Grid",
            MOD_NAME,
            f"{p}pts <reply>",
            "fun",
        ),
    }

    bot.module_manager.register_module(mod)
    bot.register_commands(mod)
