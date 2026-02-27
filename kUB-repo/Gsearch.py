"""
Модуль поиска в Google и DuckDuckGo с пагинацией
Автор: @Hairpin00
Версия: 1.0.0
"""
# requires: googlesearch-python, duckduckgo-search

import uuid
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Callable, Any, Optional

from telethon import events, Button
from telethon.tl.types import InputWebDocument, DocumentAttributeImageSize
from googlesearch import search

try:
    from duckduckgo_search import DDGS
    DDG_OK = True
except ImportError:
    DDG_OK = False

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

    MOD_NAME = "gsearch"

    # Создаём модуль
    mod = Module(
        name=MOD_NAME,
        description="Поиск в Google и DuckDuckGo",
        author="@Hairpin00",
        version="1.0.0",
    )

    p = bot.config.prefix

    # Схема настроек
    mod.settings_schema = [
        {
            "key": "max_results",
            "label": "Макс. результатов",
            "type": "int",
            "default": 10,
            "description": "Количество результатов поиска (1-20)",
        },
        {
            "key": "cache_ttl",
            "label": "Время кэша (сек)",
            "type": "int",
            "default": 600,
            "description": "Время жизни кэша в секундах",
        },
    ]

    # Зависимости
    mod.requirements = ["googlesearch-python", "duckduckgo-search"]

    # ==================== ХРАНИЛИЩЕ ====================
    cache = {}

    def set_cache(key: str, value: Any, ttl: int = 600):
        cache[key] = {"value": value, "expires": time.time() + ttl}

    def get_cache(key: str) -> Any:
        entry = cache.get(key)
        if not entry:
            return None
        if time.time() > entry["expires"]:
            del cache[key]
            return None
        return entry["value"]

    # ==================== ИКОНКИ ====================
    ICON_G = "https://kappa.lol/HCIjwW"
    ICON_I = "https://cdn-icons-png.flaticon.com/512/3342/3342137.png"
    ICON_E = "https://kappa.lol/oO9x4z"

    def thumb(url: str) -> InputWebDocument:
        return InputWebDocument(
            url=url,
            size=0,
            mime_type="image/jpeg",
            attributes=[DocumentAttributeImageSize(w=0, h=0)]
        )

    # ==================== ФОРМАТИРОВАНИЕ ====================
    def fmt_google(entry, idx: int, total: int) -> str:
        return (
            f"🔍 <b>Google</b> [{idx+1}/{total}]\n\n"
            f"🌐 <a href='{entry.url}'><b>{entry.title}</b></a>\n"
            f"📝 <i>{entry.description or 'Нет описания'}</i>\n\n"
            f"🔗 {entry.url}"
        )

    def fmt_img(entry: dict, idx: int, total: int) -> str:
        return (
            f"🖼 <b>Картинки</b> [{idx+1}/{total}]\n"
            f"📝 {entry.get('title', 'Без названия')}\n"
            f"🔗 <a href='{entry['image']}'>Источник</a>"
        )

    # ==================== КОМАНДЫ ====================

    async def cmd_google(event):
        """Поиск в Google"""
        args = event.raw_text.split(maxsplit=1)
        if len(args) < 2:
            await event.edit(f"❌ Использование: `{p}google <запрос>`")
            return

        query = args[1]

        # Читаем настройку через module_config
        max_res = module_config(MOD_NAME, "max_results", 10)

        await event.edit(f"🔍 Поиск: **{query}**...")

        try:
            results = list(search(query, num_results=max_res, advanced=True))

            if not results:
                await event.edit("❌ Ничего не найдено")
                return

            text = f"🔍 **Google: {query}**\n{'━' * 25}\n\n"

            for i, r in enumerate(results[:5], 1):
                title = r.title or "Без заголовка"
                desc = r.description or ""
                if len(desc) > 100:
                    desc = desc[:100] + "..."

                text += f"**{i}.** [{title}]({r.url})\n"
                if desc:
                    text += f"    _{desc}_\n"
                text += "\n"

            if len(results) > 5:
                text += f"_...ещё {len(results) - 5} результатов_\n"

            # Подсказка про inline
            if bot.inline_panel and bot.inline_panel.active:
                ib = await bot.inline_panel.inline_bot.get_me()
                text += f"\n💡 Пагинация: `@{ib.username} google {query}`"

            await event.edit(text, link_preview=False)

        except Exception as e:
            logger.error(f"Google error: {e}")
            await event.edit(f"❌ Ошибка: {e}")

    async def cmd_img(event):
        """Поиск картинок в DuckDuckGo"""
        if not DDG_OK:
            await event.edit(
                "❌ Библиотека не установлена\n"
                f"Установите: `{p}pip install duckduckgo-search`"
            )
            return

        args = event.raw_text.split(maxsplit=1)
        if len(args) < 2:
            await event.edit(f"❌ Использование: `{p}img <запрос>`")
            return

        query = args[1]
        max_res = module_config(MOD_NAME, "max_results", 10)

        await event.edit(f"🖼 Поиск: **{query}**...")

        try:
            with DDGS() as ddgs:
                results = list(ddgs.images(query, max_results=max_res))

            if not results:
                await event.edit("❌ Ничего не найдено")
                return

            first = results[0]

            text = f"🖼 **Картинки: {query}**\n"
            text += f"📝 {first.get('title', 'Без названия')}\n"
            text += f"🔗 [Открыть]({first['image']})\n\n"

            if len(results) > 1:
                text += f"_Найдено {len(results)} изображений_\n"

            if bot.inline_panel and bot.inline_panel.active:
                ib = await bot.inline_panel.inline_bot.get_me()
                text += f"\n💡 Пагинация: `@{ib.username} img {query}`"

            await event.edit(text, link_preview=True)

        except Exception as e:
            logger.error(f"Image error: {e}")
            await event.edit(f"❌ Ошибка: {e}")

    # ==================== INLINE ====================

    if bot.inline_panel and bot.inline_panel.active and bot.inline_panel.inline_bot:
        ib = bot.inline_panel.inline_bot

        async def inline_handler(event):
            builder = event.builder
            txt = event.text.strip()

            mode = "google"
            query = txt

            if txt.startswith("google "):
                mode = "google"
                query = txt[7:].strip()
            elif txt.startswith("img "):
                mode = "img"
                query = txt[4:].strip()

            if not query:
                icon = thumb(ICON_G if mode == "google" else ICON_I)
                r = builder.article(
                    title="Поиск",
                    text=f"Введите запрос ({mode})",
                    thumb=icon
                )
                return await event.answer([r])

            max_res = module_config(MOD_NAME, "max_results", 10)
            ttl = module_config(MOD_NAME, "cache_ttl", 600)

            try:
                uid = str(uuid.uuid4())[:8]

                if mode == "google":
                    results = list(search(query, num_results=max_res, advanced=True))
                    if not results:
                        raise Exception("Ничего не найдено")

                    set_cache(f"g_{uid}", results, ttl)

                    first = results[0]
                    total = len(results)

                    text = fmt_google(first, 0, total)
                    btns = [
                        [
                            Button.inline("⬅️", f"gs_g_{uid}_{total-1}".encode()),
                            Button.inline(f"1/{total}", f"gs_g_{uid}_0".encode()),
                            Button.inline("➡️", f"gs_g_{uid}_1".encode())
                        ],
                        [Button.url("🌐 Открыть", first.url)]
                    ]

                    r = builder.article(
                        title=f"🔎 {query}",
                        text=text,
                        description=(first.description[:50] + "...") if first.description else "",
                        thumb=thumb(ICON_G),
                        buttons=btns,
                        link_preview=False
                    )

                elif mode == "img":
                    if not DDG_OK:
                        raise Exception("duckduckgo-search не установлена")

                    with DDGS() as ddgs:
                        results = list(ddgs.images(query, max_results=max_res))

                    if not results:
                        raise Exception("Ничего не найдено")

                    set_cache(f"i_{uid}", results, ttl)

                    first = results[0]
                    total = len(results)

                    text = fmt_img(first, 0, total)
                    btns = [
                        [
                            Button.inline("⬅️", f"gs_i_{uid}_{total-1}".encode()),
                            Button.inline(f"1/{total}", f"gs_i_{uid}_0".encode()),
                            Button.inline("➡️", f"gs_i_{uid}_1".encode())
                        ],
                        [Button.url("🖼 Открыть", first["image"])]
                    ]

                    r = builder.article(
                        title=f"🖼 {query}",
                        text=f"<a href='{first['image']}'>&#8203;</a>" + text,
                        description="Изображения",
                        thumb=thumb(first.get("thumbnail", ICON_I)),
                        buttons=btns,
                        parse_mode="html",
                        link_preview=True
                    )

                await event.answer([r])

            except Exception as e:
                logger.error(f"Inline error: {e}")
                r = builder.article(
                    title="Ошибка",
                    text=f"<b>Ошибка:</b> {str(e)}",
                    description=str(e),
                    thumb=thumb(ICON_E),
                    parse_mode="html"
                )
                await event.answer([r])

        async def callback_handler(event):
            data = event.data.decode("utf-8")

            if not data.startswith("gs_"):
                return

            try:
                _, typ, uid, page_str = data.split("_")
                page = int(page_str)
            except ValueError:
                await event.answer("⚠️ Ошибка данных", alert=True)
                return

            ck = f"{typ}_{uid}"
            results = get_cache(ck)

            if not results:
                await event.answer("⚠️ Сессия истекла", alert=True)
                return

            total = len(results)

            if page < 0:
                page = total - 1
            if page >= total:
                page = 0

            entry = results[page]

            if typ == "g":
                text = fmt_google(entry, page, total)
                btns = [
                    [
                        Button.inline("⬅️", f"gs_g_{uid}_{page-1}".encode()),
                        Button.inline(f"{page+1}/{total}", f"gs_g_{uid}_{page}".encode()),
                        Button.inline("➡️", f"gs_g_{uid}_{page+1}".encode())
                    ],
                    [Button.url("🌐 Открыть", entry.url)]
                ]

                await event.edit(text, buttons=btns, parse_mode="html", link_preview=False)

            elif typ == "i":
                text = fmt_img(entry, page, total)
                btns = [
                    [
                        Button.inline("⬅️", f"gs_i_{uid}_{page-1}".encode()),
                        Button.inline(f"{page+1}/{total}", f"gs_i_{uid}_{page}".encode()),
                        Button.inline("➡️", f"gs_i_{uid}_{page+1}".encode())
                    ],
                    [Button.url("🖼 Открыть", entry["image"])]
                ]

                await event.edit(
                    f"<a href='{entry['image']}'>&#8203;</a>" + text,
                    buttons=btns,
                    parse_mode="html",
                    link_preview=True
                )

        # Регистрируем обработчики inline-бота
        h1 = ib.on(events.InlineQuery(pattern=r"^(google|img)\s?"))(inline_handler)
        h2 = ib.on(events.CallbackQuery(pattern=rb"^gs_"))(callback_handler)

        mod.handlers.extend([h1, h2])

    # ==================== КОМАНДЫ ====================

    mod.commands = {
        "google": Command(
            "google", cmd_google,
            "Поиск в Google", MOD_NAME,
            f"{p}google <запрос>", "tools"
        ),
        "img": Command(
            "img", cmd_img,
            "Поиск картинок", MOD_NAME,
            f"{p}img <запрос>", "tools"
        ),
    }

    # ==================== LIFECYCLE ====================

    async def on_unload():
        cache.clear()
        logger.info(f"{MOD_NAME}: выгружен")

    mod.on_unload = on_unload

    # ==================== РЕГИСТРАЦИЯ ====================

    bot.module_manager.register_module(mod)
    bot.register_commands(mod)

    logger.info(f"{MOD_NAME}: загружен")
