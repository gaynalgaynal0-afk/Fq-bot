#!/bin/bash
set -e

echo "==> Installing dependencies..."
apt-get update -qq
apt-get install -y -qq ffmpeg wget

# Download prebuilt telegram-bot-api binary
if [ ! -f /usr/local/bin/telegram-bot-api ]; then
  echo "==> Downloading telegram-bot-api binary..."
  wget -q https://github.com/tdlib/telegram-bot-api/releases/download/v7.11/telegram-bot-api-amd64-linux.zip -O /tmp/tgapi.zip
  unzip -q /tmp/tgapi.zip -d /tmp/tgapi
  mv /tmp/tgapi/telegram-bot-api /usr/local/bin/telegram-bot-api
  chmod +x /usr/local/bin/telegram-bot-api
  rm -rf /tmp/tgapi /tmp/tgapi.zip
  echo "==> Binary installed"
fi

mkdir -p /tmp/telegram-bot-api-data

echo "==> Starting local Telegram Bot API server on port 8081..."
telegram-bot-api \
  --api-id="${TELEGRAM_API_ID}" \
  --api-hash="${TELEGRAM_API_HASH}" \
  --local \
  --http-port=8081 \
  --dir=/tmp/telegram-bot-api-data \
  --log=/tmp/tgapi.log &

# Wait for server to be ready
echo "==> Waiting for local API server to start..."
for i in $(seq 1 15); do
  if curl -s http://127.0.0.1:8081/bot${BOT_TOKEN}/getMe > /dev/null 2>&1; then
    echo "==> Local API server is ready!"
    break
  fi
  sleep 1
done

echo "==> Starting bot..."
python bot.py
