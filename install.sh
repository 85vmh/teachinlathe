#!/usr/bin/env bash
#
# Install TeachInLathe and everything it needs on a Debian machine.
#
#   ./install.sh                  system-wide, so LinuxCNC finds it on PATH
#   ./install.sh --venv ~/venv    into a virtualenv instead
#   ./install.sh --deps-only      apt packages only, no application
#   ./install.sh --ini FILE       also point that LinuxCNC INI at this VCP
#
# The apt list is not written out here: it is read from debian/control, so the
# packaging and this script cannot drift apart.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE=system
VENV=
DEPS_ONLY=no
INI=
ASSUME_YES=no

say()  { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[33m    warning: %s\033[0m\n' "$*" >&2; }
die()  { printf '\033[31m    error: %s\033[0m\n' "$*" >&2; exit 1; }

usage() { sed -n '3,8p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0; }

while [ $# -gt 0 ]; do
    case "$1" in
        --venv)      MODE=venv; VENV="${2:?--venv needs a path}"; shift 2 ;;
        --deps-only) DEPS_ONLY=yes; shift ;;
        --ini)       INI="${2:?--ini needs a path}"; shift 2 ;;
        -y|--yes)    ASSUME_YES=yes; shift ;;
        -h|--help)   usage ;;
        *)           die "unknown option: $1 (try --help)" ;;
    esac
done

# ---------------------------------------------------------------- checks ----

[ -f "$REPO/pyproject.toml" ] || die "run this from the teachinlathe checkout"
command -v apt-get >/dev/null || die "this script is for Debian and derivatives"
[ "$(id -u)" -ne 0 ] || die "run as a normal user; the script calls sudo itself"

# ------------------------------------------------------------ apt packages --

# The binary package's Depends, minus the substitution variables dpkg fills in.
mapfile -t PACKAGES < <(python3 - "$REPO/debian/control" <<'PY'
import re, sys
text = open(sys.argv[1], encoding="utf-8").read()
# Comments are stripped before the fields are folded, as dpkg does it.
text = "\n".join(l for l in text.splitlines() if not l.startswith("#"))
stanza = text.split("\n\n")[-1]
field = re.search(r"^Depends:(.*?)(?=^\S|\Z)", stanza, re.S | re.M).group(1)
for dep in field.replace("\n", " ").split(","):
    dep = dep.strip().split()[0] if dep.strip() else ""
    if dep and not dep.startswith("${"):
        print(dep)
PY
)
[ "${#PACKAGES[@]}" -gt 0 ] || die "could not read Depends from debian/control"

# Building the wheel needs these two. They are deliberately not in
# debian/control: the .deb is built once, elsewhere, and does not need them at
# run time - this script does, because it installs from source.
if [ "$DEPS_ONLY" = no ]; then
    PACKAGES+=(python3-pip python3-poetry-core)
fi

# LinuxCNC is the one dependency that is often built from source rather than
# installed from apt. Asking apt for it on such a machine would install a
# second, older copy next to the one in use, so it is only added when the
# Python modules it provides are missing.
if python3 -c "import linuxcnc, hal, gcode" 2>/dev/null; then
    PACKAGES=("${PACKAGES[@]/linuxcnc-uspace}")
    HAVE_LINUXCNC=yes
else
    HAVE_LINUXCNC=no
fi

MISSING=()
for pkg in "${PACKAGES[@]}"; do
    [ -n "$pkg" ] || continue
    if ! dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null | grep -q "^install ok installed$"; then
        MISSING+=("$pkg")
    fi
done

if [ "${#MISSING[@]}" -eq 0 ]; then
    say "All apt dependencies are already installed"
else
    say "Installing ${#MISSING[@]} apt package(s)"
    printf '    %s\n' "${MISSING[@]}"
    APT_YES=()
    [ "$ASSUME_YES" = yes ] && APT_YES=(-y)
    sudo apt-get install "${APT_YES[@]}" "${MISSING[@]}"
fi

if [ "$DEPS_ONLY" = yes ]; then
    say "Dependencies only, as asked; the application was not installed"
    exit 0
