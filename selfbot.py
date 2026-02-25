#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════╗
║ 🤖 Telegram SelfBot — Version 12.0                      ║
║ Multi-Language + Advanced Features                       ║
║                                                          ║
║ ❤️ Made with Love by @moein_915 ❤️                       ║
╚══════════════════════════════════════════════════════════╝
"""

import asyncio
import random
import time
import sys
import os
import io
import json
import re
from collections import defaultdict
from datetime import timedelta, datetime

from telethon import TelegramClient, events
from telethon.network import ConnectionTcpMTProxyRandomizedIntermediate
from telethon.tl.functions.channels import (
    EditBannedRequest,
    GetParticipantRequest,
    JoinChannelRequest,
)
from telethon.tl.functions.folders import EditPeerFoldersRequest
from telethon.tl.functions.messages import SendReactionRequest
from telethon.tl.functions.contacts import BlockRequest
from telethon.tl.types import (
    ChatBannedRights,
    ChannelParticipantAdmin,
    ChannelParticipantCreator,
    MessageMediaPhoto,
    MessageMediaDocument,
    ReactionEmoji,
    InputPeerChannel,
    InputFolderPeer,
)
from telethon.errors import (
    ChatAdminRequiredError,
    UserAdminInvalidError,
    SessionRevokedError,
    AuthKeyUnregisteredError,
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    PasswordHashInvalidError,
    UserNotParticipantError,
    ChannelPrivateError,
)

from config import (
    API_ID, API_HASH, PHONE_NUMBER,
    MTPROTO_SERVER, MTPROTO_PORT, MTPROTO_SECRET,
    SPAM_THRESHOLD, SPAM_WINDOW, SPAM_MUTE_HOURS,
    BOT_PASSWORD, PREFIX, ADMIN_USER_ID,
)

SESSION_FILE = "selfbot_session"
ACCOUNTS_DB = "accounts.json"
SETTINGS_DB = "settings.json"

# حداکثر ۵ پیام پشت سر هم
SPAM_LIMIT = 5


def load_accounts():
    if os.path.exists(ACCOUNTS_DB):
        with open(ACCOUNTS_DB, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_accounts(data):
    with open(ACCOUNTS_DB, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_settings():
    if os.path.exists(SETTINGS_DB):
        with open(SETTINGS_DB, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"language": "fa"}


def save_settings(data):
    with open(SETTINGS_DB, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _fa_to_en_numbers(text):
    """تبدیل اعداد فارسی به انگلیسی"""
    fa_nums = '۰۱۲۳۴۵۶۷۸۹'
    en_nums = '0123456789'
    for fa, en in zip(fa_nums, en_nums):
        text = text.replace(fa, en)
    return text


accounts = load_accounts()
settings = load_settings()
active_clients = {}
all_clients = []
pending_auth = {}
owner_ids = set()


def check_password():
    if not BOT_PASSWORD:
        return True
    print("\n🔒 Password protected!\n")
    for attempt in range(3):
        pw = input(f"Password ({3 - attempt} left): ").strip()
        if pw == BOT_PASSWORD:
            print("✅ OK!\n")
            return True
        print("❌ Wrong!")
    return False


client = TelegramClient(
    session=SESSION_FILE,
    api_id=API_ID,
    api_hash=API_HASH,
    connection=ConnectionTcpMTProxyRandomizedIntermediate,
    proxy=(MTPROTO_SERVER, MTPROTO_PORT, MTPROTO_SECRET),
)

LOVE_MESSAGES = [
    "💕 عشق یعنی وقتی کنار تو باشم، دنیا زیباتره...",
    "🌹 تو تنها کسی هستی که قلبم براش می‌تپه...",
    "💗 هر نفسم به عشق تو معنا پیدا می‌کنه...",
    "🦋 وقتی بهت فکر می‌کنم، دنیا رنگی‌تر میشه...",
    "💘 تو همونی هستی که قلبم دنبالش می‌گشت...",
]

EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002600-\U000026FF"
    "\U00002300-\U000023FF"
    "]+", flags=re.UNICODE)

# آنتی اسپم پیوی
antispam_pv_enabled = False
# آنتی اسپم گپ‌ها (با لینک)
antispam_groups = {}

user_msg_times = defaultdict(list)
warned_users = set()
auto_save_enabled = False
anti_delete_enabled = False
message_cache = defaultdict(dict)
MAX_CACHE_PER_CHAT = 200
saved_count = 0
START_TIME = time.time()
BOT_VERSION = "12.0"
AUTHOR = "moein_915"

bot_enabled = True
current_language = settings.get("language", "fa")

reaction_settings = {
    "enabled": False,
    "emoji": "❤️",
    "targets": {}
}

ad_enabled = False
ad_task = None
AD_CHANNELS = ["YangMoein_Tv", "root_zone_official"]
AD_GROUPS = ["IRAN_for_sin", "GPSARA1", "Jfj_garfi", "TablightAzad9", "forsinhadi"]


def _uptime():
    diff = int(time.time() - START_TIME)
    h, r = divmod(diff, 3600)
    m, s = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _format_size(b):
    for u in ['B', 'KB', 'MB', 'GB']:
        if b < 1024:
            return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} TB"


def _parse_link(link):
    try:
        if "t.me/c/" in link:
            parts = link.split("/c/")[-1].split("/")
            return int(f"-100{parts[0]}"), None
        elif "t.me/" in link:
            parts = link.split("/")
            username = parts[-1] if not parts[-1].isdigit() else parts[-2]
            return username, None
    except:
        pass
    return None, None


def _get_file_info(msg):
    if isinstance(msg.media, MessageMediaPhoto):
        return "🖼️", "photo", "photo.jpg"
    if isinstance(msg.media, MessageMediaDocument):
        doc = msg.media.document
        emoji, tname, fname = "📎", "file", "file.bin"
        if doc:
            for attr in doc.attributes:
                cls = type(attr).__name__
                if "Video" in cls:
                    emoji, tname, fname = "🎬", "video", "video.mp4"
                elif "Audio" in cls:
                    emoji, tname, fname = "🎵", "audio", "audio.mp3"
                if hasattr(attr, 'file_name') and attr.file_name:
                    fname = attr.file_name
        return emoji, tname, fname
    return "📎", "file", "file.bin"


def _is_valid_ad_msg(msg):
    # پیام متنی یا ایموجی
    if not msg.media:
        return bool(msg.text)

    # عکس ✅
    if isinstance(msg.media, MessageMediaPhoto):
        return True

    if isinstance(msg.media, MessageMediaDocument):
        doc = msg.media.document
        if not doc:
            return False

        for attr in doc.attributes:
            cls_name = type(attr).__name__
            
            # موزیک/آهنگ ❌ (ویس اوکیه)
            if "Audio" in cls_name:
                if hasattr(attr, 'voice') and attr.voice:
                    return True  # ویس ✅
                return False  # موزیک ❌

        # فیلم ✅ گیف ✅ استیکر ✅
        return True

    return False


def _is_emoji(text):
    if not text:
        return False
    text = text.strip()
    cleaned = EMOJI_PATTERN.sub('', text)
    return len(cleaned) == 0 and len(text) > 0


async def _get_user_from_arg(cl, event, arg=None):
    reply = await event.get_reply_message()

    if reply and reply.sender_id:
        try:
            sender = await reply.get_sender()
            name = sender.first_name if sender else "User"
            return sender, reply.sender_id, name
        except:
            return None, reply.sender_id, "User"

    if arg:
        arg = arg.strip()
        if arg.isdigit():
            user_id = int(arg)
            try:
                user = await cl.get_entity(user_id)
                name = user.first_name if hasattr(user, 'first_name') else "User"
                return user, user_id, name
            except:
                return None, user_id, "User"

        if arg.startswith('@'):
            username = arg[1:]
        else:
            username = arg

        try:
            user = await cl.get_entity(username)
            name = user.first_name if hasattr(user, 'first_name') else "User"
            return user, user.id, name
        except:
            return None, None, None

    return None, None, None


async def _get_user_id_from_arg(cl, arg):
    if not arg:
        return None, None

    arg = arg.strip()
    if arg.isdigit():
        user_id = int(arg)
        try:
            user = await cl.get_entity(user_id)
            name = user.first_name if hasattr(user, 'first_name') else "User"
            return user_id, name
        except:
            return user_id, "User"

    if arg.startswith('@'):
        username = arg[1:]
    else:
        username = arg

    try:
        user = await cl.get_entity(username)
        name = user.first_name if hasattr(user, 'first_name') else "User"
        return user.id, name
    except:
        return None, None


def _get_reaction_status_text():
    if not reaction_settings["enabled"]:
        return "❌ Off"
    count = len(reaction_settings["targets"])
    emoji = reaction_settings["emoji"]
    return f"✅ On | {count} targets | {emoji}"


async def _join_and_archive(cl, entity_username):
    try:
        try:
            entity = await cl.get_entity(entity_username)
            await cl(GetParticipantRequest(entity, 'me'))
            return True
        except UserNotParticipantError:
            pass
        except:
            pass

        await cl(JoinChannelRequest(entity_username))
        await asyncio.sleep(1)

        try:
            entity = await cl.get_entity(entity_username)
            await cl(EditPeerFoldersRequest([
                InputFolderPeer(
                    peer=entity,
                    folder_id=1
                )
            ]))
        except:
            pass

        return True
    except:
        return False


async def _get_chat_id_from_link(cl, link):
    """استخراج chat_id از لینک"""
    try:
        if "t.me/c/" in link:
            parts = link.split("/c/")[-1].split("/")
            return int(f"-100{parts[0]}")
        elif "t.me/" in link:
            parts = link.split("/")
            for part in reversed(parts):
                if part and not part.isdigit():
                    entity = await cl.get_entity(part)
                    return entity.id
    except:
        pass
    return None


# ══════════════════════════════════════════════════
# 🔧 Register Handlers
# ══════════════════════════════════════════════════
def register_handlers(cl):

    async def _is_owner(event):
        """چک میکنه پیام از صاحب اکانت باشه - از هر دستگاهی"""
        me = await cl.get_me()
        return event.sender_id == me.id

    # ═══════════════ 🌐 زبان / Language ═══════════════
    @cl.on(events.NewMessage(pattern=rf"^(?:\{PREFIX})?(زبان|lang)\s*(.*)$"))
    async def cmd_language(event):
        if not await _is_owner(event):
            return
        global current_language, settings

        cmd = event.pattern_match.group(1).lower()
        if current_language == "en" and cmd == "زبان":
            return
        if current_language == "fa" and cmd == "lang":
            return

        arg = event.pattern_match.group(2).strip().lower()

        if not arg:
            await event.edit(f"""
🌐 Language / زبان
━━━━━━━━━━━━━━━━━━━

📊 Current: {'🇮🇷 فارسی' if current_language == 'fa' else '🇺🇸 English'}

📝 `{PREFIX}زبان فارسی` | `{PREFIX}lang en`

