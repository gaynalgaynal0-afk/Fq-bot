# 🎬 WMV Converter Bot — Local Bot API Edition (2GB support)

No API_ID / API_HASH from my.telegram.org needed for the bot itself.
Uses the official Telegram Bot API local server for 2GB file support.

## Environment Variables (Render)

| Variable | Description |
|---|---|
| `BOT_TOKEN` | Your bot token from @BotFather |
| `TELEGRAM_API_ID` | From my.telegram.org (for local server only) |
| `TELEGRAM_API_HASH` | From my.telegram.org (for local server only) |

> ⚠️ TELEGRAM_API_ID and TELEGRAM_API_HASH are still needed to run the
> local Bot API server binary — but this is much easier to set up than
> using Pyrogram directly.

## Deploy on Render

1. Push this folder to GitHub
2. Go to Render → New → Blueprint → connect repo
3. Add the 3 environment variables above
4. Deploy!

## How it works

start.sh:
1. Downloads the official prebuilt telegram-bot-api binary
2. Starts it on port 8081 with --local flag (removes file size limits)
3. Starts bot.py which connects to the local server instead of api.telegram.org

This gives full 2GB upload/download support using only your BOT_TOKEN
for all bot logic, with API_ID/HASH only needed for the server binary.
