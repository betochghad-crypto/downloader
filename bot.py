import os
import sqlite3
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import instaloader

# ==============================
# تنظیمات اصلی
# ==============================

TOKEN = os.getenv("BOT_TOKEN")
SPONSOR_CHANNEL = "@YangMoein_Tv"

# متن استارت (همون متن خودت بدون تغییر)
START_TEXT = (
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

# ==============================
# دیتابیس SQLite
# ==============================

conn = sqlite3.connect("reports.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS downloads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    link TEXT,
    time TEXT
)
""")
conn.commit()

# ==============================
# بررسی عضویت
# ==============================

async def check_membership(user_id, context):
    try:
        member = await context.bot.get_chat_member(SPONSOR_CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def sponsor_buttons():
    keyboard = [
        [InlineKeyboardButton("📢 عضویت در کانال", url="https://t.me/YangMoein_Tv")],
        [InlineKeyboardButton("✅ بررسی عضویت", callback_data="check_join")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==============================
# استارت
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not await check_membership(user_id, context):
        await update.message.reply_text(
            "❌ برای استفاده از ربات ابتدا عضو کانال شوید:",
            reply_markup=sponsor_buttons()
        )
        return

    await update.message.reply_text(START_TEXT, parse_mode="Markdown")

# ==============================
# دکمه بررسی عضویت
# ==============================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if query.data == "check_join":
        if await check_membership(user_id, context):
            await query.message.delete()
            await context.bot.send_message(
                chat_id=user_id,
                text=START_TEXT,
                parse_mode="Markdown"
            )
        else:
            await query.message.edit_text(
                "❌ عضویت تایید نشد\n\nابتدا عضو کانال شوید:",
                reply_markup=sponsor_buttons()
            )

# ==============================
# دانلود اینستاگرام
# ==============================

async def download_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "ندارد"
    url = update.message.text.strip()

    if not await check_membership(user_id, context):
        await update.message.reply_text(
            "❌ ابتدا عضو کانال شوید:",
            reply_markup=sponsor_buttons()
        )
        return

    if "instagram.com" not in url:
        return

    try:
        await update.message.reply_text("⏳ در حال دانلود...")

        L = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            save_metadata=False,
            quiet=True
        )

        shortcode = url.split("/")[-2]
        post = instaloader.Post.from_shortcode(L.context, shortcode)

        video_url = post.video_url if post.is_video else None
        caption = post.caption if post.caption else ""

        # ذخیره گزارش در دیتابیس
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO downloads (user_id, username, link, time) VALUES (?, ?, ?, ?)",
            (user_id, username, url, now)
        )
        conn.commit()

        caption_text = f"📊 تعداد بازدید: {post.video_view_count or 0}\n\n"
        final_caption = caption_text + caption

        if len(final_caption) > 1000:
            final_caption = caption_text

        if video_url:
            await context.bot.send_video(
                chat_id=user_id,
                video=video_url,
                caption=final_caption
            )
        else:
            await context.bot.send_photo(
                chat_id=user_id,
                photo=post.url,
                caption=final_caption
            )

    except Exception as e:
        await update.message.reply_text(f"❌ خطا در دانلود!\n{e}")

# ==============================
# اجرای ربات
# ==============================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_instagram))

    print("Bot is running...")
    app.run_polling()