━━━━━━━━━━━━━━━━━━━
""")
            return

        if arg in ["فارسی", "fa", "persian", "farsi"]:
            current_language = "fa"
            settings["language"] = "fa"
            save_settings(settings)
            await event.edit("🌐 🇮🇷 **فارسی فعال شد!** ✅")
        elif arg in ["انگلیسی", "en", "english", "eng"]:
            current_language = "en"
            settings["language"] = "en"
            save_settings(settings)
            await event.edit("🌐 🇺🇸 **English Enabled!** ✅")

    # ═══════════════ 🟢 روشن / On ═══════════════
    @cl.on(events.NewMessage(pattern=rf"^(?:\{PREFIX})?(روشن|on)$"))
    async def cmd_on(event):
        if not await _is_owner(event):
            return
        global bot_enabled
        cmd = event.pattern_match.group(1).lower()
        if current_language == "en" and cmd == "روشن":
            return
        if current_language == "fa" and cmd == "on":
            return

        bot_enabled = True
        if current_language == "fa":
            await event.edit("🟢 **ربات روشن شد!**")
        else:
            await event.edit("🟢 **Bot Enabled!**")

    # ═══════════════ 🔴 خاموش / Off ═══════════════
    @cl.on(events.NewMessage(pattern=rf"^(?:\{PREFIX})?(خاموش|off)$"))
    async def cmd_off(event):
        if not await _is_owner(event):
            return
        global bot_enabled
        cmd = event.pattern_match.group(1).lower()
        if current_language == "en" and cmd == "خاموش":
            return
        if current_language == "fa" and cmd == "off":
            return

        if not bot_enabled:
            return
        bot_enabled = False
        if current_language == "fa":
            await event.edit("🔴 **ربات خاموش شد!**")
        else:
            await event.edit("🔴 **Bot Disabled!**")

    # ═══════════════ 🆔 شناسه / GetID ═══════════════
    @cl.on(events.NewMessage(pattern=rf"^(?:\{PREFIX})?(شناسه|getid)\s*(.*)$"))
    async def cmd_getid(event):
        if not await _is_owner(event):
            return
        if not bot_enabled:
            return
        cmd = event.pattern_match.group(1).lower()
        if current_language == "en" and cmd == "شناسه":
            return
        if current_language == "fa" and cmd == "getid":
            return

        arg = event.pattern_match.group(2).strip()
        if current_language == "fa":
            arg = _fa_to_en_numbers(arg)
        reply = await event.get_reply_message()

        if reply and reply.sender_id:
            try:
                sender = await reply.get_sender()
                name = sender.first_name if sender else "User"
                user_id = reply.sender_id
                username = sender.username if sender and sender.username else "none"

                await cl.send_message("me", f"""
🆔 User ID
━━━━━━━━━━━━━━━━━━━

👤 {name}
🆔 `{user_id}`
📧 @{username}

━━━━━━━━━━━━━━━━━━━
""")
                if current_language == "fa":
                    await event.edit("✅ به پیوی ارسال شد!")
                else:
                    await event.edit("✅ Sent to Saved!")
                await asyncio.sleep(2)
                await event.delete()
            except Exception as e:
                await event.edit(f"❌ {e}")
            return

        if arg:
            user_id, name = await _get_user_id_from_arg(cl, arg)
            if user_id:
                try:
                    user = await cl.get_entity(user_id)
                    username = user.username if hasattr(user, 'username') and user.username else "none"
                except:
                    username = "none"

                await cl.send_message("me", f"""
🆔 User ID
━━━━━━━━━━━━━━━━━━━

👤 {name}
🆔 `{user_id}`
📧 @{username}

━━━━━━━━━━━━━━━━━━━
""")
                if current_language == "fa":
                    await event.edit("✅ به پیوی ارسال شد!")
                else:
                    await event.edit("✅ Sent to Saved!")
                await asyncio.sleep(2)
                await event.delete()
            else:
                if current_language == "fa":
                    await event.edit("❌ کاربر پیدا نشد!")
                else:
                    await event.edit("❌ User not found!")
            return

        me = await cl.get_me()
        username = me.username if me.username else "none"
        await event.edit(f"""
🆔 Your ID
━━━━━━━━━━━━━━━━━━━

👤 {me.first_name}
🆔 `{me.id}`
📧 @{username}

━━━━━━━━━━━━━━━━━━━
""")

    # ═══════════════ 🗑 حذف / Delete ═══════════════
    @cl.on(events.NewMessage(pattern=rf"^(?:\{PREFIX})?(حذف|del)$"))
    async def cmd_delete(event):
        if not await _is_owner(event):
            return
        if not bot_enabled:
            return
        cmd = event.pattern_match.group(1).lower()
        if current_language == "en" and cmd == "حذف":
            return
        if current_language == "fa" and cmd == "del":
            return

        reply = await event.get_reply_message()
        if reply:
            try:
                await reply.delete()
                await event.delete()
            except Exception as e:
                await event.edit(f"❌ `{e}`")
        else:
            await event.delete()

    # ═══════════════ 😍 ری اکشن / React ═══════════════
    @cl.on(events.NewMessage(pattern=rf"^(?:\{PREFIX})?(ری\s?اکشن|react)\s*(.*)$"))
    async def cmd_reaction(event):
        if not await _is_owner(event):
            return
        global reaction_settings
        if not bot_enabled:
            return

        cmd = event.pattern_match.group(1).replace(" ", "").lower()
        if current_language == "en" and cmd in ["ریاکشن", "ری‌اکشن"]:
            return
        if current_language == "fa" and cmd == "react":
            return

        arg = event.pattern_match.group(2).strip()
        if current_language == "fa":
            arg = _fa_to_en_numbers(arg)
        reply = await event.get_reply_message()
        chat_id = event.chat_id

        if not arg:
            if reaction_settings["enabled"]:
                targets_text = ""
                for key, data in list(reaction_settings["targets"].items())[:5]:
                    targets_text += f"\n  • {data.get('name', key)} | {data.get('emoji', '❤️')}"
                if len(reaction_settings["targets"]) > 5:
                    targets_text += f"\n  +{len(reaction_settings['targets']) - 5} more..."

                if current_language == "fa":
                    await event.edit(f"""
😍 ری‌اکشن
━━━━━━━━━━━━━━━━━━━

📊 {_get_reaction_status_text()}
{targets_text}

📝 `{PREFIX}ری اکشن فعال` - روشن
📝 `{PREFIX}ری اکشن خاموش` - خاموش
📝 `{PREFIX}ری اکشن ❤️` - ایموجی
📝 `{PREFIX}ری اکشن @user` - کاربر
📝 `{PREFIX}ری اکشن اینجا ❤️` - این چت

━━━━━━━━━━━━━━━━━━━
""")
                else:
                    await event.edit(f"""
😍 Reaction
━━━━━━━━━━━━━━━━━━━

📊 {_get_reaction_status_text()}
{targets_text}

📝 `{PREFIX}react on` - enable
📝 `{PREFIX}react off` - disable
📝 `{PREFIX}react ❤️` - emoji
📝 `{PREFIX}react @user` - user
📝 `{PREFIX}react here ❤️` - this chat

━━━━━━━━━━━━━━━━━━━
""")
            else:
                if current_language == "fa":
                    await event.edit(f"""
😍 ری‌اکشن خاموشه!
━━━━━━━━━━━━━━━━━━━

📝 `{PREFIX}ری اکشن فعال` - روشن کردن

━━━━━━━━━━━━━━━━━━━
""")
                else:
                    await event.edit(f"""
😍 Reaction is Off!
━━━━━━━━━━━━━━━━━━━

📝 `{PREFIX}react on` - enable

━━━━━━━━━━━━━━━━━━━
""")
            return

        if arg in ["فعال", "on"]:
            reaction_settings["enabled"] = True
            if current_language == "fa":
                await event.edit("😍 **ری‌اکشن فعال شد!** ✅")
            else:
                await event.edit("😍 **Reaction Enabled!** ✅")
            return

        if arg in ["خاموش", "off"]:
            reaction_settings["enabled"] = False
            if current_language == "fa":
                await event.edit("😍 **ری‌اکشن خاموش شد!** 🔴")
            else:
                await event.edit("😍 **Reaction Disabled!** 🔴")
            return

        if arg in ["پاک", "clear"]:
            reaction_settings["targets"].clear()
            if current_language == "fa":
                await event.edit("🗑️ **همه تارگت‌ها پاک شد!**")
            else:
                await event.edit("🗑️ **All targets cleared!**")
            return

        if not reaction_settings["enabled"]:
            if current_language == "fa":
                await event.edit(f"❌ **اول ری‌اکشن رو فعال کن!**\n`{PREFIX}ری اکشن فعال`")
            else:
                await event.edit(f"❌ **Enable reaction first!**\n`{PREFIX}react on`")
            return

        if _is_emoji(arg):
            reaction_settings["emoji"] = arg
            if current_language == "fa":
                await event.edit(f"😍 **ایموجی پیشفرض:** {arg}")
            else:
                await event.edit(f"😍 **Default emoji:** {arg}")
            return

        if arg.startswith(("اینجا", "here")):
            parts = arg.split(maxsplit=1)
            emoji = parts[1] if len(parts) > 1 and _is_emoji(parts[1]) else reaction_settings["emoji"]

            if reply and reply.sender_id:
                try:
                    sender = await reply.get_sender()
                    name = sender.first_name if sender else "User"
                    user_id = reply.sender_id

                    key = f"chat_{chat_id}_user_{user_id}"
                    reaction_settings["targets"][key] = {
                        "type": "chat_user",
                        "chat_id": chat_id,
                        "user_id": user_id,
                        "name": name,
                        "emoji": emoji
                    }

                    if current_language == "fa":
                        await event.edit(f"""
😍 تارگت اضافه شد!
━━━━━━━━━━━━━━━━━━━

👤 {name}
💬 فقط در این چت
🎯 {emoji}

━━━━━━━━━━━━━━━━━━━
""")
                    else:
                        await event.edit(f"""
😍 Target Added!
━━━━━━━━━━━━━━━━━━━

👤 {name}
💬 Only in this chat
🎯 {emoji}

━━━━━━━━━━━━━━━━━━━
""")
                except Exception as e:
                    await event.edit(f"❌ {e}")
            else:
                if current_language == "fa":
                    await event.edit("❌ روی پیام کسی ریپلای بزن!")
                else:
                    await event.edit("❌ Reply to someone's message!")
            return

        if arg.isdigit() or arg.startswith('@'):
            emoji = reaction_settings["emoji"]
            user_id, name = await _get_user_id_from_arg(cl, arg)
            if user_id:
                key = f"user_{user_id}"
                reaction_settings["targets"][key] = {
                    "type": "user",
                    "user_id": user_id,
                    "name": name,
                    "emoji": emoji
                }
                if current_language == "fa":
                    await event.edit(f"""
😍 کاربر اضافه شد!
━━━━━━━━━━━━━━━━━━━

👤 {name}
🆔 `{user_id}`
🌍 همه جا
🎯 {emoji}

━━━━━━━━━━━━━━━━━━━
""")
                else:
                    await event.edit(f"""
😍 User Added!
━━━━━━━━━━━━━━━━━━━

👤 {name}
🆔 `{user_id}`
🌍 Everywhere
🎯 {emoji}

