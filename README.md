# 🎬 WMV Converter Telegram Bot

Converts any video format to **real WMV** (Windows Media Video 2) using FFmpeg.
Includes a Telegram Mini App served at a **secret URL path** on Render.

---

## Features

- ✅ Real WMV2 codec (not a renamed file)
- ✅ Audio: WMAV2 (Windows Media Audio v2)
- ✅ Container: ASF (Advanced Systems Format)
- ✅ Supports MP4, AVI, MOV, MKV, FLV, WebM, 3GP, MPEG, etc.
- ✅ Telegram Mini App at a secret URL path
- ✅ Deploy-ready for Render (free tier)

---

## Files

```
bot.py           — Telegram bot (video handler + converter)
server.py        — Flask web server (landing page + Mini App)
requirements.txt — Python dependencies
render.yaml      — Render deployment config
start.sh         — Local start script
```

---

## Deploy on Render

### Step 1 — Create a Telegram Bot

1. Open [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow prompts
3. Copy your **Bot Token**
4. Send `/newapp` to BotFather → link it to your bot → set the Mini App URL to:
   `https://YOUR-RENDER-APP.onrender.com/secret-tools`

### Step 2 — Push to GitHub

```bash
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/YOUR_USERNAME/wmv-bot
git push -u origin main
```

### Step 3 — Deploy on Render

**Option A — Using render.yaml (recommended):**
1. Go to [render.com](https://render.com) → New → Blueprint
2. Connect your GitHub repo
3. Render will create both services automatically

**Option B — Manual:**

Create a **Web Service**:
- Build command: `apt-get update && apt-get install -y ffmpeg && pip install -r requirements.txt`
- Start command: `gunicorn server:app --bind 0.0.0.0:$PORT`
- Add env vars:
  - `SECRET_PATH` = `/secret-tools` (or any secret path you want)

Create a **Background Worker**:
- Same build command as above
- Start command: `python bot.py`
- Add env vars:
  - `BOT_TOKEN` = your bot token from BotFather
  - `MINI_APP_URL` = `https://YOUR-WEB-SERVICE.onrender.com`
  - `SECRET_PATH` = `/secret-tools` (must match web service)

### Step 4 — Register Mini App with BotFather

Tell BotFather the Mini App URL is:
```
https://YOUR-WEB-SERVICE.onrender.com/secret-tools
```

Only people with this exact URL can open the Mini App panel.

---

## Environment Variables

| Variable      | Service | Description                                      |
|---------------|---------|--------------------------------------------------|
| `BOT_TOKEN`   | Worker  | Telegram bot token from BotFather                |
| `MINI_APP_URL`| Both    | Full URL of your Render web service              |
| `SECRET_PATH` | Both    | Secret URL path for Mini App (e.g. `/my-secret`) |

---

## Local Testing

```bash
# Install FFmpeg
# Ubuntu/Debian:
sudo apt install ffmpeg
# macOS:
brew install ffmpeg

# Install Python deps
pip install -r requirements.txt

# Set env vars
export BOT_TOKEN="your_token_here"
export MINI_APP_URL="http://localhost:5000"
export SECRET_PATH="/secret-tools"

# Run server (terminal 1)
python server.py

# Run bot (terminal 2)
python bot.py
```

Then open `http://localhost:5000/secret-tools` for the Mini App panel.

---

## How WMV Conversion Works

FFmpeg command used:
```bash
ffmpeg -i input.mp4 \
  -c:v wmv2 \        # Windows Media Video 2 codec
  -c:a wmav2 \       # Windows Media Audio v2
  -b:v 1500k \       # 1.5 Mbps video bitrate
  -b:a 128k \        # 128 kbps audio
  -ar 44100 \        # 44.1 kHz sample rate
  -ac 2 \            # Stereo
  -f asf \           # ASF container (WMV's native container)
  output.wmv
```

This produces a **genuine WMV file** — not a renamed MP4.
The file will open correctly in Windows Media Player and other WMV-compatible players.

---

## Limits

- Max file size: 50MB (Telegram Bot API limit)
- Conversion timeout: 5 minutes
