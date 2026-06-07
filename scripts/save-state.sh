#!/bin/bash
# save-state — called automatically every 10min and before restart
# Usage: save-state   (GH_TOKEN and GITHUB_REPO must be set in env)

echo "[*] Saving state to GitHub..."

# ── Workspace files ──
tar -czf /tmp/ws.tar.gz \
  /root/workspace /root/uploads /root/.bashrc /root/.bash_history \
  --exclude='*.pyc' --exclude='__pycache__' \
  --exclude='node_modules' --exclude='.git' \
  2>/dev/null || true

SZ=$(stat -c%s /tmp/ws.tar.gz 2>/dev/null || echo 99999999)

if [ "$SZ" -lt "94000000" ]; then
  B64=$(base64 -w 0 /tmp/ws.tar.gz)
  SHA=$(curl -s \
    -H "Authorization: token ${GH_TOKEN}" \
    "https://api.github.com/repos/${GITHUB_REPO}/contents/state/workspace.tar.gz.b64" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('sha',''))" 2>/dev/null || echo "")
  BODY=$(python3 -c "
import json, sys
sha = sys.argv[1]
b64 = sys.argv[2]
d = {'message': 'save workspace', 'content': b64}
if sha: d['sha'] = sha
print(json.dumps(d))
" "$SHA" "$B64")
  curl -s -X PUT \
    -H "Authorization: token ${GH_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "$BODY" \
    "https://api.github.com/repos/${GITHUB_REPO}/contents/state/workspace.tar.gz.b64" > /dev/null
  echo "[OK] Workspace saved ($(( SZ / 1024 ))KB)"
else
  echo "[!] Workspace too large (${SZ} bytes) — not saved"
fi

# ── Pip packages ──
pip freeze 2>/dev/null > /tmp/pip.txt || true
PB64=$(base64 -w 0 /tmp/pip.txt)
PSHA=$(curl -s \
  -H "Authorization: token ${GH_TOKEN}" \
  "https://api.github.com/repos/${GITHUB_REPO}/contents/state/pip_packages.txt" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('sha',''))" 2>/dev/null || echo "")
PBODY=$(python3 -c "
import json, sys
sha = sys.argv[1]; b64 = sys.argv[2]
d = {'message': 'save pip', 'content': b64}
if sha: d['sha'] = sha
print(json.dumps(d))
" "$PSHA" "$PB64")
curl -s -X PUT \
  -H "Authorization: token ${GH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$PBODY" \
  "https://api.github.com/repos/${GITHUB_REPO}/contents/state/pip_packages.txt" > /dev/null

# ── Apt packages ──
apt-mark showmanual 2>/dev/null > /tmp/apt.txt || true
AB64=$(base64 -w 0 /tmp/apt.txt)
ASHA=$(curl -s \
  -H "Authorization: token ${GH_TOKEN}" \
  "https://api.github.com/repos/${GITHUB_REPO}/contents/state/apt_packages.txt" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('sha',''))" 2>/dev/null || echo "")
ABODY=$(python3 -c "
import json, sys
sha = sys.argv[1]; b64 = sys.argv[2]
d = {'message': 'save apt', 'content': b64}
if sha: d['sha'] = sha
print(json.dumps(d))
" "$ASHA" "$AB64")
curl -s -X PUT \
  -H "Authorization: token ${GH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$ABODY" \
  "https://api.github.com/repos/${GITHUB_REPO}/contents/state/apt_packages.txt" > /dev/null

echo "[OK] All state saved!"