━━━━━━━━━━━━━━━━━━━
""")
            else:
                if current_language == "fa":
                    await event.edit("❌ کاربر پیدا نشد!")
                else:
                    await event.edit("❌ User not found!")
            return

    # ═══════════════ 🗑️ سیو حذف پیام / SaveDeleted ═══════════════
    @cl.on(events.NewMessage(pattern=rf"^(?:\{PREFIX})?(سیو\s+حذف\s+پیام|savedeleted)$"))
    async def cmd_savedeleted(event):
        if not await _is_owner(event):
            return
        if not bot_enabled:
            return
        cmd = event.pattern_match.group(1).replace(" ", "").lower()
        if current_language == "en" and cmd == "سیوحذفپیام":
            return
        if current_language == "fa" and cmd == "savedeleted":
            return

        global anti_delete_enabled
        anti_delete_enabled = not anti_delete_enabled
        await event.delete()

        if current_language == "fa":
            if anti_delete_enabled:
                await cl.send_message("me", "🗑️ **سیو حذف پیام فعال شد!** ✅\n\nپیام‌های حذف شده در پیوی ذخیره میشن.")
            else:
                await cl.send_message("me", "🗑️ **سیو حذف پیام غیرفعال شد!** ❌")
        else:
            if anti_delete_enabled:
                await cl.send_message("me", "🗑️ **Save Deleted Messages Enabled!** ✅\n\nDeleted PV messages will be saved.")
            else:
                await cl.send_message("me", "🗑️ **Save Deleted Messages Disabled!** ❌")

    # ═══════════════ 🛡 زد اسپم پیوی / AntiSpam PV ═══════════════
    @cl.on(events.NewMessage(pattern=rf"^(?:\{PREFIX})?(زد\s+اسپم|antispam)$"))
    async def cmd_antispam_pv(event):
        if not await _is_owner(event):
            return
        if not bot_enabled:
            return
        cmd = event.pattern_match.group(1).replace(" ", "").lower()
        if current_language == "en" and cmd == "زداسپم":
            return
        if current_language == "fa" and cmd == "antispam":
            return

        global antispam_pv_enabled
        antispam_pv_enabled = not antispam_pv_enabled

        if current_language == "fa":
            if antispam_pv_enabled:
                await event.edit(f"""
🛡️ ضد اسپم پیوی فعال شد! ✅
━━━━━━━━━━━━━━━━━━━

📩 اگه کسی {SPAM_LIMIT} پیام پشت سر هم بده:
🚫 بلاک میشه برای ۱ روز

━━━━━━━━━━━━━━━━━━━
""")
            else:
                await event.edit("🛡️ **ضد اسپم پیوی غیرفعال شد!** ❌")
        else:
            if antispam_pv_enabled:
                await event.edit(f"""
🛡️ AntiSpam PV Enabled! ✅
━━━━━━━━━━━━━━━━━━━

📩 If someone sends {SPAM_LIMIT} messages in a row:
🚫 Gets blocked for 1 day

━━━━━━━━━━━━━━━━━━━
""")
            else:
                await event.edit("🛡️ **AntiSpam PV Disabled!** ❌")

    # ═══════════════ 🛡 زد اسپم گپ / AntiSpam Group ═══════════════
    @cl.on(events.NewMessage(pattern=rf"^(?:\{PREFIX})?(زد\s+اسپم\s+گپ|antispam\s+group)\s+(.+)$"))
    async def cmd_antispam_group(event):
        if not await _is_owner(event):
            return
        if not bot_enabled:
            return
        cmd = event.pattern_match.group(1).replace(" ", "").lower()
        if current_language == "en" and cmd == "زداسپمگپ":
            return
        if current_language == "fa" and cmd == "antispamgroup":
            return

        link = event.pattern_match.group(2).strip()
        chat_id = await _get_chat_id_from_link(cl, link)

        if not chat_id:
            if current_language == "fa":
                await event.edit("❌ **لینک نامعتبر!**")
            else:
                await event.edit("❌ **Invalid link!**")
            return

        if chat_id in antispam_groups:
            del antispam_groups[chat_id]
            if current_language == "fa":
                await event.edit(f"""
🛡️ ضد اسپم گپ غیرفعال شد! ❌
━━━━━━━━━━━━━━━━━━━

🆔 `{chat_id}`

━━━━━━━━━━━━━━━━━━━
""")
            else:
                await event.edit(f"""
🛡️ AntiSpam Group Disabled! ❌
━━━━━━━━━━━━━━━━━━━

🆔 `{chat_id}`

━━━━━━━━━━━━━━━━━━━
""")
        else:
            antispam_groups[chat_id] = True
            if current_language == "fa":
                await event.edit(f"""
🛡️ ضد اسپم گپ فعال شد! ✅
━━━━━━━━━━━━━━━━━━━

🆔 `{chat_id}`
📩 اگه کسی {SPAM_LIMIT} پیام پشت سر هم بده:
🔇 سکوت میشه برای ۱ ساعت

━━━━━━━━━━━━━━━━━━━
""")
            else:
                await event.edit(f"""
🛡️ AntiSpam Group Enabled! ✅
━━━━━━━━━━━━━━━━━━━

🆔 `{chat_id}`
📩 If someone sends {SPAM_LIMIT} messages in a row:
🔇 Gets muted for 1 hour

━━━━━━━━━━━━━━━━━━━
""")

    # ═══════════════ 📢 تبلیغ / Ad ═══════════════
    @cl.on(events.NewMessage(pattern=rf"^(?:\{PREFIX})?(تبلیغ|ad)\s*(.*)$"))
    async def cmd_ad(event):
        if not await _is_owner(event):
            return
        global ad_enabled, ad_task
        if not bot_enabled:
            return

        cmd = event.pattern_match.group(1).lower()
        if current_language == "en" and cmd == "تبلیغ":
            return
        if current_language == "fa" and cmd == "ad":
            return

        arg = event.pattern_match.group(2).strip()

        if not arg:
            ch_list = "\n".join([f"  📺 @{c}" for c in AD_CHANNELS])
            gr_list = "\n".join([f"  💬 @{g}" for g in AD_GROUPS])

            if current_language == "fa":
                await event.edit(f"""
📢 تبلیغات
━━━━━━━━━━━━━━━━━━━

📊 وضعیت: {'🟢 روشن' if ad_enabled else '🔴 خاموش'}
⏱️ پست جدید = ارسال فوری + ارسال رندوم هر ۱۰ دقیقه

📺 چنل‌ها:
{ch_list}

💬 گپ‌ها:
{gr_list}

📝 `{PREFIX}تبلیغ روشن`
📝 `{PREFIX}تبلیغ خاموش`

━━━━━━━━━━━━━━━━━━━
""")
            else:
                await event.edit(f"""
📢 Advertising
━━━━━━━━━━━━━━━━━━━

📊 Status: {'🟢 On' if ad_enabled else '🔴 Off'}
⏱️ New post = instant + random every 10 min

📺 Channels:
{ch_list}

💬 Groups:
{gr_list}

📝 `{PREFIX}ad on`
📝 `{PREFIX}ad off`

━━━━━━━━━━━━━━━━━━━
""")
            return

        if arg in ["روشن", "on"]:
            if ad_enabled:
                if current_language == "fa":
                    await event.edit("⚠️ **تبلیغات از قبل روشنه!**")
                else:
                    await event.edit("⚠️ **Ads already enabled!**")
                return

            ad_enabled = True

            if current_language == "fa":
                await event.edit("🔍 **در حال بررسی عضویت گپ‌ها...**")
            else:
                await event.edit("🔍 **Checking group memberships...**")

            already_joined = []
            need_join = []

            for group in AD_GROUPS:
                try:
                    entity = await cl.get_entity(group)
                    await cl(GetParticipantRequest(entity, 'me'))
                    already_joined.append(group)
                except UserNotParticipantError:
                    need_join.append(group)
                except:
                    need_join.append(group)

            if not need_join:
                if current_language == "fa":
                    await event.edit("✅ **همه گپ‌ها عضو هستی! در حال بررسی...**")
                else:
                    await event.edit("✅ **Already member of all groups! Checking...**")
            else:
                if current_language == "fa":
                    await event.edit(f"🔄 **در حال عضویت در {len(need_join)} گپ...**")
                else:
                    await event.edit(f"🔄 **Joining {len(need_join)} groups...**")

                for group in need_join:
                    await _join_and_archive(cl, group)
                    await asyncio.sleep(1)

            for channel in AD_CHANNELS:
                try:
                    entity = await cl.get_entity(channel)
                    await cl(GetParticipantRequest(entity, 'me'))
                except:
                    await _join_and_archive(cl, channel)
                    await asyncio.sleep(1)

            if current_language == "fa":
                await event.edit("📝 **در حال تست ارسال پیام در گپ‌ها...**")
            else:
                await event.edit("📝 **Testing message send in groups...**")

            ok_groups = []
            fail_groups = []

            for group in AD_GROUPS:
                try:
                    test_msg = await cl.send_message(group, "سلام")
                    await test_msg.delete()
                    ok_groups.append(group)
                except Exception as e:
                    err_str = str(e).lower()
                    if "not a member" in err_str or "user_not_participant" in err_str or "channel_private" in err_str:
                        joined = await _join_and_archive(cl, group)
                        if joined:
                            await asyncio.sleep(2)
                            try:
                                test_msg2 = await cl.send_message(group, "سلام")
                                await test_msg2.delete()
                                ok_groups.append(group)
                            except:
                                fail_groups.append(group)
                        else:
                            fail_groups.append(group)
                    else:
                        fail_groups.append(group)
                await asyncio.sleep(1)

            async def _ad_loop():
                global ad_enabled
                nonlocal ok_groups

                last_msg_ids = {}
                for channel in AD_CHANNELS:
                    try:
                        async for msg in cl.iter_messages(channel, limit=1):
                            last_msg_ids[channel] = msg.id
                    except:
                        last_msg_ids[channel] = 0

                while ad_enabled:
                    try:
                        for channel in AD_CHANNELS:
                            if not ad_enabled:
                                break
                            try:
                                async for msg in cl.iter_messages(channel, limit=1):
                                    if msg.id > last_msg_ids.get(channel, 0):
                                        if _is_valid_ad_msg(msg):
                                            target_groups = random.sample(ok_groups, k=min(2, len(ok_groups)))
                                            for group in target_groups:
                                                if not ad_enabled:
                                                    break
                                                try:
                                                    await cl.forward_messages(group, msg)
                                                except:
                                                    pass
                                                await asyncio.sleep(5)
                                        last_msg_ids[channel] = msg.id
                            except:
                                continue

                        channels_posts = {}
                        for channel in AD_CHANNELS:
                            valid_msgs = []
                            try:
                                async for msg in cl.iter_messages(channel, limit=20):
                                    if _is_valid_ad_msg(msg):
                                        valid_msgs.append(msg)
                            except:
                                continue
                            if valid_msgs:
                                channels_posts[channel] = valid_msgs

                        if channels_posts:
                            channel_list = list(channels_posts.keys())
                            for i, group in enumerate(ok_groups):
                                if not ad_enabled:
                                    break

                                channel = channel_list[i % len(channel_list)]
                                msgs = channels_posts[channel]
                                chosen = random.choice(msgs)

                                try:
                                    await cl.forward_messages(group, chosen)
                                except:
                                    pass

                                await asyncio.sleep(5)

                    except:
                        pass

                    for _ in range(60):
                        if not ad_enabled:
                            break
                        await asyncio.sleep(10)

            if ad_task:
                ad_task.cancel()
            ad_task = asyncio.create_task(_ad_loop())

            ok_text = "\n".join([f"  ✅ @{g}" for g in ok_groups])
            fail_text = "\n".join([f"  ❌ @{g}" for g in fail_groups]) if fail_groups else ""

            if current_language == "fa":
                result = f"""
