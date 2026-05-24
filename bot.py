import os
import logging
import asyncio
import subprocess
import tempfile
import shutil
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
MINI_APP_URL = "https://patcher.joym73021.workers.dev/"
MAX_FILE_SIZE_MB = 50  # Telegram Bot API limit for downloads

SUPPORTED_FORMATS = [
    "mp4", "avi", "mov", "mkv", "flv", "webm",
    "m4v", "3gp", "ogv", "ts", "mts", "m2ts",
    "wmv", "asf", "rm", "rmvb", "vob", "mpeg", "mpg"
]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command with Mini App button."""
    keyboard = [
        [
            InlineKeyboardButton(
                "🔧 Open Tools",
                web_app=WebAppInfo(url=MINI_APP_URL),
            )
        ],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🎬 *WMV Converter Bot*\n\n"
        "Send me any video file and I'll convert it to *real WMV* format using FFmpeg with Windows Media Video codec.\n\n"
        f"✅ Supported formats: {', '.join(SUPPORTED_FORMATS[:8])}... and more\n"
        "📦 Max file size: 50MB\n\n"
        "Just send a video file to get started!",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *How to use:*\n\n"
        "1. Send any video file (mp4, avi, mov, mkv, etc.)\n"
        "2. The bot will convert it to genuine WMV (Windows Media Video)\n"
        "3. Download your WMV file\n\n"
        "🔧 *Technical details:*\n"
        "• Codec: Windows Media Video 2 (wmv2)\n"
        "• Audio: Windows Media Audio v2 (wmav2)\n"
        "• Container: ASF (Advanced Systems Format)\n"
        "• This is REAL WMV, not a renamed file!\n\n"
        "📏 *Limits:*\n"
        "• Max file size: 50MB",
        parse_mode="Markdown",
    )


def check_ffmpeg():
    """Check if FFmpeg is installed."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


async def convert_to_wmv(input_path: str, output_path: str) -> tuple[bool, str]:
    """
    Convert video to REAL WMV using FFmpeg with WMV2 codec.
    Returns (success, message).
    """
    cmd = [
        "ffmpeg",
        "-i", input_path,
        "-c:v", "wmv2",           # Windows Media Video 2 codec (real WMV)
        "-c:a", "wmav2",          # Windows Media Audio v2
        "-b:v", "1500k",          # Video bitrate
        "-b:a", "128k",           # Audio bitrate
        "-ar", "44100",           # Audio sample rate
        "-ac", "2",               # Stereo audio
        "-f", "asf",              # ASF container (WMV container format)
        "-y",                     # Overwrite output
        output_path,
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=300
        )

        if process.returncode == 0:
            return True, "Conversion successful"
        else:
            error_msg = stderr.decode("utf-8", errors="replace")[-500:]
            return False, f"FFmpeg error: {error_msg}"

    except asyncio.TimeoutError:
        return False, "Conversion timed out (>5 minutes)"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming video/document files."""
    message = update.message

    # Determine if it's a video or document
    file_obj = None
    original_name = "video"

    if message.video:
        file_obj = message.video
        original_name = f"video_{message.video.file_unique_id}"
    elif message.document:
        doc = message.document
        if doc.mime_type and doc.mime_type.startswith("video/"):
            file_obj = doc
            original_name = doc.file_name or "video"
        else:
            # Check extension
            if doc.file_name:
                ext = Path(doc.file_name).suffix.lower().lstrip(".")
                if ext in SUPPORTED_FORMATS:
                    file_obj = doc
                    original_name = doc.file_name
            if not file_obj:
                await message.reply_text(
                    "⚠️ Please send a video file.\n"
                    f"Supported: {', '.join(SUPPORTED_FORMATS)}"
                )
                return
    else:
        await message.reply_text(
            "⚠️ Please send a video file.\n"
            f"Supported formats: {', '.join(SUPPORTED_FORMATS)}"
        )
        return

    # Check file size
    file_size_mb = (file_obj.file_size or 0) / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        await message.reply_text(
            f"❌ File too large ({file_size_mb:.1f}MB).\n"
            f"Maximum allowed: {MAX_FILE_SIZE_MB}MB"
        )
        return

    if not check_ffmpeg():
        await message.reply_text(
            "❌ FFmpeg is not installed on this server.\n"
            "Please install FFmpeg to use this bot."
        )
        return

    status_msg = await message.reply_text("⬇️ Downloading your video...")

    tmp_dir = tempfile.mkdtemp(prefix="wmvbot_")
    try:
        # Determine input extension
        input_ext = "mp4"
        if hasattr(file_obj, "file_name") and file_obj.file_name:
            input_ext = Path(file_obj.file_name).suffix.lstrip(".") or "mp4"
        elif message.video:
            input_ext = "mp4"

        input_path = os.path.join(tmp_dir, f"input.{input_ext}")
        output_name = Path(original_name).stem + ".wmv"
        output_path = os.path.join(tmp_dir, output_name)

        # Download
        tg_file = await context.bot.get_file(file_obj.file_id)
        await tg_file.download_to_drive(input_path)

        await status_msg.edit_text("🔄 Converting to WMV (wmv2 codec)...")

        success, result_msg = await convert_to_wmv(input_path, output_path)

        if not success:
            await status_msg.edit_text(
                f"❌ Conversion failed.\n\n`{result_msg}`",
                parse_mode="Markdown",
            )
            return

        output_size_mb = os.path.getsize(output_path) / (1024 * 1024)

        if output_size_mb > 50:
            await status_msg.edit_text(
                f"❌ Output file too large ({output_size_mb:.1f}MB) to send via Telegram (50MB limit)."
            )
            return

        await status_msg.edit_text("⬆️ Uploading WMV file...")

        with open(output_path, "rb") as f:
            await message.reply_document(
                document=f,
                filename=output_name,
                caption=(
                    f"✅ *Converted to WMV*\n\n"
                    f"🎬 Codec: WMV2 (Windows Media Video 2)\n"
                    f"🔊 Audio: WMAV2\n"
                    f"📦 Container: ASF\n"
                    f"📏 Size: {output_size_mb:.2f}MB"
                ),
                parse_mode="Markdown",
            )

        await status_msg.delete()

    except Exception as e:
        logger.exception("Error processing video")
        await status_msg.edit_text(f"❌ An error occurred: {str(e)}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, handle_video))

    logger.info("Bot starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
