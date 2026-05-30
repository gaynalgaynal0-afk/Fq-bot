import os
import logging
import asyncio
import subprocess
import tempfile
import shutil
import threading
from pathlib import Path
from flask import Flask

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Credentials ────────────────────────────────────────────────────────────────
BOT_TOKEN  = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
API_ID     = int(os.environ.get("API_ID", "0"))
API_HASH   = os.environ.get("API_HASH", "YOUR_API_HASH_HERE")
MINI_APP_URL = "https://restless-star-a7e9.gaynalgaynal4.workers.dev/"
PORT = int(os.environ.get("PORT", 5000))

SUPPORTED_FORMATS = [
    "mp4","avi","mov","mkv","flv","webm","m4v","3gp","ogv",
    "ts","mts","m2ts","wmv","asf","rm","rmvb","vob","mpeg","mpg"
]

MAX_FILE_SIZE_MB = 2000  # 2GB via MTProto

START_MSG = (
    "🎬 **TIKTOK Studio method**\n\n"
    ">If you want to use the TIKTOK studio method send a video file directly in chat\n"
    "**>✅ Supported: mp4, avi, mov, mkv, flv, webm, m4v, 3gp...**\n"
    "*📦 Max size: 2GB (upgraded via MTProto)*"
)
CAPTION_MSG = ">__*Upload this video using JV 60FPS studio extension*__"

# ── Flask keep-alive ───────────────────────────────────────────────────────────
flask_app = Flask(__name__)

@flask_app.route("/")
def index():
    return "Bot is running!", 200

@flask_app.route("/health")
def health():
    return {"status": "ok"}, 200

def run_flask():
    flask_app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)

# ── FFmpeg helpers ─────────────────────────────────────────────────────────────
def check_ffmpeg():
    try:
        r = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False

async def convert_to_wmv(input_path: str, output_path: str):
    cmd = [
        "ffmpeg", "-i", input_path,
        "-c:v", "wmv2",
        "-q:v", "2",        # near-lossless (1=best, 31=worst)
        "-b:v", "0",        # quality-driven, no bitrate cap
        "-c:a", "wmav2",
        "-qscale:a", "0",   # best audio quality
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
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=3600)
        if proc.returncode == 0:
            return True, "OK"
        return False, stderr.decode(errors="replace")[-500:]
    except asyncio.TimeoutError:
        return False, "Timeout (file too large or server too slow)"
    except Exception as e:
        return False, str(e)

# ── Pyrogram bot ───────────────────────────────────────────────────────────────
app = Client(
    "wmv_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

@app.on_message(filters.command("start"))
async def start(client: Client, message: Message):
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔧 Open Tools", web_app=WebAppInfo(url=MINI_APP_URL))
    ]])
    await message.reply_text(START_MSG, reply_markup=keyboard)

@app.on_message(filters.command("help"))
async def help_command(client: Client, message: Message):
    await message.reply_text(
        "Send any video file (up to **2GB**) to convert it to WMV\n"
        "Codec: wmv2 | Audio: wmav2 | Container: ASF\n"
        "Quality: near-lossless (-q:v 2, no bitrate cap)"
    )

@app.on_message(filters.video | filters.document)
async def handle_video(client: Client, message: Message):
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
        await message.reply_text(
            "Please send a video file.\nSupported: " + ", ".join(SUPPORTED_FORMATS)
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

        # ✅ FIXED: pass the message object (not file_id) to download_media
        await client.download_media(message, file_name=input_path)

        await status.edit_text("🔄 Converting to WMV (lossless quality)...")

        ok, err_msg = await convert_to_wmv(input_path, output_path)
        if not ok:
            logger.error(f"FFmpeg error: {err_msg}")
            await status.edit_text(f"❌ Conversion failed:\n`{err_msg}`")
            return

        out_mb = os.path.getsize(output_path) / 1024 / 1024
        await status.edit_text(f"⬆️ Uploading ({out_mb:.1f}MB)...")

        # ✅ FIXED: use message.reply_document (simpler, correct reply threading)
        await message.reply_document(
            document=output_path,
            file_name=output_name,
            caption=CAPTION_MSG,
        )
        await status.delete()

    except Exception as e:
        logger.exception("Error handling video")
        await status.edit_text(f"❌ Error: {e}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        raise ValueError("BOT_TOKEN environment variable is not set!")
    if API_ID == 0 or API_HASH == "YOUR_API_HASH_HERE":
        raise ValueError(
            "API_ID and API_HASH are required for Pyrogram.\n"
            "Get them at https://my.telegram.org"
        )

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info(f"Flask server started on port {PORT}")

    logger.info("Bot started with Pyrogram (MTProto) — 2GB file support active!")
    app.run()

if __name__ == "__main__":
    main()