📢 تبلیغات روشن شد! ✅
━━━━━━━━━━━━━━━━━━━

💬 گپ‌های آماده:
{ok_text}
"""
                if fail_text:
                    result += f"""
❌ گپ‌های ناموفق:
{fail_text}
"""
                result += f"""
📺 چنل‌ها: {len(AD_CHANNELS)}
⏱️ پست جدید = فوری به ۲ گپ
⏱️ هر ۱۰ دقیقه = رندوم به همه گپ

━━━━━━━━━━━━━━━━━━━
"""
            else:
                result = f"""
📢 Ads Enabled! ✅
━━━━━━━━━━━━━━━━━━━

💬 Ready groups:
{ok_text}
"""
                if fail_text:
                    result += f"""
❌ Failed groups:
{fail_text}
"""
                result += f"""
📺 Channels: {len(AD_CHANNELS)}
⏱️ New post = instant to 2 groups
⏱️ Every 10 min = random to all

━━━━━━━━━━━━━━━━━━━
"""
            await event.edit(result)
            return

        if arg in ["خاموش", "off"]:
            if not ad_enabled:
                if current_language == "fa":
                    await event.edit("⚠️ **تبلیغات از قبل خاموشه!**")
                else:
                    await event.edit("⚠️ **Ads already disabled!**")
                return

            ad_enabled = False
            if ad_task:
                ad_task.cancel()
                ad_task = None

            if current_language == "fa":
                await event.edit("📢 **تبلیغات خاموش شد!** 🔴")
            else:
                await event.edit("📢 **Ads Disabled!** 🔴")
            return

    # ═══════════════ 🎨 راهنما / Help ═══════════════
    @cl.on(events.NewMessage(pattern=rf"^(?:\{PREFIX})?(راهنما|help)$"))
    async def cmd_help(event):
        if not await _is_owner(event):
            return
        if not bot_enabled:
            return

        cmd = event.pattern_match.group(1).lower()
        if current_language == "en" and cmd == "راهنما":
            return
        if current_language == "fa" and cmd == "help":
            return

        me = await cl.get_me()
        is_admin = (me.id == ADMIN_USER_ID)

        if current_language == "fa":
            # ═══════════ نسخه فارسی ═══════════
            text = f"""
🤖 **سلف‌بات تلگرام** v{BOT_VERSION}
━━━━━━━━━━━━━━━━━━━━━━━
"""
            if is_admin:
                text += "👑 **حالت ادمین فعال**\n"

            text += f"""
**⚡ کنترل ربات**
├ `{PREFIX}روشن` • روشن کردن
├ `{PREFIX}خاموش` • خاموش کردن
╰ `{PREFIX}زبان انگلیسی` • تغییر زبان

**😍 ری‌اکشن خودکار**
├ `{PREFIX}ری اکشن فعال` • روشن
├ `{PREFIX}ری اکشن خاموش` • خاموش
├ `{PREFIX}ری اکشن ❤️` • تنظیم ایموجی
├ `{PREFIX}ری اکشن @user` • همه جا
╰ `{PREFIX}ری اکشن اینجا ❤️` • این چت + ریپلای

**🆔 دریافت شناسه**
╰ `{PREFIX}شناسه` • ریپلای → ارسال به پیوی

**💬 مدیریت پیام**
├ `{PREFIX}حذف` • حذف پیام (ریپلای)
├ `{PREFIX}پاکسازی ۵۰` • حذف چند پیام
├ `{PREFIX}اسپم ۵ متن` • ارسال تکراری
╰ `{PREFIX}پین` • پین کردن (ریپلای)

**👮 مدیریت کاربران**
├ `{PREFIX}سکوت @user` • سکوت دائم
├ `{PREFIX}سکوت ۲ @user` • سکوت ۲ ساعته
├ `{PREFIX}حذف سکوت @user` • رفع سکوت
├ `{PREFIX}بن @user` • بن کردن
╰ `{PREFIX}حذف بن @user` • رفع بن

**🛡️ ضد اسپم**
├ `{PREFIX}زد اسپم` • پیوی (بلاک ۱ روز)
╰ `{PREFIX}زد اسپم گپ [لینک]` • گپ (سکوت ۱ ساعت)

**📸 ذخیره مدیا**
├ `{PREFIX}سیو تایم دار` • ذخیره خودکار
├ `{PREFIX}سیو عکس` • ذخیره دستی (ریپلای)
├ `{PREFIX}گرفتن [لینک]` • دانلود از لینک
╰ `{PREFIX}لینک` • گرفتن لینک پیام

**🗑️ ضد حذف پیام**
╰ `{PREFIX}سیو حذف پیام` • ذخیره پیام‌های حذف شده

**📢 تبلیغات خودکار**
├ `{PREFIX}تبلیغ` • وضعیت
├ `{PREFIX}تبلیغ روشن` • شروع
╰ `{PREFIX}تبلیغ خاموش` • توقف

**📊 اطلاعات**
├ `{PREFIX}وضعیت` • وضعیت ربات
├ `{PREFIX}آیدی` • آیدی چت/کاربر
╰ `{PREFIX}عشق` • پیام عاشقانه
"""
            if is_admin:
                text += f"""
**👑 مدیریت اکانت‌ها**
├ `{PREFIX}افزودن +989...` • افزودن اکانت
├ `{PREFIX}لیست` • لیست اکانت‌ها
├ `{PREFIX}حذف اکانت +989...` • حذف اکانت
├ `{PREFIX}غیرفعال +989...` • غیرفعال کردن
╰ `{PREFIX}فعال +989...` • فعال کردن
"""
            text += f"""
━━━━━━━━━━━━━━━━━━━━━━━
   ❤️ **ساخته شده با عشق توسط** ❤️
            @{AUTHOR}
   📺 **چنل رسمی:** t.me/YangMoein_Tv
━━━━━━━━━━━━━━━━━━━━━━━
"""

        else:
            # ═══════════ نسخه انگلیسی ═══════════
            text = f"""
🤖 **Telegram SelfBot** v{BOT_VERSION}
━━━━━━━━━━━━━━━━━━━━━━━
"""
            if is_admin:
                text += "👑 **Admin Mode Active**\n"

            text += f"""
**⚡ Bot Control**
├ `{PREFIX}on` • Enable bot
├ `{PREFIX}off` • Disable bot
╰ `{PREFIX}lang fa` • Change language

**😍 Auto Reaction**
├ `{PREFIX}react on` • Enable
├ `{PREFIX}react off` • Disable
├ `{PREFIX}react ❤️` • Set emoji
├ `{PREFIX}react @user` • Everywhere
╰ `{PREFIX}react here ❤️` • This chat + reply

**🆔 Get ID**
╰ `{PREFIX}getid` • Reply → Send to PM

**💬 Message Management**
├ `{PREFIX}del` • Delete message (reply)
├ `{PREFIX}purge 50` • Delete messages
├ `{PREFIX}spam 5 text` • Spam messages
╰ `{PREFIX}pin` • Pin message (reply)

**👮 User Management**
├ `{PREFIX}mute @user` • Permanent mute
├ `{PREFIX}mute 2 @user` • Mute 2 hours
├ `{PREFIX}unmute @user` • Unmute
├ `{PREFIX}ban @user` • Ban user
╰ `{PREFIX}unban @user` • Unban user

**🛡️ Anti-Spam**
├ `{PREFIX}antispam` • PV (block 1 day)
╰ `{PREFIX}antispam group [link]` • Group (mute 1 hour)

**📸 Media Save**
├ `{PREFIX}autosave` • Auto save
├ `{PREFIX}save` • Manual save (reply)
├ `{PREFIX}grab [link]` • Download from link
╰ `{PREFIX}link` • Get message link

**🗑️ Anti-Delete**
╰ `{PREFIX}savedeleted` • Save deleted messages

**📢 Auto Advertising**
├ `{PREFIX}ad` • Status
├ `{PREFIX}ad on` • Start
╰ `{PREFIX}ad off` • Stop

**📊 Information**
├ `{PREFIX}status` • Bot status
├ `{PREFIX}id` • Chat/User ID
╰ `{PREFIX}love` • Love message
"""
            if is_admin:
                text += f"""
**👑 Account Management**
├ `{PREFIX}add +989...` • Add account
├ `{PREFIX}list` • List accounts
├ `{PREFIX}remove +989...` • Remove account
├ `{PREFIX}deactivate +989...` • Deactivate
╰ `{PREFIX}activate +989...` • Activate
"""
            text += f"""
━━━━━━━━━━━━━━━━━━━━━━━
      ❤️ **Made with Love by** ❤️
             @{AUTHOR}
   📺 **Official:** t.me/YangMoein_Tv
━━━━━━━━━━━━━━━━━━━━━━━
"""

        await event.edit(text)

    # ═══════════════ 📊 وضعیت / Status ═══════════════
    @cl.on(events.NewMessage(pattern=rf"^(?:\{PREFIX})?(وضعیت|status)$"))
    async def cmd_status(event):
        if not await _is_owner(event):
            return
        if not bot_enabled:
            return

        cmd = event.pattern_match.group(1).lower()
        if current_language == "en" and cmd == "وضعیت":
            return
        if current_language == "fa" and cmd == "status":
            return

        me = await cl.get_me()
        is_admin = (me.id == ADMIN_USER_ID)
        lang_icon = "🇮🇷" if current_language == "fa" else "🇺🇸"

        if current_language == "fa":
            text = f"""
📊 وضعیت ربات
━━━━━━━━━━━━━━━━━━━

👤 {me.first_name} | `{me.id}`
"""
            if is_admin:
                text += "👑 ادمین\n"
            text += f"""⏰ آپتایم: {_uptime()}
🌐 زبان: {lang_icon}
😍 ری‌اکشن: {_get_reaction_status_text()}
🛡️ ضد اسپم پیوی: {'✅' if antispam_pv_enabled else '❌'}
🛡️ ضد اسپم گپ: {len(antispam_groups)} گپ
📸 ذخیره خودکار: {'✅' if auto_save_enabled else '❌'}
🗑️ سیو حذف پیام: {'✅' if anti_delete_enabled else '❌'}
📢 تبلیغ: {'✅' if ad_enabled else '❌'}
"""
            if is_admin:
                text += f"👥 اکانت‌ها: {len(accounts)}\n"
            text += f"""
━━━━━━━━━━━━━━━━━━━
❤️ @{AUTHOR}
"""
        else:
            text = f"""
📊 Bot Status
━━━━━━━━━━━━━━━━━━━

👤 {me.first_name} | `{me.id}`
"""
            if is_admin:
                text += "👑 Admin\n"
            text += f"""⏰ Uptime: {_uptime()}
🌐 Language: {lang_icon}
😍 Reaction: {_get_reaction_status_text()}
🛡️ AntiSpam PV: {'✅' if antispam_pv_enabled else '❌'}
🛡️ AntiSpam Groups: {len(antispam_groups)} groups
📸 Auto-Save: {'✅' if auto_save_enabled else '❌'}
🗑️ Save Deleted: {'✅' if anti_delete_enabled else '❌'}
📢 Ads: {'✅' if ad_enabled else '❌'}
"""
            if is_admin:
                text += f"👥 Accounts: {len(accounts)}\n"
            text += f"""
