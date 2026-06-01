import os, logging, asyncio, subprocess, tempfile, shutil, threading
from pathlib import Path
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, BotCommand, ReplyKeyboardMarkup, KeyboardButton

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_ID    = int(os.environ.get("API_ID", "0"))
API_HASH  = os.environ.get("API_HASH")
MINI_APP_URL = "https://restless-star-a7e9.gaynalgaynal4.workers.dev/"
PORT = int(os.environ.get("PORT", 5000))
SUPPORTED_FORMATS = ["mp4","avi","mov","mkv","flv","webm","m4v","3gp","ogv","ts","mts","m2ts","wmv","asf","rm","rmvb","vob","mpeg","mpg"]
CAPTION_MSG = ">__*Upload this video using JV 60FPS studio extension*__"

flask_app = Flask(__name__)

@flask_app.route("/")
def index(): return "Bot running!", 200

def run_flask():
    flask_app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)

async def convert_to_wmv(input_path, output_path):
    cmd = ["ffmpeg","-i",input_path,"-c:v","wmv2","-q:v","1","-b:v","0","-c:a","wmav2","-b:a","320k","-ar","48000","-ac","2","-f","asf","-y",output_path]
    try:
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=3600)
        return (True,"OK") if proc.returncode==0 else (False, stderr.decode(errors="replace")[-300:])
    except Exception as e:
        return False, str(e)

# ── Main menu keyboard ─────────────────────────────────────────────────────────
MAIN_MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🚀 Start the bot")],
        [KeyboardButton("🎬 Convert video")],
        [KeyboardButton("🔧 time scale patcher", web_app=WebAppInfo(url=MINI_APP_URL))],
    ],
    resize_keyboard=True
)

app = Client("wmv_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("start"))
async def start(client, message):
    await client.set_bot_commands([
        BotCommand("start", "Start the bot"),
        BotCommand("convert", "Convert a video to studio60fps"),
    ])
    await message.reply_text(
        "🎬 **TIKTOK Studio method**\n\n"
        ">Send a video file to convert it to studio60fps\n"
        ">Tap **🎬 Convert video** or just send your file directly!\n\n"
        "*📦 Max size: 2GB*",
        reply_markup=MAIN_MENU
    )

@app.on_message(filters.command("convert") | filters.regex("^🎬 Convert video$"))
async def convert_prompt(client, message):
    await message.reply_text(
        "📤 Send me your video file now!\n"
        "Supported: " + ", ".join(SUPPORTED_FORMATS),
        reply_markup=MAIN_MENU
    )

@app.on_message(filters.regex("^🚀 Start the bot$"))
async def start_btn(client, message):
    await message.reply_text(
        "✅ Bot is running!\n\nSend me any video file to convert it to studio60fps.",
        reply_markup=MAIN_MENU
    )

@app.on_message(filters.video | filters.document)
async def handle_video(client, message):
    file_obj = None
    original_name = "video"
    if message.video:
        file_obj = message.video
        original_name = f"video_{message.video.file_unique_id}.mp4"
    elif message.document:
        doc = message.document
        fname = doc.file_name or ""
        ext = Path(fname).suffix.lower().lstrip(".")
        if (doc.mime_type or "").startswith("video/") or ext in SUPPORTED_FORMATS:
            file_obj = doc
            original_name = fname or "video"
    if not file_obj:
        await message.reply_text("Please send a video file.\nSupported: " + ", ".join(SUPPORTED_FORMATS))
        return
    size_mb = (file_obj.file_size or 0)/1024/1024
    if size_mb > 2000:
        await message.reply_text(f"❌ Too large ({size_mb:.1f}MB). Max 2GB.")
        return
    status = await message.reply_text("⬇️ Downloading...")
    tmp_dir = tempfile.mkdtemp(prefix="wmv_")
    try:
        ext = Path(original_name).suffix.lstrip(".") or "mp4"
        input_path = os.path.join(tmp_dir, f"input.{ext}")
        output_name = Path(original_name).stem + ".wmv"
        output_path = os.path.join(tmp_dir, output_name)
        await client.download_media(message, file_name=input_path)
        await status.edit_text("🔄 Converting to studio60fps (near-lossless)...")
        ok, err = await convert_to_wmv(input_path, output_path)
        if not ok:
            await status.edit_text(f"❌ Conversion failed:\n{err[:200]}")
            return
        out_mb = os.path.getsize(output_path)/1024/1024
        await status.edit_text(f"⬆️ Uploading ({out_mb:.1f}MB)...")
        await message.reply_document(document=output_path, file_name=output_name, caption=CAPTION_MSG)
        await status.delete()
    except Exception as e:
        await status.edit_text(f"❌ Error: {e}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

threading.Thread(target=run_flask, daemon=True).start()
logger.info("Bot starting with 2GB support!")
app.run()
