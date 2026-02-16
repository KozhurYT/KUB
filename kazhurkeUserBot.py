#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════╗
║           kazhurkeUserBot v2.4.0                        ║
║     Однофайловый Telegram Userbot с модулями            ║
║         и inline-панелью управления                     ║
║     + автоустановка зависимостей модулей                 ║
║     + HTML разметка + custom emoji                      ║
╚══════════════════════════════════════════════════════════╝

Зависимости: pip install telethon cryptg aiohttp
"""

import os
import sys
import json
import importlib
import importlib.util
import asyncio
import logging
import time
import traceback
import platform
import io
import re
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Callable, Any, Optional, Tuple

from telethon import TelegramClient, events, Button, version as telethon_version
from telethon.tl.types import (
    User, Channel, Chat,
    DocumentAttributeFilename,
)
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.errors import (
    FloodWaitError,
    AccessTokenInvalidError,
    UserAdminInvalidError,
    ChatAdminRequiredError,
)

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

# ──────────────────────── Брендинг ───────────────────────────

BRAND_NAME = "kazhurkeUserBot"
BRAND_VERSION = "2.4.0"
BRAND_EMOJI = "🦊"
BRAND_SHORT = "KUB"

BANNER = f"""
\033[38;5;208m╔══════════════════════════════════════════════════╗
║                                                  ║
║   {BRAND_EMOJI}  \033[1m{BRAND_NAME}\033[0m\033[38;5;208m v{BRAND_VERSION}                ║
║                                                  ║
║   Telegram Userbot с модулями и inline-панелью   ║
║   + автоустановка зависимостей                   ║
║   + HTML разметка + custom emoji                 ║
║                                                  ║
╚══════════════════════════════════════════════════╝\033[0m
"""

# ──────────────────────── Custom Emoji ───────────────────────

_HAS_PREMIUM = False


def _make_ce(emoji_id: int, fallback: str) -> str:
    if _HAS_PREMIUM:
        return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'
    return fallback


class CEmoji:
    def __init__(self):
        self._init_emojis()

    def _init_emojis(self):
        self.BRAND = _make_ce(5368324170671202286, "🦊")
        self.STAR = _make_ce(5368324170671202286, "⭐")
        self.CHECK = _make_ce(5382322526065218755, "✅")
        self.CROSS = _make_ce(5368324170671202286, "❌")
        self.WARN = _make_ce(5467928559664242360, "⚠️")
        self.GEAR = _make_ce(5431449001532594346, "⚙️")
        self.FIRE = _make_ce(5386399931378440750, "🔥")
        self.SPARK = _make_ce(5368324170671202286, "✨")
        self.USER = _make_ce(5368324170671202286, "👤")
        self.PING = _make_ce(5382322526065218755, "🏓")
        self.CLOCK = _make_ce(5431449001532594346, "⏱")
        self.PACKAGE = _make_ce(5467928559664242360, "📦")
        self.WRENCH = _make_ce(5386399931378440750, "🔧")
        self.KEY = _make_ce(5368324170671202286, "🔑")
        self.PYTHON = _make_ce(5386399931378440750, "🐍")
        self.SIGNAL = _make_ce(5431449001532594346, "📡")
        self.PC = _make_ce(5467928559664242360, "💻")
        self.PLUG = _make_ce(5382322526065218755, "🔌")
        self.CHART = _make_ce(5368324170671202286, "📊")
        self.STATS = _make_ce(5431449001532594346, "📈")
        self.BOT = _make_ce(5386399931378440750, "🤖")
        self.RELOAD = _make_ce(5382322526065218755, "🔄")
        self.BLUE = _make_ce(5368324170671202286, "🔵")
        self.GREEN = _make_ce(5382322526065218755, "🟢")
        self.RED = _make_ce(5467928559664242360, "🔴")
        self.DOWNLOAD = _make_ce(5431449001532594346, "📥")
        self.TRASH = _make_ce(5386399931378440750, "🗑")
        self.SEARCH = _make_ce(5368324170671202286, "🔍")
        self.CALC = _make_ce(5382322526065218755, "🔢")
        self.PIN = _make_ce(5431449001532594346, "📌")
        self.DICE = _make_ce(5467928559664242360, "🎲")
        self.COIN = _make_ce(5386399931378440750, "🪙")
        self.TARGET = _make_ce(5368324170671202286, "🎯")
        self.HAMMER = _make_ce(5382322526065218755, "🔨")
        self.BOOT = _make_ce(5431449001532594346, "👢")
        self.MUTE = _make_ce(5467928559664242360, "🔇")
        self.PAINT = _make_ce(5368324170671202286, "🎨")
        self.BOOK = _make_ce(5382322526065218755, "📖")
        self.BULB = _make_ce(5431449001532594346, "💡")
        self.ID = _make_ce(5386399931378440750, "🆔")
        self.LINK = _make_ce(5368324170671202286, "🔗")
        self.CHAT = _make_ce(5382322526065218755, "💬")
        self.WAVE = _make_ce(5368324170671202286, "👋")
        self.EMPTY = _make_ce(5431449001532594346, "📭")
        self.GLOBE = _make_ce(5467928559664242360, "🌐")
        self.FILE = _make_ce(5386399931378440750, "📎")


CE = CEmoji()


def _reinit_custom_emoji():
    global CE
    CE._init_emojis()


# ──────────────────────── HTML-утилиты ───────────────────────


def html_escape(text: str) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def html_bold(text: str) -> str:
    return f"<b>{text}</b>"


def html_italic(text: str) -> str:
    return f"<i>{text}</i>"


def html_code(text: str) -> str:
    return f"<code>{html_escape(text)}</code>"


def html_pre(text: str, lang: str = "") -> str:
    if lang:
        return f'<pre><code class="language-{lang}">{html_escape(text)}</code></pre>'
    return f"<pre>{html_escape(text)}</pre>"


def html_link(text: str, url: str) -> str:
    return f'<a href="{url}">{text}</a>'


def html_user_link(name: str, user_id: int) -> str:
    return f'<a href="tg://user?id={user_id}">{html_escape(name)}</a>'


def custom_emoji(emoji_id: int, fallback: str = "⭐") -> str:
    return _make_ce(emoji_id, fallback)


def _strip_custom_emoji(text: str) -> str:
    """Убирает tg-emoji теги, оставляя fallback текст."""
    return re.sub(r'<tg-emoji[^>]*>([^<]*)</tg-emoji>', r'\1', text)


async def safe_edit(event, text: str, **kwargs):
    """Безопасное редактирование с fallback при ошибке custom emoji."""
    kwargs.setdefault("parse_mode", "html")
    try:
        await event.edit(text, **kwargs)
    except Exception as e:
        err_str = str(e).lower()
        if "invalid" in err_str or "document" in err_str or "emoji" in err_str:
            clean = _strip_custom_emoji(text)
            try:
                await event.edit(clean, **kwargs)
            except Exception:
                plain = re.sub(r'<[^>]+>', '', clean)
                try:
                    await event.edit(plain)
                except Exception:
                    pass
        else:
            raise


async def safe_send(client, chat_id, text: str, **kwargs):
    """Безопасная отправка с fallback."""
    kwargs.setdefault("parse_mode", "html")
    try:
        return await client.send_message(chat_id, text, **kwargs)
    except Exception as e:
        err_str = str(e).lower()
        if "invalid" in err_str or "document" in err_str or "emoji" in err_str:
            clean = _strip_custom_emoji(text)
            try:
                return await client.send_message(chat_id, clean, **kwargs)
            except Exception:
                plain = re.sub(r'<[^>]+>', '', clean)
                return await client.send_message(chat_id, plain)
        else:
            raise


async def safe_send_file(client, chat_id, file, caption: str = "", **kwargs):
    """Безопасная отправка файла с fallback для caption."""
    kwargs.setdefault("parse_mode", "html")
    try:
        return await client.send_file(chat_id, file, caption=caption, **kwargs)
    except Exception as e:
        err_str = str(e).lower()
        if "invalid" in err_str or "document" in err_str or "emoji" in err_str:
            clean = _strip_custom_emoji(caption)
            try:
                return await client.send_file(chat_id, file, caption=clean, **kwargs)
            except Exception:
                plain = re.sub(r'<[^>]+>', '', clean)
                return await client.send_file(chat_id, file, caption=plain, parse_mode=None)
        else:
            raise


# ──────────────────────── Логирование ────────────────────────


class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[38;5;245m",
        logging.INFO: "\033[38;5;39m",
        logging.WARNING: "\033[38;5;208m",
        logging.ERROR: "\033[38;5;196m",
        logging.CRITICAL: "\033[48;5;196m\033[38;5;255m",
    }
    ICONS = {
        logging.DEBUG: "⚙️",
        logging.INFO: "💠",
        logging.WARNING: "⚠️",
        logging.ERROR: "❌",
        logging.CRITICAL: "🔥",
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelno, self.RESET)
        icon = self.ICONS.get(record.levelno, "")
        ts = datetime.now().strftime("%H:%M:%S")
        return f"{color}[{ts}] {icon} {record.getMessage()}{self.RESET}"


_handler = logging.StreamHandler()
_handler.setFormatter(ColorFormatter())
log = logging.getLogger(BRAND_SHORT)
log.setLevel(logging.INFO)
log.addHandler(_handler)
log.propagate = False

for _n in [
    "telethon.network.connection.connection",
    "telethon.network.mtprotosender",
    "telethon.client.updates",
]:
    logging.getLogger(_n).setLevel(logging.CRITICAL)

# ──────────────────────── Константы ──────────────────────────

CONFIG_FILE = "kub_config.json"
MODULES_DIR = "modules"
DEFAULT_PREFIX = "."


def get_default_kinfo_template():
    return (
        f"{CE.BRAND} <b>{{brand}}</b> v{{version}}\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"├ {CE.USER} Владелец: {{owner}}\n"
        f"├ {CE.PING} Пинг: {{ping}}ms\n"
        f"├ {CE.CLOCK} Аптайм: {{uptime}}\n"
        f"├ {CE.PACKAGE} Модулей: {{modules}} ({CE.BLUE}{{builtin}} {CE.GREEN}{{user_mods}})\n"
        f"├ {CE.WRENCH} Команд: {{commands}}\n"
        f"├ {CE.KEY} Префикс: {{prefix}}\n"
        f"├ {CE.PYTHON} Python: {{python}}\n"
        f"├ {CE.SIGNAL} Telethon: {{telethon}}\n"
        f"└ {CE.PC} {{os}}\n"
    )


def get_default_alive_msg():
    return (
        f"{CE.BRAND} <b>{{brand}}</b> работает!\n"
        f"├ {CE.CLOCK} {{uptime}}\n"
        f"├ {CE.PACKAGE} {{modules}} модулей\n"
        f"└ {CE.WRENCH} {{commands}} команд"
    )


# ──────────────────────── Утилиты ────────────────────────────


def format_uptime(seconds: float) -> str:
    td = timedelta(seconds=int(seconds))
    d, h, rem = td.days, *divmod(td.seconds, 3600)
    m, s = divmod(rem, 60)
    parts = []
    if d: parts.append(f"{d}д")
    if h: parts.append(f"{h}ч")
    if m: parts.append(f"{m}м")
    parts.append(f"{s}с")
    return " ".join(parts)


def truncate(text: str, mx: int = 4096) -> str:
    return text if len(text) <= mx else text[: mx - 20] + "\n\n... (обрезано)"


async def get_user_link(user) -> str:
    if not user:
        return "Unknown"
    name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "Deleted"
    escaped = html_escape(name)
    if user.username:
        return html_link(escaped, f"https://t.me/{user.username}")
    return html_user_link(name, user.id)


def get_raw_github_url(url: str) -> str:
    url = url.strip()
    if "github.com" in url and "/blob/" in url:
        url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
    if "gist.github.com" in url and "/raw" not in url:
        url = url.rstrip("/") + "/raw"
    return url


# ──────────────── Управление зависимостями ───────────────────

PIP_TO_IMPORT = {
    "pillow": "PIL", "python-dateutil": "dateutil", "beautifulsoup4": "bs4",
    "scikit-learn": "sklearn", "opencv-python": "cv2", "opencv-python-headless": "cv2",
    "python-telegram-bot": "telegram", "pyyaml": "yaml", "pycryptodome": "Crypto",
    "python-dotenv": "dotenv", "google-api-python-client": "googleapiclient",
    "python-magic": "magic", "attrs": "attr", "moviepy": "moviepy", "gtts": "gtts",
    "pydub": "pydub", "speedtest-cli": "speedtest", "wikipedia": "wikipedia",
    "translate": "translate", "qrcode": "qrcode", "cryptg": "cryptg",
}


def parse_module_requirements(content: str) -> List[str]:
    requires: List[str] = []
    seen: set = set()
    for line in content.split("\n"):
        stripped = line.strip()
        for prefix_kw in ("# requires:", "# require:", "# deps:", "# dependencies:"):
            if stripped.lower().startswith(prefix_kw):
                pkgs_str = stripped[len(prefix_kw):].strip()
                for pkg in pkgs_str.split(","):
                    pkg = pkg.strip()
                    if pkg and pkg.lower() not in seen:
                        requires.append(pkg)
                        seen.add(pkg.lower())
    for var_name in ("__requires__", "__dependencies__", "__deps__"):
        pattern = rf'{var_name}\s*=\s*\[([^\]]*)\]'
        match = re.search(pattern, content)
        if match:
            items_str = match.group(1)
            for item in re.findall(r'["\']([^"\']+)["\']', items_str):
                item = item.strip()
                if item and item.lower() not in seen:
                    requires.append(item)
                    seen.add(item.lower())
    return requires


def _get_import_name(pip_name: str) -> str:
    base = re.split(r'[><=!~]', pip_name)[0].strip()
    mapped = PIP_TO_IMPORT.get(base.lower())
    return mapped if mapped else base.replace("-", "_")


def is_package_installed(package: str) -> bool:
    base = re.split(r'[><=!~]', package)[0].strip()
    import_name = _get_import_name(package)
    try:
        importlib.import_module(import_name)
        return True
    except ImportError:
        pass
    try:
        from importlib.metadata import distribution
        distribution(base)
        return True
    except Exception:
        pass
    try:
        importlib.import_module(base.replace("-", "_").lower())
        return True
    except ImportError:
        pass
    return False


def install_pip_package(package: str, timeout: int = 120) -> Tuple[bool, str]:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package, "--quiet"],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode == 0:
            importlib.invalidate_caches()
            return True, package
        else:
            err = result.stderr.strip().split("\n")[-1] if result.stderr.strip() else "unknown error"
            return False, f"{package}: {err[:200]}"
    except subprocess.TimeoutExpired:
        return False, f"{package}: таймаут ({timeout}с)"
    except FileNotFoundError:
        return False, f"{package}: pip не найден"
    except Exception as e:
        return False, f"{package}: {e}"


def uninstall_pip_package(package: str) -> Tuple[bool, str]:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", package, "-y", "--quiet"],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0:
            return True, package
        else:
            err = result.stderr.strip().split("\n")[-1] if result.stderr.strip() else "unknown"
            return False, f"{package}: {err[:200]}"
    except Exception as e:
        return False, f"{package}: {e}"


def check_and_install_requirements(content: str) -> Dict[str, Any]:
    reqs = parse_module_requirements(content)
    result = {"all": reqs, "already": [], "installed": [], "failed": []}
    for pkg in reqs:
        if is_package_installed(pkg):
            result["already"].append(pkg)
            log.debug(f"📦 {pkg} — уже установлен")
        else:
            log.info(f"📥 Устанавливаю зависимость: {pkg} ...")
            ok, msg = install_pip_package(pkg)
            if ok:
                result["installed"].append(pkg)
                log.info(f"✅ {pkg} установлен")
            else:
                result["failed"].append(msg)
                log.error(f"❌ Не удалось установить {pkg}: {msg}")
    return result


async def async_install_pip_package(package: str, timeout: int = 120) -> Tuple[bool, str]:
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "pip", "install", package, "--quiet",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            return False, f"{package}: таймаут ({timeout}с)"
        if proc.returncode == 0:
            importlib.invalidate_caches()
            return True, package
        else:
            err = stderr.decode().strip().split("\n")[-1] if stderr else "unknown"
            return False, f"{package}: {err[:200]}"
    except FileNotFoundError:
        return False, f"{package}: pip не найден"
    except Exception as e:
        return False, f"{package}: {e}"


async def async_check_and_install_requirements(content: str) -> Dict[str, Any]:
    reqs = parse_module_requirements(content)
    result = {"all": reqs, "already": [], "installed": [], "failed": []}
    for pkg in reqs:
        if is_package_installed(pkg):
            result["already"].append(pkg)
        else:
            log.info(f"📥 Устанавливаю зависимость: {pkg} ...")
            ok, msg = await async_install_pip_package(pkg)
            if ok:
                result["installed"].append(pkg)
                log.info(f"✅ {pkg} установлен")
            else:
                result["failed"].append(msg)
                log.error(f"❌ {msg}")
    return result


# ──────────────────────── Конфиг ─────────────────────────────


class Config:
    _defaults = {
        "api_id": 0,
        "api_hash": "",
        "phone": "",
        "bot_token": "",
        "prefix": DEFAULT_PREFIX,
        "alive_message": "",
        "disabled_modules": [],
        "custom_settings": {},
        "owner_id": 0,
        "installed_modules": {},
        "kinfo": {
            "template": "",
            "emoji": BRAND_EMOJI,
            "photo": "",
            "show_ping": True,
            "show_uptime": True,
            "show_modules": True,
            "show_commands": True,
            "show_prefix": True,
            "show_python": True,
            "show_telethon": True,
            "show_os": True,
            "show_owner": True,
            "custom_lines": [],
        },
        "stats": {
            "commands_used": 0,
            "started_at": 0,
        },
    }

    def __init__(self, path: str = CONFIG_FILE):
        self.path = path
        self.data: Dict[str, Any] = {}
        self.load()

    def load(self):
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        for k, v in self._defaults.items():
            if k not in self.data:
                self.data[k] = v if not isinstance(v, (dict, list)) else (
                    {**v} if isinstance(v, dict) else list(v)
                )
            elif isinstance(v, dict):
                for dk, dv in v.items():
                    self.data[k].setdefault(dk, dv)

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def __getattr__(self, name):
        if name in ("path", "data", "_defaults"):
            return super().__getattribute__(name)
        if name in self.data:
            return self.data[name]
        raise AttributeError(name)

    def __setattr__(self, name, value):
        if name in ("path", "data", "_defaults"):
            super().__setattr__(name, value)
        else:
            self.data[name] = value

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()


# ──────────────────────── module_config ───────────────────────


def module_config(bot, mod_name: str, key: str, default=None):
    custom = bot.config.data.get("custom_settings", {})
    full_key = f"{mod_name}.{key}"
    val = custom.get(full_key)

    if val is None:
        mod = bot.module_manager.modules.get(mod_name)
        if mod:
            for s in mod.settings_schema:
                if s["key"] == key:
                    val = s.get("default", default)
                    break
        if val is None:
            return default

    mod = bot.module_manager.modules.get(mod_name)
    if mod and val is not None:
        for s in mod.settings_schema:
            if s["key"] == key:
                stype = s.get("type", "str")
                try:
                    if stype == "int":
                        return int(val)
                    elif stype == "float":
                        return float(val)
                    elif stype == "bool":
                        if isinstance(val, bool):
                            return val
                        return str(val).lower() in ("true", "1", "yes", "да", "on")
                    elif stype == "list":
                        if isinstance(val, list):
                            return val
                        return [x.strip() for x in str(val).split(",") if x.strip()]
                except (ValueError, AttributeError, TypeError):
                    return default
                break
    return val


def module_config_set(bot, mod_name: str, key: str, value):
    custom = dict(bot.config.data.get("custom_settings", {}))
    custom[f"{mod_name}.{key}"] = value
    bot.config.data["custom_settings"] = custom
    bot.config.save()


# ──────────────────────── Модульная система ───────────────────


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


class ModuleManager:
    def __init__(self, bot: "Userbot"):
        self.bot = bot
        self.modules: Dict[str, Module] = {}
        self._builtin_names: set = set()

    def register_module(self, module: Module):
        self.modules[module.name] = module
        log.info(f"📦 {module.name} v{module.version} ({len(module.commands)} cmd)")

    def mark_builtin(self, name: str):
        self._builtin_names.add(name)

    def is_builtin(self, name: str) -> bool:
        return name in self._builtin_names

    def unload_module(self, name: str) -> bool:
        if name not in self.modules:
            return False
        mod = self.modules[name]
        if mod.on_unload:
            try:
                r = mod.on_unload()
                if asyncio.iscoroutine(r):
                    asyncio.get_event_loop().create_task(r)
            except Exception:
                pass
        for h in mod.handlers:
            try:
                self.bot.client.remove_event_handler(h)
            except Exception:
                pass
        for cn in mod.commands:
            self.bot._command_handlers.pop(cn, None)
        del self.modules[name]
        return True

    def get_all_commands(self) -> Dict[str, Command]:
        cmds = {}
        for m in self.modules.values():
            cmds.update(m.commands)
        return cmds

    def get_user_modules(self) -> Dict[str, Module]:
        return {k: v for k, v in self.modules.items() if not self.is_builtin(k)}

    def load_from_directory(self, directory: str = MODULES_DIR):
        path = Path(directory)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            return
        loaded = 0
        for f in sorted(path.glob("*.py")):
            if f.name.startswith("_"):
                continue
            if f.stem in self.bot.config.disabled_modules:
                continue
            try:
                self._load_file(f)
                loaded += 1
            except Exception as e:
                log.error(f"Ошибка {f.name}: {e}")
                traceback.print_exc()
        if loaded:
            log.info(f"📂 {loaded} пользовательских модулей загружено")

    def _load_file(self, file: Path):
        content = file.read_text(encoding="utf-8", errors="replace")
        deps_result = check_and_install_requirements(content)
        if deps_result["all"]:
            installed_count = len(deps_result["installed"])
            failed_count = len(deps_result["failed"])
            if installed_count:
                log.info(
                    f"📦 {file.stem}: установлено {installed_count}/{len(deps_result['all'])} зависимостей "
                    f"({', '.join(deps_result['installed'])})"
                )
            if failed_count:
                log.warning(
                    f"⚠️ {file.stem}: не удалось установить {failed_count} зависимость(ей): "
                    f"{', '.join(deps_result['failed'])}"
                )
                log.warning(f"⚠️ {file.stem}: модуль будет загружен, но может работать некорректно")

        spec = importlib.util.spec_from_file_location(file.stem, file)
        py = importlib.util.module_from_spec(spec)
        py.bot = self.bot
        py.client = self.bot.client
        py.config = self.bot.config
        py.manager = self
        py.module_config = lambda mn, k, d=None: module_config(self.bot, mn, k, d)
        py.module_config_set = lambda mn, k, v: module_config_set(self.bot, mn, k, v)
        # HTML-утилиты и custom emoji для модулей
        py.html_escape = html_escape
        py.html_bold = html_bold
        py.html_italic = html_italic
        py.html_code = html_code
        py.html_pre = html_pre
        py.html_link = html_link
        py.html_user_link = html_user_link
        py.custom_emoji = custom_emoji
        py.CE = CE
        py.CEmoji = CEmoji
        py.safe_edit = safe_edit
        py.safe_send = safe_send
        py.safe_send_file = safe_send_file
        spec.loader.exec_module(py)
        if hasattr(py, "setup"):
            py.setup(self.bot)

    def install_from_file(self, filename: str, content: bytes) -> Tuple[bool, str]:
        if not filename.endswith(".py"):
            return False, "Файл должен быть .py"
        mod_name = filename[:-3]
        if mod_name in self._builtin_names:
            return False, f"{mod_name} зарезервировано"
        try:
            text_content = content.decode("utf-8")
        except UnicodeDecodeError:
            return False, "Невалидный UTF-8"

        deps_result = check_and_install_requirements(text_content)
        deps_info = ""
        if deps_result["installed"]:
            deps_info += f"\n📥 Установлены: {', '.join(deps_result['installed'])}"
        if deps_result["failed"]:
            deps_info += f"\n⚠️ Ошибки: {', '.join(deps_result['failed'])}"

        path = Path(MODULES_DIR)
        path.mkdir(parents=True, exist_ok=True)
        fp = path / filename
        fp.write_bytes(content)
        if mod_name in self.modules:
            self.unload_module(mod_name)
        try:
            self._load_file(fp)
        except Exception as e:
            fp.unlink(missing_ok=True)
            return False, f"Ошибка: {e}{deps_info}"
        installed = self.bot.config.get("installed_modules", {})
        installed[mod_name] = {
            "filename": filename,
            "installed_at": datetime.now().isoformat(),
            "source": "file",
            "requirements": deps_result["all"],
        }
        self.bot.config.set("installed_modules", installed)

        if mod_name in self.modules:
            self.modules[mod_name].requirements = deps_result["all"]

        return True, mod_name + deps_info

    async def install_from_url(self, url: str) -> Tuple[bool, str]:
        if not HAS_AIOHTTP:
            return False, "pip install aiohttp"
        raw_url = get_raw_github_url(url)
        fn = raw_url.split("?")[0].split("#")[0].split("/")[-1]
        if not fn.endswith(".py"):
            fn += ".py"
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(raw_url, timeout=aiohttp.ClientTimeout(total=30)) as r:
                    if r.status != 200:
                        return False, f"HTTP {r.status}"
                    content = await r.read()
                    if len(content) > 5 * 1024 * 1024:
                        return False, ">5MB"
                    txt = content.decode("utf-8", errors="replace")
                    if txt.strip().startswith(("<!DOCTYPE", "<html")):
                        return False, "HTML вместо Python"
        except Exception as e:
            return False, str(e)

        deps_result = await async_check_and_install_requirements(txt)
        deps_info = ""
        if deps_result["installed"]:
            deps_info += f"\n📥 Установлены: {', '.join(deps_result['installed'])}"
        if deps_result["failed"]:
            deps_info += f"\n⚠️ Ошибки: {', '.join(deps_result['failed'])}"

        ok, res = self.install_from_file(fn, content)
        if ok:
            inst = self.bot.config.get("installed_modules", {})
            mn = fn[:-3]
            if mn in inst:
                inst[mn]["source"] = "url"
                inst[mn]["url"] = url
                inst[mn]["requirements"] = deps_result["all"]
                self.bot.config.set("installed_modules", inst)
        return ok, res

    def uninstall_module(self, name: str) -> Tuple[bool, str]:
        if self.is_builtin(name):
            return False, "Встроенный модуль"
        self.unload_module(name)
        deleted = False
        p = Path(MODULES_DIR)
        fp = p / f"{name}.py"
        if fp.exists():
            fp.unlink()
            deleted = True
        inst = self.bot.config.get("installed_modules", {})
        if name in inst:
            if not deleted:
                fn = inst[name].get("filename", "")
                fp2 = p / fn
                if fp2.exists():
                    fp2.unlink()
                    deleted = True
            del inst[name]
            self.bot.config.set("installed_modules", inst)
        return True, f"{name} удалён" if deleted else f"{name} выгружен"


# ──────────────────────── Inline-панель ──────────────────────
# Inline-бот НЕ поддерживает custom emoji (ограничение Telegram).
# Вся панель использует Markdown и обычные unicode-эмодзи.


class InlinePanel:
    def __init__(self, bot: "Userbot"):
        self.bot = bot
        self.inline_bot: Optional[TelegramClient] = None
        self._states: Dict[int, dict] = {}
        self.active = False

    async def start(self) -> bool:
        token = self.bot.config.bot_token
        if not token:
            log.warning("Bot token не указан — inline выключен")
            return False
        try:
            self.inline_bot = TelegramClient(
                "kub_inline_session", self.bot.config.api_id, self.bot.config.api_hash
            )
            await self.inline_bot.start(bot_token=token)
            me = await self.inline_bot.get_me()
            log.info(f"🤖 Inline: @{me.username}")
            self.inline_bot.add_event_handler(self._on_callback, events.CallbackQuery())
            self.inline_bot.add_event_handler(self._on_inline_query, events.InlineQuery())
            self.inline_bot.add_event_handler(self._on_message, events.NewMessage())
            self.active = True
            return True
        except AccessTokenInvalidError:
            log.error("Bot token невалиден!")
            self.inline_bot = None
            return False
        except Exception as e:
            log.error(f"Inline ошибка: {e}")
            self.inline_bot = None
            return False

    async def stop(self):
        if self.inline_bot:
            try:
                await self.inline_bot.disconnect()
            except Exception:
                pass
            self.inline_bot = None
            self.active = False

    async def restart(self) -> bool:
        await self.stop()
        if os.path.exists("kub_inline_session.session"):
            try:
                os.remove("kub_inline_session.session")
            except Exception:
                pass
        return await self.start()

    async def _is_owner(self, uid: int) -> bool:
        return uid == self.bot.config.owner_id

    async def _on_inline_query(self, event):
        if not await self._is_owner(event.sender_id):
            await event.answer([event.builder.article(title="⛔", text="Нет доступа.")])
            return
        up = format_uptime(time.time() - self.bot.start_time)
        mods = len(self.bot.module_manager.modules)
        cmds = len(self.bot._command_handlers)
        await event.answer([event.builder.article(
            title=f"{BRAND_EMOJI} {BRAND_NAME} — Панель",
            description=f"⏱ {up} | 📦 {mods} | 🔧 {cmds}",
            text=f"{BRAND_EMOJI} **{BRAND_NAME}** v{BRAND_VERSION}\n━━━━━━━━━━━━━━━━━━━━━",
            buttons=self._main_buttons(),
        )])

    # ─── кнопки ───

    def _main_buttons(self):
        um = len(self.bot.module_manager.get_user_modules())
        return [
            [Button.inline("📋 Модули", b"p:modules"), Button.inline("⚙️ Настройки", b"p:settings")],
            [Button.inline("📊 Статус", b"p:status"), Button.inline("📈 Статистика", b"p:stats")],
            [Button.inline(f"🔌 Польз. ({um})", b"p:usermods"), Button.inline("🎨 kinfo", b"p:kinfo")],
            [Button.inline("🔄 Перезагрузка", b"act:reload")],
        ]

    def _modules_buttons(self):
        btns = []
        row = []
        for name in self.bot.module_manager.modules:
            dis = name in self.bot.config.disabled_modules
            bi = self.bot.module_manager.is_builtin(name)
            icon = "🔴" if dis else ("🔵" if bi else "🟢")
            row.append(Button.inline(f"{icon} {name}", f"m:{name}".encode()))
            if len(row) == 2:
                btns.append(row)
                row = []
        if row:
            btns.append(row)
        btns.append([Button.inline("🔙 Назад", b"p:main")])
        return btns

    def _module_buttons(self, name: str):
        dis = name in self.bot.config.disabled_modules
        bi = self.bot.module_manager.is_builtin(name)
        btns = [[Button.inline("🟢 Вкл" if dis else "🔴 Выкл", f"tog:{name}".encode())]]
        mod = self.bot.module_manager.modules.get(name)
        if mod and mod.settings_schema:
            btns.append([Button.inline("⚙️ Настройки модуля", f"ms:{name}".encode())])
        if not bi:
            btns.append([Button.inline("🗑 Удалить", f"del:{name}".encode())])
        btns.append([Button.inline("🔙 К модулям", b"p:modules")])
        return btns

    def _usermods_buttons(self):
        um = self.bot.module_manager.get_user_modules()
        btns = []
        for name, mod in um.items():
            btns.append([Button.inline(f"🟢 {name} v{mod.version}", f"m:{name}".encode())])
        if not btns:
            btns.append([Button.inline("📭 Пусто", b"p:usermods")])
        btns.append([Button.inline("🔙 Назад", b"p:main")])
        return btns

    def _settings_buttons(self):
        return [
            [Button.inline(f"🔧 Префикс: {self.bot.config.prefix}", b"s:prefix")],
            [Button.inline("💬 Alive-сообщение", b"s:alive")],
            [Button.inline("🎨 Настроить kinfo", b"p:kinfo")],
            [Button.inline("🔙 Назад", b"p:main")],
        ]

    def _mod_settings_buttons(self, mod_name: str):
        mod = self.bot.module_manager.modules.get(mod_name)
        btns = []
        if mod:
            custom = self.bot.config.data.get("custom_settings", {})
            for s in mod.settings_schema:
                fk = f"{mod_name}.{s['key']}"
                val = custom.get(fk, s.get("default", "—"))
                disp = str(val)[:25]
                stype = s.get("type", "str")
                if stype == "bool":
                    if isinstance(val, bool):
                        bval = val
                    else:
                        bval = str(val).lower() in ("true", "1", "yes", "да", "on")
                    icon = "✅" if bval else "❌"
                    btns.append([Button.inline(
                        f"{icon} {s['label']}",
                        f"stoggle:{mod_name}:{s['key']}".encode()
                    )])
                else:
                    btns.append([Button.inline(
                        f"✏️ {s['label']}: {disp}",
                        f"sm:{mod_name}:{s['key']}".encode()
                    )])
        btns.append([Button.inline("🔙 Назад", f"m:{mod_name}".encode())])
        return btns

    def _kinfo_buttons(self):
        ki = self.bot.config.data.get("kinfo", {})
        emoji = ki.get("emoji", BRAND_EMOJI)
        photo = "✅" if ki.get("photo") else "❌"
        btns = [
            [Button.inline(f"😀 Эмодзи: {emoji}", b"ki:emoji")],
            [Button.inline(f"🖼 Фото: {photo}", b"ki:photo")],
            [Button.inline("📝 Шаблон текста", b"ki:template")],
            [Button.inline("➕ Добавить строку", b"ki:addline")],
            [Button.inline("🗑 Очистить строки", b"ki:clearlines")],
        ]
        toggles = [
            ("show_ping", "🏓 Пинг"), ("show_uptime", "⏱ Аптайм"),
            ("show_modules", "📦 Модули"), ("show_commands", "🔧 Команды"),
            ("show_prefix", "🔑 Префикс"), ("show_python", "🐍 Python"),
            ("show_telethon", "📡 Telethon"), ("show_os", "💻 ОС"),
            ("show_owner", "👤 Владелец"),
        ]
        row = []
        for key, label in toggles:
            val = ki.get(key, True)
            icon = "✅" if val else "❌"
            row.append(Button.inline(f"{icon} {label}", f"kit:{key}".encode()))
            if len(row) == 2:
                btns.append(row)
                row = []
        if row:
            btns.append(row)
        btns.append([Button.inline("👁 Превью", b"ki:preview")])
        btns.append([Button.inline("🔙 Назад", b"p:main")])
        return btns

    # ─── callbacks (Markdown, без custom emoji) ───

    async def _on_callback(self, event):
        if not await self._is_owner(event.sender_id):
            await event.answer("⛔", alert=True)
            return
        data = event.data.decode()
        try:
            if data == "p:main":
                await event.edit(
                    f"{BRAND_EMOJI} **{BRAND_NAME}** v{BRAND_VERSION}\n━━━━━━━━━━━━━━━━━━━━━",
                    buttons=self._main_buttons(),
                )
            elif data == "p:modules":
                mods = self.bot.module_manager.modules
                t = f"📋 **Модули** ({len(mods)})\n━━━━━━━━━━━━━━━━━━━━━\n🔵 встр | 🟢 польз | 🔴 выкл\n\n"
                for n, m in mods.items():
                    d = n in self.bot.config.disabled_modules
                    b = self.bot.module_manager.is_builtin(n)
                    i = "🔴" if d else ("🔵" if b else "🟢")
                    t += f"{i} **{n}** `v{m.version}` — _{m.description}_\n"
                await event.edit(t, buttons=self._modules_buttons())

            elif data == "p:usermods":
                um = self.bot.module_manager.get_user_modules()
                inst = self.bot.config.get("installed_modules", {})
                p = self.bot.config.prefix
                t = f"🔌 **Пользовательские** ({len(um)})\n━━━━━━━━━━━━━━━━━━━━━\n\n"
                if um:
                    for n, m in um.items():
                        info = inst.get(n, {})
                        src = {"file": "📎", "url": "🌐"}.get(info.get("source", ""), "❓")
                        reqs = info.get("requirements", [])
                        t += f"🟢 **{n}** `v{m.version}` {src}\n"
                        if reqs:
                            t += f"   📦 Зависимости: `{', '.join(reqs)}`\n"
                        if m.settings_schema:
                            t += f"   ⚙️ {len(m.settings_schema)} настроек\n"
                else:
                    t += f"📭 Пусто\n`{p}im` / `{p}dlm <url>`\n"
                await event.edit(t, buttons=self._usermods_buttons())

            elif data == "p:settings":
                await event.edit(
                    f"⚙️ **Настройки**\n━━━━━━━━━━━━━━━━━━━━━",
                    buttons=self._settings_buttons(),
                )

            elif data == "p:status":
                up = format_uptime(time.time() - self.bot.start_time)
                me = await self.bot.client.get_me()
                um = len(self.bot.module_manager.get_user_modules())
                tm = len(self.bot.module_manager.modules)
                t = (
                    f"📊 **Статус**\n━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"👤 {me.first_name} `{me.id}`\n⏱ **{up}**\n"
                    f"📦 {tm} (🔵{tm - um} 🟢{um})\n🔧 {len(self.bot._command_handlers)}\n"
                    f"🔑 `{self.bot.config.prefix}`\n"
                    f"🐍 `{platform.python_version()}`\n📡 `{telethon_version.__version__}`\n"
                    f"💻 {platform.system()} {platform.release()}\n"
                    f"🤖 Inline: {'✅' if self.active else '❌'}"
                )
                await event.edit(t, buttons=[[Button.inline("🔙", b"p:main")]])

            elif data == "p:stats":
                st = self.bot.config.get("stats", {})
                t = (
                    f"📈 **Статистика**\n━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"🔧 Команд: **{st.get('commands_used', 0)}**\n"
                    f"📦 Установлено: **{len(self.bot.config.get('installed_modules', {}))}**\n"
                )
                await event.edit(t, buttons=[[Button.inline("🔙", b"p:main")]])

            elif data == "p:prefix":
                self._states[event.sender_id] = {"w": "prefix"}
                await event.edit(f"🔧 Текущий: `{self.bot.config.prefix}`\nОтправьте новый:",
                                 buttons=[[Button.inline("🔙", b"p:settings")]])

            elif data == "p:alive":
                self._states[event.sender_id] = {"w": "alive"}
                await event.edit("💬 Отправьте alive. Переменные: {uptime} {modules} {commands} {emoji} {brand}",
                                 buttons=[[Button.inline("🔙", b"p:settings")]])

            # ─── kinfo ───
            elif data == "p:kinfo":
                ki = self.bot.config.data.get("kinfo", {})
                cl = ki.get("custom_lines", [])
                await event.edit(
                    f"🎨 **Настройка kinfo**\n━━━━━━━━━━━━━━━━━━━━━\nДоп. строк: {len(cl)}",
                    buttons=self._kinfo_buttons(),
                )
            elif data == "ki:emoji":
                self._states[event.sender_id] = {"w": "kinfo_emoji"}
                await event.edit("😀 Отправьте эмодзи:", buttons=[[Button.inline("🔙", b"p:kinfo")]])
            elif data == "ki:photo":
                self._states[event.sender_id] = {"w": "kinfo_photo"}
                ki = self.bot.config.data.get("kinfo", {})
                cur = ki.get("photo", "")
                btns = []
                if cur:
                    btns.append([Button.inline("🗑 Удалить фото", b"ki:rmphoto")])
                btns.append([Button.inline("🔙", b"p:kinfo")])
                await event.edit(
                    f"🖼 **Фото**\n{'Установлено ✅' if cur else 'Нет ❌'}\nОтправьте фото или URL:",
                    buttons=btns,
                )
            elif data == "ki:rmphoto":
                ki = dict(self.bot.config.data.get("kinfo", {}))
                ki["photo"] = ""
                self.bot.config.data["kinfo"] = ki
                self.bot.config.save()
                await event.answer("✅ Фото удалено", alert=True)
                await event.edit(buttons=self._kinfo_buttons())
            elif data == "ki:template":
                self._states[event.sender_id] = {"w": "kinfo_template"}
                await event.edit(
                    "📝 **Шаблон** (HTML)\nПеременные: {emoji} {brand} {version} {owner} {ping} {uptime}\n"
                    "{modules} {builtin} {user_mods} {commands} {prefix} {python} {telethon} {os} {custom_lines}",
                    buttons=[
                        [Button.inline("🔄 Сбросить", b"ki:resettemplate")],
                        [Button.inline("🔙", b"p:kinfo")],
                    ],
                )
            elif data == "ki:resettemplate":
                ki = dict(self.bot.config.data.get("kinfo", {}))
                ki["template"] = get_default_kinfo_template()
                self.bot.config.data["kinfo"] = ki
                self.bot.config.save()
                await event.answer("✅ Сброшен", alert=True)
                await event.edit(buttons=self._kinfo_buttons())
            elif data == "ki:addline":
                self._states[event.sender_id] = {"w": "kinfo_addline"}
                await event.edit("➕ Отправьте текст строки:",
                                 buttons=[[Button.inline("🔙", b"p:kinfo")]])
            elif data == "ki:clearlines":
                ki = dict(self.bot.config.data.get("kinfo", {}))
                ki["custom_lines"] = []
                self.bot.config.data["kinfo"] = ki
                self.bot.config.save()
                await event.answer("✅ Очищено", alert=True)
                await event.edit(buttons=self._kinfo_buttons())
            elif data == "ki:preview":
                text = await self.bot.build_kinfo_text()
                ki = self.bot.config.data.get("kinfo", {})
                if ki.get("photo"):
                    await event.answer("Превью отправлено", alert=True)
                    try:
                        # Для inline-бота убираем custom emoji из caption
                        clean_text = _strip_custom_emoji(text)
                        await self.inline_bot.send_file(event.sender_id, ki["photo"], caption=clean_text, parse_mode="html")
                    except Exception:
                        try:
                            await self.inline_bot.send_message(event.sender_id, _strip_custom_emoji(text), parse_mode="html")
                        except Exception:
                            await self.inline_bot.send_message(event.sender_id, re.sub(r'<[^>]+>', '', text))
                else:
                    # Для inline — без custom emoji
                    clean_text = _strip_custom_emoji(text)
                    await event.edit(clean_text, buttons=[[Button.inline("🔙", b"p:kinfo")]], parse_mode="html")
            elif data.startswith("kit:"):
                key = data[4:]
                ki = dict(self.bot.config.data.get("kinfo", {}))
                ki[key] = not ki.get(key, True)
                self.bot.config.data["kinfo"] = ki
                self.bot.config.save()
                await event.edit(buttons=self._kinfo_buttons())

            # ─── Module callbacks ───
            elif data.startswith("m:"):
                name = data[2:]
                mod = self.bot.module_manager.modules.get(name)
                if not mod:
                    await event.answer("Не найден", alert=True)
                    return
                bi = self.bot.module_manager.is_builtin(name)
                ct = ""
                for cn, cmd in mod.commands.items():
                    ct += f"  `{self.bot.config.prefix}{cn}` — {cmd.description}\n"
                sp = ""
                if mod.settings_schema:
                    sp = f"\n⚙️ **Настройки:** {len(mod.settings_schema)}\n"
                    custom = self.bot.config.data.get("custom_settings", {})
                    for s in mod.settings_schema[:5]:
                        k = f"{name}.{s['key']}"
                        v = custom.get(k, s.get("default", "—"))
                        sp += f"  `{s['key']}` = `{v}`\n"
                deps_text = ""
                inst = self.bot.config.get("installed_modules", {})
                info = inst.get(name, {})
                reqs = info.get("requirements", []) or mod.requirements
                if reqs:
                    deps_text = f"\n📦 **Зависимости:** `{', '.join(reqs)}`\n"
                t = (
                    f"📦 **{mod.name}** `v{mod.version}`\n━━━━━━━━━━━━━━━━━━━━━\n"
                    f"{'🔵 Встроенный' if bi else '🟢 Пользовательский'}\n"
                    f"👤 {mod.author}\n📝 {mod.description}\n{deps_text}{sp}\n"
                    f"**Команды:**\n{ct or '_Нет_'}"
                )
                await event.edit(t, buttons=self._module_buttons(name))

            elif data.startswith("tog:"):
                name = data[4:]
                dis = list(self.bot.config.disabled_modules)
                if name in dis:
                    dis.remove(name)
                else:
                    dis.append(name)
                self.bot.config.set("disabled_modules", dis)
                await event.edit(buttons=self._module_buttons(name))

            elif data.startswith("del:"):
                name = data[4:]
                ok, msg = self.bot.module_manager.uninstall_module(name)
                await event.answer(f"{'✅' if ok else '❌'} {msg}", alert=True)
                if ok:
                    await event.edit(f"🗑 {msg}", buttons=[[Button.inline("🔙", b"p:modules")]])

            elif data.startswith("ms:"):
                mn = data[3:]
                mod = self.bot.module_manager.modules.get(mn)
                t = f"⚙️ **Настройки: {mn}**\n━━━━━━━━━━━━━━━━━━━━━\n"
                if mod and mod.settings_schema:
                    t += f"\n{mod.description}\n\n"
                    custom = self.bot.config.data.get("custom_settings", {})
                    for s in mod.settings_schema:
                        k = f"{mn}.{s['key']}"
                        v = custom.get(k, s.get("default", "—"))
                        t += f"**{s['label']}**: `{v}`\n"
                        if "description" in s:
                            t += f"  _{s['description']}_\n"
                await event.edit(t, buttons=self._mod_settings_buttons(mn))

            elif data.startswith("sm:"):
                parts = data[3:].split(":", 1)
                mn, key = parts
                self._states[event.sender_id] = {"w": "modsetting", "mn": mn, "key": key}
                mod = self.bot.module_manager.modules.get(mn)
                schema = next((s for s in (mod.settings_schema if mod else []) if s["key"] == key), {})
                desc = schema.get("description", "")
                stype = schema.get("type", "str")
                cur = self.bot.config.data.get("custom_settings", {}).get(f"{mn}.{key}", schema.get("default", "—"))
                await event.edit(
                    f"✏️ **{schema.get('label', key)}**\n"
                    f"Тип: `{stype}`\n"
                    f"Текущее: `{cur}`\n"
                    f"{f'ℹ️ {desc}' if desc else ''}\n\n"
                    f"Отправьте новое значение:",
                    buttons=[[Button.inline("🔙", f"ms:{mn}".encode())]],
                )

            elif data.startswith("stoggle:"):
                parts = data[8:].split(":", 1)
                mn, key = parts
                full_key = f"{mn}.{key}"
                custom = dict(self.bot.config.data.get("custom_settings", {}))
                cur_val = custom.get(full_key)
                if cur_val is None:
                    mod_obj = self.bot.module_manager.modules.get(mn)
                    if mod_obj:
                        for s in mod_obj.settings_schema:
                            if s["key"] == key:
                                cur_val = s.get("default", "true")
                                break
                if isinstance(cur_val, bool):
                    cur_bool = cur_val
                else:
                    cur_bool = str(cur_val).lower() in ("true", "1", "yes", "да", "on")
                custom[full_key] = "false" if cur_bool else "true"
                self.bot.config.data["custom_settings"] = custom
                self.bot.config.save()
                await event.edit(buttons=self._mod_settings_buttons(mn))

            elif data == "s:prefix":
                self._states[event.sender_id] = {"w": "prefix"}
                await event.edit("🔧 Новый префикс:", buttons=[[Button.inline("🔙", b"p:settings")]])
            elif data == "s:alive":
                self._states[event.sender_id] = {"w": "alive"}
                await event.edit("💬 Новый alive:", buttons=[[Button.inline("🔙", b"p:settings")]])

            elif data == "act:reload":
                bi = set(self.bot.module_manager._builtin_names)
                for n in [x for x in self.bot.module_manager.modules if x not in bi]:
                    self.bot.module_manager.unload_module(n)
                self.bot.module_manager.load_from_directory()
                mc = len(self.bot.module_manager.modules)
                await event.answer(f"✅ {mc} модулей", alert=True)
                await event.edit(f"✅ Перезагружено ({mc})", buttons=self._main_buttons())

        except Exception as e:
            log.error(f"CB: {e}")
            traceback.print_exc()
            try:
                await event.answer(str(e)[:150], alert=True)
            except Exception:
                pass

    # ─── messages ───

    async def _on_message(self, event):
        if not await self._is_owner(event.sender_id):
            return

        st = self._states.get(event.sender_id)
        if not st:
            if self.inline_bot:
                me = await self.inline_bot.get_me()
                await event.reply(f"Наберите `@{me.username} ` в любом чате")
            return

        w = st.get("w")
        txt = event.raw_text.strip()
        handled = True

        if w == "prefix":
            if len(txt) > 3:
                await event.reply("❌ Макс 3")
                return
            self.bot.config.set("prefix", txt)
            await event.reply(f"✅ Префикс: `{txt}`")

        elif w == "alive":
            self.bot.config.set("alive_message", txt)
            await event.reply("✅ Alive обновлён")

        elif w == "modsetting":
            mn = st.get("mn", "")
            key = st.get("key", "")
            if mn and key:
                full_key = f"{mn}.{key}"
                custom = dict(self.bot.config.data.get("custom_settings", {}))
                custom[full_key] = txt
                self.bot.config.data["custom_settings"] = custom
                self.bot.config.save()

                saved = self.bot.config.data.get("custom_settings", {}).get(full_key)
                if saved == txt:
                    await event.reply(f"✅ `{mn}.{key}` = `{txt}`")
                else:
                    await event.reply(f"⚠️ Ошибка сохранения! Ожидалось `{txt}`, получено `{saved}`")
            else:
                await event.reply("❌ Не указан модуль или ключ")
                handled = False

        elif w == "kinfo_emoji":
            ki = dict(self.bot.config.data.get("kinfo", {}))
            ki["emoji"] = txt[:5]
            self.bot.config.data["kinfo"] = ki
            self.bot.config.save()
            await event.reply(f"✅ Эмодзи: {txt[:5]}")

        elif w == "kinfo_photo":
            ki = dict(self.bot.config.data.get("kinfo", {}))
            if event.photo:
                photo_path = "kub_kinfo_photo.jpg"
                await self.inline_bot.download_media(event.photo, photo_path)
                ki["photo"] = photo_path
                self.bot.config.data["kinfo"] = ki
                self.bot.config.save()
                await event.reply("✅ Фото установлено!")
            elif txt.startswith(("http://", "https://")):
                ki["photo"] = txt
                self.bot.config.data["kinfo"] = ki
                self.bot.config.save()
                await event.reply("✅ Фото (URL)!")
            else:
                await event.reply("❌ Отправьте фото или URL")
                return

        elif w == "kinfo_template":
            ki = dict(self.bot.config.data.get("kinfo", {}))
            ki["template"] = txt
            self.bot.config.data["kinfo"] = ki
            self.bot.config.save()
            await event.reply("✅ Шаблон обновлён")

        elif w == "kinfo_addline":
            ki = dict(self.bot.config.data.get("kinfo", {}))
            lines = list(ki.get("custom_lines", []))
            lines.append(txt)
            ki["custom_lines"] = lines
            self.bot.config.data["kinfo"] = ki
            self.bot.config.save()
            await event.reply(f"✅ Строка добавлена ({len(lines)})")

        else:
            handled = False

        if handled and event.sender_id in self._states:
            del self._states[event.sender_id]


# ──────────────────────── Встроенные модули ───────────────────


def load_core_module(bot: "Userbot"):
    mod = Module(name="core", description="Основные команды", author=BRAND_NAME, version=BRAND_VERSION)
    p = bot.config.prefix

    async def cmd_alive(event):
        up = format_uptime(time.time() - bot.start_time)
        me = await bot.client.get_me()
        t = bot.config.alive_message or get_default_alive_msg()
        try:
            t = t.format(
                uptime=up, modules=len(bot.module_manager.modules),
                commands=len(bot._command_handlers),
                python=platform.python_version(),
                owner=await get_user_link(me),
                emoji=BRAND_EMOJI, brand=BRAND_NAME, version=BRAND_VERSION,
            )
        except (KeyError, IndexError):
            pass
        await safe_edit(event, t)

    async def cmd_kinfo(event):
        start = time.time()
        text = await bot.build_kinfo_text(ping_start=start)
        ki = bot.config.data.get("kinfo", {})
        photo = ki.get("photo", "")
        if photo:
            await event.delete()
            try:
                await safe_send_file(bot.client, event.chat_id, photo, caption=text)
            except Exception:
                await safe_send(bot.client, event.chat_id, text)
        else:
            await safe_edit(event, text)

    async def cmd_kset(event):
        args = event.raw_text.split(maxsplit=2)
        if len(args) < 2:
            ki = bot.config.data.get("kinfo", {})
            await safe_edit(event,
                f"{CE.PAINT} <b>kinfo настройки</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"<code>{p}kset emoji &lt;эмодзи&gt;</code>\n"
                f"<code>{p}kset photo</code> (ответ на фото)\n"
                f"<code>{p}kset photo &lt;url/remove&gt;</code>\n"
                f"<code>{p}kset addline &lt;текст&gt;</code>\n"
                f"<code>{p}kset clearlines</code>\n"
                f"<code>{p}kset reset</code>"
            )
            return
        sub = args[1].lower()
        ki = dict(bot.config.data.get("kinfo", {}))
        if sub == "emoji":
            if len(args) < 3:
                await safe_edit(event, f"{CE.CROSS} <code>{p}kset emoji &lt;эмодзи&gt;</code>")
                return
            ki["emoji"] = args[2][:5]
            bot.config.data["kinfo"] = ki
            bot.config.save()
            await safe_edit(event, f"{CE.CHECK} {args[2][:5]}")
        elif sub == "photo":
            if event.is_reply:
                reply = await event.get_reply_message()
                if reply.photo:
                    path = "kub_kinfo_photo.jpg"
                    await bot.client.download_media(reply.photo, path)
                    ki["photo"] = path
                    bot.config.data["kinfo"] = ki
                    bot.config.save()
                    await safe_edit(event, f"{CE.CHECK} Фото!")
                    return
            if len(args) >= 3:
                val = args[2].strip()
                if val.lower() == "remove":
                    ki["photo"] = ""
                    bot.config.data["kinfo"] = ki
                    bot.config.save()
                    await safe_edit(event, f"{CE.CHECK} Удалено")
                elif val.startswith(("http://", "https://")):
                    ki["photo"] = val
                    bot.config.data["kinfo"] = ki
                    bot.config.save()
                    await safe_edit(event, f"{CE.CHECK} Фото (URL)!")
                else:
                    await safe_edit(event, f"{CE.CROSS} URL или <code>remove</code>")
            else:
                await safe_edit(event, f"{CE.CROSS} Ответьте на фото или <code>{p}kset photo &lt;url/remove&gt;</code>")
        elif sub == "addline":
            if len(args) < 3:
                await safe_edit(event, f"{CE.CROSS} <code>{p}kset addline &lt;текст&gt;</code>")
                return
            lines = list(ki.get("custom_lines", []))
            lines.append(args[2])
            ki["custom_lines"] = lines
            bot.config.data["kinfo"] = ki
            bot.config.save()
            await safe_edit(event, f"{CE.CHECK} Строка ({len(lines)})")
        elif sub == "clearlines":
            ki["custom_lines"] = []
            bot.config.data["kinfo"] = ki
            bot.config.save()
            await safe_edit(event, f"{CE.CHECK} Очищено")
        elif sub == "reset":
            bot.config.data["kinfo"] = dict(Config._defaults["kinfo"])
            bot.config.data["kinfo"]["template"] = get_default_kinfo_template()
            bot.config.save()
            await safe_edit(event, f"{CE.CHECK} Сброшено")
        else:
            await safe_edit(event, f"{CE.CROSS} <code>{html_escape(sub)}</code>?")

    async def cmd_help(event):
        args = event.raw_text.split(maxsplit=1)
        if len(args) > 1:
            cn = args[1].strip().lower()
            cmd = bot._command_handlers.get(cn)
            if cmd:
                await safe_edit(event,
                    f"{CE.BOOK} <code>{html_escape(bot.config.prefix + cmd.name)}</code>\n━━━━━━━━━━━━━━━━━━━━━\n"
                    f"📝 {html_escape(cmd.description)}\n{CE.PACKAGE} {html_escape(cmd.module)}\n"
                    f"{CE.BULB} <code>{html_escape(cmd.usage)}</code>"
                )
            else:
                await safe_edit(event, f"{CE.CROSS} <code>{html_escape(cn)}</code> не найдена")
            return
        t = f"{CE.BRAND} <b>{BRAND_NAME}</b> v{BRAND_VERSION}\n━━━━━━━━━━━━━━━━━━━━━\n\n"
        for mn, m in bot.module_manager.modules.items():
            if not m.commands:
                continue
            bi = bot.module_manager.is_builtin(mn)
            icon = CE.BLUE if bi else CE.GREEN
            t += f"<b>{icon} {html_escape(mn)}</b> — <i>{html_escape(m.description)}</i>\n"
            for cn, cmd in m.commands.items():
                t += f"  ├ <code>{html_escape(bot.config.prefix + cn)}</code> — {html_escape(cmd.description)}\n"
            t += "\n"
        t += f"{CE.BULB} <code>{html_escape(bot.config.prefix)}help &lt;cmd&gt;</code>"
        await safe_edit(event, truncate(t))

    async def cmd_ping(event):
        s = time.time()
        await safe_edit(event, f"{CE.BRAND} ...")
        e = (time.time() - s) * 1000
        await safe_edit(event,
            f"{CE.PING} <b>Понг!</b> <code>{e:.1f}ms</code>\n{CE.CLOCK} {format_uptime(time.time() - bot.start_time)}"
        )

    async def cmd_prefix(event):
        args = event.raw_text.split(maxsplit=1)
        if len(args) < 2:
            await safe_edit(event, f"{CE.WRENCH} <code>{html_escape(bot.config.prefix)}</code>")
            return
        n = args[1].strip()
        if len(n) > 3:
            await safe_edit(event, f"{CE.CROSS} Макс 3!")
            return
        bot.config.set("prefix", n)
        await safe_edit(event, f"{CE.CHECK} Префикс: <code>{html_escape(n)}</code>")

    async def cmd_modules(event):
        mods = bot.module_manager.modules
        um = bot.module_manager.get_user_modules()
        t = f"{CE.PACKAGE} <b>Модули</b> ({len(mods)})\n━━━━━━━━━━━━━━━━━━━━━\n\n"
        tc = 0
        for n, m in mods.items():
            d = n in bot.config.disabled_modules
            bi = bot.module_manager.is_builtin(n)
            i = CE.RED if d else (CE.BLUE if bi else CE.GREEN)
            cc = len(m.commands)
            tc += cc
            sc = f" {CE.GEAR}{len(m.settings_schema)}" if m.settings_schema else ""
            deps = f" {CE.PACKAGE}{len(m.requirements)}" if m.requirements else ""
            t += f"{i} <b>{html_escape(n)}</b> <code>v{m.version}</code> [{cc}cmd{sc}{deps}]\n"
        t += f"\n{CE.CHART} {tc} команд, {len(um)} польз."
        await safe_edit(event, t)

    async def cmd_reload(event):
        await safe_edit(event, f"{CE.RELOAD} ...")
        bi = set(bot.module_manager._builtin_names)
        for n in [x for x in list(bot.module_manager.modules) if x not in bi]:
            bot.module_manager.unload_module(n)
        bot.module_manager.load_from_directory()
        await safe_edit(event, f"{CE.CHECK} {len(bot.module_manager.modules)} модулей | {len(bot._command_handlers)} команд")

    async def cmd_eval(event):
        a = event.raw_text.split(maxsplit=1)
        if len(a) < 2:
            await safe_edit(event, f"{CE.CROSS} <code>{p}eval &lt;expr&gt;</code>")
            return
        try:
            r = eval(a[1])
            if asyncio.iscoroutine(r): r = await r
            await safe_edit(event, truncate(f"💻\n<pre>{html_escape(str(r))}</pre>"))
        except Exception as e:
            await safe_edit(event, f"{CE.CROSS}\n<pre>{html_escape(str(e))}</pre>")

    async def cmd_exec(event):
        a = event.raw_text.split(maxsplit=1)
        if len(a) < 2:
            await safe_edit(event, f"{CE.CROSS} <code>{p}exec &lt;code&gt;</code>")
            return
        old = sys.stdout
        sys.stdout = buf = io.StringIO()
        try:
            code = "async def __ae__(e,c,b):\n" + "".join(f"    {l}\n" for l in a[1].split("\n"))
            exec(code)
            await locals()["__ae__"](event, bot.client, bot)
            out = buf.getvalue()
            await safe_edit(event, truncate(f"💻\n<pre>{html_escape(out or '✅')}</pre>"))
        except Exception:
            await safe_edit(event, truncate(f"{CE.CROSS}\n<pre>{html_escape(traceback.format_exc())}</pre>"))
        finally:
            sys.stdout = old

    async def cmd_settings(event):
        if not bot.inline_panel.active:
            await safe_edit(event, f"{CE.WARN} <code>{p}settoken &lt;token&gt;</code>")
            return
        me = await bot.inline_panel.inline_bot.get_me()
        await safe_edit(event, f"{CE.GEAR} <code>@{me.username} </code> в любом чате")

    async def cmd_settoken(event):
        a = event.raw_text.split(maxsplit=1)
        if len(a) < 2:
            s = "✅" if bot.inline_panel.active else "❌"
            await safe_edit(event, f"{CE.BOT} Inline: {s}\n<code>{p}settoken &lt;token/remove&gt;</code>")
            return
        tok = a[1].strip()
        if tok.lower() == "remove":
            bot.config.set("bot_token", "")
            await bot.inline_panel.stop()
            await safe_edit(event, f"{CE.CHECK} Удалён")
            return
        await safe_edit(event, f"{CE.RELOAD} ...")
        bot.config.set("bot_token", tok)
        if await bot.inline_panel.restart():
            me = await bot.inline_panel.inline_bot.get_me()
            await safe_edit(event, f"{CE.CHECK} @{me.username}")
        else:
            bot.config.set("bot_token", "")
            await safe_edit(event, f"{CE.CROSS} Невалидный токен")

    async def cmd_status(event):
        up = format_uptime(time.time() - bot.start_time)
        me = await bot.client.get_me()
        st = bot.config.get("stats", {})
        um = len(bot.module_manager.get_user_modules())
        tm = len(bot.module_manager.modules)
        await safe_edit(event,
            f"{CE.CHART} <b>{BRAND_NAME}</b> v{BRAND_VERSION}\n━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{CE.USER} {html_escape(me.first_name)} <code>{me.id}</code>\n{CE.CLOCK} <b>{up}</b>\n"
            f"{CE.PACKAGE} {tm} ({CE.BLUE}{tm - um} {CE.GREEN}{um})\n{CE.WRENCH} {len(bot._command_handlers)}\n"
            f"{CE.STATS} {st.get('commands_used', 0)} выполнено\n"
            f"{CE.KEY} <code>{html_escape(bot.config.prefix)}</code> | {CE.PYTHON} <code>{platform.python_version()}</code>\n"
            f"{CE.SIGNAL} <code>{telethon_version.__version__}</code> | {CE.PC} {platform.system()}\n"
            f"{CE.BOT} Inline: {'✅' if bot.inline_panel.active else '❌'}"
        )

    async def cmd_im(event):
        if not event.is_reply:
            await safe_edit(event,
                f"{CE.DOWNLOAD} Ответьте на <code>.py</code> файл: <code>{p}im</code>\nИли: <code>{p}dlm &lt;url&gt;</code>")
            return
        reply = await event.get_reply_message()
        if not reply.document:
            await safe_edit(event, f"{CE.CROSS} Нет файла")
            return
        fn = None
        for attr in reply.document.attributes:
            if isinstance(attr, DocumentAttributeFilename):
                fn = attr.file_name
        if not fn:
            fn = f"mod_{int(time.time())}.py"
        if not fn.endswith(".py"):
            await safe_edit(event, f"{CE.CROSS} Только .py")
            return
        await safe_edit(event, f"{CE.DOWNLOAD} <code>{html_escape(fn)}</code>...")
        try:
            content = await bot.client.download_media(reply, bytes)
        except Exception as e:
            await safe_edit(event, f"{CE.CROSS} {html_escape(str(e))}")
            return

        text_content = content.decode("utf-8", errors="replace")
        reqs = parse_module_requirements(text_content)
        if reqs:
            missing = [r for r in reqs if not is_package_installed(r)]
            if missing:
                await safe_edit(event,
                    f"{CE.DOWNLOAD} <code>{html_escape(fn)}</code>\n{CE.PACKAGE} Установка зависимостей: <code>{', '.join(missing)}</code>..."
                )

        ok, res = bot.module_manager.install_from_file(fn, content)
        if ok:
            mod_name = res.split("\n")[0]
            m = bot.module_manager.modules.get(mod_name)
            cc = len(m.commands) if m else 0
            cl = ""
            if m and m.commands:
                cl = "\n\n<b>Команды:</b>\n" + "".join(
                    f"  <code>{html_escape(p + c)}</code> — {html_escape(cmd.description)}\n" for c, cmd in m.commands.items()
                )
            sc = ""
            if m and m.settings_schema:
                sc = f"\n{CE.GEAR} {len(m.settings_schema)} настроек"
            deps_lines = "\n".join(res.split("\n")[1:]) if "\n" in res else ""
            await safe_edit(event, f"{CE.CHECK} <b>{html_escape(mod_name)}</b> | {CE.WRENCH} {cc} cmd{cl}{sc}\n{deps_lines}")
        else:
            await safe_edit(event, f"{CE.CROSS} {html_escape(res)}")

    async def cmd_um(event):
        a = event.raw_text.split(maxsplit=1)
        if len(a) < 2:
            um = bot.module_manager.get_user_modules()
            if not um:
                await safe_edit(event, f"{CE.EMPTY} Нет польз. модулей")
                return
            t = f"{CE.TRASH} <code>{p}um &lt;имя&gt;</code>\n\n"
            for n, m in um.items():
                t += f"  {CE.GREEN} <code>{html_escape(n)}</code> — {html_escape(m.description)}\n"
            await safe_edit(event, t)
            return
        mn = a[1].strip().lower()
        if bot.module_manager.is_builtin(mn):
            await safe_edit(event, f"{CE.CROSS} Встроенный!")
            return
        ok, msg = bot.module_manager.uninstall_module(mn)
        await safe_edit(event, f"{CE.CHECK if ok else CE.CROSS} {html_escape(msg)}")

    async def cmd_dlm(event):
        a = event.raw_text.split(maxsplit=1)
        if len(a) < 2:
            await safe_edit(event, f"{CE.GLOBE} <code>{p}dlm &lt;url&gt;</code>\nGitHub, Gist, прямые .py ссылки")
            return
        url = a[1].strip()
        if not url.startswith(("http://", "https://")):
            await safe_edit(event, f"{CE.CROSS} http(s)://")
            return
        await safe_edit(event, f"{CE.GLOBE} Скачиваю...")
        ok, res = await bot.module_manager.install_from_url(url)
        if ok:
            mod_name = res.split("\n")[0]
            m = bot.module_manager.modules.get(mod_name)
            cc = len(m.commands) if m else 0
            cl = ""
            if m and m.commands:
                cl = "\n\n<b>Команды:</b>\n" + "".join(
                    f"  <code>{html_escape(p + c)}</code> — {html_escape(cmd.description)}\n" for c, cmd in m.commands.items()
                )
            deps_lines = "\n".join(res.split("\n")[1:]) if "\n" in res else ""
            await safe_edit(event, f"{CE.CHECK} <b>{html_escape(mod_name)}</b> | {CE.WRENCH} {cc} cmd{cl}\n{deps_lines}")
        else:
            await safe_edit(event, f"{CE.CROSS} {html_escape(res)}")

    async def cmd_lm(event):
        um = bot.module_manager.get_user_modules()
        inst = bot.config.get("installed_modules", {})
        t = f"{CE.PLUG} <b>Пользовательские</b> ({len(um)})\n━━━━━━━━━━━━━━━━━━━━━\n\n"
        if not um:
            t += f"{CE.EMPTY} <code>{p}im</code> | <code>{p}dlm &lt;url&gt;</code>\n"
        else:
            tc = 0
            for n, m in um.items():
                info = inst.get(n, {})
                src = {"file": CE.FILE, "url": CE.GLOBE}.get(info.get("source", ""), "❓")
                cc = len(m.commands)
                tc += cc
                sc = f" {CE.GEAR}{len(m.settings_schema)}" if m.settings_schema else ""
                reqs = info.get("requirements", [])
                deps = f" {CE.PACKAGE}{len(reqs)}" if reqs else ""
                t += f"{CE.GREEN} <b>{html_escape(n)}</b> <code>v{m.version}</code> {src} [{cc}cmd{sc}{deps}]\n"
                for cn in m.commands:
                    t += f"   └ <code>{html_escape(p + cn)}</code>\n"
                if reqs:
                    t += f"   {CE.PACKAGE} <code>{', '.join(reqs)}</code>\n"
            t += f"\n{CE.CHART} {len(um)} модулей, {tc} команд"
        await safe_edit(event, truncate(t))

    async def cmd_pip(event):
        a = event.raw_text.split(maxsplit=2)
        if len(a) < 2:
            await safe_edit(event,
                f"{CE.PACKAGE} <b>Управление пакетами</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"<code>{p}pip install &lt;pkg&gt;</code> — установить\n"
                f"<code>{p}pip uninstall &lt;pkg&gt;</code> — удалить\n"
                f"<code>{p}pip check &lt;pkg&gt;</code> — проверить\n"
                f"<code>{p}pip search &lt;pkg&gt;</code> — версия пакета\n"
                f"<code>{p}pip list</code> — установленные (pip list)\n"
                f"<code>{p}pip deps &lt;модуль&gt;</code> — зависимости модуля\n"
            )
            return

        sub = a[1].lower()

        if sub == "install":
            if len(a) < 3:
                await safe_edit(event, f"{CE.CROSS} <code>{p}pip install &lt;pkg&gt;</code>")
                return
            pkg = a[2].strip()
            if is_package_installed(pkg):
                await safe_edit(event, f"{CE.CHECK} <code>{html_escape(pkg)}</code> уже установлен")
                return
            await safe_edit(event, f"{CE.DOWNLOAD} Устанавливаю <code>{html_escape(pkg)}</code>...")
            ok, msg = await async_install_pip_package(pkg)
            if ok:
                await safe_edit(event, f"{CE.CHECK} <code>{html_escape(pkg)}</code> установлен!")
            else:
                await safe_edit(event, f"{CE.CROSS} {html_escape(msg)}")

        elif sub == "uninstall":
            if len(a) < 3:
                await safe_edit(event, f"{CE.CROSS} <code>{p}pip uninstall &lt;pkg&gt;</code>")
                return
            pkg = a[2].strip()
            await safe_edit(event, f"{CE.TRASH} Удаляю <code>{html_escape(pkg)}</code>...")
            ok, msg = uninstall_pip_package(pkg)
            if ok:
                await safe_edit(event, f"{CE.CHECK} <code>{html_escape(pkg)}</code> удалён")
            else:
                await safe_edit(event, f"{CE.CROSS} {html_escape(msg)}")

        elif sub == "check":
            if len(a) < 3:
                await safe_edit(event, f"{CE.CROSS} <code>{p}pip check &lt;pkg&gt;</code>")
                return
            pkg = a[2].strip()
            installed = is_package_installed(pkg)
            status = "✅ установлен" if installed else "❌ не установлен"
            ver = ""
            if installed:
                try:
                    from importlib.metadata import version as get_version
                    base = re.split(r'[><=!~]', pkg)[0].strip()
                    ver = f" <code>v{get_version(base)}</code>"
                except Exception:
                    pass
            await safe_edit(event, f"{CE.PACKAGE} <code>{html_escape(pkg)}</code>: {status}{ver}")

        elif sub == "search":
            if len(a) < 3:
                await safe_edit(event, f"{CE.CROSS} <code>{p}pip search &lt;pkg&gt;</code>")
                return
            pkg = a[2].strip()
            try:
                from importlib.metadata import version as get_version, metadata
                base = re.split(r'[><=!~]', pkg)[0].strip()
                ver = get_version(base)
                meta = metadata(base)
                summary = meta.get("Summary", "—")
                author = meta.get("Author", "—")
                await safe_edit(event,
                    f"{CE.PACKAGE} <b>{html_escape(base)}</b> <code>v{ver}</code>\n"
                    f"📝 {html_escape(summary)}\n{CE.USER} {html_escape(author)}"
                )
            except Exception:
                await safe_edit(event, f"{CE.CROSS} <code>{html_escape(pkg)}</code> не найден или не установлен")

        elif sub == "list":
            await safe_edit(event, f"{CE.PACKAGE} Загрузка...")
            try:
                proc = await asyncio.create_subprocess_exec(
                    sys.executable, "-m", "pip", "list", "--format=columns",
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
                output = stdout.decode().strip()
                lines = output.split("\n")
                count = max(0, len(lines) - 2)
                if len(output) > 3500:
                    output = "\n".join(lines[:50]) + f"\n\n... и ещё {count - 48} пакетов"
                await safe_edit(event, f"{CE.PACKAGE} <b>Пакеты</b> ({count}):\n<pre>{html_escape(output)}</pre>")
            except Exception as e:
                await safe_edit(event, f"{CE.CROSS} {html_escape(str(e))}")

        elif sub == "deps":
            if len(a) < 3:
                await safe_edit(event, f"{CE.CROSS} <code>{p}pip deps &lt;модуль&gt;</code>")
                return
            mod_name = a[2].strip().lower()
            mod_obj = bot.module_manager.modules.get(mod_name)
            inst = bot.config.get("installed_modules", {})
            info = inst.get(mod_name, {})
            reqs = info.get("requirements", [])
            if mod_obj and mod_obj.requirements:
                reqs = mod_obj.requirements
            if not reqs:
                fp = Path(MODULES_DIR) / f"{mod_name}.py"
                if fp.exists():
                    content = fp.read_text(encoding="utf-8", errors="replace")
                    reqs = parse_module_requirements(content)
            if not reqs:
                await safe_edit(event, f"{CE.PACKAGE} <code>{html_escape(mod_name)}</code>: зависимостей нет")
                return
            t = f"{CE.PACKAGE} <b>{html_escape(mod_name)}</b> — зависимости:\n━━━━━━━━━━━━━━━━━━━━━\n\n"
            for r in reqs:
                installed = is_package_installed(r)
                icon = "✅" if installed else "❌"
                ver = ""
                if installed:
                    try:
                        from importlib.metadata import version as get_version
                        base = re.split(r'[><=!~]', r)[0].strip()
                        ver = f" <code>v{get_version(base)}</code>"
                    except Exception:
                        pass
                t += f"  {icon} <code>{html_escape(r)}</code>{ver}\n"
            await safe_edit(event, t)

        else:
            await safe_edit(event, f"{CE.CROSS} Неизвестная подкоманда: <code>{html_escape(sub)}</code>")

    async def cmd_fcfg(event):
        args = event.raw_text.split()
        if len(args) < 2:
            t = (
                f"{CE.GEAR} <b>Управление настройками модулей</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"<code>{p}fcfg set -m &lt;модуль&gt; &lt;параметр&gt; &lt;значение&gt;</code> — установить\n"
                f"<code>{p}fcfg remove -m &lt;модуль&gt; &lt;параметр&gt;</code> — удалить\n"
                f"<code>{p}fcfg reset -m &lt;модуль&gt;</code> — сбросить все настройки модуля\n\n"
                f"<b>Пример:</b>\n"
                f"<code>{p}fcfg set -m mymod greeting Привет!</code>\n"
                f"<code>{p}fcfg remove -m mymod greeting</code>\n"
                f"<code>{p}fcfg reset -m mymod</code>\n"
            )
            await safe_edit(event, t)
            return

        action = args[1].lower()

        if action not in ("set", "remove", "reset"):
            await safe_edit(event, f"{CE.CROSS} Неизвестный аргумент: <code>{html_escape(action)}</code>\nДопустимо: <code>set</code>, <code>remove</code>, <code>reset</code>")
            return

        if "-m" not in args:
            await safe_edit(event, f"{CE.CROSS} Укажите модуль: <code>-m &lt;название_модуля&gt;</code>")
            return

        m_index = args.index("-m")
        if m_index + 1 >= len(args):
            await safe_edit(event, f"{CE.CROSS} После <code>-m</code> укажите название модуля")
            return

        mod_name = args[m_index + 1]

        mod_obj = bot.module_manager.modules.get(mod_name)
        if not mod_obj:
            for mn in bot.module_manager.modules:
                if mn.lower() == mod_name.lower():
                    mod_name = mn
                    mod_obj = bot.module_manager.modules[mn]
                    break

        if not mod_obj:
            available = ", ".join(f"<code>{html_escape(n)}</code>" for n in bot.module_manager.modules)
            await safe_edit(event, f"{CE.CROSS} Модуль <code>{html_escape(mod_name)}</code> не найден\n\n{CE.PACKAGE} Доступные: {available}")
            return

        remaining = args[m_index + 2:]

        if action == "set":
            if len(remaining) < 2:
                if mod_obj.settings_schema:
                    t = f"{CE.GEAR} <b>Настройки <code>{html_escape(mod_name)}</code>:</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
                    custom = bot.config.data.get("custom_settings", {})
                    for s in mod_obj.settings_schema:
                        fk = f"{mod_name}.{s['key']}"
                        cur = custom.get(fk, s.get("default", "—"))
                        stype = s.get("type", "str")
                        desc = s.get("description", "")
                        t += f"  <code>{html_escape(s['key'])}</code> = <code>{html_escape(str(cur))}</code> ({stype})\n"
                        if s.get("label"):
                            t += f"    📝 {html_escape(s['label'])}\n"
                        if desc:
                            t += f"    ℹ️ <i>{html_escape(desc)}</i>\n"
                    t += f"\n{CE.BULB} <code>{p}fcfg set -m {html_escape(mod_name)} &lt;параметр&gt; &lt;значение&gt;</code>"
                    await safe_edit(event, t)
                else:
                    await safe_edit(event,
                        f"{CE.CROSS} <code>{p}fcfg set -m {html_escape(mod_name)} &lt;параметр&gt; &lt;значение&gt;</code>\n\n"
                        f"{CE.WARN} У модуля <code>{html_escape(mod_name)}</code> нет объявленных настроек (settings_schema),\n"
                        f"но вы всё равно можете задать произвольный параметр."
                    )
                return

            param = remaining[0]
            raw = event.raw_text
            param_pos = raw.find(param, raw.find(mod_name) + len(mod_name))
            if param_pos != -1:
                value = raw[param_pos + len(param):].strip()
            else:
                value = " ".join(remaining[1:])

            if not value:
                await safe_edit(event, f"{CE.CROSS} Укажите значение: <code>{p}fcfg set -m {html_escape(mod_name)} {html_escape(param)} &lt;значение&gt;</code>")
                return

            schema_entry = None
            if mod_obj.settings_schema:
                for s in mod_obj.settings_schema:
                    if s["key"] == param:
                        schema_entry = s
                        break

            if schema_entry:
                stype = schema_entry.get("type", "str")
                try:
                    if stype == "int":
                        int(value)
                    elif stype == "float":
                        float(value)
                    elif stype == "bool":
                        if value.lower() not in ("true", "false", "1", "0", "yes", "no", "да", "нет", "on", "off"):
                            await safe_edit(event,
                                f"{CE.CROSS} Параметр <code>{html_escape(param)}</code> имеет тип <code>bool</code>\n"
                                f"Допустимые значения: <code>true/false</code>, <code>1/0</code>, <code>yes/no</code>, <code>on/off</code>"
                            )
                            return
                except ValueError:
                    await safe_edit(event, f"{CE.CROSS} Параметр <code>{html_escape(param)}</code> должен быть типа <code>{stype}</code>, получено: <code>{html_escape(value)}</code>")
                    return

            module_config_set(bot, mod_name, param, value)

            saved = bot.config.data.get("custom_settings", {}).get(f"{mod_name}.{param}")
            label = ""
            if schema_entry and schema_entry.get("label"):
                label = f" ({html_escape(schema_entry['label'])})"

            if saved == value:
                await safe_edit(event, f"{CE.CHECK} <code>{html_escape(mod_name)}.{html_escape(param)}</code>{label} = <code>{html_escape(value)}</code>")
            else:
                await safe_edit(event, f"{CE.WARN} Ошибка сохранения <code>{html_escape(mod_name)}.{html_escape(param)}</code>")

        elif action == "remove":
            if len(remaining) < 1:
                await safe_edit(event, f"{CE.CROSS} <code>{p}fcfg remove -m {html_escape(mod_name)} &lt;параметр&gt;</code>")
                return

            param = remaining[0]
            full_key = f"{mod_name}.{param}"
            custom = dict(bot.config.data.get("custom_settings", {}))

            if full_key not in custom:
                await safe_edit(event, f"{CE.CROSS} Параметр <code>{html_escape(full_key)}</code> не установлен в custom_settings")
                return

            del custom[full_key]
            bot.config.data["custom_settings"] = custom
            bot.config.save()

            default_val = None
            if mod_obj.settings_schema:
                for s in mod_obj.settings_schema:
                    if s["key"] == param:
                        default_val = s.get("default")
                        break

            msg = f"{CE.CHECK} Параметр <code>{html_escape(full_key)}</code> удалён из настроек"
            if default_val is not None:
                msg += f"\n{CE.FILE} Значение по умолчанию: <code>{html_escape(str(default_val))}</code>"
            await safe_edit(event, msg)

        elif action == "reset":
            custom = dict(bot.config.data.get("custom_settings", {}))
            prefix_key = f"{mod_name}."
            keys_to_remove = [k for k in custom if k.startswith(prefix_key)]

            if not keys_to_remove:
                await safe_edit(event, f"ℹ️ У модуля <code>{html_escape(mod_name)}</code> нет пользовательских настроек для сброса")
                return

            for k in keys_to_remove:
                del custom[k]

            bot.config.data["custom_settings"] = custom
            bot.config.save()

            await safe_edit(event,
                f"{CE.CHECK} Сброшено <b>{len(keys_to_remove)}</b> настроек модуля <code>{html_escape(mod_name)}</code>:\n"
                + "\n".join(f"  {CE.TRASH} <code>{html_escape(k)}</code>" for k in keys_to_remove)
            )

    mod.commands = {
        "alive": Command("alive", cmd_alive, "Проверка", "core", f"{p}alive"),
        "kinfo": Command("kinfo", cmd_kinfo, "Инфо-карточка", "core", f"{p}kinfo"),
        "kset": Command("kset", cmd_kset, "Настройки kinfo", "core", f"{p}kset <sub>"),
        "help": Command("help", cmd_help, "Помощь", "core", f"{p}help [cmd]"),
        "ping": Command("ping", cmd_ping, "Пинг", "core", f"{p}ping"),
        "prefix": Command("prefix", cmd_prefix, "Префикс", "core", f"{p}prefix <new>"),
        "modules": Command("modules", cmd_modules, "Модули", "core", f"{p}modules"),
        "reload": Command("reload", cmd_reload, "Перезагрузка", "core", f"{p}reload"),
        "eval": Command("eval", cmd_eval, "Eval", "core", f"{p}eval <code>"),
        "exec": Command("exec", cmd_exec, "Exec", "core", f"{p}exec <code>"),
        "settings": Command("settings", cmd_settings, "Inline панель", "core", f"{p}settings"),
        "settoken": Command("settoken", cmd_settoken, "Bot token", "core", f"{p}settoken"),
        "status": Command("status", cmd_status, "Статус", "core", f"{p}status"),
        "im": Command("im", cmd_im, "Установить (файл)", "core", f"{p}im"),
        "um": Command("um", cmd_um, "Удалить модуль", "core", f"{p}um <name>"),
        "dlm": Command("dlm", cmd_dlm, "Скачать (URL)", "core", f"{p}dlm <url>"),
        "lm": Command("lm", cmd_lm, "Польз. модули", "core", f"{p}lm"),
        "pip": Command("pip", cmd_pip, "Управление пакетами", "core", f"{p}pip <sub>"),
        "fcfg": Command("fcfg", cmd_fcfg, "Настройки модулей", "core", f"{p}fcfg <set/remove/reset> -m <module> [param] [value]"),
    }

    bot.module_manager.register_module(mod)
    bot.module_manager.mark_builtin("core")
    bot.register_commands(mod)


def load_tools_module(bot: "Userbot"):
    mod = Module(name="tools", description="Инструменты", author=BRAND_NAME, version="1.0")
    p = bot.config.prefix

    async def cmd_id(event):
        t = f"{CE.ID}\n━━━━━━━━━━━━━━━━━━━━━\n{CE.CHAT} <code>{event.chat_id}</code>\n"
        if event.is_reply:
            r = await event.get_reply_message()
            u = await r.get_sender()
            t += f"{CE.USER} <code>{r.sender_id}</code>\n"
            if u:
                t += f"📛 {html_escape(u.first_name or '')}\n"
                if u.username:
                    t += f"{CE.LINK} @{u.username}\n"
            t += f"{CE.CHAT} <code>{r.id}</code>\n"
        else:
            t += f"{CE.USER} <code>{event.sender_id}</code>\n"
        await safe_edit(event, t)

    async def cmd_info(event):
        if event.is_reply:
            uid = (await event.get_reply_message()).sender_id
        else:
            a = event.raw_text.split(maxsplit=1)
            if len(a) > 1:
                try:
                    uid = (await bot.client.get_entity(a[1].strip())).id
                except Exception:
                    await safe_edit(event, f"{CE.CROSS} Не найден")
                    return
            else:
                uid = event.sender_id
        try:
            f = await bot.client(GetFullUserRequest(uid))
            u, fu = f.users[0], f.full_user
        except Exception as e:
            await safe_edit(event, f"{CE.CROSS} {html_escape(str(e))}")
            return
        t = (
            f"{CE.USER} <b>Инфо</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📛 {html_escape(u.first_name or '')} {html_escape(u.last_name or '')}\n{CE.ID} <code>{u.id}</code>\n"
            f"📱 @{u.username or '—'}\n{CE.BOT} {'Да' if u.bot else 'Нет'}\n"
            f"{CE.STAR} {'Да' if getattr(u, 'premium', False) else 'Нет'}\n"
        )
        if fu.about:
            t += f"📝 <i>{html_escape(fu.about)}</i>\n"
        if fu.common_chats_count:
            t += f"👥 {fu.common_chats_count}\n"
        await safe_edit(event, t)

    async def cmd_del(event):
        if event.is_reply:
            try:
                await (await event.get_reply_message()).delete()
            except Exception:
                pass
        await event.delete()

    async def cmd_purge(event):
        if not event.is_reply:
            await safe_edit(event, f"{CE.CROSS} Reply")
            return
        r = await event.get_reply_message()
        c = 0
        async for m in bot.client.iter_messages(event.chat_id, min_id=r.id - 1, max_id=event.id):
            try:
                await m.delete()
                c += 1
            except Exception:
                pass
        await event.delete()
        tmp = await safe_send(bot.client, event.chat_id, f"{CE.TRASH} {c}")
        await asyncio.sleep(3)
        await tmp.delete()

    async def cmd_chatinfo(event):
        ch = await event.get_chat()
        if isinstance(ch, User):
            await safe_edit(event, f"{CE.CROSS} Не чат")
            return
        t = f"{CE.CHAT} <b>{html_escape(ch.title)}</b>\n━━━━━━━━━━━━━━━━━━━━━\n{CE.ID} <code>{ch.id}</code>\n"
        if hasattr(ch, "username") and ch.username:
            t += f"{CE.LINK} @{ch.username}\n"
        if isinstance(ch, Channel):
            try:
                fc = (await bot.client(GetFullChannelRequest(ch))).full_chat
                t += f"👥 {fc.participants_count or '?'}\n"
                if fc.about:
                    t += f"📝 <i>{html_escape(fc.about[:80])}</i>\n"
            except Exception:
                pass
            t += f"📢 {'Канал' if ch.broadcast else 'Супергруппа'}\n"
        await safe_edit(event, t)

    async def cmd_calc(event):
        a = event.raw_text.split(maxsplit=1)
        if len(a) < 2:
            await safe_edit(event, f"{CE.CROSS} <code>{p}calc 2+2</code>")
            return
        expr = a[1].strip()
        if not all(c in "0123456789+-*/().% " for c in expr):
            await safe_edit(event, f"{CE.CROSS} Недопустимые символы!")
            return
        try:
            await safe_edit(event, f"{CE.CALC} <code>{html_escape(expr)}</code> = <b>{eval(expr)}</b>")
        except Exception as e:
            await safe_edit(event, f"{CE.CROSS} {html_escape(str(e))}")

    async def cmd_sd(event):
        a = event.raw_text.split(maxsplit=1)
        if len(a) < 2:
            await safe_edit(event, f"{CE.CROSS} <code>{p}sd &lt;сек&gt; &lt;текст&gt;</code>")
            return
        pts = a[1].split(maxsplit=1)
        try:
            delay = int(pts[0])
            txt = pts[1] if len(pts) > 1 else "💨"
        except (ValueError, IndexError):
            await safe_edit(event, f"{CE.CROSS} <code>{p}sd &lt;сек&gt; &lt;текст&gt;</code>")
            return
        await safe_edit(event, f"{html_escape(txt)}\n{CE.CLOCK} ~{delay}с")
        await asyncio.sleep(delay)
        await event.delete()

    async def cmd_search(event):
        a = event.raw_text.split(maxsplit=1)
        if len(a) < 2:
            await safe_edit(event, f"{CE.CROSS} <code>{p}search &lt;q&gt;</code>")
            return
        q = a[1].strip()
        await safe_edit(event, f"{CE.SEARCH} <code>{html_escape(q)}</code>...")
        rs = []
        async for m in bot.client.iter_messages(event.chat_id, search=q, limit=10):
            s = await m.get_sender()
            rs.append(f"  <code>{m.id}</code> <b>{html_escape(s.first_name if s else '?')}</b>: <i>{html_escape((m.text or '[медиа]')[:35])}</i>")
        t = f"{CE.SEARCH} <code>{html_escape(q)}</code>\n━━━━━━━━━━━━━━━━━━━━━\n\n" + ("\n".join(rs) if rs else "Ничего")
        await safe_edit(event, truncate(t))

    mod.commands = {
        "id": Command("id", cmd_id, "ID", "tools", f"{p}id"),
        "info": Command("info", cmd_info, "Инфо", "tools", f"{p}info"),
        "del": Command("del", cmd_del, "Удалить", "tools", f"{p}del"),
        "purge": Command("purge", cmd_purge, "Purge", "tools", f"{p}purge"),
        "chatinfo": Command("chatinfo", cmd_chatinfo, "Чат инфо", "tools", f"{p}chatinfo"),
        "calc": Command("calc", cmd_calc, "Калькулятор", "tools", f"{p}calc"),
        "sd": Command("sd", cmd_sd, "Самоуничтожение", "tools", f"{p}sd <с> <txt>"),
        "search": Command("search", cmd_search, "Поиск", "tools", f"{p}search <q>"),
    }
    bot.module_manager.register_module(mod)
    bot.module_manager.mark_builtin("tools")
    bot.register_commands(mod)


def load_fun_module(bot: "Userbot"):
    mod = Module(name="fun", description="Развлечения", author=BRAND_NAME, version="1.0")
    p = bot.config.prefix

    async def _gt(event):
        a = event.raw_text.split(maxsplit=1)
        if len(a) > 1:
            return a[1]
        if event.is_reply:
            r = await event.get_reply_message()
            return r.text or ""
        return None

    async def cmd_reverse(event):
        t = await _gt(event)
        if not t:
            await safe_edit(event, f"{CE.CROSS} <code>{p}reverse &lt;txt&gt;</code>")
            return
        await safe_edit(event, html_escape(t[::-1]))

    async def cmd_upper(event):
        t = await _gt(event)
        if not t:
            await safe_edit(event, f"{CE.CROSS} <code>{p}upper &lt;txt&gt;</code>")
            return
        await safe_edit(event, html_escape(t.upper()))

    async def cmd_lower(event):
        t = await _gt(event)
        if not t:
            await safe_edit(event, f"{CE.CROSS} <code>{p}lower &lt;txt&gt;</code>")
            return
        await safe_edit(event, html_escape(t.lower()))

    async def cmd_mock(event):
        t = await _gt(event)
        if not t:
            await safe_edit(event, f"{CE.CROSS} <code>{p}mock &lt;txt&gt;</code>")
            return
        import random
        result = "".join(c.upper() if random.random() > .5 else c.lower() for c in t)
        await safe_edit(event, html_escape(result))

    async def cmd_repeat(event):
        a = event.raw_text.split(maxsplit=2)
        if len(a) < 3:
            await safe_edit(event, f"{CE.CROSS} <code>{p}repeat &lt;n&gt; &lt;txt&gt;</code>")
            return
        try:
            n = min(int(a[1]), 50)
        except ValueError:
            await safe_edit(event, f"{CE.CROSS} Число!")
            return
        await safe_edit(event, truncate(html_escape("\n".join([a[2]] * n))))

    async def cmd_type(event):
        a = event.raw_text.split(maxsplit=1)
        if len(a) < 2:
            await safe_edit(event, f"{CE.CROSS} <code>{p}type &lt;txt&gt;</code>")
            return
        typed = ""
        for c in a[1][:100]:
            typed += c
            try:
                await event.edit(typed + "▌")
                await asyncio.sleep(0.05)
            except FloodWaitError as e:
                await asyncio.sleep(e.seconds)
        await event.edit(typed)

    async def cmd_dice(event):
        import random
        a = event.raw_text.split(maxsplit=1)
        s = 6
        if len(a) > 1:
            try:
                s = int(a[1])
            except ValueError:
                pass
        r = random.randint(1, max(s, 2))
        await safe_edit(event, f"{CE.DICE} d{s}: <b>{r}</b>")

    async def cmd_coin(event):
        import random
        await safe_edit(event, random.choice([f"{CE.COIN} Орёл!", f"{CE.COIN} Решка!"]))

    async def cmd_choose(event):
        import random
        a = event.raw_text.split(maxsplit=1)
        if len(a) < 2 or "|" not in a[1]:
            await safe_edit(event, f"{CE.CROSS} <code>{p}choose a | b | c</code>")
            return
        opts = [o.strip() for o in a[1].split("|") if o.strip()]
        if not opts:
            await safe_edit(event, f"{CE.CROSS} Пусто")
            return
        await safe_edit(event, f"{CE.TARGET} {html_escape(random.choice(opts))}")

    async def cmd_rate(event):
        import random
        a = event.raw_text.split(maxsplit=1)
        thing = a[1] if len(a) > 1 else "это"
        sc = random.randint(0, 100)
        bar = "█" * (sc // 10) + "░" * (10 - sc // 10)
        await safe_edit(event, f"{CE.CHART} <b>{html_escape(thing)}</b>\n[{bar}] {sc}%")

    mod.commands = {
        "reverse": Command("reverse", cmd_reverse, "Реверс", "fun", f"{p}reverse"),
        "upper": Command("upper", cmd_upper, "UPPER", "fun", f"{p}upper"),
        "lower": Command("lower", cmd_lower, "lower", "fun", f"{p}lower"),
        "mock": Command("mock", cmd_mock, "мОк", "fun", f"{p}mock"),
        "repeat": Command("repeat", cmd_repeat, "Повтор", "fun", f"{p}repeat"),
        "type": Command("type", cmd_type, "Печать", "fun", f"{p}type"),
        "dice": Command("dice", cmd_dice, "Кубик", "fun", f"{p}dice"),
        "coin": Command("coin", cmd_coin, "Монета", "fun", f"{p}coin"),
        "choose": Command("choose", cmd_choose, "Выбор", "fun", f"{p}choose"),
        "rate": Command("rate", cmd_rate, "Оценка", "fun", f"{p}rate"),
    }
    bot.module_manager.register_module(mod)
    bot.module_manager.mark_builtin("fun")
    bot.register_commands(mod)


def load_admin_module(bot: "Userbot"):
    mod = Module(name="admin", description="Администрирование", author=BRAND_NAME, version="1.0")
    p = bot.config.prefix

    async def _admin_action(event, action_fn, success_msg):
        if not event.is_reply:
            await safe_edit(event, f"{CE.CROSS} Reply")
            return
        r = await event.get_reply_message()
        try:
            await action_fn(r)
            u = await r.get_sender()
            await safe_edit(event, f"{success_msg} <b>{html_escape(u.first_name)}</b>!")
        except (UserAdminInvalidError, ChatAdminRequiredError):
            await safe_edit(event, f"{CE.CROSS} Нет прав!")
        except Exception as e:
            await safe_edit(event, f"{CE.CROSS} {html_escape(str(e))}")

    async def cmd_ban(event):
        async def do(r):
            from telethon.tl.functions.channels import EditBannedRequest
            from telethon.tl.types import ChatBannedRights
            await bot.client(EditBannedRequest(event.chat_id, r.sender_id,
                ChatBannedRights(until_date=None, view_messages=True)))
        await _admin_action(event, do, CE.HAMMER)

    async def cmd_unban(event):
        async def do(r):
            from telethon.tl.functions.channels import EditBannedRequest
            from telethon.tl.types import ChatBannedRights
            await bot.client(EditBannedRequest(event.chat_id, r.sender_id,
                ChatBannedRights(until_date=None)))
        await _admin_action(event, do, CE.CHECK)

    async def cmd_kick(event):
        async def do(r):
            await bot.client.kick_participant(event.chat_id, r.sender_id)
        await _admin_action(event, do, CE.BOOT)

    async def cmd_mute(event):
        if not event.is_reply:
            await safe_edit(event, f"{CE.CROSS} Reply")
            return
        r = await event.get_reply_message()
        a = event.raw_text.split(maxsplit=1)
        dur = None
        if len(a) > 1:
            v = a[1].strip()
            try:
                if v.endswith("m"):
                    dur = timedelta(minutes=int(v[:-1]))
                elif v.endswith("h"):
                    dur = timedelta(hours=int(v[:-1]))
                elif v.endswith("d"):
                    dur = timedelta(days=int(v[:-1]))
                else:
                    dur = timedelta(minutes=int(v))
            except ValueError:
                pass
        try:
            from telethon.tl.functions.channels import EditBannedRequest
            from telethon.tl.types import ChatBannedRights
            until = datetime.now() + dur if dur else None
            await bot.client(EditBannedRequest(event.chat_id, r.sender_id,
                ChatBannedRights(until_date=until, send_messages=True, send_media=True,
                    send_stickers=True, send_gifs=True)))
            u = await r.get_sender()
            await safe_edit(event, f"{CE.MUTE} <b>{html_escape(u.first_name)}</b>!")
        except Exception as e:
            await safe_edit(event, f"{CE.CROSS} {html_escape(str(e))}")

    async def cmd_unmute(event):
        await cmd_unban(event)

    async def cmd_pin(event):
        if not event.is_reply:
            await safe_edit(event, f"{CE.CROSS} Reply")
            return
        try:
            await bot.client.pin_message(event.chat_id, (await event.get_reply_message()).id)
            await safe_edit(event, f"{CE.PIN}!")
        except Exception as e:
            await safe_edit(event, f"{CE.CROSS} {html_escape(str(e))}")

    async def cmd_unpin(event):
        try:
            await bot.client.unpin_message(event.chat_id)
            await safe_edit(event, f"{CE.PIN} Откреплено")
        except Exception as e:
            await safe_edit(event, f"{CE.CROSS} {html_escape(str(e))}")

    mod.commands = {
        "ban": Command("ban", cmd_ban, "Бан", "admin", f"{p}ban"),
        "unban": Command("unban", cmd_unban, "Разбан", "admin", f"{p}unban"),
        "kick": Command("kick", cmd_kick, "Кик", "admin", f"{p}kick"),
        "mute": Command("mute", cmd_mute, "Мут", "admin", f"{p}mute [time]"),
        "unmute": Command("unmute", cmd_unmute, "Размут", "admin", f"{p}unmute"),
        "pin": Command("pin", cmd_pin, "Пин", "admin", f"{p}pin"),
        "unpin": Command("unpin", cmd_unpin, "Анпин", "admin", f"{p}unpin"),
    }
    bot.module_manager.register_module(mod)
    bot.module_manager.mark_builtin("admin")
    bot.register_commands(mod)


# ──────────────────────── Главный класс ──────────────────────


class Userbot:
    def __init__(self, config: Config):
        self.config = config
        self.client: Optional[TelegramClient] = None
        self.module_manager = ModuleManager(self)
        self.inline_panel = InlinePanel(self)
        self.start_time = time.time()
        self._command_handlers: Dict[str, Command] = {}

    def register_commands(self, module: Module):
        for cn, cmd in module.commands.items():
            self._command_handlers[cn] = cmd

    async def build_kinfo_text(self, ping_start: float = None) -> str:
        ki = self.config.data.get("kinfo", {})
        template = ki.get("template") or get_default_kinfo_template()
        emoji = ki.get("emoji", BRAND_EMOJI)
        if ping_start:
            ping = f"{(time.time() - ping_start) * 1000:.1f}"
        else:
            s = time.time()
            await self.client.get_me()
            ping = f"{(time.time() - s) * 1000:.1f}"
        me = await self.client.get_me()
        um = len(self.module_manager.get_user_modules())
        tm = len(self.module_manager.modules)
        bi = tm - um
        custom_lines_list = ki.get("custom_lines", [])
        custom_lines_text = ""
        if custom_lines_list:
            for line in custom_lines_list:
                custom_lines_text += f"├ {line}\n"
        vars_dict = {
            "emoji": emoji, "brand": BRAND_NAME, "version": BRAND_VERSION,
            "owner": await get_user_link(me), "ping": ping,
            "uptime": format_uptime(time.time() - self.start_time),
            "modules": str(tm), "builtin": str(bi), "user_mods": str(um),
            "commands": str(len(self._command_handlers)),
            "prefix": html_escape(self.config.prefix),
            "python": platform.python_version(),
            "telethon": telethon_version.__version__,
            "os": f"{platform.system()} {platform.release()}",
            "custom_lines": custom_lines_text,
        }
        try:
            text = template.format(**vars_dict)
        except (KeyError, IndexError, ValueError):
            text = get_default_kinfo_template().format(**vars_dict)
        lines = text.split("\n")
        filtered = []
        hide_map = {
            "show_ping": "ping", "show_uptime": "uptime", "show_modules": "modules",
            "show_commands": "commands", "show_prefix": "prefix", "show_python": "python",
            "show_telethon": "telethon", "show_os": "os", "show_owner": "owner",
        }
        for line in lines:
            skip = False
            for toggle_key, var_name in hide_map.items():
                if not ki.get(toggle_key, True):
                    val = vars_dict.get(var_name, "")
                    if val and val in line and len(val) > 2:
                        skip = True
                        break
            if not skip:
                filtered.append(line)
        return "\n".join(filtered)

    async def _handle_command(self, event):
        text = event.raw_text
        pfx = self.config.prefix
        if not text or not text.startswith(pfx):
            return
        parts = text[len(pfx):].split(maxsplit=1)
        if not parts:
            return
        cn = parts[0].lower()
        cmd = self._command_handlers.get(cn)
        if cmd:
            stats = self.config.data.get("stats", {})
            stats["commands_used"] = stats.get("commands_used", 0) + 1
            self.config.data["stats"] = stats
            self.config.save()
            try:
                await cmd.handler(event)
            except Exception as e:
                log.error(f"{cn}: {e}")
                traceback.print_exc()
                try:
                    await safe_edit(event, f"{CE.CROSS} <code>{html_escape(cn)}</code>: <code>{html_escape(str(e))}</code>")
                except Exception:
                    pass

    async def start(self):
        global _HAS_PREMIUM

        self.client = TelegramClient("kub_session", self.config.api_id, self.config.api_hash)
        await self.client.start(phone=self.config.phone)
        me = await self.client.get_me()
        self.config.set("owner_id", me.id)

        # ──── Определяем Premium-статус и переинициализируем CE ────
        _HAS_PREMIUM = getattr(me, "premium", False) or False
        _reinit_custom_emoji()

        if _HAS_PREMIUM:
            log.info(f"⭐ Premium обнаружен — custom emoji включены")
        else:
            log.info(f"ℹ️ Premium не обнаружен — обычные эмодзи")

        # Устанавливаем дефолтные шаблоны если не заданы
        if not self.config.alive_message:
            self.config.data["alive_message"] = get_default_alive_msg()
        if not self.config.data.get("kinfo", {}).get("template"):
            self.config.data.setdefault("kinfo", {})["template"] = get_default_kinfo_template()
            self.config.save()

        log.info(f"👤 {me.first_name} (ID: {me.id})")

        self.client.add_event_handler(self._handle_command, events.NewMessage(outgoing=True))

        load_core_module(self)
        load_tools_module(self)
        load_fun_module(self)
        load_admin_module(self)
        self.module_manager.load_from_directory()

        await self.inline_panel.start()

        self.start_time = time.time()
        self.config.data.setdefault("stats", {})["started_at"] = time.time()
        self.config.save()

        um = len(self.module_manager.get_user_modules())
        tm = len(self.module_manager.modules)

        log.info("━" * 45)
        log.info(f"{BRAND_EMOJI} {BRAND_NAME} v{BRAND_VERSION}")
        log.info(f"📦 {tm} модулей (🔵{tm - um} 🟢{um}) | 🔧 {len(self._command_handlers)} команд")
        log.info(f"🔑 {self.config.prefix}")
        if self.inline_panel.active:
            ib = await self.inline_panel.inline_bot.get_me()
            log.info(f"🤖 @{ib.username}")
        else:
            log.info(f"💡 {self.config.prefix}settoken")
        log.info("━" * 45)

        await self.client.run_until_disconnected()


# ──────────────────────── Setup ──────────────────────────


def initial_setup() -> Config:
    config = Config()
    if config.api_id and config.api_hash and config.phone:
        return config
    print(BANNER)
    print("  📋 Настройка\n  1️⃣  https://my.telegram.org\n")
    while True:
        try:
            api_id = int(input(f"  {BRAND_EMOJI} API ID: ").strip())
            break
        except ValueError:
            print("     ❌ Число!")
    api_hash = ""
    while not api_hash:
        api_hash = input(f"  {BRAND_EMOJI} API Hash: ").strip()
    phone = ""
    while not phone:
        phone = input(f"  {BRAND_EMOJI} Телефон: ").strip()
    print(f"\n  2️⃣  @BotFather → Inline Mode ON\n")
    bot_token = input(f"  {BRAND_EMOJI} Bot Token (Enter=skip): ").strip()
    prefix = input(f"\n  {BRAND_EMOJI} Префикс (Enter='.'): ").strip() or DEFAULT_PREFIX
    config.api_id = api_id
    config.api_hash = api_hash
    config.phone = phone
    config.bot_token = bot_token
    config.prefix = prefix
    config.alive_message = get_default_alive_msg()
    config.save()
    print(f"\n  ✅ Сохранено: {CONFIG_FILE}\n")
    return config


def main():
    print(BANNER)
    config = initial_setup()
    if not config.api_id or not config.api_hash:
        print("  ❌ API ID и Hash!")
        sys.exit(1)
    try:
        asyncio.run(Userbot(config).start())
    except KeyboardInterrupt:
        print(f"\n  👋 {BRAND_NAME} остановлен.\n")
    except Exception as e:
        log.error(f"Fatal: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