━━━━━━━━━━━━━━━━━━━
❤️ @{AUTHOR}
"""
        await event.edit(text)

    # ═══════════════ 💕 عشق / Love ═══════════════
    @cl.on(events.NewMessage(pattern=rf"^(?:\{PREFIX})?(عشق|love)$"))
    async def cmd_love(event):
        if not await _is_owner(event):
            return
        if not bot_enabled:
            return
        cmd = event.pattern_match.group(1).lower()
        if current_language == "en" and cmd == "عشق":
            return
        if current_language == "fa" and cmd == "love":
            return
        await event.edit(random.choice(LOVE_MESSAGES))

    # ═══════════════ 🧹 پاکسازی / Purge ═══════════════
    @cl.on(events.NewMessage(pattern=rf"^(?:\{PREFIX})?(پاک\s?سازی|purge)\s*(.*)$"))
    async def cmd_purge(event):
        if not await _is_owner(event):
            return
        if not bot_enabled:
            return
        cmd = event.pattern_match.group(1).replace(" ", "").lower()
        if current_language == "en" and cmd in ["پاکسازی", "پاک‌سازی"]:
            return
        if current_language == "fa" and cmd == "purge":
            return

        count_str = event.pattern_match.group(2).strip()
        if current_language == "fa":
            count_str = _fa_to_en_numbers(count_str)
        count = int(count_str) if count_str.isdigit() else 100
        
        await event.delete()
        chat = await event.get_chat()
        ids = [m.id async for m in cl.iter_messages(chat, limit=count)]
        if ids:
            for i in range(0, len(ids), 100):
                await cl.delete_messages(chat, ids[i:i + 100])
            if current_language == "fa":
                tmp = await event.respond(f"🧹 **{len(ids)} پیام پاک شد!** ✅")
            else:
                tmp = await event.respond(f"🧹 **{len(ids)} messages deleted!** ✅")
            await asyncio.sleep(2)
            await tmp.delete()

    # ═══════════════ 🔇 سکوت / Mute ═══════════════
    @cl.on(events.NewMessage(pattern=rf"^(?:\{PREFIX})?(سکوت|mute)\s*(.*)$"))
    async def cmd_mute(event):
        if not await _is_owner(event):
            return
        if not bot_enabled:
            return

        cmd = event.pattern_match.group(1).lower()
        if current_language == "en" and cmd == "سکوت":
            return
        if current_language == "fa" and cmd == "mute":
            return

        arg = event.pattern_match.group(2).strip()
        if current_language == "fa":
            arg = _fa_to_en_numbers(arg)

        # پارس کردن ساعت و یوزر
        parts = arg.split(maxsplit=1)
        hours = 0
        is_permanent = True
        user_arg = None

        if parts:
            if parts[0].isdigit():
                hours = int(parts[0])
                is_permanent = False
                user_arg = parts[1] if len(parts) > 1 else None
            else:
                user_arg = arg

        user, user_id, name = await _get_user_from_arg(cl, event, user_arg)

        if not user_id:
            if current_language == "fa":
                return await event.edit("❌ **ریپلای بزن یا @user/ID بده!**")
            else:
                return await event.edit("❌ **Reply or provide @user/ID!**")

        try:
            if is_permanent:
                await cl(EditBannedRequest(event.chat_id, user_id,
                    ChatBannedRights(until_date=timedelta(days=366), send_messages=True)))

                if current_language == "fa":
                    await event.edit(f"""
🔇 کاربر سکوت شد!
━━━━━━━━━━━━━━━━━━━

👤 {name}
🆔 `{user_id}`
⏱️ دائمی ∞

━━━━━━━━━━━━━━━━━━━
""")
                else:
                    await event.edit(f"""
🔇 User Muted!
━━━━━━━━━━━━━━━━━━━

👤 {name}
🆔 `{user_id}`
⏱️ Permanent ∞

━━━━━━━━━━━━━━━━━━━
""")
            else:
                await cl(EditBannedRequest(event.chat_id, user_id,
                    ChatBannedRights(until_date=timedelta(hours=hours), send_messages=True)))

                if current_language == "fa":
                    await event.edit(f"""
🔇 کاربر سکوت شد!
━━━━━━━━━━━━━━━━━━━

👤 {name}
🆔 `{user_id}`
⏱️ {hours} ساعت

━━━━━━━━━━━━━━━━━━━
""")
                else:
                    await event.edit(f"""
🔇 User Muted!
━━━━━━━━━━━━━━━━━━━

👤 {name}
🆔 `{user_id}`
⏱️ {hours} hour(s)

━━━━━━━━━━━━━━━━━━━
""")

        except ChatAdminRequiredError:
            if current_language == "fa":
                await event.edit("❌ **نیاز به دسترسی ادمین!**")
            else:
                await event.edit("❌ **Admin rights required!**")
        except UserAdminInvalidError:
            if current_language == "fa":
                await event.edit("❌ **نمیشه ادمین رو سکوت کرد!**")
            else:
                await event.edit("❌ **Can't mute admin!**")
        except Exception as e:
            await event.edit(f"❌ `{e}`")

    # ═══════════════ 🔊 حذف سکوت / Unmute ═══════════════
    @cl.on(events.NewMessage(pattern=rf"^(?:\{PREFIX})?(حذف\s+سکوت|unmute)\s*(.*)$"))
    async def cmd_unmute(event):
        if not await _is_owner(event):
            return
        if not bot_enabled:
            return
        cmd = event.pattern_match.group(1).replace(" ", "").lower()
        if current_language == "en" and cmd == "حذفسکوت":
            return
        if current_language == "fa" and cmd == "unmute":
            return

        user_arg = event.pattern_match.group(2).strip()
        user, user_id, name = await _get_user_from_arg(cl, event, user_arg if user_arg else None)

        if not user_id:
            if current_language == "fa":
                return await event.edit("❌ **ریپلای بزن یا @user/ID بده!**")
            else:
                return await event.edit("❌ **Reply or provide @user/ID!**")

        try:
            await cl(EditBannedRequest(event.chat_id, user_id,
                ChatBannedRights(until_date=None, send_messages=False)))

            if current_language == "fa":
                await event.edit(f"""
🔊 سکوت برداشته شد!
━━━━━━━━━━━━━━━━━━━

👤 {name}
🆔 `{user_id}`

━━━━━━━━━━━━━━━━━━━
""")
            else:
                await event.edit(f"""
🔊 User Unmuted!
━━━━━━━━━━━━━━━━━━━

👤 {name}
🆔 `{user_id}`

━━━━━━━━━━━━━━━━━━━
""")
        except Exception as e:
            await event.edit(f"❌ {e}")

    # ═══════════════ 🚫 بن / Ban ═══════════════
    @cl.on(events.NewMessage(pattern=rf"^(?:\{PREFIX})?(بن|ban)\s*(.*)$"))
    async def cmd_ban(event):
        if not await _is_owner(event):
            return
        if not bot_enabled:
            return
        cmd = event.pattern_match.group(1).lower()
        if current_language == "en" and cmd == "بن":
            return
        if current_language == "fa" and cmd == "ban":
            return

        user_arg = event.pattern_match.group(2).strip()
        user, user_id, name = await _get_user_from_arg(cl, event, user_arg if user_arg else None)

        if not user_id:
            if current_language == "fa":
                return await event.edit("❌ **ریپلای بزن یا @user/ID بده!**")
            else:
                return await event.edit("❌ **Reply or provide @user/ID!**")

        try:
            await cl(EditBannedRequest(event.chat_id, user_id,
                ChatBannedRights(until_date=None, view_messages=True)))

            if current_language == "fa":
                await event.edit(f"""
🚫 کاربر بن شد!
━━━━━━━━━━━━━━━━━━━

👤 {name}
🆔 `{user_id}`

━━━━━━━━━━━━━━━━━━━
""")
            else:
                await event.edit(f"""
🚫 User Banned!
━━━━━━━━━━━━━━━━━━━

👤 {name}
🆔 `{user_id}`

━━━━━━━━━━━━━━━━━━━
""")
        except ChatAdminRequiredError:
            if current_language == "fa":
                await event.edit("❌ نیاز به دسترسی ادمین!")
            else:
                await event.edit("❌ Admin rights required!")
        except UserAdminInvalidError:
            if current_language == "fa":
                await event.edit("❌ نمیشه ادمین رو بن کرد!")
            else:
                await event.edit("❌ Can't ban admin!")
        except Exception as e:
            await event.edit(f"❌ {e}")

    # ═══════════════ ✅ حذف بن / Unban ═══════════════
    @cl.on(events.NewMessage(pattern=rf"^(?:\{PREFIX})?(حذف\s+بن|unban)\s*(.*)$"))
    async def cmd_unban(event):
        if not await _is_owner(event):
            return
        if not bot_enabled:
            return
        cmd = event.pattern_match.group(1).replace(" ", "").lower()
        if current_language == "en" and cmd == "حذفبن":
            return
        if current_language == "fa" and cmd == "unban":
            return

        user_arg = event.pattern_match.group(2).strip()
        user, user_id, name = await _get_user_from_arg(cl, event, user_arg if user_arg else None)

        if not user_id:
            if current_language == "fa":
                return await event.edit("❌ **ریپلای بزن یا @user/ID بده!**")
            else:
                return await event.edit("❌ **Reply or provide @user/ID!**")

        try:
            await cl(EditBannedRequest(event.chat_id, user_id,
                ChatBannedRights(until_date=None, view_messages=False)))

            if current_language == "fa":
                await event.edit(f"""
✅ بن برداشته شد!
━━━━━━━━━━━━━━━━━━━

👤 {name}
🆔 `{user_id}`

━━━━━━━━━━━━━━━━━━━
""")
            else:
                await event.edit(f"""
✅ User Unbanned!
━━━━━━━━━━━━━━━━━━━

👤 {name}
🆔 `{user_id}`

