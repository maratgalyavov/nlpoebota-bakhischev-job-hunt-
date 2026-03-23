#!/bin/sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$PROJECT_ROOT/.venv/bin/python}"
LAUNCH_AGENTS_DIR="${HOME}/Library/LaunchAgents"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "Python interpreter not found: $PYTHON_BIN" >&2
  echo "Create the virtualenv first, or pass PYTHON_BIN=/path/to/python." >&2
  exit 1
fi

mkdir -p "$PROJECT_ROOT/logs" "$LAUNCH_AGENTS_DIR"

render_template() {
  template_path="$1"
  output_path="$2"
  sed \
    -e "s|__PROJECT_ROOT__|$PROJECT_ROOT|g" \
    -e "s|__PYTHON_BIN__|$PYTHON_BIN|g" \
    "$template_path" > "$output_path"
}

BACKEND_PLIST="$LAUNCH_AGENTS_DIR/com.hr.backend.plist"
BOT_PLIST="$LAUNCH_AGENTS_DIR/com.hr.bot.plist"

render_template "$PROJECT_ROOT/launchd/com.hr.backend.plist.template" "$BACKEND_PLIST"
render_template "$PROJECT_ROOT/launchd/com.hr.bot.plist.template" "$BOT_PLIST"

launchctl unload "$BACKEND_PLIST" >/dev/null 2>&1 || true
launchctl unload "$BOT_PLIST" >/dev/null 2>&1 || true
launchctl load "$BACKEND_PLIST"
launchctl load "$BOT_PLIST"

echo "Installed and loaded:"
echo "  $BACKEND_PLIST"
echo "  $BOT_PLIST"
echo
echo "Status:"
launchctl list | grep 'com.hr\.' || true
