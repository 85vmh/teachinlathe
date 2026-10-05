#!/bin/bash
# Starts LinuxCNC with TeachInLathe straight from this checkout, using the
# system python3 (no venv, nothing installed). The apt packages it needs come
# from ./install.sh --deps-only.

# Machine specific: edit these two on each machine.
LINUXCNC_HOME=/home/cnc/Work/linuxcnc-dev4
INI_FILE_PATH=/home/cnc/linuxcnc/configs/sim.axis/weiler_lathe.ini

set -euo pipefail

LINUXCNC="$LINUXCNC_HOME/scripts/linuxcnc"
[ -x "$LINUXCNC" ] || { echo "LinuxCNC not found: $LINUXCNC (check LINUXCNC_HOME)" >&2; exit 1; }
[ -f "$INI_FILE_PATH" ] || { echo "no such INI file: $INI_FILE_PATH (check INI_FILE_PATH)" >&2; exit 1; }

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

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

cd "$(dirname "$INI_FILE_PATH")"
"$LINUXCNC" "$(basename "$INI_FILE_PATH")"
