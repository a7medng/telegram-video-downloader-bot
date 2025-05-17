import logging
import os
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# اكتب التوكن هنا
BOT_TOKEN = "7616062086:AAH45-yLIxW1Gx04VtMS-6YE9wWHWXsuC7M"

# إعداد اللوج
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# الحجم الأقصى للملف (تقريباً 49 ميجا)
MAX_FILE_SIZE = 49 * 1024 * 1024

# نخزن الروابط اللي الناس تبعتها عشان نعرف كل يوزر بعت إيه
user_links = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أهلاً بيك! ابعتلي لينك فيديو وأنا أجيبلك كل الخيارات.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if not url.startswith("http"):
        await update.message.reply_text("❌ من فضلك ابعت رابط فيديو صحيح.")
        return

    user_id = update.message.from_user.id
    user_links[user_id] = url

    keyboard = [
        [InlineKeyboardButton("🎥 تحميل الفيديو", callback_data='download_video')],
        [InlineKeyboardButton("🎵 تحميل الصوت فقط", callback_data='download_audio')],
        [InlineKeyboardButton("📺 اختيار جودة الفيديو", callback_data='choose_quality')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("✅ اختار اللي تحبه:", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    url = user_links.get(user_id)

    if not url:
        await query.edit_message_text("❗ مفيش رابط مرتبط بيك، ابعت رابط فيديو الأول.")
        return

    if query.data == 'download_video':
        await download_media(query, url, media_type='video')
    elif query.data == 'download_audio':
        await download_media(query, url, media_type='audio')
    elif query.data == 'choose_quality':
        await send_quality_options(query, url)

async def download_media(query, url, media_type='video', quality=None):
    await query.edit_message_text("⏳ جاري التحميل... استنى شوية.")

    try:
        ydl_opts = {
            'format': 'bestaudio/best' if media_type == 'audio' else 'best',
            'outtmpl': 'downloads/video.%(ext)s',
            'noplaylist': True,
            'quiet': True,
            'merge_output_format': 'mp4',
        }

        if quality:
            ydl_opts['format'] = quality

        os.makedirs("downloads", exist_ok=True)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        # لو تحميل صوت فقط
        if media_type == 'audio':
            filename = filename.rsplit('.', 1)[0] + '.mp3'

        file_size = os.path.getsize(filename)

        if file_size > MAX_FILE_SIZE:
            await query.edit_message_text("❗ الفيديو كبير ومش هينفع ابعته هنا.")
        else:
            with open(filename, 'rb') as f:
                if media_type == 'audio':
                    await query.message.reply_audio(f)
                else:
                    await query.message.reply_video(f)

        os.remove(filename)

    except Exception as e:
        logging.error(f"خطأ: {e}")
        await query.edit_message_text("❌ حصل خطأ أثناء التحميل.")

async def send_quality_options(query, url):
    try:
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = info.get('formats', [])

        keyboard = []
        for fmt in formats:
            if fmt.get('vcodec') != 'none' and fmt.get('acodec') != 'none':
                quality = fmt.get('format_id')
                res = fmt.get('format_note') or fmt.get('height')
                if res:
                    button_text = f"{res} ({quality})"
                    keyboard.append([InlineKeyboardButton(button_text, callback_data=f'quality_{quality}')])

        if not keyboard:
            await query.edit_message_text("❌ مفيش جودات متاحة للاختيار.")
            return

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📺 اختار الجودة اللي تريحك:", reply_markup=reply_markup)

    except Exception as e:
        logging.error(f"خطأ أثناء جلب الجودات: {e}")
        await query.edit_message_text("❌ حصل خطأ أثناء جلب الجودات.")

async def quality_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    url = user_links.get(user_id)

    if not url:
        await query.edit_message_text("❗ مفيش رابط مرتبط بيك.")
        return

    quality = query.data.split("_", 1)[1]
    await download_media(query, url, media_type='video', quality=quality)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(quality_choice, pattern=r'^quality_'))
    app.add_handler(CallbackQueryHandler(button))

    app.run_polling()

if __name__ == '__main__':
    main()
