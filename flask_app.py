from flask import Flask, request
import os
import logging
import traceback
import telegram
import yt_dlp

# راه‌اندازی اولیه
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# خواندن توکن از متغیرهای Railway
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

if TELEGRAM_BOT_TOKEN:
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    logging.info("Bot initialized successfully.")
else:
    bot = None
    logging.error("TELEGRAM_BOT_TOKEN not found!")


def download_twitter_video(tweet_url):
    # مسیر موقت برای ذخیره ویدیو
    output_template = '/tmp/%(id)s.%(ext)s'
    ydl_opts = {
        'format': 'b[ext=mp4]',
        'outtmpl': output_template,
        'quiet': True,
        'nocheckcertificate': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(tweet_url, download=True)
            return ydl.prepare_filename(info)
    except Exception as e:
        logging.error(f"yt-dlp Error: {traceback.format_exc()}")
        return None


@app.route('/webhook', methods=['POST'])
def webhook_handler():
    if not bot:
        return "ERROR: Bot not initialized", 500
    try:
        update = telegram.Update.de_json(request.get_json(force=True), bot)
        chat_id = update.message.chat_id
        message_text = update.message.text

        if not message_text or not ('twitter.com' in message_text or 'x.com' in message_text):
            return "OK"

        # به کاربر اطلاع می‌دهیم که کار شروع شد
        processing_message = bot.send_message(chat_id=chat_id, text="⏳ در حال پردازش لینک...")
        video_path = download_twitter_video(message_text)

        # پیام "در حال پردازش" را پاک می‌کنیم
        bot.delete_message(chat_id=chat_id, message_id=processing_message.message_id)

        if video_path:
            with open(video_path, 'rb') as video_file:
                bot.send_video(chat_id=chat_id, video=video_file, caption="✅ دانلود انجام شد.")
            os.remove(video_path) # فایل موقت را پاک می‌کنیم
        else:
            bot.send_message(chat_id=chat_id, text="❌ دانلود ویدیو ممکن نبود. لطفاً لینک را بررسی کنید.")

    except Exception as e:
        logging.error(f"Main Error: {traceback.format_exc()}")
    return "OK"


@app.route('/')
def index():
    return "Bot is running on Railway!"


if __name__ == "__main__":
    # این بخش توسط Railway استفاده می‌شود
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
