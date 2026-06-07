#!/bin/bash
LIST="/tmp/.autorun_list"; touch "$LIST"
case "$1" in
  add)
    echo "$2" >> "$LIST"
    IDX=$(wc -l < "$LIST")
    screen -dmS "ar_${IDX}" bash -c "$2"
    echo "[+] Started screen ar_${IDX}: $2"
    echo "    View: screen -r ar_${IDX}"
    ;;
  list)
    echo "=== Autorun processes ==="
    i=1
    while IFS= read -r cmd; do
      [ -z "$cmd" ] && { i=$((i+1)); continue; }
      R=$(screen -ls 2>/dev/null | grep -c "ar_${i}" || echo 0)
      S=$([ "$R" -gt 0 ] && echo "RUNNING" || echo "STOPPED")
      echo "  [$i] [$S] $cmd"
      i=$((i+1))
    done < "$LIST"
    ;;
  remove)
    sed -i "${2}d" "$LIST"
    echo "[+] Removed line $2"
    ;;
  run)
    i=1
    while IFS= read -r cmd; do
      [ -z "$cmd" ] && { i=$((i+1)); continue; }
      screen -dmS "ar_${i}" bash -c "$cmd"
      echo "[+] Started ar_${i}: $cmd"
      i=$((i+1))
    done < "$LIST"
    ;;
  stop)
    screen -S "$2" -X quit && echo "[+] Stopped: $2" || echo "[-] Not found: $2"
    ;;
  *)
    echo "Usage: autorun add|list|remove|run|stop"
    ;;
esac
