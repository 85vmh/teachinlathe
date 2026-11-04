# TeachInLathe

A touch-screen control panel for LinuxCNC lathes, written in PyQt6 and QML.
It covers manual turning (jogging, spindle, teach-in limits), running G-code
programs with a live backplot, a tool library, and a conversational editor
that builds G-code from operations filled in on forms.

## Install

On a Debian machine with LinuxCNC:

```bash
./install.sh                  # system-wide, so LinuxCNC finds it on PATH
./install.sh --ini FILE       # also point that LinuxCNC INI at this panel
./install.sh --deps-only      # only the apt packages, to run from a checkout
```

Or build a Debian package with `./build_deb.sh`.

LinuxCNC starts the panel from the INI file:

```ini
[DISPLAY]
DISPLAY = teachinlathe
PROGRAM_PREFIX = /path/to/programs
```

Conversational output (`Conversational Gcode`, `Conversational Json`) and the
DXF import folder (`DXF Profiles`) live under `PROGRAM_PREFIX`.

## Run from a checkout

After `./install.sh --deps-only`, edit the paths at the top of
`scripts/teachinlathe.sh` (this checkout, the LinuxCNC tree, the INI file) and
run it. It starts LinuxCNC with the panel straight from `src/`, with nothing
installed.

## Tests

```bash
PYTHONPATH=/path/to/linuxcnc/lib/python:src QT_QPA_PLATFORM=offscreen python3 -m pytest tests
```

## Layout

The package in `src/teachinlathe/` is organised by feature (`manual`,
`programs`, `conversational`, `tooling`, `machine`), with `core` for the
LinuxCNC repositories, `app` for the window that wires them together and `ui`
for shared QML and images. See `CLAUDE.md` for details.

## License

GPL-2.0, see `LICENSE`.