━━━━━━━━━━━━━━━━━━━
""")
        except Exception as e:
            await event.edit(f"❌ {e}")

    # ═══════════════ 📷 سیو تایم دار / AutoSave ═══════════════
    @cl.on(events.NewMessage(pattern=rf"^(?:\{PREFIX})?(سیو\s+تایم\s+دار|autosave)$"))
    async def cmd_autosave(event):
        if not await _is_owner(event):
            return
        if not bot_enabled:
            return
        cmd = event.pattern_match.group(1).replace(" ", "").lower()
        if current_language == "en" and cmd == "سیوتایمدار":
            return
        if current_language == "fa" and cmd == "autosave":
            return

        global auto_save_enabled
        await event.delete()
        auto_save_enabled = not auto_save_enabled

        if current_language == "fa":
            if auto_save_enabled:
                await cl.send_message("me", "📸 **ذخیره خودکار فعال شد!** ✅")
            else:
                await cl.send_message("me", "📸 **ذخیره خودکار غیرفعال شد!** ❌")
        else:
            if auto_save_enabled:
                await cl.send_message("me", "📸 **Auto-Save Enabled!** ✅")
            else:
                await cl.send_message("me", "📸 **Auto-Save Disabled!** ❌")

    # ═══════════════ 💾 سیو عکس / Save ═══════════════
    @cl.on(events.NewMessage(pattern=rf"^(?:\{PREFIX})?(سیو\s+عکس|save)$"))
    async def cmd_save(event):
        if not await _is_owner(event):
            return
        if not bot_enabled:
            return
        cmd = event.pattern_match.group(1).replace(" ", "").lower()
        if current_language == "en" and cmd == "سیوعکس":
            return
        if current_language == "fa" and cmd == "save":
            return

        await event.delete()
        reply = await event.get_reply_message()
        if not reply or not reply.media:
            if current_language == "fa":
                return await cl.send_message("me", "❌ **روی مدیا ریپلای بزن!**")
            else:
                return await cl.send_message("me", "❌ **Reply to media!**")
        try:
            buf = io.BytesIO()
            await cl.download_media(reply, file=buf)
            buf.seek(0)
            if buf.getbuffer().nbytes > 0:
                global saved_count
                saved_count += 1
                buf.name = "saved.jpg"
                if current_language == "fa":
                    await cl.send_file("me", buf, caption="📸 **ذخیره شد!** ✅")
                else:
                    await cl.send_file("me", buf, caption="📸 **Saved!** ✅")
        except Exception as e:
            await cl.send_message("me", f"❌ `{e}`")

    # ═══════════════ 📢 اسپم / Spam ═══════════════
    @cl.on(events.NewMessage(pattern=rf"^(?:\{PREFIX})?(اسپم|spam)\s+(.+)$"))
    async def cmd_spam(event):
        if not await _is_owner(event):
            return
        if not bot_enabled:
            return
        cmd = event.pattern_match.group(1).lower()
        if current_language == "en" and cmd == "اسپم":
            return
        if current_language == "fa" and cmd == "spam":
            return

        arg = event.pattern_match.group(2).strip()
        if current_language == "fa":
            arg = _fa_to_en_numbers(arg)

        parts = arg.split(maxsplit=1)
        if len(parts) < 2 or not parts[0].isdigit():
            return

        count = min(int(parts[0]), 100)
        text = parts[1]
        await event.delete()
        for _ in range(count):
            try:
                await cl.send_message(event.chat_id, text)
                await asyncio.sleep(0.4)
            except:
                break

    # ═══════════════ 📌 پین / Pin ═══════════════
    @cl.on(events.NewMessage(pattern=rf"^(?:\{PREFIX})?(پین|pin)$"))
    async def cmd_pin(event):
        if not await _is_owner(event):
            return
        if not bot_enabled:
            return
        cmd = event.pattern_match.group(1).lower()
        if current_language == "en" and cmd == "پین":
            return
        if current_language == "fa" and cmd == "pin":
            return

        reply = await event.get_reply_message()
        if not reply:
            if current_language == "fa":
                return await event.edit("❌ **روی پیام ریپلای بزن!**")
            else:
                return await event.edit("❌ **Reply to a message!**")
        try:
            await cl.pin_message(event.chat_id, reply.id)
            if current_language == "fa":
                await event.edit("📌 **پین شد!** ✅")
            else:
                await event.edit("📌 **Pinned!** ✅")
        except Exception as e:
            await event.edit(f"❌ `{e}`")

    # ═══════════════ ⬇️ گرفتن / Grab ═══════════════
    @cl.on(events.NewMessage(pattern=rf"^(?:\{PREFIX})?(گرفتن|grab)\s+(.+)$"))
    async def cmd_grab(event):
        if not await _is_owner(event):
            return
        if not bot_enabled:
            return
        cmd = event.pattern_match.group(1).lower()
        if current_language == "en" and cmd == "گرفتن":
            return
        if current_language == "fa" and cmd == "grab":
            return

        link = event.pattern_match.group(2).strip()
        ch_id, msg_id = _parse_link(link)
        if ch_id is None:
            if current_language == "fa":
                return await event.edit("❌ **لینک نامعتبر!**")
            else:
                return await event.edit("❌ **Invalid link!**")

        if current_language == "fa":
            await event.edit("📥 **در حال دریافت...**")
        else:
            await event.edit("📥 **Grabbing...**")

        try:
            msg = await cl.get_messages(ch_id, ids=msg_id)
        except Exception as e:
            return await event.edit(f"❌ `{e}`")

        if not msg:
            if current_language == "fa":
                return await event.edit("❌ **پیام پیدا نشد!**")
            else:
                return await event.edit("❌ **Message not found!**")

        if not msg.media:
            await event.delete()
            await cl.send_message(event.chat_id, msg.text or "")
            return

        buf = io.BytesIO()
        try:
            await cl.download_media(msg, file=buf)
        except:
            pass

        if buf.tell() == 0:
            if current_language == "fa":
                return await event.edit("❌ **دانلود ناموفق!**")
            else:
                return await event.edit("❌ **Download failed!**")

        _, _, fname = _get_file_info(msg)
        buf.seek(0)
        buf.name = fname

        try:
            await cl.send_file(event.chat_id, buf, caption=msg.text or None)
            await event.delete()
        except Exception as e:
            await event.edit(f"❌ `{e}`")

    # ═══════════════ 🔗 لینک / Link ═══════════════
    @cl.on(events.NewMessage(pattern=rf"^(?:\{PREFIX})?(لینک|link)$"))
    async def cmd_link(event):
        if not await _is_owner(event):
            return
        if not bot_enabled:
            return
        cmd = event.pattern_match.group(1).lower()
        if current_language == "en" and cmd == "لینک":
            return
        if current_language == "fa" and cmd == "link":
            return

        reply = await event.get_reply_message()
        if not reply:
            if current_language == "fa":
                return await event.edit("❌ **روی پیام ریپلای بزن!**")
            else:
                return await event.edit("❌ **Reply to a message!**")
        chat = await event.get_chat()
        if hasattr(chat, 'username') and chat.username:
            link = f"https://t.me/{chat.username}/{reply.id}"
        else:
            cid = str(chat.id)
            if cid.startswith("-100"):
                link = f"https://t.me/c/{cid[4:]}/{reply.id}"
            else:
                return await event.edit("❌")
        await event.edit(f"🔗 `{link}`")

    # ═══════════════ 🆔 آیدی / ID ═══════════════
    @cl.on(events.NewMessage(pattern=rf"^(?:\{PREFIX})?(آیدی|id)$"))
    async def cmd_id(event):
        if not await _is_owner(event):
            return
        if not bot_enabled:
            return
        cmd = event.pattern_match.group(1).lower()
        if current_language == "en" and cmd == "آیدی":
            return
        if current_language == "fa" and cmd == "id":
            return

        chat = await event.get_chat()
        me = await cl.get_me()
        cn = getattr(chat, 'title', getattr(chat, 'first_name', '?'))
        text = f"💬 **{cn}** | `{chat.id}`\n"
        reply = await event.get_reply_message()
        if reply:
            s = await reply.get_sender()
            if s:
                text += f"👤 **{s.first_name}** | `{s.id}`\n"
        text += f"🙋 **{me.first_name}** | `{me.id}`"
        await event.edit(text)

    # ═══════════════ Watchers ═══════════════

    @cl.on(events.NewMessage(incoming=True))
    async def reaction_watcher(event):
        if not bot_enabled or not reaction_settings["enabled"]:
            return

        chat_id = event.chat_id
        sender_id = event.sender_id

        emoji_to_use = None

        key_chat_user = f"chat_{chat_id}_user_{sender_id}"
        if key_chat_user in reaction_settings["targets"]:
            emoji_to_use = reaction_settings["targets"][key_chat_user].get("emoji", reaction_settings["emoji"])

        if not emoji_to_use:
            key_user = f"user_{sender_id}"
            if key_user in reaction_settings["targets"]:
                emoji_to_use = reaction_settings["targets"][key_user].get("emoji", reaction_settings["emoji"])

        if emoji_to_use:
            try:
                await cl(SendReactionRequest(
                    peer=chat_id,
                    msg_id=event.id,
                    reaction=[ReactionEmoji(emoticon=emoji_to_use)]
                ))
            except:
                pass

    # ═══════════════ 🛡️ ضد اسپم / AntiSpam Watcher ═══════════════
    @cl.on(events.NewMessage(incoming=True))
    async def antispam_watcher(event):
        if not bot_enabled:
            return

        me = await cl.get_me()
        if event.sender_id == me.id:
            return

        cid = event.chat_id
        uid = event.sender_id
        now = time.time()
        key = (cid, uid)

        # پیوی
        if event.is_private and antispam_pv_enabled:
            user_msg_times[key] = [t for t in user_msg_times[key] if now - t < 10]
            user_msg_times[key].append(now)

            if len(user_msg_times[key]) >= SPAM_LIMIT and key not in warned_users:
                warned_users.add(key)
                try:
                    await cl.send_message(uid, "🚫 **شما به دلیل اسپم بلاک شدید برای ۱ روز!**")
                    await cl(BlockRequest(uid))
                except:
                    pass
            return

        # گپ
        if cid in antispam_groups:
            sender = await event.get_sender()
            if not sender or sender.bot:
                return

            try:
                p = await cl(GetParticipantRequest(cid, uid))
                if isinstance(p.participant, (ChannelParticipantAdmin, ChannelParticipantCreator)):
                    return
            except:
                pass

            user_msg_times[key] = [t for t in user_msg_times[key] if now - t < 10]
            user_msg_times[key].append(now)

            if len(user_msg_times[key]) >= SPAM_LIMIT and key not in warned_users:
                warned_users.add(key)
                try:
                    await event.delete()
                    await cl(EditBannedRequest(cid, uid,
                        ChatBannedRights(until_date=timedelta(hours=1), send_messages=True)))
                except:
                    pass

    @cl.on(events.NewMessage(incoming=True))
    async def autosave_w(event):
        if not bot_enabled or not auto_save_enabled or not event.media:
            return
        if not getattr(event.media, 'ttl_seconds', None):
            return
        try:
            sender = await event.get_sender()
            buf = io.BytesIO()
            await cl.download_media(event.message, file=buf)
            buf.seek(0)
            if buf.getbuffer().nbytes > 0:
                global saved_count
                saved_count += 1
                buf.name = "timed.jpg"
                sn = sender.first_name if sender else "?"
                await cl.send_file("me", buf, caption=f"📸 {sn}")
        except:
            pass

    # ═══════════════ 🗑️ ذخیره پیام‌های پیوی / Cache PV ═══════════════
    @cl.on(events.NewMessage(incoming=True))
    async def cache_pv_messages(event):
        if not bot_enabled or not anti_delete_enabled:
            return
        if not event.is_private:
            return

        chat_id = event.chat_id
        msg_id = event.id

        try:
            sender = await event.get_sender()
            sender_name = sender.first_name if sender else "?"
        except:
            sender_name = "?"

        data = {
            "text": event.text or "",
            "sender_id": event.sender_id,
            "sender_name": sender_name,
            "date": event.date.strftime("%Y-%m-%d %H:%M:%S"),
            "media": None,
            "media_name": None
        }

        if event.media:
            try:
                buf = io.BytesIO()
                await cl.download_media(event, file=buf)
                buf.seek(0)
                if buf.getbuffer().nbytes > 0:
                    _, _, fname = _get_file_info(event)
                    buf.name = fname
                    data["media"] = buf
                    data["media_name"] = fname
            except:
                pass

        message_cache[chat_id][msg_id] = data

        if len(message_cache[chat_id]) > MAX_CACHE_PER_CHAT:
            oldest = sorted(message_cache[chat_id].keys())[:50]
            for k in oldest:
                del message_cache[chat_id][k]

    # ═══════════════ 🗑️ تشخیص حذف پیام / Detect Delete ═══════════════
    @cl.on(events.MessageDeleted())
    async def on_message_deleted(event):
        if not bot_enabled or not anti_delete_enabled:
            return

        deleted_ids = event.deleted_ids

        found = {}
        for chat_id, messages in list(message_cache.items()):
            for msg_id in deleted_ids:
                if msg_id in messages:
                    if chat_id not in found:
                        found[chat_id] = []
                    found[chat_id].append((msg_id, messages[msg_id]))

        for chat_id, msg_list in found.items():

            if len(msg_list) >= 5:
                sender_name = msg_list[0][1]["sender_name"]
                sender_id = msg_list[0][1]["sender_id"]

                content = f"📋 پیام‌های حذف شده\n"
                content += f"👤 {sender_name} | {sender_id}\n"
                content += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                content += f"━━━━━━━━━━━━━━━━━━━\n\n"

                for msg_id, data in sorted(msg_list, key=lambda x: x[0]):
                    content += f"[{data['date']}]\n"
                    if data["text"]:
                        content += f"{data['text']}\n"
                    elif data.get("media_name"):
                        content += f"(📎 {data['media_name']})\n"
                    else:
                        content += "(بدون متن)\n"
                    content += "\n"

                txt_buf = io.BytesIO(content.encode('utf-8'))
                txt_buf.name = f"deleted_chat_{sender_name}.txt"

                if current_language == "fa":
                    await cl.send_file("me", txt_buf,
                        caption=f"🗑️ **دیلیت چت!**\n\n👤 **{sender_name}**\n🆔 `{sender_id}`\n📊 **{len(msg_list)}** پیام حذف شد")
                else:
                    await cl.send_file("me", txt_buf,
                        caption=f"🗑️ **Chat Deleted!**\n\n👤 **{sender_name}**\n🆔 `{sender_id}`\n📊 **{len(msg_list)}** messages deleted")

                for msg_id, data in msg_list:
                    if data.get("media"):
                        try:
                            data["media"].seek(0)
                            await cl.send_file("me", data["media"],
                                caption=f"📎 مدیای حذف شده | {sender_name}")
                        except:
                            pass

                try:
                    await cl.send_message(chat_id, "ریدی چرا پاک کردی 😂")
                except:
                    pass

                for msg_id, _ in msg_list:
                    message_cache[chat_id].pop(msg_id, None)

            else:
                for msg_id, data in msg_list:
                    if current_language == "fa":
                        text = f"""
