import os
import logging
import asyncio
import subprocess
import tempfile
import shutil
import threading
from pathlib import Path
from flask import Flask

# Use ffmpeg installed via imageio/pip — no apt-get needed
import imageio_ffmpeg
FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN    = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
MINI_APP_URL = "https://restless-star-a7e9.gaynalgaynal4.workers.dev/"
PORT         = int(os.environ.get("PORT", 5000))

SUPPORTED_FORMATS = [
    "mp4","avi","mov","mkv","flv","webm","m4v","3gp","ogv",
    "ts","mts","m2ts","wmv","asf","rm","rmvb","vob","mpeg","mpg"
]

MAX_FILE_SIZE_MB = 50

START_MSG = (
    "\U0001f3ac __*TIKTOK Studio method*__\n\n"
    ">If you want to use the TIKTOK studio method sent a video file directly in chat\n"
    "**>\\u2705 Supported: mp4, avi, mov, mkv, flv, webm, m4v, 3gp\\.\\.\\.**\n"
    "*\U0001f4e6 Max size: 50MB*"
)
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

async def convert_to_wmv(input_path, output_path):
    cmd = [
        FFMPEG_PATH, "-i", input_path,
        "-c:v", "wmv2",
        "-q:v", "2",
        "-b:v", "0",
        "-c:a", "wmav2",
        "-qscale:a", "0",
        "-ar", "48000",
        "-ac", "2",
        "-f", "asf",
        "-y", output_path
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
        if proc.returncode == 0:
            return True, "OK"
        return False, stderr.decode(errors="replace")[-300:]
    except asyncio.TimeoutError:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("\U0001f527 Open Tools", web_app=WebAppInfo(url=MINI_APP_URL))]]
    await update.message.reply_text(
        START_MSG, parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send any video file to convert it to WMV\nCodec: wmv2 | Audio: wmav2 | Container: ASF"
    )

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    file_obj = None
    original_name = "video"

    if message.video:
        file_obj = message.video
        original_name = f"video_{message.video.file_unique_id}.mp4"
    elif message.document:
        doc = message.document
        fname = doc.file_name or ""
        ext = Path(fname).suffix.lower().lstrip(".")
        mime = doc.mime_type or ""
        if mime.startswith("video/") or ext in SUPPORTED_FORMATS:
            file_obj = doc
            original_name = fname or "video"

    if not file_obj:
        await message.reply_text("Please send a video file.\nSupported: " + ", ".join(SUPPORTED_FORMATS))
        return

    size_mb = (file_obj.file_size or 0) / 1024 / 1024
    if size_mb > MAX_FILE_SIZE_MB:
        await message.reply_text(f"❌ File too large ({size_mb:.1f}MB). Max: {MAX_FILE_SIZE_MB}MB")
        return

    status = await message.reply_text("⬇️ Downloading...")
    tmp_dir = tempfile.mkdtemp(prefix="wmv_")

    try:
        ext = Path(original_name).suffix.lstrip(".") or "mp4"
        input_path  = os.path.join(tmp_dir, f"input.{ext}")
        output_name = Path(original_name).stem + ".wmv"
        output_path = os.path.join(tmp_dir, output_name)

        tg_file = await context.bot.get_file(file_obj.file_id)
        await tg_file.download_to_drive(input_path)

        await status.edit_text("🔄 Converting to WMV (near-lossless)...")

        ok, err = await convert_to_wmv(input_path, output_path)
        if not ok:
            logger.error(f"FFmpeg: {err}")
            await status.edit_text(f"❌ Conversion failed:\n{err[:200]}")
            return

        out_mb = os.path.getsize(output_path) / 1024 / 1024
        if out_mb > 50:
            await status.edit_text(f"❌ Output too large ({out_mb:.1f}MB) to send.")
            return

        await status.edit_text(f"⬆️ Uploading ({out_mb:.1f}MB)...")

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
        await status.edit_text(f"❌ Error: {e}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

def main():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        raise ValueError("BOT_TOKEN not set!")

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info(f"Flask running on port {PORT}")
    logger.info(f"FFmpeg path: {FFMPEG_PATH}")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, handle_video))

    logger.info("Bot started!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
