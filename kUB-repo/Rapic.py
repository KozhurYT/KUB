# modules/rapic.py
"""
🎌 Random Anime Pic — случайная аниме-картинка
author: @ke_mods, port: @Hairpin00 (конвертировано для kazhurkeUserBot)
version: 1.4.0
requires: aiohttp
"""

import asyncio
import logging

logger = logging.getLogger("KUB.rapic")


def setup(bot):
    import sys
    main = sys.modules["__main__"]
    Module, Command = main.Module, main.Command
    mc = main.module_config
    client = bot.client
    p = bot.config.prefix

    mod = Module(
        name="rapic",
        description="Случайная аниме-картинка",
        author="@ke_mods & @Hairpin00",
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
                "key": "api_category",
                "label": "Категория API",
                "type": "str",
                "default": "cute",
                "description": "cute / neko / kitsune / waifu и др.",
            },
        ],
    )

    STRINGS = {
        "ru": {
            "img": "✅ Ваша аниме-картинка\n🔗 [Ссылка]({})",
            "loading": "✨ Загрузка изображения...",
            "error": "🚫 Произошла ошибка...",
            "no_aiohttp": "❌ Установите aiohttp: `pip install aiohttp`",
        },
        "en": {
            "img": "✅ Your anime pic\n🔗 [URL]({})",
            "loading": "✨ Loading image...",
            "error": "🚫 An unexpected error occurred...",
            "no_aiohttp": "❌ Install aiohttp: `pip install aiohttp`",
        },
    }

    def get_strings():
        lang = mc(bot, "rapic", "language", "ru")
        return STRINGS.get(lang, STRINGS["ru"])

    async def cmd_rapic(event):
        """Случайная аниме-картинка."""
        try:
            import aiohttp
        except ImportError:
            await event.edit(get_strings()["no_aiohttp"])
            return

        s = get_strings()
        await event.edit(s["loading"])

        try:
            category = mc(bot, "rapic", "api_category", "cute")
            url = f"https://api.nekosia.cat/api/v1/images/{category}?count=1"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as res:
                    res.raise_for_status()
                    data = await res.json()
                    image_url = data["image"]["original"]["url"]

            await event.delete()
            await client.send_file(
                event.chat_id,
                file=image_url,
                caption=s["img"].format(image_url),
                reply_to=event.reply_to_msg_id,
            )
        except Exception as e:
            logger.error(f"rapic error: {e}")
            try:
                await event.edit(s["error"])
                await asyncio.sleep(5)
                await event.delete()
            except Exception:
                pass

    mod.commands = {
        "rapic": Command("rapic", cmd_rapic, "Случайная аниме-картинка", "rapic", f"{p}rapic"),
    }

    bot.module_manager.register_module(mod)
    bot.register_commands(mod)
