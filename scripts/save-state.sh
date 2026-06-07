#!/bin/bash
echo "[*] Saving state..."
tar -czf /tmp/ws.tar.gz \
  /root/workspace /root/uploads /root/.bashrc /root/.bash_history \
  --exclude='*.pyc' --exclude='__pycache__' --exclude='node_modules' 2>/dev/null || true

SZ=$(stat -c%s /tmp/ws.tar.gz 2>/dev/null || echo 99999999)
if [ "$SZ" -lt "94000000" ]; then
  B64=$(base64 -w 0 /tmp/ws.tar.gz)
  SHA=$(curl -s -H "Authorization: token ${GH_TOKEN}" \
    "https://api.github.com/repos/${GITHUB_REPO}/contents/state/workspace.tar.gz.b64" \
    | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('sha',''))" 2>/dev/null || echo "")
  BODY=$(python3 -c "import json; print(json.dumps({'message':'save','content':'${B64}'}))")
  [ -n "$SHA" ] && BODY=$(python3 -c "import json; print(json.dumps({'message':'save','content':'${B64}','sha':'${SHA}'}))") 
  curl -s -X PUT -H "Authorization: token ${GH_TOKEN}" \
    -H "Content-Type: application/json" -d "$BODY" \
    "https://api.github.com/repos/${GITHUB_REPO}/contents/state/workspace.tar.gz.b64" > /dev/null
  echo "[OK] Workspace saved (${SZ} bytes)"
fi

pip freeze 2>/dev/null > /tmp/pip.txt || true
PB64=$(base64 -w 0 /tmp/pip.txt)
PSHA=$(curl -s -H "Authorization: token ${GH_TOKEN}" \
  "https://api.github.com/repos/${GITHUB_REPO}/contents/state/pip_packages.txt" \
  | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('sha',''))" 2>/dev/null || echo "")
PBODY=$(python3 -c "import json; print(json.dumps({'message':'pip','content':'${PB64}'}))")
[ -n "$PSHA" ] && PBODY=$(python3 -c "import json; print(json.dumps({'message':'pip','content':'${PB64}','sha':'${PSHA}'}))") 
curl -s -X PUT -H "Authorization: token ${GH_TOKEN}" -H "Content-Type: application/json" \
  -d "$PBODY" "https://api.github.com/repos/${GITHUB_REPO}/contents/state/pip_packages.txt" > /dev/null

apt-mark showmanual 2>/dev/null > /tmp/apt.txt || true
AB64=$(base64 -w 0 /tmp/apt.txt)
ASHA=$(curl -s -H "Authorization: token ${GH_TOKEN}" \
  "https://api.github.com/repos/${GITHUB_REPO}/contents/state/apt_packages.txt" \
  | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('sha',''))" 2>/dev/null || echo "")
ABODY=$(python3 -c "import json; print(json.dumps({'message':'apt','content':'${AB64}'}))")
[ -n "$ASHA" ] && ABODY=$(python3 -c "import json; print(json.dumps({'message':'apt','content':'${AB64}','sha':'${ASHA}'}))") 
curl -s -X PUT -H "Authorization: token ${GH_TOKEN}" -H "Content-Type: application/json" \
  -d "$ABODY" "https://api.github.com/repos/${GITHUB_REPO}/contents/state/apt_packages.txt" > /dev/null
echo "[OK] State saved!"
