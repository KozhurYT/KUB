"""
Модуль поиска и отправки информации об аниме
Использует API Jikan (MyAnimeList)
Автор: AI Assistant
Версия: 1.0.0
"""
# requires: aiohttp

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Callable, Any, Optional

logger = logging.getLogger(__name__)

try:
    import aiohttp
    AIOHTTP_OK = True
except ImportError:
    AIOHTTP_OK = False

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

    if not AIOHTTP_OK:
        logger.error("anime: библиотека aiohttp не установлена!")

        mod = Module(
            name="anime",
            description="Поиск аниме (требуется aiohttp)",
            author="AI Assistant",
            version="1.0.0",
        )

        async def cmd_error(event):
            await event.edit(
                "❌ <b>Для работы модуля нужна библиотека aiohttp</b>\n"
                f"Установите: <code>{bot.config.prefix}pip install aiohttp</code>",
                parse_mode='html'
            )

        p = bot.config.prefix
        mod.commands = {"anime": Command("anime", cmd_error, "Требуется aiohttp", "anime", f"{p}anime", "fun")}

        bot.module_manager.register_module(mod)
        bot.register_commands(mod)
        return

    MOD_NAME = "anime"

    # Создаём модуль
    mod = Module(
        name=MOD_NAME,
        description="Поиск и отправка информации об аниме",
        author="AI Assistant",
        version="1.0.0",
    )

    p = bot.config.prefix

    # Схема настроек
    mod.settings_schema = [
        {
            "key": "max_results",
            "label": "Макс. результатов",
            "type": "int",
            "default": 5,
            "description": "Количество результатов поиска (1-10)",
        },
        {
            "key": "show_synopsis",
            "label": "Показывать описание",
            "type": "bool",
            "default": True,
            "description": "Показывать краткое описание аниме",
        },
        {
            "key": "language",
            "label": "Язык",
            "type": "str",
            "default": "ru",
            "description": "Язык описания (ru/en)",
        },
    ]

    # Зависимости
    mod.requirements = ["aiohttp"]

    # ==================== API ====================

    API_BASE = "https://api.jikan.moe/v4"

    async def search_anime(query: str, limit: int = 5) -> Optional[List[dict]]:
        """Поиск аниме через Jikan API"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{API_BASE}/anime"
                params = {
                    "q": query,
                    "limit": limit,
                    "order_by": "popularity",
                    "sort": "asc"
                }

                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("data", [])
                    else:
                        logger.error(f"Jikan API error: {resp.status}")
                        return None
        except Exception as e:
            logger.error(f"Anime search error: {e}")
            return None

    async def get_anime_by_id(anime_id: int) -> Optional[dict]:
        """Получить детальную информацию об аниме"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{API_BASE}/anime/{anime_id}"

                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("data")
                    else:
                        return None
        except Exception as e:
            logger.error(f"Get anime error: {e}")
            return None

    # ==================== ФОРМАТИРОВАНИЕ ====================

    def format_anime_short(anime: dict, index: int = 0) -> str:
        """Краткое форматирование аниме"""
        title = anime.get("title", "Без названия")
        title_en = anime.get("title_english", "")
        score = anime.get("score", "N/A")
        episodes = anime.get("episodes", "?")
        status = anime.get("status", "Unknown")
        year = anime.get("year", "?")

        text = f"**{index + 1}.** [{title}]({anime.get('url', '#')})"
        if title_en and title_en != title:
            text += f" ({title_en})"
        text += "\n"
        text += f"    ⭐ {score}/10 | 📺 {episodes} эп. | 📅 {year} | 📊 {status}\n"

        return text

    def format_anime_full(anime: dict) -> str:
        """Полное форматирование информации об аниме"""
        title = anime.get("title", "Без названия")
        title_en = anime.get("title_english") or ""
        title_jp = anime.get("title_japanese") or ""

        score = anime.get("score", "N/A")
        episodes = anime.get("episodes", "?")
        duration = anime.get("duration", "?")
        status = anime.get("status", "Unknown")
        type_anime = anime.get("type", "Unknown")

        aired = anime.get("aired", {})
        from_date = aired.get("from", "")[:10] if aired.get("from") else "?"
        to_date = aired.get("to", "")[:10] if aired.get("to") else "?"

        genres = anime.get("genres", [])
        genre_names = ", ".join([g.get("name", "") for g in genres[:5]])

        studios = anime.get("studios", [])
        studio_names = ", ".join([s.get("name", "") for s in studios[:3]])

        synopsis = anime.get("synopsis", "Описание отсутствует")
        if len(synopsis) > 500:
            synopsis = synopsis[:500] + "..."

        text = f"🎬 **{title}**\n"
        if title_en and title_en != title:
            text += f"🇬🇧 _{title_en}_\n"
        if title_jp:
            text += f"🇯🇵 {title_jp}\n"

        text += f"\n{'━' * 30}\n\n"
        text += f"⭐ **Рейтинг:** {score}/10\n"
        text += f"📺 **Тип:** {type_anime}\n"
        text += f"📹 **Эпизодов:** {episodes}\n"
        text += f"⏱ **Длительность:** {duration}\n"
        text += f"📊 **Статус:** {status}\n"
        text += f"📅 **Выход:** {from_date}"

        if to_date != "?":
            text += f" → {to_date}"
        text += "\n"

        if genre_names:
            text += f"🎭 **Жанры:** {genre_names}\n"

        if studio_names:
            text += f"🎨 **Студия:** {studio_names}\n"

        # Проверяем настройку показа описания
        show_synopsis = module_config(MOD_NAME, "show_synopsis", True)
        if show_synopsis and synopsis:
            text += f"\n📖 **Описание:**\n_{synopsis}_\n"

        url = anime.get("url", "")
        if url:
            text += f"\n🔗 [MyAnimeList]({url})"

        return text

    # ==================== КОМАНДЫ ====================

    async def cmd_anime(event):
        """Поиск аниме"""
        args = event.raw_text.split(maxsplit=1)

        if len(args) < 2:
            await event.edit(
                f"❌ **Использование:**\n"
                f"`{p}anime <название>`\n\n"
                f"**Пример:**\n"
                f"`{p}anime Naruto`"
            )
            return

        query = args[1]
        max_results = module_config(MOD_NAME, "max_results", 5)

        status = await event.edit(f"🔍 Поиск аниме: **{query}**...")

        results = await search_anime(query, max_results)

        if not results:
            await status.edit("❌ Ничего не найдено или ошибка API")
            return

        if len(results) == 0:
            await status.edit("❌ Результаты не найдены")
            return

        # Формируем список результатов
        text = f"🎬 **Результаты поиска: {query}**\n{'━' * 30}\n\n"

        for i, anime in enumerate(results):
            text += format_anime_short(anime, i)
            text += "\n"

        text += f"\n💡 Для подробной информации: `{p}animeinfo <номер>`"

        # Сохраняем результаты для animeinfo
        mod.settings["last_search"] = results
        mod.settings["last_search_chat"] = event.chat_id

        await status.edit(text, link_preview=False)

    async def cmd_animeinfo(event):
        """Подробная информация об аниме из последнего поиска"""
        args = event.raw_text.split(maxsplit=1)

        # Проверяем есть ли последний поиск
        if "last_search" not in mod.settings or mod.settings.get("last_search_chat") != event.chat_id:
            await event.edit(
                f"❌ Сначала выполните поиск командой `{p}anime <название>`"
            )
            return

        if len(args) < 2:
            await event.edit(
                f"❌ **Использование:**\n"
                f"`{p}animeinfo <номер>`\n\n"
                f"Укажите номер из результатов поиска"
            )
            return

        try:
            index = int(args[1]) - 1
        except ValueError:
            await event.edit("❌ Номер должен быть числом")
            return

        results = mod.settings.get("last_search", [])

        if index < 0 or index >= len(results):
            await event.edit(f"❌ Номер должен быть от 1 до {len(results)}")
            return

        anime_id = results[index].get("mal_id")

        status = await event.edit("⏳ Загрузка информации...")

        anime = await get_anime_by_id(anime_id)

        if not anime:
            await status.edit("❌ Ошибка загрузки информации")
            return

        text = format_anime_full(anime)

        # Проверяем есть ли изображение
        image_url = anime.get("images", {}).get("jpg", {}).get("large_image_url")

        if image_url:
            try:
                await status.delete()
                await bot.client.send_file(
                    event.chat_id,
                    image_url,
                    caption=text,
                    parse_mode='markdown'
                )
            except Exception as e:
                logger.error(f"Failed to send image: {e}")
                await bot.client.send_message(event.chat_id, text, parse_mode='markdown')
        else:
            await status.edit(text, link_preview=False)

    async def cmd_randomanime(event):
        """Случайное аниме"""
        status = await event.edit("🎲 Выбираю случайное аниме...")

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{API_BASE}/random/anime"

                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        anime = data.get("data")

                        if not anime:
                            await status.edit("❌ Ошибка получения случайного аниме")
                            return

                        text = format_anime_full(anime)
                        image_url = anime.get("images", {}).get("jpg", {}).get("large_image_url")

                        if image_url:
                            try:
                                await status.delete()
                                await bot.client.send_file(
                                    event.chat_id,
                                    image_url,
                                    caption=text,
                                    parse_mode='markdown'
                                )
                            except Exception as e:
                                logger.error(f"Failed to send image: {e}")
                                await status.edit(text, link_preview=False)
                        else:
                            await status.edit(text, link_preview=False)
                    else:
                        await status.edit("❌ Ошибка API")

        except Exception as e:
            logger.error(f"Random anime error: {e}")
            await status.edit(f"❌ Ошибка: {e}")

    async def cmd_topanime(event):
        """Топ аниме по рейтингу"""
        max_results = module_config(MOD_NAME, "max_results", 5)

        status = await event.edit("📊 Загружаю топ аниме...")

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{API_BASE}/top/anime"
                params = {"limit": max_results}

                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = data.get("data", [])

                        if not results:
                            await status.edit("❌ Не удалось получить топ")
                            return

                        text = f"📊 **Топ-{len(results)} аниме**\n{'━' * 30}\n\n"

                        for i, anime in enumerate(results):
                            text += format_anime_short(anime, i)
                            text += "\n"

                        text += f"\n💡 Подробнее: `{p}animeinfo <номер>`"

                        mod.settings["last_search"] = results
                        mod.settings["last_search_chat"] = event.chat_id

                        await status.edit(text, link_preview=False)
                    else:
                        await status.edit("❌ Ошибка API")

        except Exception as e:
            logger.error(f"Top anime error: {e}")
            await status.edit(f"❌ Ошибка: {e}")

    # ==================== РЕГИСТРАЦИЯ ====================

    mod.commands = {
        "anime": Command(
            "anime", cmd_anime,
            "Поиск аниме", MOD_NAME,
            f"{p}anime <название>", "fun"
        ),
        "animeinfo": Command(
            "animeinfo", cmd_animeinfo,
            "Подробная информация", MOD_NAME,
            f"{p}animeinfo <номер>", "fun"
        ),
        "randomanime": Command(
            "randomanime", cmd_randomanime,
            "Случайное аниме", MOD_NAME,
            f"{p}randomanime", "fun"
        ),
        "topanime": Command(
            "topanime", cmd_topanime,
            "Топ аниме", MOD_NAME,
            f"{p}topanime", "fun"
        ),
    }

    # ==================== LIFECYCLE ====================

    async def on_unload():
        # Очищаем временные данные
        if "last_search" in mod.settings:
            del mod.settings["last_search"]
        if "last_search_chat" in mod.settings:
            del mod.settings["last_search_chat"]

        logger.info(f"{MOD_NAME}: выгружен")

    mod.on_unload = on_unload

    # ==================== РЕГИСТРАЦИЯ ====================

    bot.module_manager.register_module(mod)
    bot.register_commands(mod)

    logger.info(f"{MOD_NAME}: загружен")
