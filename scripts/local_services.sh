#!/bin/sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
BACKEND_PLIST="${HOME}/Library/LaunchAgents/com.hr.backend.plist"
BOT_PLIST="${HOME}/Library/LaunchAgents/com.hr.bot.plist"

usage() {
  echo "Usage: $0 {install|start|stop|restart|status|logs}"
  exit 1
}

[ $# -eq 1 ] || usage

case "$1" in
  install)
    exec "$(CDPATH= cd -- "$(dirname "$0")" && pwd)/install_launchd_services.sh"
    ;;
  start)
    launchctl load "$BACKEND_PLIST"
    launchctl load "$BOT_PLIST"
    ;;
  stop)
    launchctl unload "$BOT_PLIST" >/dev/null 2>&1 || true
    launchctl unload "$BACKEND_PLIST" >/dev/null 2>&1 || true
    ;;
  restart)
    launchctl unload "$BOT_PLIST" >/dev/null 2>&1 || true
    launchctl unload "$BACKEND_PLIST" >/dev/null 2>&1 || true
    launchctl load "$BACKEND_PLIST"
    launchctl load "$BOT_PLIST"
    ;;
  status)
    launchctl list | grep 'com.hr\.' || true
    ;;
  logs)
    tail -n 60 \
      "$PROJECT_ROOT/logs/backend.out.log" \
      "$PROJECT_ROOT/logs/backend.err.log" \
      "$PROJECT_ROOT/logs/bot.out.log" \
      "$PROJECT_ROOT/logs/bot.err.log"
    ;;
  *)
    usage
    ;;
esac
