"""
Модуль Gemini для kazhurkeUserBot v2.3.0
Взаимодействие с Google Gemini AI: текст, медиа, диалоги с памятью, авто-ответы
Автор: rewrite by AI
Версия: 6.0.0
"""
# requires: google-genai, pytz

import os
import re
import io
import json
import random
import asyncio
import logging
import tempfile
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Callable, Any, Optional, Tuple
from pathlib import Path

import pytz

from telethon import events, Button
from telethon.tl.types import Message, DocumentAttributeFilename, DocumentAttributeSticker
from telethon.utils import get_display_name
from telethon.errors import MessageTooLongError

# Google Gemini
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    types = None

logger = logging.getLogger(__name__)

# ==================== КОНСТАНТЫ ====================
MOD_NAME = "gemini"
DATA_FILE = "gemini_data.json"
TIMEOUT = 60
MAX_FILE_SIZE = 90 * 1024 * 1024

TEXT_TYPES = {
    "text/plain", "text/markdown", "text/html", "text/css",
    "application/json", "application/xml", "text/x-python",
}

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

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def escape_html(text: Any) -> str:
    """Экранирование HTML"""
    if text is None:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def get_args(event) -> str:
    """Извлечь аргументы команды"""
    parts = event.raw_text.split(maxsplit=1)
    return parts[1] if len(parts) > 1 else ""

def markdown_to_html(text: str) -> str:
    """Простая конвертация markdown в HTML"""
    # Жирный текст
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    # Курсив
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    # Код
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    # Блоки кода
    text = re.sub(r'```(\w*)\n([\s\S]+?)\n```', r'<pre><code>\2</code></pre>', text)
    return text