🗑️ پیام حذف شده!
━━━━━━━━━━━━━━━━━━━

👤 {data['sender_name']}
🆔 `{data['sender_id']}`
📅 {data['date']}

💬 {data['text'] or '(بدون متن)'}

━━━━━━━━━━━━━━━━━━━
"""
                    else:
                        text = f"""
🗑️ Deleted Message!
━━━━━━━━━━━━━━━━━━━

👤 {data['sender_name']}
🆔 `{data['sender_id']}`
📅 {data['date']}

💬 {data['text'] or '(no text)'}

━━━━━━━━━━━━━━━━━━━
"""
                    await cl.send_message("me", text)

                    if data.get("media"):
                        try:
                            data["media"].seek(0)
                            await cl.send_file("me", data["media"],
                                caption=f"📎 {data['sender_name']}")
                        except:
                            pass

                    try:
                        await cl.send_message(chat_id, "ریدی چرا پاک کردی 😂")
                    except:
                        pass

                    message_cache[chat_id].pop(msg_id, None)


# ══════════════════════════════════════════════════
# 👑 Admin Commands (Account Management)
# ══════════════════════════════════════════════════
@client.on(events.NewMessage(pattern=rf"^(?:\{PREFIX})?(افزودن|add)\s+(\+\d+)$"))
async def cmd_add(event):
    if event.sender_id != ADMIN_USER_ID:
        return
    if not bot_enabled:
        return
    cmd = event.pattern_match.group(1).lower()
    if current_language == "en" and cmd == "افزودن":
        return
    if current_language == "fa" and cmd == "add":
        return

    phone = event.pattern_match.group(2).strip()

    if phone in accounts:
        if current_language == "fa":
            return await event.edit("⚠️ **این شماره قبلاً اضافه شده!**")
        else:
            return await event.edit("⚠️ **This number already exists!**")

    sn = f"account_{phone.replace('+', '')}"
    try:
        nc = TelegramClient(sn, API_ID, API_HASH,
            connection=ConnectionTcpMTProxyRandomizedIntermediate,
            proxy=(MTPROTO_SERVER, MTPROTO_PORT, MTPROTO_SECRET))
        await nc.connect()
        sc = await nc.send_code_request(phone)
        pending_auth[ADMIN_USER_ID] = {"client": nc, "phone": phone,
            "hash": sc.phone_code_hash, "step": "code", "session": sn}

        if current_language == "fa":
            await event.edit(f"""
✅ کد ارسال شد!
━━━━━━━━━━━━━━━━━━━

📱 شماره: `{phone}`
📨 کد به تلگرام ارسال شد

📝 کد رو وارد کن:
`{PREFIX}کد 12345`

━━━━━━━━━━━━━━━━━━━
""")
        else:
            await event.edit(f"""
✅ Code Sent!
━━━━━━━━━━━━━━━━━━━

📱 Phone: `{phone}`
📨 Code sent to Telegram

📝 Enter the code:
`{PREFIX}code 12345`

━━━━━━━━━━━━━━━━━━━
""")
    except Exception as e:
        await event.edit(f"❌ {e}")


@client.on(events.NewMessage(pattern=rf"^(?:\{PREFIX})?(کد|code)\s+(.+)$"))
async def cmd_code(event):
    if event.sender_id != ADMIN_USER_ID:
        return
    if not bot_enabled:
        return
    cmd = event.pattern_match.group(1).lower()
    if current_language == "en" and cmd == "کد":
        return
    if current_language == "fa" and cmd == "code":
        return

    if ADMIN_USER_ID not in pending_auth:
        if current_language == "fa":
            return await event.edit("❌ **درخواستی وجود ندارد!**")
        else:
            return await event.edit("❌ **No pending request!**")

    ad = pending_auth[ADMIN_USER_ID]
    if ad["step"] != "code":
        return

    code = event.pattern_match.group(2).strip()
    if current_language == "fa":
        code = _fa_to_en_numbers(code)

    try:
        await ad["client"].sign_in(ad["phone"], code, phone_code_hash=ad["hash"])
        mn = await ad["client"].get_me()
        accounts[ad["phone"]] = {
            "session": ad["session"],
            "name": mn.first_name or "?",
            "username": mn.username or "none",
            "user_id": mn.id,
            "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        save_accounts(accounts)
        active_clients[ad["phone"]] = ad["client"]
        register_handlers(ad["client"])
        all_clients.append(ad["client"])
        del pending_auth[ADMIN_USER_ID]

        if current_language == "fa":
            await event.edit(f"""
✅ اکانت اضافه شد!
━━━━━━━━━━━━━━━━━━━

👤 نام: {mn.first_name}
🆔 آیدی: `{mn.id}`
📧 یوزرنیم: @{mn.username or 'none'}
📱 شماره: `{ad['phone']}`

━━━━━━━━━━━━━━━━━━━
""")
        else:
            await event.edit(f"""
✅ Account Added!
━━━━━━━━━━━━━━━━━━━

👤 Name: {mn.first_name}
🆔 ID: `{mn.id}`
📧 Username: @{mn.username or 'none'}
📱 Phone: `{ad['phone']}`

━━━━━━━━━━━━━━━━━━━
""")
    except PhoneCodeInvalidError:
        if current_language == "fa":
            await event.edit("❌ کد اشتباه است!")
        else:
            await event.edit("❌ Invalid code!")
    except PhoneCodeExpiredError:
        del pending_auth[ADMIN_USER_ID]
        if current_language == "fa":
            await event.edit("❌ کد منقضی شده! دوباره امتحان کن.")
        else:
            await event.edit("❌ Code expired! Try again.")
    except Exception as e:
        if "password" in str(e).lower():
            ad["step"] = "password"
            if current_language == "fa":
                await event.edit(f"""
🔐 رمز دو مرحله‌ای لازمه!
━━━━━━━━━━━━━━━━━━━

📝 رمز رو وارد کن:
`{PREFIX}رمز yourpassword`

━━━━━━━━━━━━━━━━━━━
""")
            else:
                await event.edit(f"""
🔐 2FA Password Required!
━━━━━━━━━━━━━━━━━━━

📝 Enter password:
`{PREFIX}pass yourpassword`

━━━━━━━━━━━━━━━━━━━
""")
        else:
            await event.edit(f"❌ {e}")


@client.on(events.NewMessage(pattern=rf"^(?:\{PREFIX})?(رمز|pass)\s+(.+)$"))
async def cmd_pass(event):
    if event.sender_id != ADMIN_USER_ID:
        return
    if not bot_enabled:
        return
    cmd = event.pattern_match.group(1).lower()
    if current_language == "en" and cmd == "رمز":
        return
    if current_language == "fa" and cmd == "pass":
        return

    if ADMIN_USER_ID not in pending_auth:
        return
    ad = pending_auth[ADMIN_USER_ID]
    if ad["step"] != "password":
        return

    try:
        await ad["client"].sign_in(password=event.pattern_match.group(2).strip())
        mn = await ad["client"].get_me()
        accounts[ad["phone"]] = {
            "session": ad["session"],
            "name": mn.first_name or "?",
            "username": mn.username or "none",
            "user_id": mn.id,
            "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        save_accounts(accounts)
        active_clients[ad["phone"]] = ad["client"]
        register_handlers(ad["client"])
        all_clients.append(ad["client"])
        del pending_auth[ADMIN_USER_ID]

        if current_language == "fa":
            await event.edit(f"""
✅ اکانت اضافه شد! 🔐
━━━━━━━━━━━━━━━━━━━

👤 نام: {mn.first_name}
🆔 آیدی: `{mn.id}`
📧 یوزرنیم: @{mn.username or 'none'}
📱 شماره: `{ad['phone']}`

━━━━━━━━━━━━━━━━━━━
""")
        else:
            await event.edit(f"""
✅ Account Added! 🔐
━━━━━━━━━━━━━━━━━━━

👤 Name: {mn.first_name}
🆔 ID: `{mn.id}`
📧 Username: @{mn.username or 'none'}
📱 Phone: `{ad['phone']}`

━━━━━━━━━━━━━━━━━━━
""")
    except PasswordHashInvalidError:
        if current_language == "fa":
            await event.edit("❌ رمز اشتباه است!")
        else:
            await event.edit("❌ Wrong password!")
    except Exception as e:
        await event.edit(f"❌ {e}")


@client.on(events.NewMessage(pattern=rf"^(?:\{PREFIX})?(لیست|list)$"))
async def cmd_list(event):
    if event.sender_id != ADMIN_USER_ID:
        return
    if not bot_enabled:
        return
    cmd = event.pattern_match.group(1).lower()
    if current_language == "en" and cmd == "لیست":
        return
    if current_language == "fa" and cmd == "list":
        return

    if not accounts:
        if current_language == "fa":
            return await event.edit("📭 **هیچ اکانتی وجود ندارد!**")
        else:
            return await event.edit("📭 **No accounts!**")

    if current_language == "fa":
        text = f"""
👥 لیست اکانت‌ها
━━━━━━━━━━━━━━━━━━━

