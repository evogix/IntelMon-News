#!/usr/bin/env bash
# IntelMon-News setup — Cross-platform (Linux / macOS / Windows WSL / Termux)
set -e
cd "$(dirname "$0")"

OS="$(uname -s 2>/dev/null || echo Unknown)"
echo "[*] Detected OS: $OS"
echo "[*] Installing Python deps..."
if command -v pip3 >/dev/null 2>&1; then
  pip3 install -q -r requirements.txt 2>/dev/null || pip3 install -q requests feedparser
elif command -v pip >/dev/null 2>&1; then
  pip install -q -r requirements.txt 2>/dev/null || pip install -q requests feedparser
else
  echo "[!] pip not found — install Python 3.10+ first"
  exit 1
fi

echo "[*] Creating dirs..."
mkdir -p data logs

# Copy example config if needed
if [ ! -f config.json ] && [ -f config.json.example ]; then
  cp config.json.example config.json
  echo "[*] Created config.json from example (edit it with your bot token)"
fi

echo ""
echo "════════════════════════════════════════"
echo " Setup complete — next steps:"
echo " 1) Telegram: @BotFather → /newbot → copy token"
echo " 2) Edit config.json → telegram.bot_token"
echo " 3) Send a message to your bot, then get chat ID:"
echo "    curl https://api.telegram.org/bot<TOKEN>/getUpdates"
echo "    (look for chat.id)"
echo " 4) Edit config.json → telegram.chat_id"
echo " 5) Test:   python3 monitor.py --test"
echo " 6) Run:    python3 monitor.py --loop 180   (every 3 min)"
echo ""
echo " Cross-platform run options:"
echo "  Linux/macOS/WSL:"
echo "    nohup python3 monitor.py --loop 180 > logs/nohup.log 2>&1 &"
echo "  Windows (PowerShell):"
echo "    python monitor.py --loop 180"
echo "  Docker:"
echo "    docker-compose up -d"
echo "  Systemd (VPS):"
echo "    sudo cp intel-monitor.service /etc/systemd/system/"
echo "    sudo systemctl enable --now intel-monitor"
echo "  Cron (every 3 min):"
echo "    */3 * * * * cd $(pwd) && python3 monitor.py --once >> logs/cron.log 2>&1"
echo "  Termux (Android):"
echo "    termux-wake-lock && python3 monitor.py --loop 180 &"
echo "════════════════════════════════════════"
