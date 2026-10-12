#!/bin/bash
# Starts LinuxCNC with TeachInLathe straight from this checkout, using the
# system python3 (no venv, nothing installed). The apt packages it needs come
# from ./install.sh --deps-only.
#
#   scripts/qt6_app.sh path/to/machine.ini
#
# LinuxCNC is taken from $LINUXCNC_DIR (a run-in-place source tree), which
# defaults to linuxcnc-dev4 next to this checkout; when that does not exist,
# the linuxcnc found on PATH is used.

set -euo pipefail

INI="${1:?usage: $0 path/to/machine.ini}"
[ -f "$INI" ] || { echo "no such INI file: $INI" >&2; exit 1; }
INI="$(realpath -- "$INI")"

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LINUXCNC_DIR="${LINUXCNC_DIR:-$(dirname "$REPO")/linuxcnc-dev4}"

if [ -x "$LINUXCNC_DIR/scripts/linuxcnc" ]; then
    LINUXCNC="$LINUXCNC_DIR/scripts/linuxcnc"
elif command -v linuxcnc >/dev/null; then
    LINUXCNC="$(command -v linuxcnc)"
else
    echo "LinuxCNC not found: set LINUXCNC_DIR to your source tree" >&2
    exit 1
fi

# Diagnostics. LinuxCNC starts the display as a child, so anything exported
# here reaches it. Comment out when you are done measuring.

# The G-code preview reports what it costs to ~/teachinlathe.log every 5s:
# polls/s, redraws/s, ms per redraw, share of one core, preview reloads.
#export TEACHINLATHE_PERF=1
#export  TEACHINLATHE_SAMPLES=0

# Uncomment if the QML engine's garbage collector is suspected again.
#export QT_LOGGING_RULES="qt.qml.gc.statistics=true;qt.qml.gc.allocatorStats=true"

# The ini says DISPLAY = teachinlathe, so LinuxCNC looks it up on PATH.
# Provide a throwaway launcher for it instead of an installed one.
LAUNCHER_DIR=$(mktemp -d)
trap 'rm -rf "$LAUNCHER_DIR"' EXIT
cat > "$LAUNCHER_DIR/teachinlathe" <<'EOF'
#!/usr/bin/python3
import sys
from teachinlathe import main
sys.exit(main())
EOF
chmod +x "$LAUNCHER_DIR/teachinlathe"

export PATH="$LAUNCHER_DIR:$PATH"
# LinuxCNC's run-in-place environment prepends its own lib/python to this.
export PYTHONPATH="$REPO/src${PYTHONPATH:+:$PYTHONPATH}"

cd "$(dirname "$INI")"
"$LINUXCNC" "$(basename "$INI")"
