#!/usr/bin/env bash
# start.sh — launches both the Flask web server and Telegram bot

set -e

echo "=== WMV Converter Bot ==="
echo "Checking FFmpeg..."
if command -v ffmpeg &>/dev/null; then
  echo "✓ FFmpeg found: $(ffmpeg -version 2>&1 | head -1)"
  echo "Checking WMV2 codec..."
  ffmpeg -encoders 2>/dev/null | grep wmv2 && echo "✓ wmv2 encoder available" || echo "⚠ wmv2 not listed (may still work)"
else
  echo "⚠ FFmpeg not found! Install it for conversions to work."
fi

echo ""
echo "Starting Flask server on port ${PORT:-5000}..."
gunicorn server:app --bind "0.0.0.0:${PORT:-5000}" --workers 2 --daemon --log-file /tmp/flask.log

echo "Starting Telegram bot..."
python bot.py
