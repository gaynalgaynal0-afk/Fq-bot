import os
import logging
import asyncio
import subprocess
import tempfile
import shutil
import threading
from pathlib import Path
from flask import Flask

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
MINI_APP_URL = "https://patcher.joym73021.workers.dev/"
PORT = int(os.environ.get("PORT", 5000))

SUPPORTED_FORMATS = ["mp4","avi","mov","mkv","flv","webm","m4v","3gp","ogv","ts","mts","m2ts","wmv","asf","rm","rmvb","vob","mpeg","mpg"]
MAX_FILE_SIZE_MB = 50

START_MSG = ("\U0001f3ac __*TIKTOK Studio method*__\n\n"
    ">If you want to use the TIKTOK studio method sent a video file directly in chat\n"
    "**>\u2705 Supported: mp4, avi, mov, mkv, flv, webm, m4v, 3gp\\.\\.\\.\n"
    "*\U0001f4e6 Max size: 50MB*")
CAPTION_MSG = ">__*Upload this video using JV 60FPS studio extension*__"

flask_app = Flask(__name__)

@flask_app.route("/")
def index():
    return "Bot is running!", 200

@flask_app.route("/health")
def health():
    return {"status": "ok"}, 200

def run_flask():
    flask_app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("\U0001f527 Open Tools", web_app=WebAppInfo(url=MINI_APP_URL))]]
    await update.message.reply_text(START_MSG, parse_mode="MarkdownV2", reply_markup=InlineKeyboardMarkup(keyboard))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send any video file to convert it to WMV\nCodec: wmv2 | Audio: wmav2 | Container: ASF")

def check_ffmpeg():
    try:
        r = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False

def get_video_duration(input_path):
    """Get video duration in seconds using ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", input_path],
            capture_output=True, text=True, timeout=30
        )
        return float(result.stdout.strip())
    except Exception:
        return None


async def convert_to_wmv(input_path, output_path):
    # Get duration to calculate best bitrate that fits in 50MB
    duration = get_video_duration(input_path)

    if duration and duration > 0:
        # Target 48MB (leave 2MB buffer for audio/container)
        target_size_bits = 48 * 1024 * 1024 * 8
        audio_bitrate = 128 * 1000  # 128kbps audio
        video_bitrate = int((target_size_bits / duration - audio_bitrate) / 1000)
        video_bitrate = max(300, min(video_bitrate, 8000))  # clamp 300k-8000k
        v_bitrate = f"{video_bitrate}k"
    else:
        v_bitrate = "2000k"  # fallback

    cmd = [
        "ffmpeg", "-i", input_path,
        "-c:v", "wmv2",
        "-b:v", v_bitrate,
        "-c:a", "wmav2",
        "-b:a", "128k",
        "-ar", "44100",
        "-ac", "2",
        "-f", "asf",
        "-y", output_path,
    ]
    try:
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
        if proc.returncode == 0:
            return True, "OK"
        return False, stderr.decode(errors="replace")[-300:]
    except asyncio.TimeoutError:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    file_obj = None
    original_name = "video"

    if message.video:
        file_obj = message.video
    elif message.document:
        doc = message.document
        fname = doc.file_name or ""
        ext = Path(fname).suffix.lower().lstrip(".")
        if (doc.mime_type and doc.mime_type.startswith("video/")) or ext in SUPPORTED_FORMATS:
            file_obj = doc
            original_name = fname or "video"

    if not file_obj:
        await message.reply_text("Please send a video file.\nSupported: " + ", ".join(SUPPORTED_FORMATS))
        return

    size_mb = (file_obj.file_size or 0) / 1024 / 1024
    if size_mb > MAX_FILE_SIZE_MB:
        await message.reply_text(f"File too large ({size_mb:.1f}MB). Max: {MAX_FILE_SIZE_MB}MB")
        return

    if not check_ffmpeg():
        await message.reply_text("FFmpeg not found on this server.")
        return

    status = await message.reply_text("Downloading...")
    tmp_dir = tempfile.mkdtemp(prefix="wmv_")

    try:
        ext = Path(original_name).suffix.lstrip(".") or "mp4"
        input_path = os.path.join(tmp_dir, f"input.{ext}")
        output_name = Path(original_name).stem + ".wmv"
        output_path = os.path.join(tmp_dir, output_name)

        tg_file = await context.bot.get_file(file_obj.file_id)
        await tg_file.download_to_drive(input_path)
        await status.edit_text("Converting to WMV...")

        ok, msg = await convert_to_wmv(input_path, output_path)
        if not ok:
            await status.edit_text(f"Conversion failed.")
            return

        out_mb = os.path.getsize(output_path) / 1024 / 1024
        if out_mb > 50:
            await status.edit_text(f"Output too large ({out_mb:.1f}MB) to send.")
            return

        await status.edit_text("Uploading...")
        with open(output_path, "rb") as f:
            await message.reply_document(
                document=f,
                filename=output_name,
                caption=CAPTION_MSG,
                parse_mode="MarkdownV2",
            )
        await status.delete()

    except Exception as e:
        logger.exception("Error")
        await status.edit_text(f"Error: {e}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

def main():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        raise ValueError("BOT_TOKEN environment variable is not set!")

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info(f"Flask server started on port {PORT}")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, handle_video))

    logger.info("Bot started!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
