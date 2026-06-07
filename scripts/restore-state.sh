#!/bin/bash
set -e
sudo mkdir -p /root/workspace /root/uploads
echo "[*] Restoring state from GitHub..."

for FILE in workspace.tar.gz.b64 pip_packages.txt apt_packages.txt; do
  HTTP=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: token ${GH_TOKEN}" \
    "https://api.github.com/repos/${GITHUB_REPO}/contents/state/${FILE}")

  [ "$HTTP" != "200" ] && echo "[*] No saved $FILE yet" && continue

  curl -s \
    -H "Authorization: token ${GH_TOKEN}" \
    -H "Accept: application/vnd.github.v3.raw" \
    "https://api.github.com/repos/${GITHUB_REPO}/contents/state/${FILE}" \
    -o "/tmp/${FILE}"

  case "$FILE" in
    *.tar.gz.b64)
      base64 -d "/tmp/${FILE}" | sudo tar -xzf - -C / 2>/dev/null && echo "[OK] Files restored"
      ;;
    pip_packages.txt)
      sudo pip install -r "/tmp/${FILE}" -q 2>/dev/null && echo "[OK] Pip packages restored"
      ;;
    apt_packages.txt)
      xargs -a "/tmp/${FILE}" sudo apt-get install -y -qq 2>/dev/null && echo "[OK] Apt packages restored"
      ;;
  esac
done
echo "[*] Restore complete"
