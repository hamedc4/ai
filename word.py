# merged_bot_v3.py

import os
import asyncio
import logging
import instaloader
import yt_dlp
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
    BotCommand
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    CallbackQueryHandler
)

# تنظیمات پایه لاگ‌گیری
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# توکن ربات
TOKEN = "7575761667:AAHWIa4GVT9ChFKpU9M1yV2KDmWJbeRwBAo"
# پوشه دانلود مشترک
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# تعریف وضعیت‌ها برای مدیریت گفتگو
CHOOSING, AWAIT_INSTAGRAM_LINK, AWAIT_SOUNDCLOUD_LINK = range(3)


async def post_init(application: Application) -> None:
    """این تابع پس از راه اندازی ربات، منوی دستورات را تنظیم می‌کند."""
    commands = [
        BotCommand("start", "▶️ انتخاب سرویس و شروع مجدد"),
        BotCommand("help", "❓ راهنما و اطلاعات")
    ]
    await application.bot.set_my_commands(commands)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """منوی شروع با دکمه‌های شیشه‌ای"""
    user = update.effective_user
    welcome_msg = (
        f"✨ سلام {user.mention_html()}!\n\n"
        "سرویس مورد نظر خود را برای دانلود انتخاب کنید.\n\n"
        "پس از انتخاب، می‌توانید به صورت متوالی از آن سرویس دانلود کنید. برای تغییر سرویس، این دستور را مجدداً اجرا کنید."
    )
    
    keyboard = [
        [InlineKeyboardButton("📷 دانلود از اینستاگرام", callback_data='select_instagram')],
        [InlineKeyboardButton("🎵 دانلود از ساندکلود", callback_data='select_soundcloud')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # پاک کردن وضعیت قبلی کاربر برای شروع تازه
    context.user_data.clear()
    
    await update.message.reply_html(
        text=welcome_msg,
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )
    context.user_data['state'] = CHOOSING

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش جعبه دکمه‌ای راهنما"""
    help_text = "❔ راهنمای کدام بخش را نیاز دارید؟"
    keyboard = [
        [InlineKeyboardButton("راهنمای اینستاگرام", callback_data='help_instagram')],
        [InlineKeyboardButton("راهنمای ساندکلود", callback_data='help_soundcloud')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(help_text, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """مدیریت کلیک روی دکمه‌های شیشه‌ای"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == 'select_instagram':
        context.user_data['state'] = AWAIT_INSTAGRAM_LINK
        await query.edit_message_text(text="✅ حالت دانلود از اینستاگرام فعال شد.\nاکنون می‌توانید لینک‌های خود را به صورت متوالی ارسال کنید.")
    elif data == 'select_soundcloud':
        context.user_data['state'] = AWAIT_SOUNDCLOUD_LINK
        await query.edit_message_text(text="✅ حالت دانلود از ساندکلود فعال شد.\nاکنون می‌توانید لینک‌های خود را به صورت متوالی ارسال کنید.")
    elif data == 'help_instagram':
        help_text_insta = (
            "📚 **راهنمای دانلود از اینستاگرام**:\n\n"
            "1. با دستور /start، دکمه «📷 دانلود از اینستاگرام» را انتخاب کنید.\n"
            "2. لینک پست، استوری یا ریلز را ارسال کنید.\n"
            "3. پس از دانلود، می‌توانید لینک بعدی را بلافاصله ارسال کنید.\n\n"
            "⚠️ *فقط پست‌های عمومی (Public) قابل دانلود هستند.*"
        )
        await query.edit_message_text(text=help_text_insta, parse_mode='Markdown')
    elif data == 'help_soundcloud':
        help_text_sc = (
            "📚 **راهنمای دانلود از ساندکلود**:\n\n"
            "1. با دستور /start، دکمه «🎵 دانلود از ساندکلود» را انتخاب کنید.\n"
            "2. لینک موزیک مورد نظر را ارسال کنید.\n"
            "3. پس از دانلود، می‌توانید لینک بعدی را بلافاصله ارسال کنید."
        )
        await query.edit_message_text(text=help_text_sc, parse_mode='Markdown')


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """مدیریت پیام‌های متنی کاربر بر اساس وضعیت"""
    user_state = context.user_data.get('state')
    text = update.message.text.strip()
    
    if user_state == AWAIT_INSTAGRAM_LINK:
        if "instagram.com" in text:
            await download_instagram_content(update, context)
        else:
            await update.message.reply_text("لینک نامعتبر است. لطفاً یک لینک اینستاگرام ارسال کنید.\nبرای تغییر سرویس از /start استفاده کنید.")
    elif user_state == AWAIT_SOUNDCLOUD_LINK:
        if "soundcloud.com" in text:
            await download_soundcloud_link(update, context)
        else:
            await update.message.reply_text("لینک نامعتبر است. لطفاً یک لینک ساندکلود ارسال کنید.\nبرای تغییر سرویس از /start استفاده کنید.")
    else:
        await update.message.reply_text("لطفاً ابتدا با دستور /start سرویس مورد نظر خود را انتخاب کنید.")


async def download_instagram_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دانلود محتوای اینستاگرام"""
    url = update.message.text.strip()
    status_msg = await update.message.reply_text("🔍 در حال پردازش لینک اینستاگرام...")
    
    try:
        shortcode = url.split("/")[-2]
        temp_dir = os.path.join(DOWNLOAD_FOLDER, f"insta_{update.effective_chat.id}_{shortcode}")
        
        L = instaloader.Instaloader(dirname_pattern=temp_dir, save_metadata=False, quiet=True, download_video_thumbnails=False)
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        L.download_post(post, target=f"ig_{shortcode}")
        
        await status_msg.edit_text("📤 در حال آپلود محتوا...")
        
        downloaded_files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) if f.endswith((".mp4", ".jpg", ".jpeg"))]
        
        if not downloaded_files:
            raise Exception("هیچ محتوایی برای دانلود یافت نشد.")

        for file_path in downloaded_files:
            if os.path.getsize(file_path) > 49 * 1024 * 1024:
                await update.message.reply_text(f"⚠️ فایل به دلیل حجم بالا (بیش از 50 مگابایت) قابل ارسال نیست.")
                continue

            with open(file_path, 'rb') as f:
                caption = "✅ @YourBotName"
                if file_path.endswith(".mp4"):
                    await update.message.reply_video(video=f, caption=caption, supports_streaming=True)
                elif file_path.endswith((".jpg", ".jpeg")):
                    await update.message.reply_photo(photo=f, caption=caption)
            os.remove(file_path)
        
        os.rmdir(temp_dir)
        await status_msg.edit_text("✅ دانلود کامل شد. می‌توانید لینک بعدی را ارسال کنید.")
    except Exception as e:
        logger.error(f"خطا در دانلود از اینستاگرام: {str(e)}")
        await status_msg.edit_text(f"❌ خطا در دانلود.\nممکن است پست خصوصی باشد یا لینک نامعتبر باشد.")
    # finally:
    #     context.user_data.clear()  <-- این خط حذف شد تا حالت دانلود باقی بماند


async def download_soundcloud_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دانلود موزیک از ساندکلود"""
    url = update.message.text.strip()
    status_msg = await update.message.reply_text("🔍 در حال پردازش لینک ساندکلود...")

    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
            'quiet': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            title = info_dict.get('title', 'Untitled Track')
            artist = info_dict.get('uploader', 'Unknown Artist')
            
            await status_msg.edit_text(f"📥 در حال دانلود: {title}")
            ydl.download([url])

            base_filename, _ = os.path.splitext(ydl.prepare_filename(info_dict))
            file_path = base_filename + '.mp3'
            
            if os.path.exists(file_path):
                await status_msg.edit_text(f"📤 در حال ارسال موزیک: {title}")
                with open(file_path, 'rb') as audio_file:
                    await context.bot.send_audio(chat_id=update.effective_chat.id, audio=audio_file, title=title, performer=artist, duration=info_dict.get('duration', 0))
                os.remove(file_path)
                await status_msg.edit_text("✅ دانلود کامل شد. می‌توانید لینک بعدی را ارسال کنید.")
            else:
                raise Exception("فایل دانلود شده پیدا نشد.")
    except Exception as e:
        logger.error(f"خطای yt-dlp یا ساندکلود: {e}")
        await status_msg.edit_text("❌ موفق به دانلود این لینک نشدم. ممکن است موزیک خصوصی باشد یا لینک نامعتبر باشد.")
    # finally:
    #     context.user_data.clear()  <-- این خط حذف شد تا حالت دانلود باقی بماند


def main() -> None:
    """تنظیم و راه‌اندازی ربات"""
    application = (
        Application.builder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🤖 ربات با قابلیت دانلود متوالی در حال اجرا است...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()