#!/bin/bash
sudo mkdir -p /root/workspace /root/uploads
echo "[*] Restoring state from GitHub..."

for FILE in workspace.tar.gz.b64 pip_packages.txt apt_packages.txt; do
  HTTP=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: token ${GH_TOKEN}" \
    "https://api.github.com/repos/${GITHUB_REPO}/contents/state/${FILE}")

  if [ "$HTTP" != "200" ]; then
    echo "[*] No saved $FILE yet"
    continue
  fi

  curl -s \
    -H "Authorization: token ${GH_TOKEN}" \
    -H "Accept: application/vnd.github.v3.raw" \
    "https://api.github.com/repos/${GITHUB_REPO}/contents/state/${FILE}" \
    -o "/tmp/${FILE}"

  case "$FILE" in
    *.tar.gz.b64)
      if [ -f "/tmp/${FILE}" ]; then
        base64 -d "/tmp/${FILE}" | sudo tar -xzf - -C / 2>/dev/null && echo "[OK] Files restored" || echo "[!] Failed to restore files"
      fi
      ;;
    pip_packages.txt)
      if [ -f "/tmp/${FILE}" ]; then
        sudo pip install -r "/tmp/${FILE}" --break-system-packages --ignore-installed -q 2>/dev/null && echo "[OK] Pip packages restored" || echo "[!] Failed to restore pip packages"
      fi
      ;;
    apt_packages.txt)
      if [ -f "/tmp/${FILE}" ]; then
        xargs -a "/tmp/${FILE}" sudo apt-get install -y -qq 2>/dev/null && echo "[OK] Apt packages restored" || echo "[!] Failed to restore apt packages"
      fi
      ;;
  esac
done
echo "[*] Restore complete"
