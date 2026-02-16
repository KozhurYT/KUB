# requires:
# Модуль Python-команд для kazhurkeUserBot
# Автор: kazhurkeUserBot community
# Версия: 1.2

"""
Модуль расширенных Python-команд.

Команды:
  .py <code>       — выполнить Python-код (exec) с захватом stdout/stderr
  .pyeval <expr>   — вычислить выражение (eval) и вернуть результат
  .pyi <code>      — интерактивный режим: код выполняется с сохранением переменных между вызовами
  .pyreset          — сбросить интерактивную сессию
  .pyenv            — показать переменные интерактивной сессии
  .pytime <code>   — замерить время выполнения кода
  .pyrun <n> <code> — выполнить код N раз и показать среднее время
  .sysinfo          — информация о системе и Python
  .pyfile            — выполнить .py файл (ответ на документ)
"""

import sys
import io
import os
import time
import asyncio
import traceback
import platform
import textwrap
from datetime import datetime

__requires__ = []
__dependencies__ = []


def setup(bot):
    from dataclasses import field

    mod_name = "python_tools"

    # ─── Интерактивная сессия: общий namespace между вызовами ───
    interactive_ns = {
        "__builtins__": __builtins__,
        "asyncio": asyncio,
        "os": os,
        "sys": sys,
        "time": time,
        "platform": platform,
    }

    # ─── Вспомогательные ───

    def _make_exec_globals(event, bot_ref):
        """Создаёт globals-словарь для exec/eval с полезными переменными."""
        g = {
            "__builtins__": __builtins__,
            "event": event,
            "e": event,
            "client": bot_ref.client,
            "c": bot_ref.client,
            "bot": bot_ref,
            "b": bot_ref,
            "config": bot_ref.config,
            "asyncio": asyncio,
            "os": os,
            "sys": sys,
            "time": time,
            "platform": platform,
            "manager": bot_ref.module_manager,
            "reply": None,
            "chat": None,
            "me": None,
        }
        return g

    async def _enrich_globals(g, event, bot_ref):
        """Добавляет асинхронные переменные в globals."""
        try:
            g["me"] = await bot_ref.client.get_me()
        except Exception:
            pass
        try:
            g["chat"] = await event.get_chat()
        except Exception:
            pass
        if event.is_reply:
            try:
                g["reply"] = await event.get_reply_message()
            except Exception:
                pass
        return g

    def _format_output(stdout_text: str, stderr_text: str, result=None,
                       execution_time: float = None) -> str:
        """Форматирует вывод выполнения."""
        parts = []

        if stdout_text and stdout_text.strip():
            parts.append(f"📤 <b>stdout:</b>\n<pre>{html_escape(stdout_text.strip())}</pre>")

        if stderr_text and stderr_text.strip():
            parts.append(f"⚠️ <b>stderr:</b>\n<pre>{html_escape(stderr_text.strip())}</pre>")

        if result is not None:
            result_str = str(result)
            if len(result_str) > 3000:
                result_str = result_str[:3000] + "\n... (обрезано)"
            parts.append(f"📎 <b>Результат:</b>\n<pre>{html_escape(result_str)}</pre>")

        if execution_time is not None:
            if execution_time < 0.001:
                time_str = f"{execution_time * 1_000_000:.1f}μs"
            elif execution_time < 1:
                time_str = f"{execution_time * 1000:.2f}ms"
            else:
                time_str = f"{execution_time:.3f}s"
            parts.append(f"⏱ <code>{time_str}</code>")

        if not parts:
            parts.append(f"{CE.CHECK} Выполнено (нет вывода)")

        return "\n\n".join(parts)

    def _truncate(text: str, max_len: int = 4000) -> str:
        if len(text) <= max_len:
            return text
        return text[:max_len - 30] + "\n\n... (обрезано)"

    def _get_code_from_text(raw_text: str, command: str) -> str:
        """Извлекает код после команды, учитывая многострочность."""
        prefix = bot.config.prefix
        full_cmd = prefix + command
        if raw_text.startswith(full_cmd):
            code = raw_text[len(full_cmd):]
            # Убираем первый пробел/перенос если есть
            if code and code[0] in (' ', '\n'):
                code = code[1:]
            return code
        return ""

    # ─── Команды ───

    async def cmd_py(event):
        """Выполнить Python-код (exec) с захватом stdout/stderr."""
        code = _get_code_from_text(event.raw_text, "py")

        # Также попробуем взять код из reply
        if not code and event.is_reply:
            reply = await event.get_reply_message()
            if reply and reply.text:
                code = reply.text
                # Если в reply тоже команда — извлекаем
                if code.startswith(bot.config.prefix):
                    code = ""

        if not code:
            await safe_edit(event,
                f"{CE.PYTHON} <b>Python exec</b>\n"
                f"<code>{bot.config.prefix}py &lt;code&gt;</code>\n\n"
                f"Доступные переменные:\n"
                f"  <code>event/e</code> — событие\n"
                f"  <code>client/c</code> — TelegramClient\n"
                f"  <code>bot/b</code> — Userbot\n"
                f"  <code>reply</code> — ответное сообщение\n"
                f"  <code>chat</code> — текущий чат\n"
                f"  <code>me</code> — ваш юзер\n"
                f"  <code>config</code> — конфиг\n"
                f"  <code>manager</code> — менеджер модулей"
            )
            return

        await safe_edit(event, f"{CE.PYTHON} <b>Выполняю...</b>")

        g = _make_exec_globals(event, bot)
        await _enrich_globals(g, event, bot)

        # Оборачиваем код в async-функцию
        indented = textwrap.indent(code, "    ")
        wrapped = (
            f"async def __kub_exec__():\n"
            f"{indented}\n"
        )

        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = cap_stdout = io.StringIO()
        sys.stderr = cap_stderr = io.StringIO()

        result = None
        error = None
        start_time = time.perf_counter()

        try:
            exec(wrapped, g)
            result = await g["__kub_exec__"]()
        except Exception:
            error = traceback.format_exc()
        finally:
            elapsed = time.perf_counter() - start_time
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        stdout_text = cap_stdout.getvalue()
        stderr_text = cap_stderr.getvalue()

        if error:
            # Убираем лишние строки трейсбека о wrapper
            lines = error.split("\n")
            cleaned = []
            skip_next = False
            for line in lines:
                if "__kub_exec__" in line or "exec(wrapped" in line:
                    skip_next = True
                    continue
                if skip_next and line.startswith("  "):
                    skip_next = False
                    continue
                skip_next = False
                cleaned.append(line)
            error_clean = "\n".join(cleaned).strip()

            text = f"{CE.CROSS} <b>Ошибка</b>\n\n<pre>{html_escape(error_clean)}</pre>"
            if stdout_text.strip():
                text += f"\n\n📤 <b>stdout до ошибки:</b>\n<pre>{html_escape(stdout_text.strip())}</pre>"
            text += f"\n\n⏱ <code>{elapsed:.3f}s</code>"
        else:
            text = f"{CE.PYTHON} <b>Python exec</b>\n\n"
            text += _format_output(stdout_text, stderr_text, result, elapsed)

        await safe_edit(event, _truncate(text))

    async def cmd_pyeval(event):
        """Вычислить Python-выражение (eval)."""
        expr = _get_code_from_text(event.raw_text, "pyeval")

        if not expr and event.is_reply:
            reply = await event.get_reply_message()
            if reply and reply.text:
                expr = reply.text

        if not expr:
            await safe_edit(event,
                f"{CE.PYTHON} <b>Python eval</b>\n"
                f"<code>{bot.config.prefix}pyeval &lt;expression&gt;</code>\n\n"
                f"Примеры:\n"
                f"  <code>{bot.config.prefix}pyeval 2 ** 100</code>\n"
                f"  <code>{bot.config.prefix}pyeval [i**2 for i in range(10)]</code>\n"
                f"  <code>{bot.config.prefix}pyeval len(manager.modules)</code>"
            )
            return

        g = _make_exec_globals(event, bot)
        await _enrich_globals(g, event, bot)

        start_time = time.perf_counter()
        try:
            result = eval(expr, g)
            if asyncio.iscoroutine(result) or asyncio.isfuture(result):
                result = await result
            elapsed = time.perf_counter() - start_time

            result_str = repr(result)
            result_type = type(result).__name__

            text = (
                f"{CE.PYTHON} <b>eval</b>\n\n"
                f"📥 <code>{html_escape(expr)}</code>\n\n"
                f"📤 <pre>{html_escape(str(result_str))}</pre>\n\n"
                f"📎 Тип: <code>{html_escape(result_type)}</code>"
            )

            # Для коллекций показываем длину
            if hasattr(result, '__len__'):
                try:
                    text += f" | Длина: <code>{len(result)}</code>"
                except Exception:
                    pass

            if elapsed < 0.001:
                time_str = f"{elapsed * 1_000_000:.1f}μs"
            elif elapsed < 1:
                time_str = f"{elapsed * 1000:.2f}ms"
            else:
                time_str = f"{elapsed:.3f}s"
            text += f"\n⏱ <code>{time_str}</code>"

        except Exception:
            elapsed = time.perf_counter() - start_time
            error = traceback.format_exc()
            text = (
                f"{CE.CROSS} <b>Ошибка eval</b>\n\n"
                f"📥 <code>{html_escape(expr)}</code>\n\n"
                f"<pre>{html_escape(error)}</pre>\n"
                f"⏱ <code>{elapsed:.3f}s</code>"
            )

        await safe_edit(event, _truncate(text))

    async def cmd_pyi(event):
        """Интерактивный Python — переменные сохраняются между вызовами."""
        code = _get_code_from_text(event.raw_text, "pyi")

        if not code:
            var_count = len([k for k in interactive_ns if not k.startswith("_")])
            await safe_edit(event,
                f"{CE.PYTHON} <b>Интерактивный Python</b>\n\n"
                f"<code>{bot.config.prefix}pyi &lt;code&gt;</code>\n\n"
                f"Переменные сохраняются между вызовами.\n"
                f"Текущих переменных: <code>{var_count}</code>\n\n"
                f"<code>{bot.config.prefix}pyreset</code> — сбросить сессию\n"
                f"<code>{bot.config.prefix}pyenv</code> — посмотреть переменные"
            )
            return

        await safe_edit(event, f"{CE.PYTHON} <b>Интерактивный режим...</b>")

        # Добавляем в namespace контекст
        interactive_ns["event"] = event
        interactive_ns["e"] = event
        interactive_ns["client"] = bot.client
        interactive_ns["c"] = bot.client
        interactive_ns["bot"] = bot
        interactive_ns["b"] = bot
        interactive_ns["config"] = bot.config

        try:
            interactive_ns["me"] = await bot.client.get_me()
        except Exception:
            pass
        try:
            interactive_ns["chat"] = await event.get_chat()
        except Exception:
            pass
        if event.is_reply:
            try:
                interactive_ns["reply"] = await event.get_reply_message()
            except Exception:
                pass

        # Определяем: это выражение или statements
        is_expr = False
        try:
            compile(code, "<pyi>", "eval")
            is_expr = True
        except SyntaxError:
            is_expr = False

        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = cap_stdout = io.StringIO()
        sys.stderr = cap_stderr = io.StringIO()

        result = None
        error = None
        start_time = time.perf_counter()

        try:
            if is_expr:
                result = eval(code, interactive_ns)
                if asyncio.iscoroutine(result) or asyncio.isfuture(result):
                    result = await result
            else:
                # Пробуем как async
                indented = textwrap.indent(code, "    ")
                wrapped = f"async def __kub_pyi__():\n{indented}\n"
                exec(wrapped, interactive_ns)
                fn = interactive_ns.pop("__kub_pyi__")
                result = await fn()
        except Exception:
            error = traceback.format_exc()
        finally:
            elapsed = time.perf_counter() - start_time
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        stdout_text = cap_stdout.getvalue()
        stderr_text = cap_stderr.getvalue()

        if error:
            text = (
                f"{CE.CROSS} <b>Ошибка (interactive)</b>\n\n"
                f"<pre>{html_escape(error)}</pre>\n"
                f"⏱ <code>{elapsed:.3f}s</code>"
            )
        else:
            text = f"{CE.PYTHON} <b>Interactive</b>\n\n"
            text += _format_output(stdout_text, stderr_text, result, elapsed)

        await safe_edit(event, _truncate(text))

    async def cmd_pyreset(event):
        """Сбросить интерактивную сессию."""
        interactive_ns.clear()
        interactive_ns.update({
            "__builtins__": __builtins__,
            "asyncio": asyncio,
            "os": os,
            "sys": sys,
            "time": time,
            "platform": platform,
        })
        await safe_edit(event, f"{CE.CHECK} <b>Интерактивная сессия сброшена</b>")

    async def cmd_pyenv(event):
        """Показать переменные интерактивной сессии."""
        user_vars = {}
        skip = {"__builtins__", "asyncio", "os", "sys", "time", "platform",
                "event", "e", "client", "c", "bot", "b", "config", "me",
                "chat", "reply", "manager"}

        for k, v in interactive_ns.items():
            if k.startswith("_"):
                continue
            if k in skip:
                continue
            user_vars[k] = v

        if not user_vars:
            await safe_edit(event,
                f"{CE.PYTHON} <b>Интерактивная сессия</b>\n\n"
                f"📭 Пользовательских переменных нет\n\n"
                f"Используйте <code>{bot.config.prefix}pyi x = 42</code> чтобы создать"
            )
            return

        text = f"{CE.PYTHON} <b>Переменные сессии</b> ({len(user_vars)})\n━━━━━━━━━━━━━━━━━━━━━\n\n"

        for k, v in sorted(user_vars.items()):
            type_name = type(v).__name__
            val_repr = repr(v)
            if len(val_repr) > 80:
                val_repr = val_repr[:77] + "..."
            text += f"  <code>{html_escape(k)}</code>: <code>{html_escape(type_name)}</code> = <code>{html_escape(val_repr)}</code>\n"

        text += f"\n{CE.TRASH} <code>{bot.config.prefix}pyreset</code> — сбросить"
        await safe_edit(event, _truncate(text))

    async def cmd_pytime(event):
        """Замерить время выполнения кода."""
        code = _get_code_from_text(event.raw_text, "pytime")

        if not code:
            await safe_edit(event,
                f"{CE.CLOCK} <b>Python Timer</b>\n"
                f"<code>{bot.config.prefix}pytime &lt;code&gt;</code>\n\n"
                f"Замеряет время выполнения кода.\n\n"
                f"Пример:\n"
                f"  <code>{bot.config.prefix}pytime sum(range(1000000))</code>"
            )
            return

        await safe_edit(event, f"{CE.CLOCK} <b>Замеряю...</b>")

        g = _make_exec_globals(event, bot)
        await _enrich_globals(g, event, bot)

        # Пробуем как выражение
        is_expr = False
        try:
            compile(code, "<pytime>", "eval")
            is_expr = True
        except SyntaxError:
            is_expr = False

        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()

        error = None
        result = None

        try:
            if is_expr:
                start = time.perf_counter()
                result = eval(code, g)
                if asyncio.iscoroutine(result) or asyncio.isfuture(result):
                    result = await result
                elapsed = time.perf_counter() - start
            else:
                indented = textwrap.indent(code, "    ")
                wrapped = f"async def __kub_time__():\n{indented}\n"
                exec(wrapped, g)
                start = time.perf_counter()
                result = await g["__kub_time__"]()
                elapsed = time.perf_counter() - start
        except Exception:
            elapsed = time.perf_counter() - start if 'start' in dir() else 0
            error = traceback.format_exc()
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        if error:
            text = (
                f"{CE.CROSS} <b>Ошибка</b>\n\n"
                f"<pre>{html_escape(error)}</pre>\n"
                f"⏱ <code>{elapsed:.6f}s</code>"
            )
        else:
            # Красивый вывод времени
            if elapsed < 0.000001:
                time_str = f"{elapsed * 1_000_000_000:.1f}ns"
            elif elapsed < 0.001:
                time_str = f"{elapsed * 1_000_000:.2f}μs"
            elif elapsed < 1:
                time_str = f"{elapsed * 1000:.3f}ms"
            else:
                time_str = f"{elapsed:.4f}s"

            result_text = ""
            if result is not None:
                r_str = repr(result)
                if len(r_str) > 200:
                    r_str = r_str[:197] + "..."
                result_text = f"\n\n📎 <pre>{html_escape(r_str)}</pre>"

            text = (
                f"{CE.CLOCK} <b>Замер времени</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📥 <pre>{html_escape(code)}</pre>\n\n"
                f"⏱ <b>{time_str}</b>"
                f"{result_text}"
            )

        await safe_edit(event, _truncate(text))

    async def cmd_pyrun(event):
        """Выполнить код N раз и показать статистику."""
        raw = _get_code_from_text(event.raw_text, "pyrun")

        if not raw:
            await safe_edit(event,
                f"{CE.STATS} <b>Python Benchmark</b>\n"
                f"<code>{bot.config.prefix}pyrun &lt;N&gt; &lt;code&gt;</code>\n\n"
                f"Выполняет код N раз и показывает статистику.\n\n"
                f"Пример:\n"
                f"  <code>{bot.config.prefix}pyrun 1000 sum(range(100))</code>"
            )
            return

        parts = raw.split(maxsplit=1)
        try:
            n = int(parts[0])
            code = parts[1] if len(parts) > 1 else ""
        except (ValueError, IndexError):
            await safe_edit(event,
                f"{CE.CROSS} <code>{bot.config.prefix}pyrun &lt;N&gt; &lt;code&gt;</code>"
            )
            return

        if not code:
            await safe_edit(event, f"{CE.CROSS} Укажите код после числа")
            return

        n = max(1, min(n, 100000))

        await safe_edit(event, f"{CE.STATS} <b>Бенчмарк ({n} итераций)...</b>")

        g = _make_exec_globals(event, bot)
        await _enrich_globals(g, event, bot)

        # Определяем тип
        is_expr = False
        try:
            compile(code, "<pyrun>", "eval")
            is_expr = True
        except SyntaxError:
            pass

        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()

        times = []
        error = None
        last_result = None

        try:
            if is_expr:
                compiled = compile(code, "<pyrun>", "eval")
                for _ in range(n):
                    start = time.perf_counter()
                    last_result = eval(compiled, g)
                    if asyncio.iscoroutine(last_result) or asyncio.isfuture(last_result):
                        last_result = await last_result
                    times.append(time.perf_counter() - start)
            else:
                indented = textwrap.indent(code, "    ")
                wrapped = f"async def __kub_run__():\n{indented}\n"
                exec(wrapped, g)
                fn = g["__kub_run__"]
                for _ in range(n):
                    start = time.perf_counter()
                    last_result = await fn()
                    times.append(time.perf_counter() - start)
        except Exception:
            error = traceback.format_exc()
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        if error:
            text = (
                f"{CE.CROSS} <b>Ошибка на итерации {len(times) + 1}</b>\n\n"
                f"<pre>{html_escape(error)}</pre>"
            )
        else:
            total = sum(times)
            avg = total / len(times)
            mn = min(times)
            mx = max(times)

            def fmt_time(t):
                if t < 0.000001:
                    return f"{t * 1_000_000_000:.1f}ns"
                elif t < 0.001:
                    return f"{t * 1_000_000:.2f}μs"
                elif t < 1:
                    return f"{t * 1000:.3f}ms"
                return f"{t:.4f}s"

            # Медиана
            sorted_times = sorted(times)
            mid = len(sorted_times) // 2
            if len(sorted_times) % 2 == 0:
                median = (sorted_times[mid - 1] + sorted_times[mid]) / 2
            else:
                median = sorted_times[mid]

            result_text = ""
            if last_result is not None:
                r_str = repr(last_result)
                if len(r_str) > 100:
                    r_str = r_str[:97] + "..."
                result_text = f"\n📎 Результат: <code>{html_escape(r_str)}</code>"

            text = (
                f"{CE.STATS} <b>Бенчмарк</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📥 <pre>{html_escape(code)}</pre>\n\n"
                f"🔁 Итераций: <b>{n}</b>\n"
                f"⏱ Общее: <b>{fmt_time(total)}</b>\n"
                f"📊 Среднее: <b>{fmt_time(avg)}</b>\n"
                f"📉 Медиана: <b>{fmt_time(median)}</b>\n"
                f"⬇️ Мин: <code>{fmt_time(mn)}</code>\n"
                f"⬆️ Макс: <code>{fmt_time(mx)}</code>"
                f"{result_text}"
            )

        await safe_edit(event, _truncate(text))

    async def cmd_sysinfo(event):
        """Подробная информация о системе."""
        import struct

        me = await bot.client.get_me()
        up = time.time() - bot.start_time

        # Память процесса
        mem_info = "N/A"
        try:
            import resource
            usage = resource.getrusage(resource.RUSAGE_SELF)
            mem_mb = usage.ru_maxrss / 1024  # Linux: KB -> MB
            if platform.system() == "Darwin":
                mem_mb = usage.ru_maxrss / (1024 * 1024)  # macOS: bytes -> MB
            mem_info = f"{mem_mb:.1f} MB"
        except Exception:
            try:
                # Fallback через /proc на Linux
                with open(f"/proc/{os.getpid()}/status") as f:
                    for line in f:
                        if line.startswith("VmRSS:"):
                            mem_kb = int(line.split()[1])
                            mem_info = f"{mem_kb / 1024:.1f} MB"
                            break
            except Exception:
                pass

        # Кол-во ядер
        try:
            cpu_count = os.cpu_count() or "?"
        except Exception:
            cpu_count = "?"

        # Версии
        py_impl = platform.python_implementation()
        py_ver = platform.python_version()
        py_build = platform.python_build()[0]
        arch = platform.machine()
        bits = struct.calcsize("P") * 8

        # Модули
        tm = len(bot.module_manager.modules)
        um = len(bot.module_manager.get_user_modules())
        cmds = len(bot._command_handlers)

        text = (
            f"{CE.PC} <b>Системная информация</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>🖥 Система:</b>\n"
            f"  ├ ОС: <code>{platform.system()} {platform.release()}</code>\n"
            f"  ├ Платформа: <code>{platform.platform()}</code>\n"
            f"  ├ Архитектура: <code>{arch} ({bits}-bit)</code>\n"
            f"  ├ CPU ядер: <code>{cpu_count}</code>\n"
            f"  └ Память: <code>{mem_info}</code>\n\n"
            f"<b>{CE.PYTHON} Python:</b>\n"
            f"  ├ Версия: <code>{py_ver}</code>\n"
            f"  ├ Реализация: <code>{py_impl}</code>\n"
            f"  ├ Билд: <code>{py_build}</code>\n"
            f"  └ Путь: <code>{html_escape(sys.executable)}</code>\n\n"
            f"<b>{CE.BRAND} {BRAND_NAME}:</b>\n"
            f"  ├ Версия: <code>{BRAND_VERSION}</code>\n"
            f"  ├ Telethon: <code>{html_escape(str(getattr(bot, '_telethon_ver', '?')))}</code>\n"
            f"  ├ Модулей: <code>{tm}</code> (🔵{tm - um} 🟢{um})\n"
            f"  ├ Команд: <code>{cmds}</code>\n"
            f"  ├ PID: <code>{os.getpid()}</code>\n"
            f"  └ Аптайм: <code>{_format_uptime(up)}</code>\n"
        )

        await safe_edit(event, text)

    async def cmd_pyfile(event):
        """Выполнить .py файл из ответа на документ."""
        if not event.is_reply:
            await safe_edit(event,
                f"{CE.FILE} <b>Выполнить .py файл</b>\n"
                f"Ответьте на <code>.py</code> документ командой <code>{bot.config.prefix}pyfile</code>"
            )
            return

        reply = await event.get_reply_message()
        if not reply.document:
            await safe_edit(event, f"{CE.CROSS} В ответе нет документа")
            return

        # Проверяем имя файла
        filename = None
        for attr in reply.document.attributes:
            if hasattr(attr, 'file_name'):
                filename = attr.file_name
                break

        if filename and not filename.endswith(".py"):
            await safe_edit(event, f"{CE.CROSS} Только <code>.py</code> файлы")
            return

        await safe_edit(event, f"{CE.PYTHON} <b>Скачиваю и выполняю...</b>")

        try:
            content = await bot.client.download_media(reply, bytes)
            code = content.decode("utf-8")
        except Exception as e:
            await safe_edit(event, f"{CE.CROSS} Ошибка загрузки: <code>{html_escape(str(e))}</code>")
            return

        g = _make_exec_globals(event, bot)
        await _enrich_globals(g, event, bot)

        # Оборачиваем
        indented = textwrap.indent(code, "    ")
        wrapped = f"async def __kub_file__():\n{indented}\n"

        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = cap_stdout = io.StringIO()
        sys.stderr = cap_stderr = io.StringIO()

        result = None
        error = None
        start_time = time.perf_counter()

        try:
            exec(wrapped, g)
            result = await g["__kub_file__"]()
        except Exception:
            error = traceback.format_exc()
        finally:
            elapsed = time.perf_counter() - start_time
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        stdout_text = cap_stdout.getvalue()
        stderr_text = cap_stderr.getvalue()
        fn_display = html_escape(filename or "unknown.py")

        if error:
            text = (
                f"{CE.CROSS} <b>Ошибка в {fn_display}</b>\n\n"
                f"<pre>{html_escape(error)}</pre>\n"
                f"⏱ <code>{elapsed:.3f}s</code>"
            )
        else:
            text = f"{CE.PYTHON} <b>{fn_display}</b>\n\n"
            text += _format_output(stdout_text, stderr_text, result, elapsed)

        await safe_edit(event, _truncate(text))

    def _format_uptime(seconds: float) -> str:
        """Локальный форматировщик аптайма."""
        from datetime import timedelta
        td = timedelta(seconds=int(seconds))
        d = td.days
        h, rem = divmod(td.seconds, 3600)
        m, s = divmod(rem, 60)
        parts = []
        if d: parts.append(f"{d}д")
        if h: parts.append(f"{h}ч")
        if m: parts.append(f"{m}м")
        parts.append(f"{s}с")
        return " ".join(parts)

    # ─── Получаем ссылки на утилиты из bot-контекста ───
    # Они уже инжектированы в модуль загрузчиком:
    # html_escape, html_code, html_pre, safe_edit, CE, BRAND_NAME, BRAND_VERSION

    # Но на всякий случай fallback:
    try:
        _ = html_escape
    except NameError:
        html_escape = lambda t: str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    try:
        _ = safe_edit
    except NameError:
        async def safe_edit(event, text, **kw):
            await event.edit(text, parse_mode="html", **kw)

    try:
        _ = CE
    except NameError:
        class _FakeCE:
            def __getattr__(self, name):
                return "⭐"
        CE = _FakeCE()

    try:
        _ = BRAND_NAME
    except NameError:
        BRAND_NAME = "kazhurkeUserBot"
        BRAND_VERSION = "2.4.0"

    # Сохраняем версию telethon в bot для sysinfo
    try:
        from telethon import version as tv
        bot._telethon_ver = tv.__version__
    except Exception:
        bot._telethon_ver = "?"

    # ─── Регистрация модуля ───

    from dataclasses import dataclass, field as df

    p = bot.config.prefix

    # Используем классы из основного кода
    # Module и Command уже доступны через bot
    mod_cls = type(list(bot.module_manager.modules.values())[0]) if bot.module_manager.modules else None
    cmd_cls = None

    if mod_cls:
        # Получаем Command class из существующих модулей
        for m in bot.module_manager.modules.values():
            if m.commands:
                cmd_cls = type(list(m.commands.values())[0])
                break

    # Fallback — импортируем напрямую (модуль загружается в том же процессе)
    if not mod_cls or not cmd_cls:
        # Они определены в главном файле, и доступны через sys.modules
        import __main__
        mod_cls = getattr(__main__, 'Module', None)
        cmd_cls = getattr(__main__, 'Command', None)

    if not mod_cls or not cmd_cls:
        # Последний fallback — через уже загруженные модули
        for mod_name_iter, mod_obj in bot.module_manager.modules.items():
            mod_cls = type(mod_obj)
            for cmd_obj in mod_obj.commands.values():
                cmd_cls = type(cmd_obj)
                break
            if cmd_cls:
                break

    module = mod_cls(
        name="python_tools",
        description="Расширенные Python-команды",
        author="kazhurkeUserBot",
        version="1.2",
    )

    module.commands = {
        "py": cmd_cls("py", cmd_py, "Выполнить Python (exec)", "python_tools",
                       f"{p}py <code>", "dev"),
        "pyeval": cmd_cls("pyeval", cmd_pyeval, "Вычислить выражение", "python_tools",
                          f"{p}pyeval <expr>", "dev"),
        "pyi": cmd_cls("pyi", cmd_pyi, "Интерактивный Python", "python_tools",
                        f"{p}pyi <code>", "dev"),
        "pyreset": cmd_cls("pyreset", cmd_pyreset, "Сбросить сессию", "python_tools",
                           f"{p}pyreset", "dev"),
        "pyenv": cmd_cls("pyenv", cmd_pyenv, "Переменные сессии", "python_tools",
                         f"{p}pyenv", "dev"),
        "pytime": cmd_cls("pytime", cmd_pytime, "Замер времени", "python_tools",
                          f"{p}pytime <code>", "dev"),
        "pyrun": cmd_cls("pyrun", cmd_pyrun, "Бенчмарк (N раз)", "python_tools",
                         f"{p}pyrun <N> <code>", "dev"),
        "sysinfo": cmd_cls("sysinfo", cmd_sysinfo, "Инфо о системе", "python_tools",
                           f"{p}sysinfo", "dev"),
        "pyfile": cmd_cls("pyfile", cmd_pyfile, "Выполнить .py файл", "python_tools",
                          f"{p}pyfile (reply)", "dev"),
    }

    bot.module_manager.register_module(module)
    bot.register_commands(module)