"""
    else:
        text = f"""
👥 Account List
━━━━━━━━━━━━━━━━━━━

"""

    for i, (ph, info) in enumerate(accounts.items(), 1):
        st = "🟢" if ph in active_clients else "🔴"
        text += f"""**{i}.** {st} `{ph}`
╰ 👤 {info['name']} | @{info.get('username', 'none')}
╰ 🆔 `{info.get('user_id', '?')}`

"""

    if current_language == "fa":
        text += f"""━━━━━━━━━━━━━━━━━━━
📊 تعداد کل: {len(accounts)} اکانت
🟢 فعال: {len(active_clients)} | 🔴 غیرفعال: {len(accounts) - len(active_clients)}
"""
    else:
        text += f"""━━━━━━━━━━━━━━━━━━━
📊 Total: {len(accounts)} accounts
🟢 Active: {len(active_clients)} | 🔴 Inactive: {len(accounts) - len(active_clients)}
"""

    await event.edit(text)


@client.on(events.NewMessage(pattern=rf"^(?:\{PREFIX})?(حذف\s+اکانت|remove)\s+(\+\d+)$"))
async def cmd_remove(event):
    if event.sender_id != ADMIN_USER_ID:
        return
    if not bot_enabled:
        return
    cmd = event.pattern_match.group(1).replace(" ", "").lower()
    if current_language == "en" and cmd == "حذفاکانت":
        return
    if current_language == "fa" and cmd == "remove":
        return

    phone = event.pattern_match.group(2).strip()

    if phone not in accounts:
        if current_language == "fa":
            return await event.edit("❌ **این شماره در لیست نیست!**")
        else:
            return await event.edit("❌ **This number not found!**")

    acc_info = accounts[phone]
    acc_name = acc_info.get('name', '?')
    acc_id = acc_info.get('user_id', '?')

    if phone in active_clients:
        try:
            await active_clients[phone].disconnect()
        except:
            pass
        del active_clients[phone]

    sf = f"{acc_info['session']}.session"
    if os.path.exists(sf):
        os.remove(sf)

    del accounts[phone]
    save_accounts(accounts)

    if current_language == "fa":
        await event.edit(f"""
🗑️ اکانت حذف شد!
━━━━━━━━━━━━━━━━━━━

👤 نام: {acc_name}
🆔 آیدی: `{acc_id}`
📱 شماره: `{phone}`

📊 باقی‌مانده: {len(accounts)} اکانت

━━━━━━━━━━━━━━━━━━━
""")
    else:
        await event.edit(f"""
🗑️ Account Removed!
━━━━━━━━━━━━━━━━━━━

👤 Name: {acc_name}
🆔 ID: `{acc_id}`
📱 Phone: `{phone}`

📊 Remaining: {len(accounts)} accounts

━━━━━━━━━━━━━━━━━━━
""")


@client.on(events.NewMessage(pattern=rf"^(?:\{PREFIX})?(غیر\s?فعال|deactivate)\s+(\+\d+)$"))
async def cmd_deactivate(event):
    if event.sender_id != ADMIN_USER_ID:
        return
    if not bot_enabled:
        return
    cmd = event.pattern_match.group(1).replace(" ", "").lower()
    if current_language == "en" and cmd == "غیرفعال":
        return
    if current_language == "fa" and cmd == "deactivate":
        return

    phone = event.pattern_match.group(2).strip()

    if phone not in accounts:
        if current_language == "fa":
            return await event.edit("❌ **این شماره در لیست نیست!**")
        else:
            return await event.edit("❌ **This number not found!**")

    acc_info = accounts[phone]
    acc_name = acc_info.get('name', '?')
    acc_id = acc_info.get('user_id', '?')

    if phone not in active_clients:
        if current_language == "fa":
            return await event.edit(f"""
⚠️ این اکانت از قبل غیرفعال است!
━━━━━━━━━━━━━━━━━━━

👤 نام: {acc_name}
📱 شماره: `{phone}`

━━━━━━━━━━━━━━━━━━━
""")
        else:
            return await event.edit(f"""
⚠️ This account is already deactivated!
━━━━━━━━━━━━━━━━━━━

👤 Name: {acc_name}
📱 Phone: `{phone}`

━━━━━━━━━━━━━━━━━━━
""")

    try:
        await active_clients[phone].disconnect()
    except:
        pass

    if active_clients[phone] in all_clients:
        all_clients.remove(active_clients[phone])

    del active_clients[phone]

    if current_language == "fa":
        await event.edit(f"""
🔴 اکانت غیرفعال شد!
━━━━━━━━━━━━━━━━━━━

👤 نام: {acc_name}
🆔 آیدی: `{acc_id}`
📱 شماره: `{phone}`

💡 برای فعال‌سازی مجدد:
`{PREFIX}فعال {phone}`

📊 فعال: {len(active_clients)} | غیرفعال: {len(accounts) - len(active_clients)}

━━━━━━━━━━━━━━━━━━━
""")
    else:
        await event.edit(f"""
🔴 Account Deactivated!
━━━━━━━━━━━━━━━━━━━

👤 Name: {acc_name}
🆔 ID: `{acc_id}`
📱 Phone: `{phone}`

💡 To reactivate:
`{PREFIX}activate {phone}`

📊 Active: {len(active_clients)} | Inactive: {len(accounts) - len(active_clients)}

━━━━━━━━━━━━━━━━━━━
""")


@client.on(events.NewMessage(pattern=rf"^(?:\{PREFIX})?(فعال|activate)\s+(\+\d+)$"))
async def cmd_activate(event):
    if event.sender_id != ADMIN_USER_ID:
        return
    if not bot_enabled:
        return
    cmd = event.pattern_match.group(1).lower()
    if current_language == "en" and cmd == "فعال":
        return
    if current_language == "fa" and cmd == "activate":
        return

    phone = event.pattern_match.group(2).strip()

    if phone not in accounts:
        if current_language == "fa":
            return await event.edit("❌ **این شماره در لیست نیست!**")
        else:
            return await event.edit("❌ **This number not found!**")

    acc_info = accounts[phone]
    acc_name = acc_info.get('name', '?')
    acc_id = acc_info.get('user_id', '?')

    if phone in active_clients:
        if current_language == "fa":
            return await event.edit(f"""
⚠️ این اکانت از قبل فعال است!
━━━━━━━━━━━━━━━━━━━

👤 نام: {acc_name}
📱 شماره: `{phone}`

━━━━━━━━━━━━━━━━━━━
""")
        else:
            return await event.edit(f"""
⚠️ This account is already active!
━━━━━━━━━━━━━━━━━━━

👤 Name: {acc_name}
📱 Phone: `{phone}`

━━━━━━━━━━━━━━━━━━━
""")

    if current_language == "fa":
        await event.edit(f"🔄 **در حال فعال‌سازی** `{phone}` **...**")
    else:
        await event.edit(f"🔄 **Activating** `{phone}` **...**")

    try:
        ac = TelegramClient(acc_info["session"], API_ID, API_HASH,
            connection=ConnectionTcpMTProxyRandomizedIntermediate,
            proxy=(MTPROTO_SERVER, MTPROTO_PORT, MTPROTO_SECRET))
        await ac.connect()

        if not await ac.is_user_authorized():
            if current_language == "fa":
                return await event.edit(f"""
❌ سشن منقضی شده!
━━━━━━━━━━━━━━━━━━━

📱 شماره: `{phone}`
💡 باید دوباره اضافه کنی:
`{PREFIX}حذف اکانت {phone}`
`{PREFIX}افزودن {phone}`

━━━━━━━━━━━━━━━━━━━
""")
            else:
                return await event.edit(f"""
❌ Session expired!
━━━━━━━━━━━━━━━━━━━

📱 Phone: `{phone}`
💡 You need to re-add:
`{PREFIX}remove {phone}`
`{PREFIX}add {phone}`

━━━━━━━━━━━━━━━━━━━
""")

        active_clients[phone] = ac
        register_handlers(ac)
        all_clients.append(ac)

        mn = await ac.get_me()
        accounts[phone]["name"] = mn.first_name or "?"
        accounts[phone]["username"] = mn.username or "none"
        save_accounts(accounts)

        if current_language == "fa":
            await event.edit(f"""
🟢 اکانت فعال شد!
━━━━━━━━━━━━━━━━━━━

👤 نام: {mn.first_name}
🆔 آیدی: `{acc_id}`
📱 شماره: `{phone}`

📊 فعال: {len(active_clients)} | غیرفعال: {len(accounts) - len(active_clients)}

━━━━━━━━━━━━━━━━━━━
""")
        else:
            await event.edit(f"""
🟢 Account Activated!
━━━━━━━━━━━━━━━━━━━

👤 Name: {mn.first_name}
🆔 ID: `{acc_id}`
📱 Phone: `{phone}`

📊 Active: {len(active_clients)} | Inactive: {len(accounts) - len(active_clients)}

━━━━━━━━━━━━━━━━━━━
""")
    except Exception as e:
        await event.edit(f"❌ {e}")


# ══════════════════════════════════════════════════
# 🚀 Main
# ══════════════════════════════════════════════════
async def main():
    global current_language
    current_language = settings.get("language", "fa")

    print("\n🔄 Connecting...")
    try:
        await client.start(phone=PHONE_NUMBER)
    except (SessionRevokedError, AuthKeyUnregisteredError):
        if os.path.exists(f"{SESSION_FILE}.session"):
            os.remove(f"{SESSION_FILE}.session")
        await client.start(phone=PHONE_NUMBER)
    except Exception as e:
        print(f"❌ {e}")
        sys.exit(1)

    me = await client.get_me()
    register_handlers(client)
    all_clients.append(client)

    is_admin = (me.id == ADMIN_USER_ID)
    lang_icon = "🇮🇷" if current_language == "fa" else "🇺🇸"
    admin_badge = "👑 ADMIN" if is_admin else "👤 USER"

    print(f"""
╔══════════════════════════════════════════════════════════╗
║ 🤖 Telegram SelfBot — v{BOT_VERSION}                             ║
║ ❤️ Made with Love by @{AUTHOR}                     ❤️ ║
╠══════════════════════════════════════════════════════════╣
║ 👤 {me.first_name:<50} ║
║ 🆔 {me.id:<50} ║
║ 🏷️  {admin_badge:<49} ║
║ 🌐 {lang_icon} {current_language.upper():<47} ║
║ 📝 {PREFIX}{'راهنما' if current_language == 'fa' else 'help':<49} ║
╚══════════════════════════════════════════════════════════╝
""")

    if is_admin:
        for ph, info in accounts.items():
            try:
                ac = TelegramClient(info["session"], API_ID, API_HASH,
                    connection=ConnectionTcpMTProxyRandomizedIntermediate,
                    proxy=(MTPROTO_SERVER, MTPROTO_PORT, MTPROTO_SECRET))
                await ac.connect()
                if await ac.is_user_authorized():
                    active_clients[ph] = ac
                    register_handlers(ac)
                    all_clients.append(ac)
                    print(f"  ✅ {ph} ({info['name']})")
            except Exception as e:
                print(f"  ❌ {ph}: {e}")

    print(f"\n🚀 Running... | Made with ❤️ by @{AUTHOR}\n")
    await client.run_until_disconnected()


if __name__ == "__main__":
    if not check_password():
        sys.exit(1)
    client.loop.run_until_complete(main())