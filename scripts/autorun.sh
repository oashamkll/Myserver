#!/bin/bash
# autorun — manage persistent processes (survive browser disconnect via screen)
#
# Commands:
#   autorun add "python3 /root/workspace/bot.py"   — add & start in screen
#   autorun list                                    — show all with status
#   autorun remove 1                                — remove entry #1
#   autorun run                                     — start all (called on boot)
#   autorun stop 1                                  — stop screen session #1
#   autorun log 1                                   — show logs for #1

LIST="/tmp/.autorun_list"
touch "$LIST"

case "$1" in
  add)
    CMD="$2"
    [ -z "$CMD" ] && echo "Usage: autorun add \"command\"" && exit 1
    echo "$CMD" >> "$LIST"
    IDX=$(wc -l < "$LIST")
    SNAME="ar_${IDX}"
    screen -dmS "$SNAME" bash -c "$CMD; echo '[process exited]'; sleep 5"
    echo "[+] Started in screen session: $SNAME"
    echo "    cmd : $CMD"
    echo "    log : /tmp/${SNAME}.log"
    echo "    view: screen -r $SNAME"
    ;;

  list)
    echo "╔══════════════════════════════════════════╗"
    echo "║           Autorun Processes              ║"
    echo "╚══════════════════════════════════════════╝"
    i=1
    while IFS= read -r cmd; do
      [ -z "$cmd" ] && { i=$(( i+1 )); continue; }
      SNAME="ar_${i}"
      R=$(screen -ls 2>/dev/null | grep -c "${SNAME}" || echo 0)
      S=$( [ "$R" -gt 0 ] && echo "🟢 RUNNING" || echo "🔴 STOPPED")
      echo "  [$i] $S"
      echo "       $cmd"
      i=$(( i+1 ))
    done < "$LIST"
    echo ""
    echo "Active screen sessions:"
    screen -ls 2>/dev/null || echo "  none"
    ;;

  remove)
    N="$2"
    [ -z "$N" ] && echo "Usage: autorun remove <number>" && exit 1
    sed -i "${N}d" "$LIST"
    screen -S "ar_${N}" -X quit 2>/dev/null || true
    echo "[+] Removed entry $N"
    ;;

  run)
    echo "[*] Starting all autorun processes..."
    i=1
    while IFS= read -r cmd; do
      [ -z "$cmd" ] && { i=$(( i+1 )); continue; }
      SNAME="ar_${i}"
      # Only start if not already running
      if ! screen -ls 2>/dev/null | grep -q "$SNAME"; then
        screen -dmS "$SNAME" bash -c "$cmd; echo '[exited]'; sleep 5"
        echo "[+] Started $SNAME: $cmd"
      else
        echo "[=] Already running: $SNAME"
      fi
      i=$(( i+1 ))
    done < "$LIST"
    ;;

  stop)
    N="$2"
    [ -z "$N" ] && echo "Usage: autorun stop <number>" && exit 1
    screen -S "ar_${N}" -X quit 2>/dev/null \
      && echo "[+] Stopped ar_${N}" \
      || echo "[-] Not found: ar_${N}"
    ;;

  log)
    N="$2"
    [ -z "$N" ] && echo "Usage: autorun log <number>" && exit 1
    LOG="/tmp/ar_${N}.log"
    [ -f "$LOG" ] && tail -50 "$LOG" || echo "No log file: $LOG"
    ;;

  *)
    echo "Usage: autorun <add|list|remove|run|stop|log>"
    echo ""
    echo "  add \"cmd\"   — add process and start it now"
    echo "  list        — show all processes and status"
    echo "  remove N    — remove process #N"
    echo "  run         — start all processes (on boot)"
    echo "  stop N      — stop process #N"
    echo "  log N       — show last 50 lines of log #N"
    ;;
esac
