# 📚 Module Development Documentation for kazhurkeUserBot v2.3.0

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Modular System Architecture](#2-modular-system-architecture)
3. [Quick Start: Minimal Module](#3-quick-start-minimal-module)
4. [Module Structure](#4-module-structure)
5. [The `setup(bot)` Function](#5-the-setupbot-function)
6. [Command Registration](#6-command-registration)
7. [Event Handlers](#7-event-handlers)
8. [Module Settings (settings_schema)](#8-module-settings-settings_schema)
9. [Module Dependencies](#9-module-dependencies)
10. [Module Lifecycle](#10-module-lifecycle)
11. [Available Objects and API](#11-available-objects-and-api)
12. [Userbot Utilities](#12-userbot-utilities)
13. [Working with Configuration](#13-working-with-configuration)
14. [Installing and Removing Modules](#14-installing-and-removing-modules)
15. [The `.fcfg` Command — Settings Management](#15-the-fcfg-command--settings-management)
16. [The `.pip` Command — Package Management](#16-the-pip-command--package-management)
17. [Built-in Modules](#17-built-in-modules)
18. [Module Examples](#18-module-examples)
19. [Recommendations and Best Practices](#19-recommendations-and-best-practices)
20. [Object Reference](#20-object-reference)
21. [FAQ](#21-faq)

---

## 1. Introduction

**kazhurkeUserBot** (KUB) is a single-file Telegram Userbot based on the **Telethon** library, supporting:

- Modular architecture with hot loading/unloading
- Inline control panel via a bot
- Automatic installation of module dependencies
- Flexible settings system for each module
- pip package management directly from Telegram

Modules are Python files (`.py`) placed in the `modules/` folder. On startup, the userbot automatically loads all modules from this folder, installing necessary dependencies.

---

## 2. Modular System Architecture

```
kazhurkeUserBot
├── kub_config.json          # Configuration
├── kub_session.session      # Telethon session (main account)
├── kub_inline_session.session # Inline bot session
├── modules/                 # User modules folder
│   ├── my_module.py
│   ├── weather.py
│   └── ...
└── main.py                  # Main userbot file
```

### Key Classes

| Class | Description |
|-------|-------------|
| `Userbot` | Main userbot class. Contains `client`, `config`, `module_manager`, `inline_panel` |
| `ModuleManager` | Module manager. Loading, unloading, installing, removing |
| `Module` | Module dataclass. Stores metadata, commands, handlers, settings |
| `Command` | Command dataclass. Name, handler, description, usage |
| `Config` | Configuration management (JSON file) |
| `InlinePanel` | Inline bot for managing the userbot via buttons |

### Loading Order

1. Load configuration (`kub_config.json`)
2. Connect Telethon client
3. Load built-in modules (`core`, `tools`, `fun`, `admin`)
4. Load user modules from `modules/`
5. Start inline bot (if configured)

---

## 3. Quick Start: Minimal Module

Create a file `modules/hello.py`:

```python
"""My first module for KUB."""

def setup(bot):
    """Module entry point."""
    from pathlib import Path
    
    # Create a module object
    mod = bot.module_manager.modules.get("hello")
    if not mod:
        # Use classes available through bot
        mod = type('Module', (), {
            'name': 'hello',
            'description': 'My first module',
            'author': 'MyName',
            'version': '1.0',
            'commands': {},
            'handlers': [],
            'on_load': None,
            'on_unload': None,
            'settings': {},
            'settings_schema': [],
            'requirements': [],
        })()

    async def cmd_hello(event):
        """Command .hello — greeting."""
        await event.edit("👋 Hello from my module!")

    # Register the command
    from dataclasses import dataclass
    
    cmd = type('Command', (), {
        'name': 'hello',
        'handler': cmd_hello,
        'description': 'Greeting',
        'module': 'hello',
        'usage': f'{bot.config.prefix}hello',
        'category': 'misc',
    })()

    mod.commands = {'hello': cmd}
    
    bot.module_manager.register_module(mod)
    bot.register_commands(mod)
```

However, this approach is verbose. Below is the **recommended approach** using imports of the necessary classes.

---

## 4. Module Structure

### Recommended Module Template

```python
# requires: aiohttp, Pillow
# -*- coding: utf-8 -*-
"""
Module description.
Author: YourName
Version: 1.0
"""

__requires__ = ["aiohttp", "Pillow>=9.0"]

# When loading the module, the userbot automatically injects into the namespace:
#   bot      — Userbot instance
#   client   — TelegramClient instance
#   config   — Config instance
#   manager  — ModuleManager instance
#   module_config(mod_name, key, default) — read setting
#   module_config_set(mod_name, key, value) — write setting


def setup(bot):
    """
    Entry point. Called when the module is loaded.
    
    Args:
        bot: Userbot instance
    """
    pass
```

### Injected Variables

When loading a module from a file (`_load_file`), the userbot automatically adds the following variables to the module's namespace:

| Variable | Type | Description |
|----------|------|-------------|
| `bot` | `Userbot` | Main userbot instance |
| `client` | `TelegramClient` | Telethon client (main account) |
| `config` | `Config` | Configuration object |
| `manager` | `ModuleManager` | Module manager |
| `module_config` | `Callable` | Settings read function: `module_config(mod_name, key, default)` |
| `module_config_set` | `Callable` | Settings write function: `module_config_set(mod_name, key, value)` |

These variables are available at the module level (globally within the file), so they can be used outside of `setup()` as well.

---

## 5. The `setup(bot)` Function

The `setup` function is the **entry point** of the module. If it is defined in the module file, the userbot will call it after executing the file, passing the `Userbot` instance.

```python
def setup(bot):
    """
    Called once when the module is loaded.
    
    Here you need to:
    1. Create a Module object
    2. Define commands (async functions)
    3. Create Command objects
    4. Register the module via bot.module_manager.register_module()
    5. Register commands via bot.register_commands()
    6. (Optionally) Add event handlers
    """
    pass
```

> **Important:** The `setup` function is **not** async. If you need to perform asynchronous operations during initialization, use `on_load` (see [Module Lifecycle](#10-module-lifecycle)).

---

## 6. Command Registration

### Creating Command and Module Objects

Since `Command` and `Module` are defined in the main userbot file, the module must create them accordingly. There are several approaches:

#### Approach 1: Using dataclass from the main file (recommended)

```python
from dataclasses import dataclass, field
from typing import Dict, List, Callable, Any, Optional


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
    commands: Dict[str, 'Command'] = field(default_factory=dict)
    handlers: List[Any] = field(default_factory=list)
    on_load: Optional[Callable] = None
    on_unload: Optional[Callable] = None
    settings: Dict[str, Any] = field(default_factory=dict)
    settings_schema: List[Dict] = field(default_factory=list)
    requirements: List[str] = field(default_factory=list)


def setup(bot):
    mod = Module(
        name="mymod",
        description="My module",
        author="MyName",
        version="1.0",
    )
    
    p = bot.config.prefix

    async def cmd_test(event):
        await event.edit("✅ It works!")

    mod.commands = {
        "test": Command("test", cmd_test, "Test command", "mymod", f"{p}test"),
    }

    bot.module_manager.register_module(mod)
    bot.register_commands(mod)
```

#### Approach 2: Compatible (without redefining dataclass)

If you want to avoid duplicating the `Command` and `Module` definitions, you can import them from the main module provided it is accessible. However, since the userbot is single-file, the simplest approach is to duplicate the definitions (they are small) or use the `type()` approach.

### Command Parameters

```python
@dataclass
class Command:
    name: str          # Command name (without prefix). Example: "test"
    handler: Callable  # Async handler function
    description: str   # Brief description for .help
    module: str        # Name of the owning module
    usage: str         # Usage example. Example: ".test <argument>"
    category: str      # Category: "misc", "admin", "fun", "tools", etc.
```

### Module Parameters

```python
@dataclass
class Module:
    name: str                    # Unique module name (matches filename without .py)
    description: str             # Module description
    author: str                  # Author
    version: str                 # Version (semantic versioning)
    commands: Dict[str, Command] # Commands dictionary: {"cmd_name": Command(...)}
    handlers: List[Any]          # List of registered event handlers
    on_load: Optional[Callable]  # Callback on load (can be async)
    on_unload: Optional[Callable]# Callback on unload (can be async)
    settings: Dict[str, Any]     # Arbitrary module data
    settings_schema: List[Dict]  # Settings schema (for inline panel and .fcfg)
    requirements: List[str]      # List of pip dependencies
```

---

## 7. Event Handlers

In addition to commands, a module can register arbitrary Telethon event handlers.

```python
from telethon import events


def setup(bot):
    mod = Module(name="spy", description="Tracking", author="Me", version="1.0")
    
    # Incoming message handler
    async def on_new_message(event):
        # Process only other people's messages
        if event.out:
            return
        # Logic...
    
    # Register handler via Telethon client
    handler = bot.client.on(events.NewMessage(incoming=True))(on_new_message)
    mod.handlers.append(handler)  # Save for proper unloading
    
    # Deleted message handler
    async def on_deleted(event):
        pass
    
    handler2 = bot.client.on(events.MessageDeleted())(on_deleted)
    mod.handlers.append(handler2)
    
    bot.module_manager.register_module(mod)
    bot.register_commands(mod)
```

> **Important:** Always add registered handlers to `mod.handlers`. This is necessary for proper module unloading — the userbot will call `client.remove_event_handler()` for each of them.

### Available Telethon Event Types

| Event | Description |
|-------|-------------|
| `events.NewMessage` | New message |
| `events.MessageEdited` | Message edited |
| `events.MessageDeleted` | Message deleted |
| `events.MessageRead` | Message read |
| `events.ChatAction` | Chat action (join, leave, photo change...) |
| `events.UserUpdate` | User status update (online/offline) |
| `events.CallbackQuery` | Inline button press |
| `events.InlineQuery` | Inline query |
| `events.Album` | Group of media messages |

---

## 8. Module Settings (settings_schema)

Modules can declare configurable parameters via `settings_schema`. These settings are accessible:

- Through the inline panel (buttons in the bot)
- Through the `.fcfg` command
- Programmatically via `module_config()` / `module_config_set()`

### settings_schema Format

```python
mod.settings_schema = [
    {
        "key": "greeting",        # Unique key (string, no spaces)
        "label": "Greeting",      # Display name
        "type": "str",            # Type: "str", "int", "float", "bool", "list"
        "default": "Hello!",      # Default value
        "description": "Greeting text when entering chat",  # Description (optional)
    },
    {
        "key": "enabled",
        "label": "Enabled",
        "type": "bool",
        "default": True,
        "description": "Enable/disable the feature",
    },
    {
        "key": "max_count",
        "label": "Maximum",
        "type": "int",
        "default": 10,
        "description": "Maximum count",
    },
    {
        "key": "threshold",
        "label": "Threshold",
        "type": "float",
        "default": 0.75,
    },
    {
        "key": "ignored_chats",
        "label": "Ignored Chats",
        "type": "list",
        "default": [],
        "description": "Chat IDs separated by commas",
    },
]
```

### Supported Types

| Type | Description | Example Value |
|------|-------------|---------------|
| `str` | String | `"Hello!"` |
| `int` | Integer | `42` |
| `float` | Floating-point number | `3.14` |
| `bool` | Boolean value | `true` / `false` |
| `list` | List of strings (comma-separated) | `"chat1, chat2, chat3"` |

### Reading Settings in a Module

```python
def setup(bot):
    mod = Module(name="mymod", ...)
    
    mod.settings_schema = [
        {"key": "greeting", "label": "Greeting", "type": "str", "default": "Hello!"},
        {"key": "enabled", "label": "Enabled", "type": "bool", "default": True},
    ]

    async def cmd_greet(event):
        # Read setting
        greeting = module_config(bot, "mymod", "greeting", "Hello!")
        enabled = module_config(bot, "mymod", "enabled", True)
        
        if not enabled:
            await event.edit("❌ Feature is disabled")
            return
        
        await event.edit(greeting)
    
    # ... registration
```

### Writing Settings Programmatically

```python
# Set a value
module_config_set(bot, "mymod", "greeting", "Good day!")

# Or directly through bot
bot.config.data["custom_settings"]["mymod.greeting"] = "Good day!"
bot.config.save()
```

### How Settings Are Stored

All user module settings are stored in `kub_config.json` in the `custom_settings` section:

```json
{
  "custom_settings": {
    "mymod.greeting": "Good day!",
    "mymod.enabled": "true",
    "mymod.max_count": "42"
  }
}
```

> **Note:** Values are stored as strings. The `module_config()` function automatically casts them to the required type based on `settings_schema`.

### Behavior in the Inline Panel

- Parameters of type `bool` are displayed as toggles (✅/❌) with instant toggle
- Other types open a dialog for entering a new value
- All settings are accessible via the "⚙️ Module Settings" button in the module panel

---

## 9. Module Dependencies

The userbot automatically detects and installs pip dependencies of modules **before** loading them.

### Ways to Declare Dependencies

#### Method 1: Comments (recommended for simplicity)

```python
# requires: aiohttp, Pillow, pydub
# require: beautifulsoup4
# deps: requests, lxml
# dependencies: opencv-python
```

Supported keywords (case-insensitive):
- `# requires:`
- `# require:`
- `# deps:`
- `# dependencies:`

#### Method 2: Variable in code

```python
__requires__ = ["aiohttp", "Pillow>=9.0", "beautifulsoup4"]
# or
__dependencies__ = ["requests"]
# or
__deps__ = ["pydub"]
```

Version specification is supported: `Pillow>=9.0`, `aiohttp>=3.8,<4.0`

### Package Name Mapping

The userbot knows about discrepancies between pip names and import names for popular packages:

| pip install | import |
|-------------|--------|
| `pillow` | `PIL` |
| `beautifulsoup4` | `bs4` |
| `opencv-python` | `cv2` |
| `pyyaml` | `yaml` |
| `pycryptodome` | `Crypto` |
| `python-dotenv` | `dotenv` |
| `scikit-learn` | `sklearn` |
| `python-magic` | `magic` |
| `speedtest-cli` | `speedtest` |
| `gtts` | `gtts` |
| and others... | |

### Installation Process

1. When loading a module, dependencies are parsed from the source code
2. For each dependency, a check is performed to see if it is installed
3. Missing dependencies are installed via `pip install`
4. If installation fails — a warning is displayed, but the module is still loaded
5. Dependency information is saved in `installed_modules` in the configuration

### When Installing via `.im` or `.dlm`

When installing a module via the `.im` (file) or `.dlm` (URL) commands, dependencies are installed **asynchronously** and the user sees the progress:

```
📥 my_module.py
📦 Installing dependencies: aiohttp, Pillow...
✅ my_module | 🔧 3 cmd
📥 Installed: aiohttp, Pillow
```

---

## 10. Module Lifecycle

```
Module file found
        │
        ▼
Parse dependencies from source code
        │
        ▼
Install missing dependencies (pip install)
        │
        ▼
Execute file code (exec_module)
  - Inject variables: bot, client, config, manager, module_config, module_config_set
        │
        ▼
Call setup(bot) — if the function is defined
  - Create Module, Command
  - register_module()
  - register_commands()
        │
        ▼
Call on_load() — if defined
        │
        ▼
    ══ RUNNING ══
        │
        ▼
Unload (unload_module)
  - Call on_unload()
  - Remove event handlers
  - Remove commands from _command_handlers
  - Remove from modules dict
```

### on_load and on_unload

```python
def setup(bot):
    mod = Module(name="mymod", ...)
    
    async def on_load():
        """Called after the module is fully loaded."""
        print("Module loaded!")
        # Initialize resources, connections, etc.
    
    async def on_unload():
        """Called before the module is unloaded."""
        print("Module unloading!")
        # Release resources, close connections
    
    mod.on_load = on_load
    mod.on_unload = on_unload
    
    # ... rest of registration
```

> **Note:** `on_load` and `on_unload` can be either synchronous or asynchronous functions. For `on_unload`, asynchronous coroutines are wrapped in `create_task`.

---

## 11. Available Objects and API

### bot (Userbot)

```python
bot.client              # TelegramClient — main client
bot.config              # Config — configuration
bot.module_manager      # ModuleManager — module manager
bot.inline_panel        # InlinePanel — inline bot
bot.start_time          # float — startup time (timestamp)
bot._command_handlers   # Dict[str, Command] — all registered commands
```

### bot.client (TelegramClient)

A full-fledged `telethon.TelegramClient` instance. Main methods:

```python
# Sending messages
await bot.client.send_message(chat_id, "Text")
await bot.client.send_file(chat_id, "photo.jpg", caption="Caption")

# Getting information
me = await bot.client.get_me()
entity = await bot.client.get_entity("username")

# Iterating over messages
async for msg in bot.client.iter_messages(chat_id, limit=100):
    print(msg.text)

# Downloading media
path = await bot.client.download_media(message)
data = await bot.client.download_media(message, bytes)  # To memory

# Uploading files
await bot.client.send_file(chat_id, "/path/to/file")

# Working with participants
async for user in bot.client.iter_participants(chat_id):
    print(user.first_name)

# Forwarding
await bot.client.forward_messages(to_chat, msg_id, from_chat)

# Deleting
await bot.client.delete_messages(chat_id, [msg_id])

# Pin/Unpin
await bot.client.pin_message(chat_id, msg_id)
await bot.client.unpin_message(chat_id)
```

### bot.config (Config)

```python
bot.config.prefix            # str — current command prefix
bot.config.owner_id          # int — owner ID
bot.config.bot_token         # str — inline bot token
bot.config.disabled_modules  # list — list of disabled modules
bot.config.alive_message     # str — alive message template
bot.config.custom_settings   # dict — user module settings
bot.config.installed_modules # dict — information about installed modules
bot.config.kinfo             # dict — kinfo settings

# Read/Write
val = bot.config.get("key", "default")
bot.config.set("key", value)  # Automatically saves to file

# Direct data access
bot.config.data["custom_settings"]["mymod.key"] = "value"
bot.config.save()  # Manual save
```

### bot.module_manager (ModuleManager)

```python
# Getting modules
bot.module_manager.modules                    # Dict[str, Module] — all modules
bot.module_manager.get_user_modules()         # Dict[str, Module] — user modules only
bot.module_manager.get_all_commands()         # Dict[str, Command] — all commands
bot.module_manager.is_builtin("core")         # bool — is it a built-in module

# Managing modules
bot.module_manager.register_module(mod)       # Register module
bot.module_manager.mark_builtin("name")       # Mark as built-in
bot.module_manager.unload_module("name")      # Unload module
bot.module_manager.install_from_file(fn, data) # Install from file
await bot.module_manager.install_from_url(url) # Install from URL
bot.module_manager.uninstall_module("name")   # Remove module
bot.module_manager.load_from_directory()       # Reload all modules from folder
```

### bot.inline_panel (InlinePanel)

```python
bot.inline_panel.active      # bool — is the inline panel active
bot.inline_panel.inline_bot  # TelegramClient — bot client (or None)

await bot.inline_panel.start()    # Start inline bot
await bot.inline_panel.stop()     # Stop
await bot.inline_panel.restart()  # Restart
```

---

## 12. Userbot Utilities

The following utilities are defined in the main file and are available for import or use:

### format_uptime(seconds) → str

```python
format_uptime(3661)  # "1h 1m 1s"
format_uptime(90061) # "1d 1h 1m 1s"
```

### truncate(text, mx=4096) → str

Truncates text to maximum length (default 4096 — Telegram limit):

```python
truncate(very_long_text)  # "...text...\n\n... (truncated)"
```

### get_user_link(user) → str

Returns a Markdown link to a user:

```python
link = await get_user_link(user)  # "[Name](tg://user?id=123)"
```

### get_raw_github_url(url) → str

Converts a GitHub link to a raw link for downloading:

```python
get_raw_github_url("https://github.com/user/repo/blob/main/module.py")
# → "https://raw.githubusercontent.com/user/repo/main/module.py"
```

### module_config(bot, mod_name, key, default=None)

Read a module setting with automatic type casting:

```python
value = module_config(bot, "mymod", "greeting", "Hello!")
enabled = module_config(bot, "mymod", "enabled", True)  # → bool
count = module_config(bot, "mymod", "max_count", 10)     # → int
```

### module_config_set(bot, mod_name, key, value)

Write a module setting:

```python
module_config_set(bot, "mymod", "greeting", "Good day!")
```

### Functions for Working with Dependencies

```python
parse_module_requirements(content: str) → List[str]  # Parse dependencies from code
is_package_installed(package: str) → bool             # Check if package is installed
install_pip_package(package: str) → Tuple[bool, str]  # Synchronous installation
uninstall_pip_package(package: str) → Tuple[bool, str]# Remove package
check_and_install_requirements(content: str) → Dict   # Check and install all dependencies

# Asynchronous versions
await async_install_pip_package(package: str) → Tuple[bool, str]
await async_check_and_install_requirements(content: str) → Dict
```

---

## 13. Working with Configuration

### kub_config.json Structure

```json
{
  "api_id": 12345,
  "api_hash": "abc...",
  "phone": "+7...",
  "bot_token": "123:ABC...",
  "prefix": ".",
  "alive_message": "{emoji} **{brand}** is running!\n...",
  "disabled_modules": ["somemod"],
  "custom_settings": {
    "mymod.greeting": "Hello!",
    "mymod.enabled": "true"
  },
  "owner_id": 123456789,
  "installed_modules": {
    "mymod": {
      "filename": "mymod.py",
      "installed_at": "2024-01-01T00:00:00",
      "source": "file",
      "requirements": ["aiohttp"],
      "url": "https://..."
    }
  },
  "kinfo": {
    "template": "...",
    "emoji": "🦊",
    "photo": "",
    "show_ping": true,
    "show_uptime": true,
    "custom_lines": []
  },
  "stats": {
    "commands_used": 42,
    "started_at": 1700000000
  }
}
```

### Working with Configuration in a Module

```python
def setup(bot):
    # Reading
    prefix = bot.config.prefix
    owner = bot.config.owner_id
    
    # Writing with auto-save
    bot.config.set("my_custom_key", "value")
    
    # Direct access
    bot.config.data["my_key"] = "value"
    bot.config.save()
    
    # Getting with default value
    val = bot.config.get("nonexistent", "default")
```

---

## 14. Installing and Removing Modules

### Installing from File (`.im`)

1. Reply to a message with a `.py` file
2. Type `.im`

The userbot will:
1. Download the file
2. Parse dependencies
3. Install missing packages
4. Load the module
5. Save information in `installed_modules`

### Installing from URL (`.dlm`)

```
.dlm https://github.com/user/repo/blob/main/modules/mymod.py
.dlm https://gist.github.com/user/abc123
.dlm https://example.com/module.py
```

Supported:
- Direct links to `.py` files
- GitHub blob links (auto-converted to raw)
- GitHub Gist (auto-appended with `/raw`)

### Removing a Module (`.um`)

```
.um mymod
```

Removes the file from `modules/`, unloads the module, clears `installed_modules`.

### Reloading Modules (`.reload`)

Unloads all user modules and reloads them from `modules/`.

### Viewing Modules

```
.modules    — all modules (built-in + user)
.lm         — only user modules with details
```

---

## 15. The `.fcfg` Command — Settings Management

The `.fcfg` command allows you to manage module settings from the chat.

### Syntax

```
.fcfg set -m <module> <parameter> <value>
.fcfg remove -m <module> <parameter>
.fcfg reset -m <module>
```

### Examples

```
.fcfg set -m mymod greeting Hello, world!
.fcfg set -m mymod enabled true
.fcfg set -m mymod max_count 42
.fcfg remove -m mymod greeting
.fcfg reset -m mymod
```

### Viewing Module Settings

```
.fcfg set -m mymod
```

Without specifying a parameter and value, it will show all available settings of the module (from `settings_schema`).

### Validation

When `settings_schema` is present, values are validated by type:
- `int` — checks that the value is a number
- `float` — checks that the value is a floating-point number
- `bool` — accepted values: `true/false`, `1/0`, `yes/no`, `on/off`

---

## 16. The `.pip` Command — Package Management

### Subcommands

```
.pip install <package>      — install a pip package
.pip uninstall <package>    — remove a pip package
.pip check <package>        — check if a package is installed
.pip search <package>       — package info (version, description, author)
.pip list                   — list all installed packages
.pip deps <module>          — show module dependencies
```

### Examples

```
.pip install aiohttp
.pip check Pillow
.pip deps mymod
.pip list
```

---

## 17. Built-in Modules

### core (Core Commands)

| Command | Description |
|---------|-------------|
| `.alive` | Health check |
| `.kinfo` | Information card |
| `.kset <sub>` | kinfo settings (emoji, photo, addline, clearlines, reset) |
| `.help [cmd]` | List of commands / help for a command |
| `.ping` | Latency check |
| `.prefix <new>` | Change prefix |
| `.modules` | List all modules |
| `.reload` | Reload modules |
| `.eval <expr>` | Execute Python expression |
| `.exec <code>` | Execute Python code |
| `.settings` | Open inline panel |
| `.settoken <token>` | Set inline bot token |
| `.status` | Userbot status |
| `.im` | Install module from file (by reply) |
| `.um <name>` | Remove module |
| `.dlm <url>` | Install module by URL |
| `.lm` | List user modules |
| `.pip <sub>` | Package management |
| `.fcfg <sub>` | Module settings |

### tools (Tools)

| Command | Description |
|---------|-------------|
| `.id` | Show chat/user/message ID |
| `.info [user]` | User information |
| `.del` | Delete message |
| `.purge` | Delete messages from reply to current |
| `.chatinfo` | Chat information |
| `.calc <expr>` | Calculator |
| `.sd <sec> <text>` | Self-destructing message |
| `.search <query>` | Search messages in chat |

### fun (Entertainment)

| Command | Description |
|---------|-------------|
| `.reverse <text>` | Reverse text |
| `.upper <text>` | Convert to UPPERCASE |
| `.lower <text>` | Convert to lowercase |
| `.mock <text>` | rAnDoM cAsE |
| `.repeat <n> <text>` | Repeat text N times |
| `.type <text>` | Typing effect |
| `.dice [sides]` | Roll a die |
| `.coin` | Flip a coin |
| `.choose a \| b \| c` | Random choice |
| `.rate <thing>` | Random rating |

### admin (Administration)

| Command | Description |
|---------|-------------|
| `.ban` | Ban (by reply) |
| `.unban` | Unban (by reply) |
| `.kick` | Kick (by reply) |
| `.mute [time]` | Mute (5m, 2h, 1d) |
| `.unmute` | Unmute |
| `.pin` | Pin message |
| `.unpin` | Unpin |

---

## 18. Module Examples

### Example 1: Simple Module with One Command

**`modules/hello.py`**

```python
"""
Simple greeting module.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Callable, Any, Optional


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
    mod = Module(
        name="hello",
        description="Greeting module",
        author="Developer",
        version="1.0",
    )
    p = bot.config.prefix

    async def cmd_hello(event):
        """Send a greeting."""
        args = event.raw_text.split(maxsplit=1)
        name = args[1] if len(args) > 1 else "world"
        await event.edit(f"👋 Hello, **{name}**!")

    mod.commands = {
        "hello": Command("hello", cmd_hello, "Greeting", "hello", f"{p}hello [name]"),
    }

    bot.module_manager.register_module(mod)
    bot.register_commands(mod)
```

### Example 2: Module with Settings

**`modules/greeter.py`**

```python
"""
Auto-greeting module with settings.
"""
# requires: 

from dataclasses import dataclass, field
from typing import Dict, List, Callable, Any, Optional
from telethon import events


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
    mod = Module(
        name="greeter",
        description="Auto-greeting for new members",
        author="Developer",
        version="1.2",
    )
    p = bot.config.prefix

    # Module settings
    mod.settings_schema = [
        {
            "key": "enabled",
            "label": "Enabled",
            "type": "bool",
            "default": True,
            "description": "Enable auto-greeting",
        },
        {
            "key": "message",
            "label": "Message",
            "type": "str",
            "default": "Welcome, {name}! 👋",
            "description": "Greeting template. {name} = user's name",
        },
        {
            "key": "delete_after",
            "label": "Delete after (sec)",
            "type": "int",
            "default": 0,
            "description": "Delete greeting after N seconds (0 = don't delete)",
        },
    ]

    import asyncio

    # Chat join handler
    async def on_chat_action(event):
        if not event.user_joined and not event.user_added:
            return

        enabled = module_config(bot, "greeter", "enabled", True)
        if not enabled:
            return

        user = await event.get_user()
        if not user:
            return

        template = module_config(bot, "greeter", "message", "Welcome, {name}! 👋")
        name = user.first_name or "friend"

        try:
            text = template.format(name=name)
        except (KeyError, IndexError):
            text = f"Welcome, {name}! 👋"

        msg = await event.reply(text)

        delete_after = module_config(bot, "greeter", "delete_after", 0)
        if delete_after and delete_after > 0:
            await asyncio.sleep(delete_after)
            try:
                await msg.delete()
            except Exception:
                pass

    handler = bot.client.on(events.ChatAction())(on_chat_action)
    mod.handlers.append(handler)

    # Command for checking/managing
    async def cmd_greeter(event):
        enabled = module_config(bot, "greeter", "enabled", True)
        message = module_config(bot, "greeter", "message", "...")
        delete_after = module_config(bot, "greeter", "delete_after", 0)

        await event.edit(
            f"👋 **Greeter**\n━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{'✅' if enabled else '❌'} Status: {'On' if enabled else 'Off'}\n"
            f"💬 Template: `{message}`\n"
            f"⏱ Delete after: {delete_after}s\n\n"
            f"Settings: `{p}fcfg set -m greeter <param> <value>`"
        )

    mod.commands = {
        "greeter": Command("greeter", cmd_greeter, "Greeting status", "greeter", f"{p}greeter"),
    }

    bot.module_manager.register_module(mod)
    bot.register_commands(mod)
```

### Example 3: Module with Dependencies

**`modules/weather.py`**

```python
"""
Weather module.
"""
# requires: aiohttp

__requires__ = ["aiohttp"]

from dataclasses import dataclass, field
from typing import Dict, List, Callable, Any, Optional


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
    mod = Module(
        name="weather",
        description="Weather via wttr.in",
        author="Developer",
        version="1.0",
    )
    p = bot.config.prefix

    mod.settings_schema = [
        {
            "key": "default_city",
            "label": "Default City",
            "type": "str",
            "default": "Moscow",
            "description": "City for weather request if not specified",
        },
        {
            "key": "lang",
            "label": "Language",
            "type": "str",
            "default": "en",
            "description": "Response language (en, ru, de, ...)",
        },
    ]

    import aiohttp

    async def cmd_weather(event):
        args = event.raw_text.split(maxsplit=1)
        city = args[1] if len(args) > 1 else module_config(bot, "weather", "default_city", "Moscow")
        lang = module_config(bot, "weather", "lang", "en")

        await event.edit(f"🌤 Loading weather for **{city}**...")

        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://wttr.in/{city}?format=3&lang={lang}"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        await event.edit(f"🌤 {text.strip()}")
                    else:
                        await event.edit(f"❌ HTTP Error {resp.status}")
        except Exception as e:
            await event.edit(f"❌ {e}")

    mod.commands = {
        "weather": Command("weather", cmd_weather, "Weather", "weather", f"{p}weather [city]"),
    }

    bot.module_manager.register_module(mod)
    bot.register_commands(mod)
```

### Example 4: Module with on_load/on_unload and Storage

**`modules/notes.py`**

```python
"""
Notes module with file storage.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Callable, Any, Optional


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


NOTES_FILE = "kub_notes.json"


def setup(bot):
    mod = Module(
        name="notes",
        description="Notes",
        author="Developer",
        version="1.0",
    )
    p = bot.config.prefix

    # Notes storage (in module settings, for access from on_unload)
    notes_data = {"notes": {}}

    def load_notes():
        if os.path.exists(NOTES_FILE):
            with open(NOTES_FILE, "r", encoding="utf-8") as f:
                notes_data["notes"] = json.load(f)

    def save_notes():
        with open(NOTES_FILE, "w", encoding="utf-8") as f:
            json.dump(notes_data["notes"], f, ensure_ascii=False, indent=2)

    async def on_load():
        load_notes()

    async def on_unload():
        save_notes()

    mod.on_load = on_load
    mod.on_unload = on_unload

    # Load immediately
    load_notes()

    async def cmd_note(event):
        """Add a note: .note <name> <text>"""
        args = event.raw_text.split(maxsplit=2)
        if len(args) < 3:
            await event.edit(f"❌ `{p}note <name> <text>`")
            return
        name = args[1]
        text = args[2]
        notes_data["notes"][name] = text
        save_notes()
        await event.edit(f"📝 Note `{name}` saved!")

    async def cmd_notes(event):
        """List notes."""
        if not notes_data["notes"]:
            await event.edit("📭 No notes")
            return
        t = "📝 **Notes:**\n━━━━━━━━━━━━━━━━━━━━━\n\n"
        for name, text in notes_data["notes"].items():
            t += f"  📌 **{name}**: _{text[:50]}_\n"
        await event.edit(t)

    async def cmd_getnote(event):
        """Get a note: .getnote <name>"""
        args = event.raw_text.split(maxsplit=1)
        if len(args) < 2:
            await event.edit(f"❌ `{p}getnote <name>`")
            return
        name = args[1]
        text = notes_data["notes"].get(name)
        if text:
            await event.edit(f"📌 **{name}**:\n{text}")
        else:
            await event.edit(f"❌ Note `{name}` not found")

    async def cmd_delnote(event):
        """Delete a note: .delnote <name>"""
        args = event.raw_text.split(maxsplit=1)
        if len(args) < 2:
            await event.edit(f"❌ `{p}delnote <name>`")
            return
        name = args[1]
        if name in notes_data["notes"]:
            del notes_data["notes"][name]
            save_notes()
            await event.edit(f"🗑 Note `{name}` deleted")
        else:
            await event.edit(f"❌ `{name}` not found")

    mod.commands = {
        "note": Command("note", cmd_note, "Add a note", "notes", f"{p}note <name> <text>"),
        "notes": Command("notes", cmd_notes, "List notes", "notes", f"{p}notes"),
        "getnote": Command("getnote", cmd_getnote, "Get a note", "notes", f"{p}getnote <name>"),
        "delnote": Command("delnote", cmd_delnote, "Delete a note", "notes", f"{p}delnote <name>"),
    }

    bot.module_manager.register_module(mod)
    bot.register_commands(mod)
```

### Example 5: Module with Event Handler (Anti-spam)

**`modules/antispam.py`**

```python
"""
Simple anti-spam module.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Callable, Any, Optional
from telethon import events


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
    mod = Module(
        name="antispam",
        description="Spam protection",
        author="Developer",
        version="1.0",
    )
    p = bot.config.prefix

    mod.settings_schema = [
        {
            "key": "enabled",
            "label": "Enabled",
            "type": "bool",
            "default": False,
            "description": "Enable anti-spam",
        },
        {
            "key": "max_messages",
            "label": "Max messages",
            "type": "int",
            "default": 5,
            "description": "Maximum messages per period",
        },
        {
            "key": "period",
            "label": "Period (sec)",
            "type": "int",
            "default": 10,
            "description": "Check period in seconds",
        },
        {
            "key": "action",
            "label": "Action",
            "type": "str",
            "default": "warn",
            "description": "Action on spam: warn, mute, kick",
        },
    ]

    # User message storage
    user_messages = defaultdict(list)

    async def on_new_message(event):
        if event.out:
            return
        if not event.is_group:
            return

        enabled = module_config(bot, "antispam", "enabled", False)
        if not enabled:
            return

        max_msgs = module_config(bot, "antispam", "max_messages", 5)
        period = module_config(bot, "antispam", "period", 10)
        action = module_config(bot, "antispam", "action", "warn")

        uid = event.sender_id
        now = time.time()

        # Clear old entries
        user_messages[uid] = [t for t in user_messages[uid] if now - t < period]
        user_messages[uid].append(now)

        if len(user_messages[uid]) > max_msgs:
            user_messages[uid].clear()
            user = await event.get_sender()
            name = user.first_name if user else "User"

            if action == "warn":
                await event.reply(f"⚠️ {name}, please stop spamming!")
            elif action == "mute":
                try:
                    from telethon.tl.functions.channels import EditBannedRequest
                    from telethon.tl.types import ChatBannedRights
                    from datetime import datetime, timedelta
                    await bot.client(EditBannedRequest(
                        event.chat_id, uid,
                        ChatBannedRights(
                            until_date=datetime.now() + timedelta(minutes=5),
                            send_messages=True,
                        )
                    ))
                    await event.reply(f"🔇 {name} muted for 5 minutes for spamming")
                except Exception as e:
                    await event.reply(f"⚠️ {name}, please stop spamming! (failed to mute: {e})")
            elif action == "kick":
                try:
                    await bot.client.kick_participant(event.chat_id, uid)
                    await event.reply(f"👢 {name} kicked for spamming")
                except Exception as e:
                    await event.reply(f"⚠️ {name}, please stop spamming! (failed to kick: {e})")

    handler = bot.client.on(events.NewMessage(incoming=True))(on_new_message)
    mod.handlers.append(handler)

    async def cmd_antispam(event):
        enabled = module_config(bot, "antispam", "enabled", False)
        max_msgs = module_config(bot, "antispam", "max_messages", 5)
        period = module_config(bot, "antispam", "period", 10)
        action = module_config(bot, "antispam", "action", "warn")

        await event.edit(
            f"🛡 **Anti-spam**\n━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{'✅' if enabled else '❌'} Status: {'On' if enabled else 'Off'}\n"
            f"📊 Limit: {max_msgs} messages per {period}s\n"
            f"⚡ Action: `{action}`\n\n"
            f"Settings: `{p}fcfg set -m antispam <param> <value>`"
        )

    mod.commands = {
        "antispam": Command("antispam", cmd_antispam, "Anti-spam status", "antispam", f"{p}antispam"),
    }

    bot.module_manager.register_module(mod)
    bot.register_commands(mod)
```

### Example 6: Module without setup() (Alternative Approach)

You can create a module that registers itself directly when the file is executed, without `setup()`:

**`modules/quickmod.py`**

```python
"""
Quick module without setup().
Uses injected variables bot, client, config, manager.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Callable, Any, Optional


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


# bot, client, config, manager — already available in the namespace

_mod = Module(
    name="quickmod",
    description="Quick module",
    author="Me",
    version="0.1",
)

_p = config.prefix  # config is injected automatically


async def cmd_quick(event):
    await event.edit("⚡ Quick module is working!")


_mod.commands = {
    "quick": Command("quick", cmd_quick, "Quick command", "quickmod", f"{_p}quick"),
}

# Registration without setup()
manager.register_module(_mod)  # manager is injected automatically
bot.register_commands(_mod)    # bot is injected automatically
```

> **Note:** This approach works, but `setup()` is preferred as it explicitly shows the entry point and provides a cleaner structure.

---

## 19. Recommendations and Best Practices

### Naming

- **Module name** = filename without `.py`, lowercase, no spaces
- **Command names** — short, intuitive, lowercase: `weather`, `note`, `ban`
- Avoid conflicts with built-in commands: `alive`, `help`, `ping`, `eval`, `exec`, `modules`, `reload`, `settings`, `status`, `im`, `um`, `dlm`, `lm`, `pip`, `fcfg`, `prefix`, `settoken`, `kinfo`, `kset`, `id`, `info`, `del`, `purge`, `chatinfo`, `calc`, `sd`, `search`, `reverse`, `upper`, `lower`, `mock`, `repeat`, `type`, `dice`, `coin`, `choose`, `rate`, `ban`, `unban`, `kick`, `mute`, `unmute`, `pin`, `unpin`

### Error Handling

```python
async def cmd_example(event):
    try:
        # Your logic
        result = await some_operation()
        await event.edit(f"✅ {result}")
    except FloodWaitError as e:
        await event.edit(f"⏳ Please wait {e.seconds} seconds")
    except ChatAdminRequiredError:
        await event.edit("❌ Admin rights required")
    except Exception as e:
        await event.edit(f"❌ Error: {e}")
```

### Working with Arguments

```python
async def cmd_example(event):
    args = event.raw_text.split(maxsplit=2)
    # args[0] = ".command"
    # args[1] = first argument (if present)
    # args[2] = remaining text (if present)
    
    if len(args) < 2:
        await event.edit(f"❌ Usage: `{p}example <arg>`")
        return
    
    arg1 = args[1]
    rest = args[2] if len(args) > 2 else ""
```

### Working with Reply Messages

```python
async def cmd_example(event):
    # Get text from argument or from reply
    args = event.raw_text.split(maxsplit=1)
    text = None
    
    if len(args) > 1:
        text = args[1]
    elif event.is_reply:
        reply = await event.get_reply_message()
        text = reply.text or ""
    
    if not text:
        await event.edit("❌ Specify text or reply to a message")
        return
```

### Long Operations

```python
async def cmd_download(event):
    await event.edit("⏳ Loading...")
    
    try:
        # Long operation
        result = await long_operation()
        await event.edit(f"✅ Done: {result}")
    except Exception as e:
        await event.edit(f"❌ {e}")
```

### Sending Files

```python
async def cmd_export(event):
    data = "File contents"
    
    # Send as file
    await event.delete()
    await bot.client.send_file(
        event.chat_id,
        file=data.encode("utf-8"),
        attributes=[DocumentAttributeFilename("export.txt")],
        caption="📎 Data export",
    )
```

### Limiting Text Length

Telegram limits message length to 4096 characters. Use `truncate()`:

```python
async def cmd_long(event):
    very_long_text = "..." * 10000
    await event.edit(truncate(very_long_text))
```

### Don't Block the Event Loop

```python
# ❌ Bad:
import time
time.sleep(5)

# ✅ Good:
import asyncio
await asyncio.sleep(5)

# ❌ Bad (blocking HTTP request):
import requests
resp = requests.get(url)

# ✅ Good (async request):
import aiohttp
async with aiohttp.ClientSession() as session:
    async with session.get(url) as resp:
        data = await resp.text()
```

### Cleanup on Unload

If the module creates background tasks, opens files or connections — clean them up in `on_unload`:

```python
_tasks = []

async def on_unload():
    for task in _tasks:
        task.cancel()
    _tasks.clear()

mod.on_unload = on_unload
```

---

## 20. Object Reference

### event (events.NewMessage.Event)

| Property/Method | Description |
|-----------------|-------------|
| `event.raw_text` | Message text (str) |
| `event.text` | Message text |
| `event.message` | Message object |
| `event.chat_id` | Chat ID |
| `event.sender_id` | Sender ID |
| `event.is_reply` | Is a reply (bool) |
| `event.is_group` | Message in a group (bool) |
| `event.is_private` | Private message (bool) |
| `event.is_channel` | Message in a channel (bool) |
| `event.out` | Outgoing message (bool) |
| `event.photo` | Photo (if present) |
| `event.document` | Document (if present) |
| `event.media` | Media (if present) |
| `await event.edit(text)` | Edit message |
| `await event.reply(text)` | Reply to message |
| `await event.delete()` | Delete message |
| `await event.get_reply_message()` | Get the reply message |
| `await event.get_sender()` | Get sender |
| `await event.get_chat()` | Get chat |

### User (telethon.tl.types.User)

| Property | Description |
|----------|-------------|
| `user.id` | User ID |
| `user.first_name` | First name |
| `user.last_name` | Last name |
| `user.username` | Username |
| `user.phone` | Phone number |
| `user.bot` | Is a bot (bool) |
| `user.premium` | Premium account (bool) |
| `user.verified` | Verified (bool) |

---

## 21. FAQ

### How do I create the simplest module?

Create a file in `modules/`, define `setup(bot)`, create `Module` and `Command`, register them.

### Why isn't my module loading?

1. Check that the file is in the `modules/` folder and has the `.py` extension
2. The filename doesn't start with `_`
3. The module isn't in the `disabled_modules` list in the configuration
4. Check logs for errors: `Error <filename>: ...`
5. Check Python syntax

### How do I debug a module?

Use the built-in `.eval` or `.exec` commands for testing:

```
.eval bot.module_manager.modules.get("mymod")
.eval module_config(bot, "mymod", "key")
```

### How do I update a module?

Simply reinstall it via `.im` or `.dlm` — the old version will be unloaded and replaced.

### Why aren't settings being applied?

1. Make sure you read settings via `module_config()` on each command call, not during module initialization
2. Check that the module name matches: `module_config(bot, "exact_module_name", ...)`
3. Use `.fcfg set -m <mod>` without parameters to see current values

### How do I make a module that runs in the background?

Use `asyncio.create_task()`:

```python
import asyncio

async def background_task(bot):
    while True:
        # Your logic
        await asyncio.sleep(60)

def setup(bot):
    task = asyncio.get_event_loop().create_task(background_task(bot))
    mod.settings["_task"] = task
    
    async def on_unload():
        task = mod.settings.get("_task")
        if task:
            task.cancel()
    
    mod.on_unload = on_unload
```

### How do I access the Telethon API directly?

```python
from telethon.tl.functions.messages import GetHistoryRequest

async def cmd_history(event):
    result = await bot.client(GetHistoryRequest(
        peer=event.chat_id,
        offset_id=0,
        offset_date=None,
        add_offset=0,
        limit=10,
        max_id=0,
        min_id=0,
        hash=0,
    ))
    await event.edit(f"Retrieved {len(result.messages)} messages")
```

### Can I use the inline bot from a module?

Yes, via `bot.inline_panel.inline_bot`:

```python
if bot.inline_panel.active:
    await bot.inline_panel.inline_bot.send_message(user_id, "Hello from the bot!")
```

### How do I determine if the userbot is in a group or a DM?

```python
async def cmd_example(event):
    if event.is_private:
        await event.edit("This is a DM")
    elif event.is_group:
        await event.edit("This is a group")
    elif event.is_channel:
        await event.edit("This is a channel")
```

---

## Module Template (copy and use)

```python
"""
Description of your module.

Author: Your name
Version: 1.0
"""
# requires: 

from dataclasses import dataclass, field
from typing import Dict, List, Callable, Any, Optional


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
    MOD_NAME = "mymodule"
    mod = Module(
        name=MOD_NAME,
        description="Description",
        author="Author",
        version="1.0",
    )
    p = bot.config.prefix

    # Settings (optional)
    mod.settings_schema = [
        {
            "key": "example_setting",
            "label": "Example",
            "type": "str",
            "default": "value",
            "description": "Setting description",
        },
    ]

    # Commands
    async def cmd_example(event):
        setting = module_config(bot, MOD_NAME, "example_setting", "value")
        await event.edit(f"✅ Setting: {setting}")

    mod.commands = {
        "example": Command(
            "example", cmd_example,
            "Command description", MOD_NAME,
            f"{p}example",
        ),
    }

    # Lifecycle (optional)
    async def on_load():
        pass

    async def on_unload():
        pass

    mod.on_load = on_load
    mod.on_unload = on_unload

    # Registration
    bot.module_manager.register_module(mod)
    bot.register_commands(mod)
```

---

**kazhurkeUserBot** v2.3.0 • Module Documentation • 2026
