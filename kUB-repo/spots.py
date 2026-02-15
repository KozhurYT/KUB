# modules/spots.py
"""
🎵 Spotify — слушай музыку, тексты, карточки треков
authors: @LoLpryvet, port: @Hairpin00 (конвертировано для kazhurkeUserBot)
version: 1.0.2
requires: spotipy, aiohttp, pillow
"""

import asyncio
import logging
import tempfile
import os
import re
import textwrap
from io import BytesIO

logger = logging.getLogger("KUB.spots")

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

try:
    import spotipy
    import spotipy.oauth2
    HAS_SPOTIPY = True
except ImportError:
    HAS_SPOTIPY = False

try:
    from PIL import Image, ImageDraw, ImageFont, ImageStat
    import colorsys
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def setup(bot):
    import sys
    main = sys.modules["__main__"]
    Module, Command = main.Module, main.Command
    mc = main.module_config
    mc_set = main.module_config_set
    client = bot.client
    p = bot.config.prefix

    mod = Module(
        name="spots",
        description="Spotify: треки, тексты, карточки",
        author="@LoLpryvet & @Hairpin00",
        version="1.0.2",
        settings_schema=[
            {"key": "client_id", "label": "Spotify Client ID", "type": "str", "default": "",
             "description": "Из developer.spotify.com/dashboard"},
            {"key": "client_secret", "label": "Spotify Client Secret", "type": "str", "default": "",
             "description": "Из developer.spotify.com/dashboard"},
            {"key": "auth_token", "label": "Auth Token", "type": "str", "default": "",
             "description": "Заполняется автоматически"},
            {"key": "refresh_token", "label": "Refresh Token", "type": "str", "default": "",
             "description": "Заполняется автоматически"},
            {"key": "scopes", "label": "Scopes", "type": "str",
             "default": "user-read-playback-state user-library-read"},
            {"key": "genius_token", "label": "Genius API Token", "type": "str", "default": "",
             "description": "Для поиска текстов на Genius (опционально)"},
            {"key": "font_url", "label": "URL шрифта", "type": "str",
             "default": "https://raw.githubusercontent.com/kamekuro/assets/master/fonts/Onest-Bold.ttf"},
        ],
    )

    # ─── Состояние ───
    _state = {
        "realtime_data": None,
        "playnow_data": None,
    }

    # ─── Утилиты ───

    def _get_sp():
        token = mc(bot, "spots", "auth_token", "")
        if not token:
            return None
        return spotipy.Spotify(auth=token)

    def _check_deps():
        missing = []
        if not HAS_SPOTIPY:
            missing.append("spotipy")
        if not HAS_AIOHTTP:
            missing.append("aiohttp")
        if not HAS_PIL:
            missing.append("pillow")
        return missing

    async def _load_font(size):
        try:
            font_url = mc(bot, "spots", "font_url",
                          "https://raw.githubusercontent.com/kamekuro/assets/master/fonts/Onest-Bold.ttf")
            async with aiohttp.ClientSession() as session:
                async with session.get(font_url) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        return ImageFont.truetype(BytesIO(data), size)
        except Exception:
            pass
        for fallback in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                         "arial.ttf", "DejaVuSans-Bold.ttf"]:
            try:
                return ImageFont.truetype(fallback, size)
            except Exception:
                continue
        return ImageFont.load_default()

    # ─── Тексты песен ───

    async def _get_lyrics_lrclib(artist, title, duration_ms=None):
        try:
            clean_t = re.sub(r'\([^)]*\)', '', title).strip()
            clean_a = re.sub(r'\([^)]*\)', '', artist).strip()
            params = {"artist_name": clean_a, "track_name": clean_t}
            if duration_ms:
                params["duration"] = duration_ms // 1000
            async with aiohttp.ClientSession() as s:
                async with s.get("https://lrclib.net/api/search", params=params) as r:
                    if r.status == 200:
                        data = await r.json()
                        if data:
                            d = data[0]
                            synced = d.get("syncedLyrics")
                            plain = d.get("plainLyrics")
                            if synced:
                                return {"type": "synced", "lyrics": synced, "plain": plain}
                            elif plain:
                                return {"type": "plain", "lyrics": plain}
        except Exception as e:
            logger.error(f"lrclib: {e}")
        return None

    async def _get_lyrics_genius(artist, title):
        token = mc(bot, "spots", "genius_token", "")
        if not token:
            return None
        try:
            clean_t = re.sub(r'\([^)]*\)', '', title).strip()
            clean_a = re.sub(r'\([^)]*\)', '', artist).strip()
            headers = {"Authorization": f"Bearer {token}"}
            params = {"q": f"{clean_a} {clean_t}"}
            async with aiohttp.ClientSession() as s:
                async with s.get("https://api.genius.com/search", headers=headers, params=params) as r:
                    if r.status != 200:
                        return None
                    data = await r.json()
                    hits = data.get("response", {}).get("hits", [])
                    if not hits:
                        return None
                    url = hits[0].get("result", {}).get("url")
                    if not url:
                        return None
                async with s.get(url) as r2:
                    if r2.status != 200:
                        return None
                    html = await r2.text()
                    pat = r'<div[^>]*data-lyrics-container="true"[^>]*>(.*?)</div>'
                    matches = re.findall(pat, html, re.DOTALL | re.IGNORECASE)
                    if matches:
                        lyrics = re.sub(r'<br[^>]*>', '\n', matches[0])
                        lyrics = re.sub(r'<[^>]+>', '', lyrics).strip()
                        for old, new in [("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                                         ("&quot;", '"'), ("&#x27;", "'")]:
                            lyrics = lyrics.replace(old, new)
                        return lyrics if lyrics else None
        except Exception as e:
            logger.error(f"genius: {e}")
        return None

    async def _get_lyrics_ovh(artist, title):
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(f"https://api.lyrics.ovh/v1/{artist}/{title}") as r:
                    if r.status == 200:
                        data = await r.json()
                        lyr = data.get("lyrics")
                        if lyr:
                            return {"type": "plain", "lyrics": lyr}
        except Exception as e:
            logger.error(f"lyrics.ovh: {e}")
        return None

    def _parse_synced(synced):
        if not synced:
            return None
        lines = synced.strip().split("\n")
        parsed = []
        for line in lines:
            m = re.match(r'\[(\d{2}):(\d{2})\.(\d{2})\](.*)', line)
            if m:
                ms = (int(m[1]) * 60 + int(m[2])) * 1000 + int(m[3]) * 10
                txt = m[4].strip()
                if txt:
                    parsed.append({"time_ms": ms, "text": txt})
        return parsed

    async def _get_synced_data(artist, title, duration_ms=None):
        try:
            clean_t = re.sub(r'\([^)]*\)', '', title).strip()
            clean_a = re.sub(r'\([^)]*\)', '', artist).strip()
            params = {"artist_name": clean_a, "track_name": clean_t}
            if duration_ms:
                params["duration"] = duration_ms // 1000
            async with aiohttp.ClientSession() as s:
                async with s.get("https://lrclib.net/api/search", params=params) as r:
                    if r.status == 200:
                        data = await r.json()
                        if data:
                            synced = data[0].get("syncedLyrics")
                            if synced:
                                return _parse_synced(synced)
        except Exception as e:
            logger.error(f"synced: {e}")
        return None

    def _get_current_line(lyrics_data, progress_ms):
        if not lyrics_data:
            return None, -1
        for i, line in enumerate(lyrics_data):
            if line["time_ms"] <= progress_ms:
                if i + 1 < len(lyrics_data):
                    if progress_ms < lyrics_data[i + 1]["time_ms"]:
                        return line, i
                else:
                    return line, i
        return None, -1

    def _format_rt_lyrics(lyrics_data, idx, ctx=2):
        if not lyrics_data or idx == -1:
            return "🎵 Ожидание..."
        lines = []
        start = max(0, idx - ctx)
        end = min(len(lyrics_data), idx + ctx + 1)
        for i in range(start, end):
            t = lyrics_data[i]["text"]
            if i == idx:
                lines.append(f"**▶️ {t}**")
            elif i < idx:
                lines.append(f"_{t}_")
            else:
                lines.append(t)
        return "\n".join(lines)

    def _format_synced_lyrics(synced, progress_ms=None):
        if not synced:
            return None
        lines = synced.strip().split("\n")
        out = []
        found = False
        for line in lines:
            m = re.match(r'\[(\d{2}):(\d{2})\.(\d{2})\](.*)', line)
            if m:
                ms = (int(m[1]) * 60 + int(m[2])) * 1000 + int(m[3]) * 10
                txt = m[4].strip()
                if progress_ms and not found and ms <= progress_ms:
                    nxt = None
                    li = lines.index(line)
                    if li + 1 < len(lines):
                        nm = re.match(r'\[(\d{2}):(\d{2})\.(\d{2})\]', lines[li + 1])
                        if nm:
                            nxt = (int(nm[1]) * 60 + int(nm[2])) * 1000 + int(nm[3]) * 10
                    if nxt is None or progress_ms < nxt:
                        out.append(f"**→ {txt}**")
                        found = True
                    else:
                        out.append(txt)
                else:
                    out.append(txt)
            elif line.strip():
                out.append(line.strip())
        return "\n".join(out)

    # ─── Карточки ───

    async def _create_card(track_info, with_time=True):
        if not HAS_PIL or not HAS_AIOHTTP:
            return None
        try:
            W = 600
            H = 250 if with_time else 200
            title_font = await _load_font(34)
            artist_font = await _load_font(22)
            time_font = await _load_font(18) if with_time else None

            async with aiohttp.ClientSession() as s:
                async with s.get(track_info["album_art"]) as r:
                    art_orig = Image.open(BytesIO(await r.read()))

            small = art_orig.resize((50, 50))
            stat = ImageStat.Stat(small)
            dr, dg, db = [int(x) for x in stat.mean[:3]]

            h, sv, v = colorsys.rgb_to_hsv(dr / 255, dg / 255, db / 255)
            v = max(0.15, v * 0.4)
            sv = min(1.0, sv * 1.1)
            br, bg, bb = [int(x * 255) for x in colorsys.hsv_to_rgb(h, sv, v)]

            card = Image.new("RGB", (W, H), (br, bg, bb))
            draw = ImageDraw.Draw(card)
            for y in range(H):
                f = y / H
                draw.line([(0, y), (W, y)], fill=(
                    int(br * (1 - f * 0.2)), int(bg * (1 - f * 0.2)), int(bb * (1 - f * 0.2))
                ))

            asize = 180 if with_time else 160
            art = art_orig.resize((asize, asize), Image.Resampling.LANCZOS)
            mask = Image.new("L", (asize, asize), 0)
            ImageDraw.Draw(mask).rounded_rectangle([0, 0, asize, asize], radius=15, fill=255)
            art.putalpha(mask)

            ax = 20 if with_time else 15
            ay = (H - asize) // 2
            card.paste(art, (ax, ay), art)

            tx = ax + asize + 20 if with_time else ax + asize + 15
            name = track_info["track_name"]
            if len(name) > 25:
                name = name[:25] + "..."
            wrapped = textwrap.wrap(name, width=18)
            ty = ay + 5
            for i, line in enumerate(wrapped[:2]):
                draw.text((tx, ty + i * 40), line, font=title_font, fill="white")

            aname = track_info["artist_name"]
            if len(aname) > 30:
                aname = aname[:30] + "..."
            aty = ty + (len(wrapped) * 40 if wrapped else 40)
            draw.text((tx, aty), aname, font=artist_font, fill="#A0A0A0")

            if with_time and time_font:
                py = H - 45
                pw = W - tx - 20
                ph = 5
                draw.rounded_rectangle([tx, py, tx + pw, py + ph], radius=2, fill="#555555")
                cur = track_info.get("current_time", "0:00")
                dur = track_info["duration"]
                try:
                    cp = cur.split(":")
                    cs = int(cp[0]) * 60 + int(cp[1])
                    dp = dur.split(":")
                    ds = int(dp[0]) * 60 + int(dp[1])
                    ratio = cs / ds if ds > 0 else 0
                except Exception:
                    ratio = 0
                fill = int(pw * ratio)
                draw.rounded_rectangle([tx, py, tx + fill, py + ph], radius=2, fill="#1DB954")
                draw.text((tx, py + 10), cur, font=time_font, fill="#A0A0A0")
                tb = draw.textbbox((0, 0), dur, font=time_font)
                draw.text((tx + pw - (tb[2] - tb[0]), py + 10), dur, font=time_font, fill="#A0A0A0")
            elif not with_time:
                live_font = await _load_font(16)
                ltxt = "LIVE"
                lb = draw.textbbox((0, 0), ltxt, font=live_font)
                lx = W - (lb[2] - lb[0]) - 20
                draw.ellipse([lx - 20, 20, lx - 8, 32], fill="#FF0000")
                draw.text((lx, 18), ltxt, font=live_font, fill="#FF0000")

            path = os.path.join(tempfile.gettempdir(), f"kub_spots_{track_info['track_id']}.png")
            card.save(path, "PNG")
            return path
        except Exception as e:
            logger.error(f"card: {e}")
            return None

    # ─── Realtime loops ───

    async def _realtime_loop():
        data = _state["realtime_data"]
        if not data or not data["active"]:
            return
        try:
            count = 0
            pause = 0
            while data["active"] and count < 600:
                try:
                    sp = _get_sp()
                    if not sp:
                        break
                    pb = sp.current_playback()
                    if not pb or not pb.get("item"):
                        pause += 1
                        if pause > 30:
                            break
                        await asyncio.sleep(1)
                        count += 1
                        continue
                    if pb["item"].get("id", "") != data["track_id"]:
                        break
                    progress = pb.get("progress_ms", 0)
                    if not pb.get("is_playing", False):
                        pause += 1
                        if pause >= 120:
                            break
                        await asyncio.sleep(1)
                        count += 1
                        continue
                    pause = 0
                    _, idx = _get_current_line(data["lyrics_data"], progress)
                    if idx != data["last_idx"]:
                        fmt = _format_rt_lyrics(data["lyrics_data"], idx)
                        data["last_idx"] = idx
                        try:
                            await client.edit_message(data["chat_id"], data["msg_id"],
                                                      data["header"] + fmt)
                        except Exception:
                            break
                    await asyncio.sleep(1)
                    count += 1
                except Exception as e:
                    logger.error(f"rt loop: {e}")
                    await asyncio.sleep(2)
                    count += 1
            data["active"] = False
            try:
                await client.edit_message(data["chat_id"], data["msg_id"],
                                          data["header"] + "✅ _Сеанс завершён_")
            except Exception:
                pass
        except Exception as e:
            logger.error(f"rt critical: {e}")
            data["active"] = False

    async def _playnow_loop():
        data = _state["playnow_data"]
        if not data or not data["active"]:
            return
        try:
            count = 0
            pause = 0
            cur_tid = data.get("track_id")
            while data["active"] and count < 1200:
                try:
                    sp = _get_sp()
                    if not sp:
                        break
                    pb = sp.current_playback()
                    if not pb or not pb.get("item"):
                        pause += 1
                        if pause > 30:
                            break
                        await asyncio.sleep(1)
                        count += 1
                        continue
                    new_tid = pb["item"].get("id", "")
                    progress = pb.get("progress_ms", 0)
                    if new_tid != cur_tid:
                        # Трек сменился — обновляем карточку
                        track = pb["item"]
                        ti = {
                            "track_name": track.get("name", "?"),
                            "artist_name": track["artists"][0].get("name", "?"),
                            "album_art": track["album"]["images"][0]["url"],
                            "track_id": new_tid,
                        }
                        card = await _create_card(ti, with_time=False)
                        ld = await _get_synced_data(ti["artist_name"], ti["track_name"],
                                                     track.get("duration_ms", 0))
                        cap = "🎵 Ожидание..." if ld else "❌ _Текст не найден_"
                        data["lyrics_data"] = ld
                        data["last_idx"] = -1
                        cur_tid = new_tid
                        data["track_id"] = new_tid
                        if card:
                            try:
                                await client.delete_messages(data["chat_id"], data["msg_id"])
                            except Exception:
                                pass
                            msg = await client.send_file(data["chat_id"], card, caption=cap)
                            data["msg_id"] = msg.id
                            try:
                                os.remove(card)
                            except Exception:
                                pass
                        continue
                    if not pb.get("is_playing", False):
                        pause += 1
                        if pause >= 120:
                            break
                        await asyncio.sleep(1)
                        count += 1
                        continue
                    pause = 0
                    if data.get("lyrics_data"):
                        _, idx = _get_current_line(data["lyrics_data"], progress)
                        if idx != data.get("last_idx", -1):
                            fmt = _format_rt_lyrics(data["lyrics_data"], idx)
                            data["last_idx"] = idx
                            try:
                                await client.edit_message(data["chat_id"], data["msg_id"], fmt)
                            except Exception:
                                break
                    await asyncio.sleep(1)
                    count += 1
                except Exception as e:
                    logger.error(f"playnow loop: {e}")
                    await asyncio.sleep(2)
                    count += 1
            data["active"] = False
            try:
                await client.edit_message(data["chat_id"], data["msg_id"],
                                          "✅ _Live-сеанс завершён_")
            except Exception:
                pass
        except Exception as e:
            logger.error(f"playnow critical: {e}")
            data["active"] = False

    # ─── Команды ───

    async def _check(event):
        missing = _check_deps()
        if missing:
            await event.edit(f"❌ Установите: `pip install {' '.join(missing)}`")
            return False
        if not mc(bot, "spots", "auth_token", ""):
            await event.edit(f"❌ Авторизуйтесь: `{p}spauth`")
            return False
        return True

    async def cmd_spauth(event):
        """Авторизация в Spotify."""
        missing = _check_deps()
        if missing:
            await event.edit(f"❌ `pip install {' '.join(missing)}`")
            return
        cid = mc(bot, "spots", "client_id", "")
        csec = mc(bot, "spots", "client_secret", "")
        if not cid or not csec:
            await event.edit(
                f"🔐 **Настройка Spotify**\n━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"1. Создайте приложение: [developer.spotify.com](https://developer.spotify.com/dashboard)\n"
                f"2. Redirect URI: `https://sp.fajox.one`\n"
                f"3. Установите client\\_id и client\\_secret через `{p}settings` (inline)\n"
                f"   или вручную:\n"
                f"   Модуль `spots` → ⚙️ Настройки\n"
                f"4. Снова `{p}spauth`"
            )
            return
        scopes = mc(bot, "spots", "scopes", "user-read-playback-state user-library-read")
        oauth = spotipy.oauth2.SpotifyOAuth(
            client_id=cid, client_secret=csec,
            redirect_uri="https://sp.fajox.one", scope=scopes
        )
        url = oauth.get_authorize_url()
        await event.edit(
            f"🔗 **Авторизация Spotify**\n\n"
            f"[Перейдите по ссылке]({url})\n\n"
            f"Затем: `{p}spcode <код>`"
        )

    async def cmd_spcode(event):
        """Ввести код авторизации."""
        args = event.text.split(maxsplit=1)
        if len(args) < 2:
            await event.edit(f"❌ `{p}spcode <код>`")
            return
        cid = mc(bot, "spots", "client_id", "")
        csec = mc(bot, "spots", "client_secret", "")
        if not cid or not csec:
            await event.edit(f"❌ Сначала `{p}spauth`")
            return
        scopes = mc(bot, "spots", "scopes", "user-read-playback-state user-library-read")
        oauth = spotipy.oauth2.SpotifyOAuth(
            client_id=cid, client_secret=csec,
            redirect_uri="https://sp.fajox.one", scope=scopes
        )
        try:
            token_info = oauth.get_access_token(args[1].strip())
            mc_set(bot, "spots", "auth_token", token_info["access_token"])
            mc_set(bot, "spots", "refresh_token", token_info["refresh_token"])
            await event.edit("✅ **Авторизация успешна!** 🎵")
        except Exception as e:
            await event.edit(f"❌ Ошибка: `{e}`")

    async def cmd_now(event):
        """Карточка текущего трека."""
        if not await _check(event):
            return
        try:
            sp = _get_sp()
            pb = sp.current_playback()
            if not pb or not pb.get("item"):
                await event.edit("❌ Ничего не играет")
                return
            await event.edit("🎵 Загружаю...")
            track = pb["item"]
            dur_ms = track.get("duration_ms", 0)
            prog_ms = pb.get("progress_ms", 0)
            dm, ds = divmod(dur_ms // 1000, 60)
            pm, ps = divmod(prog_ms // 1000, 60)
            tid = track.get("id", "")
            ti = {
                "track_name": track.get("name", "?"),
                "artist_name": track["artists"][0].get("name", "?"),
                "album_name": track["album"].get("name", "?"),
                "duration": f"{dm}:{ds:02d}",
                "current_time": f"{pm}:{ps:02d}",
                "album_art": track["album"]["images"][0]["url"],
                "track_id": tid,
            }
            card = await _create_card(ti, with_time=True)
            turl = track["external_urls"]["spotify"]
            slink = f"https://song.link/s/{tid}"
            cap = f"🎵 [Spotify]({turl}) • [song.link]({slink})"
            if card:
                await event.delete()
                await client.send_file(event.chat_id, card, caption=cap,
                                        reply_to=event.reply_to_msg_id if event.is_reply else None)
                try:
                    os.remove(card)
                except Exception:
                    pass
            else:
                await event.edit(
                    f"🎧 **{ti['track_name']}**\n"
                    f"👤 {ti['artist_name']}\n"
                    f"💿 {ti['album_name']}\n\n{cap}"
                )
        except spotipy.exceptions.SpotifyException as e:
            if "expired" in str(e).lower():
                await event.edit(f"❌ Токен истёк: `{p}spauth`")
            else:
                await event.edit(f"❌ {e}")
        except Exception as e:
            await event.edit(f"❌ {e}")

    async def cmd_spnow(event):
        """Текущий трек + скачивание аудио."""
        if not await _check(event):
            return
        try:
            sp = _get_sp()
            pb = sp.current_playback()
            if not pb or not pb.get("item"):
                await event.edit("❌ Ничего не играет")
                return
            await event.edit("🎵 Загружаю трек...")
            track = pb["item"]
            name = track.get("name", "?")
            artist = track["artists"][0].get("name", "?")
            album = track["album"].get("name", "?")
            dur_ms = track.get("duration_ms", 0)
            turl = track["external_urls"]["spotify"]

            # Пробуем скачать через inline-ботов
            doc = None
            for inline_bot in ["@vkm4bot", "@spotifysavebot", "@lybot"]:
                try:
                    results = await client.inline_query(inline_bot, f"{artist} - {name}")
                    if results and results[0].document:
                        doc = results[0].document
                        break
                except Exception:
                    continue
            if not doc:
                try:
                    results = await client.inline_query("@losslessrobot", f"{artist} - {name}")
                    if results and results[0].document:
                        doc = results[0].document
                except Exception:
                    pass

            if not doc:
                await event.edit("❌ Не удалось скачать трек")
                return

            # Обложка
            art_url = track["album"]["images"][0]["url"]
            art_path = None
            try:
                async with aiohttp.ClientSession() as s:
                    async with s.get(art_url) as r:
                        art_path = os.path.join(tempfile.gettempdir(), "kub_cover.jpg")
                        with open(art_path, "wb") as f:
                            f.write(await r.read())
            except Exception:
                pass

            from telethon import types as tl_types
            caption = (
                f"🎧 **Now Playing**\n\n"
                f"🎵 {name} — `{artist}`\n"
                f"💿 {album}\n\n"
                f"🔗 [Spotify]({turl})"
            )
            await client.send_file(
                event.chat_id, doc, caption=caption,
                attributes=[tl_types.DocumentAttributeAudio(
                    duration=dur_ms // 1000, title=name, performer=artist
                )],
                thumb=art_path,
                reply_to=event.reply_to_msg_id if event.is_reply else None,
            )
            await event.delete()
            if art_path:
                try:
                    os.remove(art_path)
                except Exception:
                    pass
        except spotipy.exceptions.SpotifyException as e:
            if "expired" in str(e).lower():
                await event.edit(f"❌ `{p}spauth`")
            else:
                await event.edit(f"❌ {e}")
        except Exception as e:
            await event.edit(f"❌ {e}")

    async def cmd_lyrics(event):
        """Текст текущего трека."""
        if not await _check(event):
            return
        try:
            sp = _get_sp()
            pb = sp.current_playback()
            if not pb or not pb.get("item"):
                await event.edit("❌ Ничего не играет")
                return
            await event.edit("🔍 Ищу текст...")
            track = pb["item"]
            name = track.get("name", "?")
            artist = track["artists"][0].get("name", "?")
            dur_ms = track.get("duration_ms", 0)
            prog_ms = pb.get("progress_ms", 0)
            turl = track["external_urls"]["spotify"]

            ld = await _get_lyrics_lrclib(artist, name, dur_ms)
            if not ld:
                genius = await _get_lyrics_genius(artist, name)
                if genius:
                    ld = {"type": "plain", "lyrics": genius}
            if not ld:
                ld = await _get_lyrics_ovh(artist, name)

            if ld:
                if ld["type"] == "synced":
                    fmt = _format_synced_lyrics(ld["lyrics"], prog_ms)
                else:
                    fmt = ld["lyrics"]
                await event.edit(main.truncate(
                    f"📜 **{artist} — {name}**\n[Spotify]({turl})\n\n{fmt}"
                ))
            else:
                await event.edit(f"❌ Текст для [{artist} — {name}]({turl}) не найден")
        except spotipy.exceptions.SpotifyException as e:
            if "expired" in str(e).lower():
                await event.edit(f"❌ `{p}spauth`")
            else:
                await event.edit(f"❌ {e}")
        except Exception as e:
            await event.edit(f"❌ {e}")

    async def cmd_rlyrics(event):
        """Текст в реальном времени."""
        if not await _check(event):
            return
        try:
            sp = _get_sp()
            pb = sp.current_playback()
            if not pb or not pb.get("item"):
                await event.edit("❌ Ничего не играет")
                return
            await event.edit("🔍 Ищу синхронизированный текст...")
            track = pb["item"]
            name = track.get("name", "?")
            artist = track["artists"][0].get("name", "?")
            turl = track["external_urls"]["spotify"]
            tid = track.get("id", "")
            dur_ms = track.get("duration_ms", 0)

            ld = await _get_synced_data(artist, name, dur_ms)
            if not ld:
                await event.edit(
                    f"❌ Синхронизированный текст не найден\n"
                    f"Попробуйте `{p}lyrics`"
                )
                return

            header = f"📜 **Realtime**\n[{artist} — {name}]({turl})\n\n"
            msg = await event.edit(header + "🎵 Ожидание...")

            if _state["realtime_data"] and _state["realtime_data"].get("active"):
                _state["realtime_data"]["active"] = False
                await asyncio.sleep(1)

            _state["realtime_data"] = {
                "msg_id": msg.id, "chat_id": event.chat_id,
                "lyrics_data": ld, "track_id": tid,
                "header": header, "last_idx": -1, "active": True,
            }
            asyncio.create_task(_realtime_loop())
        except spotipy.exceptions.SpotifyException as e:
            if "expired" in str(e).lower():
                await event.edit(f"❌ `{p}spauth`")
            else:
                await event.edit(f"❌ {e}")
        except Exception as e:
            await event.edit(f"❌ {e}")

    async def cmd_stoplyrics(event):
        """Остановить realtime текст."""
        if _state["realtime_data"] and _state["realtime_data"].get("active"):
            _state["realtime_data"]["active"] = False
            await event.edit("✅ Остановлено")
        else:
            await event.edit("❌ Нет активного сеанса")

    async def cmd_playnow(event):
        """Live карточка + текст."""
        if not await _check(event):
            return
        try:
            sp = _get_sp()
            pb = sp.current_playback()
            if not pb or not pb.get("item"):
                await event.edit("❌ Ничего не играет")
                return
            await event.edit("🎵 Загружаю...")
            track = pb["item"]
            name = track.get("name", "?")
            artist = track["artists"][0].get("name", "?")
            turl = track["external_urls"]["spotify"]
            tid = track.get("id", "")
            dur_ms = track.get("duration_ms", 0)

            ti = {
                "track_name": name, "artist_name": artist,
                "album_art": track["album"]["images"][0]["url"], "track_id": tid,
            }
            card = await _create_card(ti, with_time=False)
            ld = await _get_synced_data(artist, name, dur_ms)
            cap = "🎵 Ожидание..." if ld else "❌ _Текст не найден_"

            if _state["playnow_data"] and _state["playnow_data"].get("active"):
                _state["playnow_data"]["active"] = False
                await asyncio.sleep(1)

            if card:
                msg = await client.send_file(event.chat_id, card, caption=cap,
                                              reply_to=event.reply_to_msg_id if event.is_reply else None)
                try:
                    os.remove(card)
                except Exception:
                    pass
            else:
                msg = await event.edit(cap)

            _state["playnow_data"] = {
                "msg_id": msg.id, "chat_id": event.chat_id,
                "lyrics_data": ld, "track_id": tid,
                "last_idx": -1, "active": True,
            }
            await event.delete()
            asyncio.create_task(_playnow_loop())
        except spotipy.exceptions.SpotifyException as e:
            if "expired" in str(e).lower():
                await event.edit(f"❌ `{p}spauth`")
            else:
                await event.edit(f"❌ {e}")
        except Exception as e:
            await event.edit(f"❌ {e}")

    async def cmd_stopplaynow(event):
        """Остановить live-отображение."""
        if _state["playnow_data"] and _state["playnow_data"].get("active"):
            _state["playnow_data"]["active"] = False
            await event.edit("✅ Live остановлено")
        else:
            await event.edit("❌ Нет активного сеанса")

    # ─── Регистрация ───

    mod.commands = {
        "spauth": Command("spauth", cmd_spauth, "Авторизация Spotify", "spots", f"{p}spauth"),
        "spcode": Command("spcode", cmd_spcode, "Код авторизации", "spots", f"{p}spcode <code>"),
        "now": Command("now", cmd_now, "Карточка трека", "spots", f"{p}now"),
        "spnow": Command("spnow", cmd_spnow, "Трек + аудио", "spots", f"{p}spnow"),
        "lyrics": Command("lyrics", cmd_lyrics, "Текст песни", "spots", f"{p}lyrics"),
        "rlyrics": Command("rlyrics", cmd_rlyrics, "Текст realtime", "spots", f"{p}rlyrics"),
        "stoplyrics": Command("stoplyrics", cmd_stoplyrics, "Стоп realtime", "spots", f"{p}stoplyrics"),
        "playnow": Command("playnow", cmd_playnow, "Live трек+текст", "spots", f"{p}playnow"),
        "stopplaynow": Command("stopplaynow", cmd_stopplaynow, "Стоп live", "spots", f"{p}stopplaynow"),
    }

    def _unload():
        if _state["realtime_data"]:
            _state["realtime_data"]["active"] = False
        if _state["playnow_data"]:
            _state["playnow_data"]["active"] = False

    mod.on_unload = _unload

    bot.module_manager.register_module(mod)
    bot.register_commands(mod)