# ==================== SETUP ====================
def setup(bot):
    """Точка входа модуля"""

    # Проверка доступности библиотеки
    if not GEMINI_AVAILABLE:
        logger.error("Gemini: библиотека google-genai не установлена!")

        mod = Module(
            name=MOD_NAME,
            description="Модуль Gemini (требуется google-genai)",
            author="AI",
            version="6.0.0",
        )

        async def cmd_error(event):
            await event.edit(
                "❗️ <b>Для работы модуля нужна библиотека google-genai</b>\n"
                "Выполните: <code>.pip install google-genai</code>",
                parse_mode='html'
            )

        p = bot.config.prefix
        mod.commands = {"g": Command("g", cmd_error, "Требуется google-genai", MOD_NAME, f"{p}g", "ai")}

        bot.module_manager.register_module(mod)
        bot.register_commands(mod)
        return

    # ==================== ХРАНИЛИЩЕ ДАННЫХ ====================
    data_path = Path(DATA_FILE)

    # Структуры данных
    state = {
        "conversations": {},  # {chat_id: [{"role": "user/model", "content": "..."}]}
        "gauto_conversations": {},
        "gauto_chats": set(),  # чаты с включенным авто-ответом
        "last_requests": {},  # для регенерации
        "api_key_index": 0,  # текущий используемый ключ
    }

    me = None  # информация о текущем пользователе

    # Загрузка данных
    def load_data():
        if data_path.exists():
            try:
                with open(data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    state["conversations"] = data.get("conversations", {})
                    state["gauto_conversations"] = data.get("gauto_conversations", {})
                    state["gauto_chats"] = set(data.get("gauto_chats", []))
                    state["last_requests"] = data.get("last_requests", {})
                    state["api_key_index"] = data.get("api_key_index", 0)
                logger.info(f"Gemini: загружено {len(state['conversations'])} диалогов")
            except Exception as e:
                logger.error(f"Gemini: ошибка загрузки данных: {e}")

    # Сохранение данных
    async def save_data():
        try:
            data = {
                "conversations": state["conversations"],
                "gauto_conversations": state["gauto_conversations"],
                "gauto_chats": list(state["gauto_chats"]),
                "last_requests": state["last_requests"],
                "api_key_index": state["api_key_index"],
            }
            with open(data_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Gemini: ошибка сохранения: {e}")

    # Получение информации о пользователе
    async def get_me():
        nonlocal me
        if not me:
            try:
                me = await bot.client.get_me()
            except Exception as e:
                logger.error(f"Не удалось получить me: {e}")
        return me

    # Загружаем данные
    load_data()
    asyncio.create_task(get_me())

    # ==================== РАБОТА С GEMINI ====================

    def get_api_keys() -> List[str]:
        """Получить список API ключей"""
        key_str = module_config(bot, MOD_NAME, "api_key", "")
        if not key_str:
            return []
        return [k.strip() for k in key_str.split(",") if k.strip()]

    def get_history(chat_id: int, gauto: bool = False) -> List[dict]:
        """Получить историю диалога"""
        storage = state["gauto_conversations"] if gauto else state["conversations"]
        key = str(chat_id)
        if key not in storage:
            storage[key] = []
        return storage[key]

    async def add_to_history(chat_id: int, user_text: str, model_text: str,
                            gauto: bool = False, regenerate: bool = False):
        """Добавить сообщения в историю"""
        history = get_history(chat_id, gauto)

        if regenerate and history:
            # Заменяем последний ответ модели
            for i in range(len(history) - 1, -1, -1):
                if history[i]["role"] == "model":
                    history[i]["content"] = model_text
                    history[i]["timestamp"] = int(datetime.now().timestamp())
                    break
        else:
            # Добавляем новые сообщения
            now = int(datetime.now().timestamp())
            history.append({"role": "user", "content": user_text, "timestamp": now})
            history.append({"role": "model", "content": model_text, "timestamp": now})

        # Ограничение размера истории
        max_len = module_config(bot, MOD_NAME, "max_history", 100)
        if max_len > 0 and len(history) > max_len * 2:
            history[:] = history[-(max_len * 2):]

        await save_data()

    async def clear_history(chat_id: int, gauto: bool = False):
        """Очистить историю"""
        storage = state["gauto_conversations"] if gauto else state["conversations"]
        key = str(chat_id)
        if key in storage:
            del storage[key]
            await save_data()

    def handle_error(e: Exception) -> str:
        """Обработка ошибок API"""
        msg = str(e).lower()

        if "quota" in msg or "429" in msg:
            return (
                "❗️ <b>Превышен лимит API</b>\n"
                "Попробуйте позже или добавьте другие ключи."
            )

        if "key" in msg and "invalid" in msg:
            return (
                "❗️ <b>Неверный API ключ</b>\n"
                "Проверьте ключ в настройках модуля."
            )

        if "blocked" in msg or "safety" in msg:
            return f"🚫 <b>Запрос заблокирован</b>\n<code>{escape_html(str(e))}</code>"

        return f"❗️ <b>Ошибка:</b>\n<code>{escape_html(str(e))}</code>"

    async def prepare_content(event: Message, custom_text: str = None) -> Tuple[List, str]:
        """Подготовить контент для отправки в Gemini"""
        parts = []
        text_parts = []

        # Текст команды
        args = custom_text if custom_text is not None else get_args(event)

        # Текст из reply
        reply = await event.get_reply_message()
        if reply and reply.text:
            text_parts.append(f"Контекст: {reply.text}")

        if args:
            text_parts.append(args)

        # Обработка медиа
        media_msg = event if (event.media or event.document) else reply
        if media_msg and (media_msg.photo or media_msg.document):
            # Изображение
            if media_msg.photo:
                try:
                    bio = io.BytesIO()
                    await bot.client.download_media(media_msg, bio)
                    parts.append(types.Part(
                        inline_data=types.Blob(mime_type="image/jpeg", data=bio.getvalue())
                    ))
                except Exception as e:
                    logger.error(f"Ошибка загрузки фото: {e}")

            # Документ
            elif media_msg.document:
                doc = media_msg.document
                mime = doc.mime_type or "application/octet-stream"

                # Текстовые файлы
                if mime in TEXT_TYPES or mime.startswith("text/"):
                    try:
                        bio = io.BytesIO()
                        await bot.client.download_media(media_msg, bio)
                        content = bio.getvalue().decode("utf-8", errors="ignore")
                        text_parts.insert(0, f"[Содержимое файла]:\n```\n{content[:10000]}\n```")
                    except Exception as e:
                        logger.error(f"Ошибка чтения файла: {e}")

        # Формируем финальный текст
        full_text = "\n\n".join(text_parts).strip()
        if not full_text and not parts:
            full_text = "[медиа без текста]"

        if full_text:
            parts.insert(0, types.Part(text=full_text))

        # Краткое описание для UI
        display = args or (reply.text[:100] if reply and reply.text else "[медиа]")

        return parts, display

    async def send_to_gemini(event: Message, parts: List,
                            regenerate: bool = False,
                            status_msg: Message = None,
                            chat_id_override: int = None,
                            gauto_mode: bool = False) -> Optional[str]:
        """Отправить запрос в Gemini"""

        # Определяем chat_id
        if regenerate:
            chat_id = chat_id_override
            msg_id = event  # тут передан ID сообщения
        else:
            chat_id = event.chat_id
            msg_id = event.id

        # API ключи
        api_keys = get_api_keys()
        if not api_keys:
            if status_msg and not gauto_mode:
                await status_msg.edit(
                    "❗️ <b>API ключи не настроены</b>\n"
                    f"Используйте: <code>.fcfg set -m {MOD_NAME} api_key YOUR_KEY</code>",
                    parse_mode='html'
                )
            return None

        # Системная инструкция
        system = module_config(bot, MOD_NAME, "system_prompt", "")
        if gauto_mode:
            user = await get_me()
            name = user.first_name if user else "User"
            system = f"Ты отвечаешь от имени пользователя {name}. Веди себя естественно."

        # История
        history_data = get_history(chat_id, gauto_mode)
        if regenerate and history_data:
            history_data = history_data[:-2]  # убираем последний обмен

        contents = []
        for item in history_data:
            contents.append(types.Content(
                role=item["role"],
                parts=[types.Part(text=item["content"])]
            ))

        # Добавляем текущий запрос
        contents.append(types.Content(role="user", parts=parts))

        # Конфиг генерации
        gen_config = types.GenerateContentConfig(
            temperature=module_config(bot, MOD_NAME, "temperature", 0.9),
            system_instruction=system if system else None,
            safety_settings=[
                types.SafetySetting(category=cat, threshold="BLOCK_NONE")
                for cat in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH",
                           "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]
            ]
        )

        # Пробуем ключи по очереди
        result = None
        last_error = None

        for i in range(len(api_keys)):
            idx = (state["api_key_index"] + i) % len(api_keys)
            key = api_keys[idx]

            try:
                client = genai.Client(api_key=key)
                model_name = module_config(bot, MOD_NAME, "model", "gemini-2.0-flash-exp")

                response = await client.aio.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=gen_config
                )

                if response.text:
                    result = response.text
                    state["api_key_index"] = idx
                    break
                else:
                    raise ValueError("Пустой ответ от модели")

            except Exception as e:
                last_error = e
                err_msg = str(e).lower()

                # Если квота - пробуем следующий ключ
                if "quota" in err_msg or "429" in err_msg:
                    continue
                else:
                    break  # другая ошибка - прерываем

        # Обработка результата
        if not result:
            error_text = handle_error(last_error or Exception("Неизвестная ошибка"))
            if status_msg and not gauto_mode:
                await status_msg.edit(error_text, parse_mode='html')
            return None

        # Сохраняем в историю
        user_text = " ".join(p.text for p in parts if hasattr(p, "text") and p.text) or "[медиа]"
        await add_to_history(chat_id, user_text, result, gauto_mode, regenerate)

        # Для gauto просто возвращаем текст
        if gauto_mode:
            return result

        # Формируем ответ
        hist_count = len(get_history(chat_id)) // 2
        max_hist = module_config(bot, MOD_NAME, "max_history", 100)
        memory_badge = f"🧠 [{hist_count}/{max_hist}]" if max_hist > 0 else f"🧠 [{hist_count}/∞]"

        # Конвертируем markdown
        html_response = markdown_to_html(result)

        # Оборачиваем в blockquote если нет кода
        if "<pre>" not in html_response and "<code>" not in html_response:
            html_response = f'<blockquote expandable>{html_response}</blockquote>'

        final_text = (
            f"{memory_badge}\n\n"
            f"💬 <b>Запрос:</b>\n<blockquote>{escape_html(user_text[:200])}</blockquote>\n\n"
            f"✨ <b>Gemini:</b>\n{html_response}"
        )

        # Если слишком длинный - отправляем файлом
        if len(final_text) > 4000:
            file = io.BytesIO(result.encode("utf-8"))
            file.name = "gemini_response.txt"

            if status_msg:
                await status_msg.delete()

            await bot.client.send_file(
                chat_id,
                file,
                caption="📄 Ответ слишком длинный, отправлен файлом",
                reply_to=msg_id if not regenerate else None
            )
        else:
            # Кнопки управления
            buttons = None
            if module_config(bot, MOD_NAME, "show_buttons", True):
                buttons = [
                    [Button.inline("🧹 Очистить", f"gem_clear_{chat_id}".encode())],
                    [Button.inline("🔄 Другой ответ", f"gem_regen_{msg_id}_{chat_id}".encode())]
                ]

            if status_msg:
                await status_msg.edit(final_text, buttons=buttons, parse_mode='html')
            else:
                await bot.client.send_message(
                    chat_id,
                    final_text,
                    buttons=buttons,
                    parse_mode='html',
                    reply_to=msg_id
                )

        # Сохраняем для регенерации
        if not regenerate:
            state["last_requests"][f"{chat_id}:{msg_id}"] = (parts, user_text)
            await save_data()

        return result

    # ==================== КОМАНДЫ ====================
    p = bot.config.prefix

    async def cmd_g(event):
        """Основная команда - запрос к Gemini"""
        status = await event.edit("⏳ <b>Обработка...</b>", parse_mode='html')
        parts, display = await prepare_content(event)

        if not parts:
            await status.edit("⚠️ Нужен текст или медиа", parse_mode='html')
            return

        await send_to_gemini(event, parts, status_msg=status)

    async def cmd_gclear(event):
        """Очистить историю"""
        args = get_args(event)
        gauto = "auto" in args
        chat_id = event.chat_id

        history = get_history(chat_id, gauto)
        if not history:
            await event.edit("ℹ️ История пуста", parse_mode='html')
            return

        await clear_history(chat_id, gauto)
        mode = "авто-ответа" if gauto else "диалога"
        await event.edit(f"🧹 История {mode} очищена", parse_mode='html')

    async def cmd_gmem(event):
        """Показать историю"""
        args = get_args(event)
        gauto = "auto" in args
        history = get_history(event.chat_id, gauto)

        if not history:
            await event.edit("ℹ️ История пуста", parse_mode='html')
            return

        lines = []
        for item in history[-20:]:
            role = "👤" if item["role"] == "user" else "✨"
            content = escape_html(item["content"][:100])
            lines.append(f"{role} {content}")

        await event.edit(
            f"<b>📝 История (последние {len(lines)}):</b>\n\n" + "\n\n".join(lines),
            parse_mode='html'
        )

    async def cmd_gauto(event):
        """Управление авто-ответами"""
        args = get_args(event).split()

        if not args:
            # Показываем статус
            if event.chat_id in state["gauto_chats"]:
                chance = int(module_config(bot, MOD_NAME, "gauto_chance", 0.3) * 100)
                await event.edit(
                    f"🎭 <b>Авто-ответ включен</b>\nВероятность: {chance}%",
                    parse_mode='html'
                )
            else:
                await event.edit("🎭 Авто-ответ выключен", parse_mode='html')
            return

        action = args[0].lower()

        if action == "on":
            state["gauto_chats"].add(event.chat_id)
            await save_data()
            await event.edit("✅ Авто-ответ включен", parse_mode='html')

        elif action == "off":
            state["gauto_chats"].discard(event.chat_id)
            await save_data()
            await event.edit("❌ Авто-ответ выключен", parse_mode='html')

        else:
            await event.edit(
                "ℹ️ Использование:\n"
                f"<code>{p}gauto on</code> — включить\n"
                f"<code>{p}gauto off</code> — выключить\n"
                f"<code>{p}gauto</code> — статус",
                parse_mode='html'
            )

    async def cmd_ginfo(event):
        """Информация о модуле"""
        api_keys = get_api_keys()
        model = module_config(bot, MOD_NAME, "model", "gemini-2.0-flash-exp")
        conv_count = len(state["conversations"])
        gauto_count = len(state["gauto_chats"])

        await event.edit(
            f"<b>📊 Модуль Gemini v6.0</b>\n\n"
            f"🔑 API ключей: {len(api_keys)}\n"
            f"🤖 Модель: <code>{model}</code>\n"
            f"💬 Активных диалогов: {conv_count}\n"
            f"🎭 Чатов с авто-ответом: {gauto_count}\n\n"
            f"Настройка: <code>{p}fcfg set -m {MOD_NAME} ...</code>",
            parse_mode='html'
        )

    # ==================== ОБРАБОТЧИКИ ====================

    # Callback для кнопок
    async def callback_handler(event):
        data = event.data.decode()

        if data.startswith("gem_clear_"):
            chat_id = int(data.replace("gem_clear_", ""))
            await clear_history(chat_id)
            await event.edit("🧹 История очищена", buttons=None, parse_mode='html')

        elif data.startswith("gem_regen_"):
            parts = data.replace("gem_regen_", "").split("_")
            msg_id = int(parts[0])
            chat_id = int(parts[1])

            # Получаем сохраненный запрос
            key = f"{chat_id}:{msg_id}"
            if key not in state["last_requests"]:
                await event.answer("❌ Запрос не найден", alert=True)
                return

            saved_parts, _ = state["last_requests"][key]

            await event.edit("⏳ Генерация...", parse_mode='html')
            await send_to_gemini(
                msg_id,  # передаем ID
                saved_parts,
                regenerate=True,
                status_msg=event,
                chat_id_override=chat_id
            )

    # Watcher для авто-ответов
    async def gauto_watcher(event):
        # Проверки
        if not hasattr(event, 'chat_id'):
            return

        chat_id = event.chat_id
        if chat_id not in state["gauto_chats"]:
            return

        # Не реагируем на свои сообщения
        user = await get_me()
        if not user or event.sender_id == user.id or event.out:
            return

        # Проверяем вероятность
        chance = module_config(bot, MOD_NAME, "gauto_chance", 0.3)
        if random.random() > chance:
            return

        # Не отвечаем ботам
        sender = await event.get_sender()
        if sender and getattr(sender, 'bot', False):
            return

        # Готовим контент и отправляем
        try:
            parts, _ = await prepare_content(event)
            if not parts:
                return

            response = await send_to_gemini(event, parts, gauto_mode=True)

            if response:
                # Имитируем набор
                await asyncio.sleep(random.uniform(1, 3))
                async with bot.client.action(chat_id, "typing"):
                    await asyncio.sleep(min(10, len(response) * 0.05))

                await event.reply(response)

        except Exception as e:
            logger.error(f"Ошибка gauto: {e}")

    # Регистрируем обработчики
    callback_h = bot.client.on(events.CallbackQuery(pattern=b"gem_"))(callback_handler)
    watcher_h = bot.client.on(events.NewMessage(incoming=True))(gauto_watcher)

    # ==================== СБОРКА МОДУЛЯ ====================

    mod = Module(
        name=MOD_NAME,
        description="Взаимодействие с Google Gemini AI",
        author="AI Rewrite",
        version="6.0.0",
        requirements=["google-genai", "pytz"],
        settings_schema=[
            {
                "key": "api_key",
                "label": "API ключи",
                "type": "str",
                "default": "",
                "description": "Ключи через запятую"
            },
            {
                "key": "model",
                "label": "Модель",
                "type": "str",
                "default": "gemini-2.0-flash-exp",
                "description": "Название модели"
            },
            {
                "key": "system_prompt",
                "label": "Системный промпт",
                "type": "str",
                "default": "",
                "description": "Инструкция для модели"
            },
            {
                "key": "temperature",
                "label": "Температура",
                "type": "float",
                "default": 0.9,
                "description": "Креативность (0.0-2.0)"
            },
            {
                "key": "max_history",
                "label": "Лимит истории",
                "type": "int",
                "default": 100,
                "description": "Макс. пар сообщений (0 = безлимит)"
            },
            {
                "key": "show_buttons",
                "label": "Показывать кнопки",
                "type": "bool",
                "default": True,
                "description": "Кнопки управления"
            },
            {
                "key": "gauto_chance",
                "label": "Вероятность авто-ответа",
                "type": "float",
                "default": 0.3,
                "description": "От 0.0 до 1.0"
            }
        ]
    )

    mod.commands = {
        "g": Command("g", cmd_g, "Запрос к Gemini", MOD_NAME, f"{p}g <текст>", "ai"),
        "gemini": Command("gemini", cmd_g, "Запрос к Gemini", MOD_NAME, f"{p}gemini <текст>", "ai"),
        "gclear": Command("gclear", cmd_gclear, "Очистить историю", MOD_NAME, f"{p}gclear [auto]", "ai"),
        "gmem": Command("gmem", cmd_gmem, "Показать историю", MOD_NAME, f"{p}gmem [auto]", "ai"),
        "gauto": Command("gauto", cmd_gauto, "Управление авто-ответами", MOD_NAME, f"{p}gauto [on/off]", "ai"),
        "ginfo": Command("ginfo", cmd_ginfo, "Информация о модуле", MOD_NAME, f"{p}ginfo", "ai"),
    }

    mod.handlers = [callback_h, watcher_h]

    async def on_unload():
        await save_data()
        logger.info("Gemini: модуль выгружен")

    mod.on_unload = on_unload

    # Регистрация
    bot.module_manager.register_module(mod)
    bot.register_commands(mod)

    logger.info("Gemini: модуль загружен")
