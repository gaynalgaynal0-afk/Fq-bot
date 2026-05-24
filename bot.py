import os
import logging
import asyncio
import subprocess
import tempfile
import shutil
from pathlib import Path

# Fix for Python 3.14 compatibility
import sys
if sys.version_info >= (3, 12):
    import asyncio
    if not hasattr(asyncio, 'get_event_loop'):
        asyncio.get_event_loop = asyncio.get_running_loop

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
MINI_APP_URL = "https://patcher.joym73021.workers.dev/"

SUPPORTED_FORMATS = [
    "mp4","avi","mov","mkv","flv","webm","m4v","3gp",
    "ogv","ts","mts","m2ts","wmv","asf","rm","rmvb",
    "vob","mpeg","mpg"
]

MAX_FILE_SIZE_MB = 50


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton("🔧 Open Tools", web_app=WebAppInfo(url=MINI_APP_URL))
    ]]
    await update.message.reply_text(
        "🎬 *WMV Converter Bot*\n\n"
        "Send me any video and I'll convert it to *real WMV* (wmv2 codec).\n\n"
        f"✅ Supported: {', '.join(SUPPORTED_FORMATS[:8])}...\n"
        "📦 Max size: 50MB",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 Send any video file to convert it to WMV.\n\n"
        "Codec: wmv2 | Audio: wmav2 | Container: ASF\n"
        "This is REAL WMV, not a renamed file!"
    )


def check_ffmpeg():
    try:
        r = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False


async def convert_to_wmv(input_path, output_path):
    cmd = [
        "ffmpeg", "-i", input_path,
        "-c:v", "wmv2",
        "-c:a", "wmav2",
        "-b:v", "1500k",
        "-b:a", "128k",
        "-ar", "44100",
        "-ac", "2",
        "-f", "asf",
        "-y", output_path,
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
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
        original_name = "video"
    elif message.document:
        doc = message.document
        fname = doc.file_name or ""
        ext = Path(fname).suffix.lower().lstrip(".")
        if (doc.mime_type and doc.mime_type.startswith("video/")) or ext in SUPPORTED_FORMATS:
            file_obj = doc
            original_name = fname or "video"

    if not file_obj:
        await message.reply_text(
            f"⚠️ Please send a video file.\nSupported: {', '.join(SUPPORTED_FORMATS)}"
        )
        return

    size_mb = (file_obj.file_size or 0) / 1024 / 1024
    if size_mb > MAX_FILE_SIZE_MB:
        await message.reply_text(f"❌ File too large ({size_mb:.1f}MB). Max: {MAX_FILE_SIZE_MB}MB")
        return

    if not check_ffmpeg():
        await message.reply_text("❌ FFmpeg not found on this server.")
        return

    status = await message.reply_text("⬇️ Downloading...")
    tmp_dir = tempfile.mkdtemp(prefix="wmv_")

    try:
        ext = Path(original_name).suffix.lstrip(".") or "mp4"
        input_path = os.path.join(tmp_dir, f"input.{ext}")
        output_name = Path(original_name).stem + ".wmv"
        output_path = os.path.join(tmp_dir, output_name)

        tg_file = await context.bot.get_file(file_obj.file_id)
        await tg_file.download_to_drive(input_path)
        await status.edit_text("🔄 Converting to WMV...")

        ok, msg = await convert_to_wmv(input_path, output_path)
        if not ok:
            await status.edit_text(f"❌ Conversion failed:\n`{msg}`", parse_mode="Markdown")
            return

        out_mb = os.path.getsize(output_path) / 1024 / 1024
        if out_mb > 50:
            await status.edit_text(f"❌ Output too large ({out_mb:.1f}MB) to send.")
            return

        await status.edit_text("⬆️ Uploading...")
        with open(output_path, "rb") as f:
            await message.reply_document(
                document=f,
                filename=output_name,
                caption=f"✅ Converted to WMV\n🎬 wmv2 | 🔊 wmav2 | 📦 ASF\n📏 {out_mb:.2f}MB",
            )
        await status.delete()

    except Exception as e:
        logger.exception("Error")
        await status.edit_text(f"❌ Error: {e}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def main():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        raise ValueError("BOT_TOKEN environment variable is not set!")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .concurrent_updates(False)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, handle_video))

    logger.info("Bot started!")
    app.run_polling(drop_pending_updates=True, close_loop=False)


if __name__ == "__main__":
    main()
