# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TeachInLathe is a **PyQt6-based Virtual Control Panel (VCP)** for LinuxCNC CNC lathes. It provides both manual machine control (jogging, spindle) and a conversational programming interface where operators define machining operations through forms rather than hand-coded G-code. The conversational UI is built with QML.

## Commands

```bash
# Install for development
pip install -e .

# Run the VCP (requires LinuxCNC environment)
teachinlathe --ini=/path/to/config.ini

# Build Debian package
./build_deb.sh

# Run the tests (pytest; needs LinuxCNC's Python modules on the path)
PYTHONPATH=/path/to/linuxcnc/lib/python:src QT_QPA_PLATFORM=offscreen python3 -m pytest tests
```

There is no linter configured for this project.

## Architecture

### Technology Stack
- **Python 3.11**, **PyQt6** (Qt 6), **QML** (Qt declarative UI)
- **LinuxCNC HAL** — hardware abstraction layer for machine I/O pins

### Package Layout

The package (`src/teachinlathe/`) is organised by feature. Each feature splits into
`model/` (domain), `store/` (files on disk), `ui/` (QML + ViewModels) as it needs them.

```
app/             → mainwindow.py (wires all tabs together), AppRoot.qml, app shell, dev panel, logging
core/            → repositories: the only layer that talks to LinuxCNC (HAL, INI, status, commands);
                   lathe_hal_component.py is the singleton owning all HAL pin definitions
manual/          → logic/ (manual_lathe.py: jog/spindle, joystick, teach-in limits) + ui/
machine/         → model/ (fixtures) + ui/
tooling/         → model/ (tool types, catalogs) + store/ (tool library JSON, .tbl) + ui/ (+ ui/shapes)
programs/        → model/ (program runtime) + ui/ (file browser, G-code viewer, backplot/)
conversational/  → model/ (data_types.py: domain dataclasses) + store/ + gcode/ (G-code generation)
                   + ui/ (ConversationalQml.py, the QML editor, profile definition canvases)
ui/              → shared QML modules: theme, touchable_input, common (Images singleton + images/)
```

Shared QML is imported by module name (`import theme 1.0`, `import touchable_input 1.0`,
`import common 1.0`); `teachinlathe.ui.QML_IMPORT_DIR` is on every engine's import path.
All images live in `ui/common/images/` and are referenced as `Images.url("name.svg")` in QML or
through `teachinlathe.ui.common.images` in Python — never by a relative path.

### Conversational Module Data Flow

The domain model is a hierarchy of Python dataclasses (`conversational/model/data_types.py`):

```
Program → Header (Workpiece) + List[Operation]
Operation subtypes: ChangeTool, Facing, Profiling, Drilling, Tapping, Parting, Threading, DefineProfile
Each TurnableOperation contains: SpindleParameters, CuttingParameters, GeometryParameters, M1Parameters, EdgeBreak
```

Programs are stored as JSON files in `conversational/`. The `Operation` registry maps string keys to classes:

```python
operation_types = {"facing": Facing, "drilling": Drilling, ...}
```

Data flow for edits:
1. User fills in QML form → QML emits a signal (e.g. `updateFacing(data)`)
2. `ConversationalQml._hook_screen_item()` connects QML signals to Python slots
3. Python slot patches the in-memory `current_program` dataclass
4. `_save_current_program()` serializes to JSON and reloads to keep model consistent
5. `ProgramListModel` (a `QAbstractListModel`) refreshes the QML ListView

### QML ↔ Python Bridge

`ConversationalQml` (`QQuickWidget`) loads `Root.qml`, which uses a `Loader` to swap between screens. Navigation history is maintained in Python.

- **Python → QML:** context properties (`programsModel`, `showBack`) and direct property sets on the root item
- **QML → Python:** typed signals declared in QML (`signal updateFacing(var data)`) connected to Python slots in `_hook_screen_item()`
- Screen state is passed as a `params` object when calling `loadScreen()` from Python

### HAL Component

`TeachInLatheComponent` is a singleton. All HAL pins (joystick axes, spindle direction, tool-change handshake, axis limits, etc.) are defined there. `app/mainwindow.py` registers listener callbacks on these pins; `manual/logic/manual_lathe.py` uses them to drive jog commands.

### QML File Conventions (conversational/ui)

- `Root.qml` — navigation shell
- `MainScreen.qml` — program list
- `ChildScreen.qml` — operation list editor for a single program
- `*DetailsView.qml` — per-operation parameter editor (e.g. `FacingDetailsView.qml`)
- `*Parameters.qml` — reusable parameter sub-components (e.g. `CuttingParameters.qml`, `SpindleParameters.qml`)

### Auto-Save Pattern

Every `*DetailsView.qml` emits a signal when the user changes a value. The corresponding Python slot patches only the relevant fields on the in-memory dataclass, then calls `_save_current_program()`. This is the established pattern for all new operation types.

### Adding a New Operation Type

1. Add a dataclass in `conversational/model/data_types.py` (subclass `TurnableOperation`)
2. Register it in `operation_types` dict
3. Create `<Op>DetailsView.qml` and any `<Op>Parameters.qml` reusable components in `conversational/ui/`, and its generator in `conversational/gcode/operations/`
4. Add the signal/slot pair in `ConversationalQml._hook_screen_item()` and implement the slot
5. Wire the new operation into `ChildScreen.qml`