#!/data/data/com.termux/files/usr/bin/bash
# ORACLE-INTEL-MON setup — Termux/Linux compatible
set -e
cd "$(dirname "$0")"

echo "[*] Installing Python deps..."
pip install -q requests feedparser 2>/dev/null || pip3 install -q requests feedparser

echo "[*] Creating dirs..."
mkdir -p data logs

echo ""
echo "════════════════════════════════════════"
echo " Setup steps:"
echo " 1) Telegram pe @BotFather open karo -> /newbot -> token copy karo"
echo " 2) config.json me bot_token daalo"
echo " 3) Chat ID lo: https://api.telegram.org/bot<TOKEN>/getUpdates"
echo "    (apne bot ko ek message bhejo, 'chat':{'id':12345...} dikhega)"
echo " 4) config.json me chat_id daalo"
echo " 5) Test:   python3 monitor.py --test"
echo " 6) Run:    python3 monitor.py --loop 600"
echo ""
echo " Termux background run:"
echo "   termux-wake-lock && python3 monitor.py --loop 600 &"
echo ""
echo " Cron mode (VPS/Termux+cronie):"
echo "   */10 * * * * cd $(pwd) && python3 monitor.py --once >> logs/cron.log 2>&1"
echo "════════════════════════════════════════"
