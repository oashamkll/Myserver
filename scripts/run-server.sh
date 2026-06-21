#!/bin/bash
set -e

sudo cp server.py /root/server.py
sudo cp telegram_bot.py /root/telegram_bot.py
sudo mkdir -p /root/workspace /root/uploads
sudo cp scripts/save-state.sh /usr/local/bin/save-state
sudo cp scripts/autorun.sh    /usr/local/bin/autorun
sudo chmod +x /usr/local/bin/save-state /usr/local/bin/autorun

# ── Security: lock down the server ──
# Only allow connections through ngrok tunnel
sudo iptables -A INPUT -p tcp --dport 8080 -s 127.0.0.1 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8080 ! -s 127.0.0.1 -j DROP 2>/dev/null || true

# Restore autorun processes in screen
autorun run 2>/dev/null || true

# Start web server in SCREEN — survives browser disconnect
sudo screen -dmS termux-server bash -c \
  'cd /root && python3 /root/server.py > /tmp/server.log 2>&1'
sleep 5

curl -sf http://localhost:8080 > /dev/null || {
  echo "[!] Server failed to start!"
  cat /tmp/server.log
  exit 1
}
echo "[OK] Server is up"

# Start Telegram Bot in SCREEN if token is set
if [ -n "$TELEGRAM_BOT_TOKEN" ]; then
  echo "[*] Starting Telegram Bot..."
  sudo screen -dmS telegram-bot bash -c \
    'OPENROUTER_API_KEY="'"$OPENROUTER_API_KEY"'" TELEGRAM_BOT_TOKEN="'"$TELEGRAM_BOT_TOKEN"'" python3 /root/telegram_bot.py > /tmp/telegram_bot.log 2>&1'
  sleep 2
  if screen -ls | grep -q "telegram-bot"; then
    echo "[OK] Telegram bot started successfully in screen 'telegram-bot'"
  else
    echo "[!] Failed to start Telegram bot! Check logs in /tmp/telegram_bot.log"
  fi
else
  echo "[!] TELEGRAM_BOT_TOKEN is not set. Skipping Telegram Bot startup."
fi

# Start ngrok in SCREEN — tunnels to public URL
screen -dmS termux-ngrok bash -c \
  'ngrok http 8080 --log=stdout > /tmp/ngrok.log 2>&1'
sleep 12

PUBLIC_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    for t in d.get('tunnels', []):
        if t.get('proto') == 'https':
            print(t['public_url']); break
except: pass
")

[ -z "$PUBLIC_URL" ] && {
  echo "[!] No ngrok URL!"
  cat /tmp/ngrok.log
  exit 1
}

echo ""
echo "======================================"
echo "  Termux Server LIVE!"
echo "  URL: $PUBLIC_URL"
echo "======================================"
screen -ls || true

# Push URL to repo (no secrets in commit)
git config user.email "bot@myserver.dev"
git config user.name "MyServer Bot"
git remote set-url origin "https://x-access-token:${GH_TOKEN}@github.com/${GITHUB_REPO}.git"
git pull origin main --rebase 2>/dev/null || true
echo "$PUBLIC_URL" > SERVER_URL.txt
echo "Started: $(date -u '+%Y-%m-%d %H:%M UTC')" >> SERVER_URL.txt
git add SERVER_URL.txt
git commit -m "Live: $PUBLIC_URL" || true
git push origin HEAD:main || true

# ── Main loop: save every 10min, auto-restart at 5h 30min ──
ELAPSED=0
MAX=19800
INTERVAL=600
echo "[*] Loop: save every 10min, restart at 5h30min"

while [ $ELAPSED -lt $MAX ]; do
  sleep $INTERVAL
  ELAPSED=$(( ELAPSED + INTERVAL ))
  echo "[$(date -u '+%H:%M')] ${ELAPSED}s — saving state..."
  save-state

  # Health check ngrok tunnel
  if ! curl -s http://localhost:4040/api/tunnels \
      | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('tunnels')" 2>/dev/null; then
    echo "[!] Ngrok tunnel lost — restarting..."
    screen -S termux-ngrok -X quit 2>/dev/null || true
    sleep 2
    screen -dmS termux-ngrok bash -c 'ngrok http 8080 > /tmp/ngrok.log 2>&1'
    sleep 12
    NEW=$(curl -s http://localhost:4040/api/tunnels | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    for t in d.get('tunnels', []):
        if t.get('proto') == 'https':
            print(t['public_url']); break
except: pass
")
    if [ -n "$NEW" ]; then
      git pull origin main --rebase 2>/dev/null || true
      echo "$NEW" > SERVER_URL.txt
      echo "Restarted: $(date -u '+%H:%M UTC')" >> SERVER_URL.txt
      git add SERVER_URL.txt
      git commit -m "New URL: $NEW" || true
      git push origin HEAD:main || true
      echo "[OK] New URL: $NEW"
    fi
  fi
done

# ── Final save then trigger next run via empty commit ──
echo "[*] 5h30min done — final save..."
save-state

echo "[*] Triggering next workflow run..."
MAIN_SHA=$(git rev-parse HEAD 2>/dev/null || \
  curl -s -H "Authorization: token ${GH_TOKEN}" \
    "https://api.github.com/repos/${GITHUB_REPO}/git/ref/heads/main" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['object']['sha'])")

BASE_TREE=$(curl -s \
  -H "Authorization: token ${GH_TOKEN}" \
  "https://api.github.com/repos/${GITHUB_REPO}/git/commits/${MAIN_SHA}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['tree']['sha'])")

NEW_COMMIT=$(curl -s -X POST \
  -H "Authorization: token ${GH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"auto-restart\",\"tree\":\"${BASE_TREE}\",\"parents\":[\"${MAIN_SHA}\"]}" \
  "https://api.github.com/repos/${GITHUB_REPO}/git/commits" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['sha'])")

curl -s -X PATCH \
  -H "Authorization: token ${GH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"sha\":\"${NEW_COMMIT}\"}" \
  "https://api.github.com/repos/${GITHUB_REPO}/git/refs/heads/main" > /dev/null

echo "[OK] Next run triggered! Staying alive 5min for handover..."
sleep 300
