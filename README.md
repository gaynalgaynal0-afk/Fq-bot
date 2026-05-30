# 🎬 WMV Converter Telegram Bot (2GB Upgraded)

Converts any video format to **real WMV** (Windows Media Video 2) using FFmpeg.
Supports files up to **2GB** via Pyrogram (MTProto). Near-lossless video quality.

---

## ✅ What Changed vs Original

| Feature | Before | After |
|---|---|---|
| Max file size | 50MB | **2GB** |
| API used | python-telegram-bot (Bot API) | **Pyrogram (MTProto)** |
| Video quality | Fixed bitrate 1500k (lossy) | **-q:v 2, no cap (near-lossless)** |
| Audio quality | Fixed 128k | **qscale:a 0 (best quality)** |
| Conversion timeout | 5 min | **60 min (for large files)** |

---

## ⚙️ New Environment Variables

You now need **3** env vars instead of 1:

| Variable | Where to get it | Description |
|---|---|---|
| `BOT_TOKEN` | @BotFather | Your bot token |
| `API_ID` | https://my.telegram.org | MTProto API ID (number) |
| `API_HASH` | https://my.telegram.org | MTProto API Hash (string) |

### How to get API_ID and API_HASH:
1. Go to **https://my.telegram.org**
2. Log in with your phone number
3. Click **API development tools**
4. Create an app (name/platform don't matter)
5. Copy `App api_id` and `App api_hash`

---

## 🚀 Deploy on Render

### Build command:
```
apt-get update && apt-get install -y ffmpeg && pip install -r requirements.txt
```

### Start command (bot worker):
```
python bot.py
```

### Environment Variables:
- `BOT_TOKEN` = your bot token
- `API_ID` = your api_id (number)
- `API_HASH` = your api_hash
- `MINI_APP_URL` = your render web service URL
- `SECRET_PATH` = `/secret-tools` (or your custom path)

---

## 🎬 FFmpeg Quality Settings

```bash
ffmpeg -i input.mp4 \
  -c:v wmv2 \
  -q:v 2 \        # Near-lossless (1=best, 31=worst) — NO fixed bitrate cap
  -b:v 0 \        # Quality-driven, not bitrate-driven
  -c:a wmav2 \
  -qscale:a 0 \   # Best possible audio quality
  -ar 48000 \     # 48kHz sample rate
  -ac 2 \
  -f asf \
  output.wmv
```

This is the highest quality WMV2 encoding FFmpeg can produce.

---

## Local Testing

```bash
pip install -r requirements.txt

export BOT_TOKEN="your_token"
export API_ID="12345"
export API_HASH="your_hash"

python bot.py
```