fi

# ----------------------------------------------------------- application ----

if [ "$MODE" = venv ]; then
    # --system-site-packages on purpose: PyQt6 and the LinuxCNC modules are
    # apt packages, and a sealed virtualenv cannot see either of them.
    [ -d "$VENV" ] || python3 -m venv --system-site-packages "$VENV"
    say "Installing into $VENV"
    "$VENV/bin/pip" install --no-build-isolation --upgrade "$REPO"
    LAUNCHER="$VENV/bin/teachinlathe"
else
    # Debian marks its Python installation externally managed (PEP 668). This
    # is a machine control panel that LinuxCNC has to find on PATH, which is
    # exactly the case the override exists for.
    say "Installing system-wide"
    sudo pip install --break-system-packages --no-build-isolation --upgrade "$REPO"
    LAUNCHER="$(command -v teachinlathe || echo /usr/local/bin/teachinlathe)"
fi

# ------------------------------------------------------------- post-check ---

say "Checking the installation"

"$([ "$MODE" = venv ] && echo "$VENV/bin/python" || echo python3)" - <<'PY'
import importlib, sys
missing = [m for m in ("PyQt6.QtCore", "PyQt6.QtQuickWidgets", "ezdxf", "OpenGL")
           if not importlib.util.find_spec(m)]
print("    python modules:", "ok" if not missing else "MISSING " + ", ".join(missing))
sys.exit(1 if missing else 0)
PY

if [ "$HAVE_LINUXCNC" = yes ] || python3 -c "import linuxcnc" 2>/dev/null; then
    echo "    linuxcnc modules: ok"
    # The backplot embeds LinuxCNC's own qt5_graphics. Older releases bind it
    # straight to PyQt5, and two Qt bindings in one process do not work: the
    # Programs tab would fail with a confusing TypeError about QWidget. Newer
    # LinuxCNC goes through QtPy, which this application pins to PyQt6.
    GRAPHICS="$(python3 -c "import qt5_graphics; print(qt5_graphics.__file__)" 2>/dev/null || true)"
    if [ -n "$GRAPHICS" ] && grep -q "^from PyQt5" "$GRAPHICS"; then
        warn "$GRAPHICS is bound to PyQt5, so the G-code backplot will not load."
        warn "Build LinuxCNC from a version whose qt5_graphics imports qtpy."
        warn "That is the copy on the current PYTHONPATH; if LinuxCNC runs from"
        warn "a source tree, re-run with that tree's lib/python on PYTHONPATH."
    elif [ -n "$GRAPHICS" ]; then
        echo "    qt5_graphics: ok (binding-agnostic)"
    fi
else
    warn "LinuxCNC's Python modules were not found. Install linuxcnc-uspace,"
    warn "or put your own build's lib/python on PYTHONPATH."
fi

# ------------------------------------------------------------------- INI ----

if [ -n "$INI" ]; then
    [ -f "$INI" ] || die "no such INI file: $INI"
    if grep -qE '^\s*DISPLAY\s*=\s*teachinlathe\s*$' "$INI"; then
        say "$INI already starts this VCP"
    else
        cp -- "$INI" "$INI.before-teachinlathe"
        # DISPLAY names the program LinuxCNC launches; anything else in that
        # slot (axis, qtpyvcp, ...) starts a different front end entirely.
        sed -i -E 's|^([[:space:]]*)DISPLAY[[:space:]]*=.*$|\1DISPLAY = teachinlathe|' "$INI"
        say "Pointed $INI at teachinlathe (previous version: $INI.before-teachinlathe)"
    fi
fi

# ----------------------------------------------------------------- done -----

say "Done"
echo "    launcher: $LAUNCHER"
echo
echo "    Add this to your LinuxCNC INI, under [DISPLAY]:"
echo
echo "        DISPLAY = teachinlathe"
echo
if [ "$MODE" = venv ]; then
    echo "    LinuxCNC has to find that launcher on PATH, so start it with the"
    echo "    virtualenv active, or use the system-wide install instead."
    echo
fi
