import os
import sqlite3
from io import BytesIO
from datetime import datetime
import instaloader
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
)

# ------------------ تنظیمات ------------------
TOKEN = "token"
ADMIN_ID = 5302294637
SPONSOR_CHANNEL = "YangMoein_Tv"
DB_FILE = "downloads.db"

loader = instaloader.Instaloader(
    download_comments=False,
    save_metadata=False,
    download_video_thumbnails=False
)

user_busy = set()

# ------------------ دیتابیس ------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            url TEXT,
            date TEXT,
            time TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_download(user_id, username, url):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = datetime.now()
    c.execute("""
        INSERT INTO downloads (user_id, username, url, date, time)
        VALUES (?, ?, ?, ?, ?)
    """, (
        user_id,
        username,
        url,
        now.strftime("%Y-%m-%d"),
        now.strftime("%H:%M:%S")
    ))
    conn.commit()
    conn.close()

def get_reports():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id, username, url, date, time FROM downloads ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return rows

# ------------------ متن استارت ------------------
def start_text():
    return (
        "🤖 **ربات دانلودر اینستاگرام**\n\n"
        "سلام! من می‌توانم محتوای عمومی اینستاگرام را برای شما دانلود کنم.\n\n"
        "📋 **نحوه استفاده:**\n"
        "• لینک پست، رییل، یا ویدیو اینستاگرام را ارسال کنید\n"
        "• من محتوا را دانلود و برای شما ارسال می‌کنم\n\n"
        "🔗 **لینک‌های پشتیبانی شده:**\n"
        "• پست‌های عادی: https://instagram.com/p/...\n"
        "• رییل‌ها: https://instagram.com/reel/...\n"
        "• ویدیوهای IGTV: https://instagram.com/tv/...\n\n"
        "✅ **ویژگی‌ها:**\n"
        "• دانلود محتوای عمومی بدون نیاز به ورود\n"
        "• پشتیبانی از عکس و ویدیو\n"
        "• دانلود با کیفیت بالا\n"
        "• حداکثر حجم فایل: 50 مگابایت\n\n"
        "⚠️ **نکته مهم:**\n"
        "• فقط پست‌های عمومی قابل دانلود هستند\n"
        "• پست‌های خصوصی پشتیبانی نمی‌شوند\n\n"
        "به زودی پلتفرم‌های دیگر مانند یوتیوب، تیک تاک و ... اضافه خواهند شد.\n\n"
        "برای شروع، لینک اینستاگرام خود را ارسال کنید! 🚀"
    )

# ------------------ منوها ------------------
def main_menu(user_id):
    keyboard = [[InlineKeyboardButton("📢 درباره سیستم", callback_data="about")]]
    if user_id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("📊 گزارش دانلودها", callback_data="report")])
    return InlineKeyboardMarkup(keyboard)

def about_menu():
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]]
    return InlineKeyboardMarkup(keyboard)

# ------------------ بررسی عضویت ------------------
async def check_membership(bot, user_id):
    try:
        member = await bot.get_chat_member(chat_id=f"@{SPONSOR_CHANNEL}", user_id=user_id)
        return member.status != "left"
    except:
        return False

# ------------------ استارت ------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not await check_membership(context.bot, user_id):
        keyboard = [
            [InlineKeyboardButton("🔗 عضویت در کانال اسپانسر", url=f"https://t.me/{SPONSOR_CHANNEL}")],
            [InlineKeyboardButton("✅ بررسی عضویت", callback_data="check_join")]
        ]
        await update.message.reply_text(
            "⚠️ برای استفاده از ربات باید عضو کانال اسپانسر شوید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    await update.message.reply_text(start_text(), reply_markup=main_menu(user_id), parse_mode="Markdown")

# ------------------ دکمه‌ها ------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == "check_join":
        if await check_membership(context.bot, user_id):
            await query.message.delete()
            await context.bot.send_message(chat_id=user_id, text=start_text(), reply_markup=main_menu(user_id), parse_mode="Markdown")
        else:
            await query.message.edit_text(
                "❌ عضویت تایید نشد\nلطفا ابتدا عضو کانال شوید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔗 عضویت در کانال اسپانسر", url=f"https://t.me/{SPONSOR_CHANNEL}")],
                    [InlineKeyboardButton("✅ بررسی عضویت", callback_data="check_join")]
                ])
            )

    elif query.data == "about":
        await query.message.edit_text(
            "🤖 **درباره ربات**\n\nاین ربات محتوای عمومی اینستاگرام را دانلود می‌کند.\nبه زودی پلتفرم‌های دیگر مثل یوتیوب، تیک تاک و ... اضافه خواهند شد.",
            reply_markup=about_menu(),
            parse_mode="Markdown"
        )

    elif query.data == "back":
        await query.message.edit_text(start_text(), reply_markup=main_menu(user_id), parse_mode="Markdown")

    elif query.data == "report" and user_id == ADMIN_ID:
        rows = get_reports()
        if not rows:
            await query.message.reply_text("هیچ دانلودی ثبت نشده.")
            return

        text = "📊 گزارش دانلودها:\n\n"
        for user_id_db, username, url, date, time in rows:
            text += f"👤 Username: {username}\n"
            text += f"🆔 User ID: {user_id_db}\n"
            text += f"🔗 {url}\n"
            text += f"📅 {date} | 🕒 {time}\n"
            text += "----------------------\n"

        await query.message.reply_text(text)

# ------------------ دانلود ------------------
async def download_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id in user_busy:
        await update.message.reply_text("⏳ صبر کنید تا دانلود قبلی شما تکمیل شود.")
        return

    if not await check_membership(context.bot, user_id):
        return

    url = update.message.text.strip()
    username = update.message.from_user.username or update.message.from_user.first_name

    if "instagram.com" not in url:
        return

    user_busy.add(user_id)
    msg = await update.message.reply_text("⏳ در حال دانلود...")

    try:
        if "/reel/" in url:
            shortcode = url.split("/reel/")[1].split("/")[0]
        elif "/p/" in url:
            shortcode = url.split("/p/")[1].split("/")[0]
        elif "/tv/" in url:
            shortcode = url.split("/tv/")[1].split("/")[0]
        else:
            shortcode = url.rstrip("/").split("/")[-1]

        post = instaloader.Post.from_shortcode(loader.context, shortcode)
        if not post.is_video:
            await msg.edit_text("❌ این پست ویدیو ندارد!")
            return

        r = requests.get(post.video_url, stream=True)
        video_data = BytesIO(r.content)

        save_download(user_id, username, url)

        caption = post.caption or ""
        views = getattr(post, "video_view_count", "نامشخص")

        if len(caption) > 1000:
            caption_text = None
        else:
            caption_text = f"👁 تعداد بازدید: {views}\n\n📜 کپشن:\n{caption}"

        await msg.edit_text("✅ دانلود شد! در حال ارسال...")
        await update.message.reply_video(
            video=InputFile(video_data, filename="video.mp4"),
            supports_streaming=True,
            caption=caption_text
        )
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"❌ خطا در دانلود!\n{str(e)}")
    finally:
        user_busy.discard(user_id)

# ------------------ اجرا ------------------
init_db()

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_instagram))

app.run_polling()
