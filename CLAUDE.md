# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TeachInLathe is a **PyQt6-based Virtual Control Panel (VCP)** for LinuxCNC CNC lathes. It provides both manual machine control (jogging, spindle) and a conversational programming interface where operators define machining operations through forms rather than hand-coded G-code. The conversational UI is built with QML.

## Commands

Nothing is installed for development: the app runs straight from this checkout, with `src/`
on `PYTHONPATH`. The LinuxCNC build in use is the run-in-place tree `~/Work/linuxcnc-dev4`;
its `lib/python` is the one to use (the system `dist-packages` `hal` lacks `hal.Type`).

```bash
# Start LinuxCNC with TeachInLathe from this checkout (~/Work/teachinlathe.sh: puts src/ on
# PYTHONPATH and a throwaway `teachinlathe` launcher on PATH for the INI's DISPLAY line)
~/Work/teachinlathe.sh

# Run the tests
PYTHONPATH=/home/cnc/Work/linuxcnc-dev4/lib/python:src QT_QPA_PLATFORM=offscreen python3 -m pytest tests

# Install on a machine without a checkout (pip install from the repo), or build the .deb
./install.sh
./build_deb.sh
```

There is no linter configured for this project.

## Architecture

### Technology Stack
- **Python 3.11**, **PyQt6** (Qt 6), **QML** (Qt declarative UI)
- **LinuxCNC HAL** — hardware abstraction layer for machine I/O pins

### Package Layout

The package (`src/teachinlathe/`) keeps each feature's domain in its own package
(`model/`, `logic/`, `store/`, `gcode/` as it needs them) and all of the UI (QML + ViewModels)
under `ui/`: one directory per tab in `ui/tabs/`, and what they share in `ui/common/` and `ui/theme/`.

```
app/             → application.py (Application: builds the HAL component and the repositories at
                   start-up), app_window.py (AppWindow: the QML scene, wires all tabs together), AppRoot.qml, app shell, dev panel, logging
core/            → repositories: the only layer that talks to LinuxCNC (HAL, INI, status, commands);
                   lathe_hal_component.py is the singleton owning all HAL pin definitions;
                   tool_library_repository.py is the only way to the tool table and the tool library
                   files (through ToolTblFileDataSource and LatheToolExtrasDataSource)
manual/          → logic/ (manual_turning_use_case.py: spindle lever, joystick, handwheels, angle feed;
                   machine_limits.py: teach-in limits)
machine/         → model/ (fixtures)
tooling/         → model/ (tool types, catalogs)
programs/        → model/ (program runtime) + logic/ (programs_use_case.py: the HAL pins of a program run)
conversational/  → model/ (data_types.py: domain dataclasses) + logic/ (conversational_use_case.py: what is
                   done to programs) + store/ (JSON and DXF files) + gcode/ (G-code generation)
ui/tabs/         → manual_turning/, tool_library/ (+ shapes/), conversational/ (ConversationalViewModel.py,
                   the QML editor, profile definition canvases), programs/ (file browser, G-code
                   viewer, backplot/), machine_settings/
ui/              → shared QML modules: theme, common (Images singleton + images/, touchable_input/)
```

Shared QML is imported by module name (`import theme 1.0`, `import common 1.0`,
`import common.touchable_input 1.0`); `teachinlathe.ui.QML_IMPORT_DIR` is on every engine's import path.
All images live in `ui/common/images/` and are referenced as `Images.url("name.svg")` in QML or
through `teachinlathe.ui.common.images` in Python — never by a relative path.

### Conversational Module Data Flow

The domain model is a hierarchy of Python dataclasses (`conversational/model/data_types.py`):

```
Program → Header (Workpiece) + List[Operation]
Operation subtypes: ChangeTool, Facing, Profiling, Drilling, Tapping, Parting, Threading, DefineProfile
Each TurnableOperation contains: SpindleParameters, CuttingParameters, GeometryParameters, M1Parameters, EdgeBreak
```

Programs are stored as JSON files in `conversational/` (`PROGRAMS_DIR` in `conversational_use_case.py`). The `Operation` registry maps string keys to classes:

```python
operation_types = {"facing": Facing, "drilling": Drilling, ...}
```

Data flow for edits:
1. Selecting an operation makes its editor view model (`ConversationalViewModel.editor`, one class per
   operation type in `OperationEditorViewModel.py`); `ChildScreen` loads the matching `*DetailsView.qml`
   and hands it the editor (`editor` property, then `applyData(editor.opIndex, editor.operation)`)
2. User fills in the form → the editor calls `editor.save(payload)`
3. `ConversationalUseCase` patches the in-memory `current_program` dataclass (`_updaters`)
4. `_save_current_program()` has the use case write it to JSON; the screens follow the view model's properties
5. `ProgramListModel` (a `QAbstractListModel`) refreshes the QML ListView

### QML ↔ Python Bridge

`ConversationalViewModel` (published to QML as `conversationalViewModel`) holds which screens are open
(`screens`: programs → program → profile editor / DXF import), and `ConversationalTabRoot.qml` keeps a
`StackView` in step with it - the Tool Library pattern; see `~/Work/prompts/Tab architecture.md`.

- **Python → QML:** view model properties the screens are bound to (`required property` on `MainScreen` and
  `ChildScreen`), and signals (`detailsReady`, `gcodeGenerationStarted`, `dxfImportFailed`, ...)
- **QML → Python:** the screens' signals, connected to view model slots in `ConversationalTabRoot.qml`;
  an operation's editor calls its own view model (`editor.save`, `editor.preview`, `editor.useTool`, ...)
- Python holds no QML item: no `findChild`, `objectName` or `invokeMethod`

### HAL Component

`TeachInLatheComponent` is a singleton. All HAL pins (joystick axes, spindle direction, tool-change handshake, axis limits, etc.) are defined there. Each feature's use case listens to and writes the pins it needs (e.g. `manual/logic/manual_turning_use_case.py` for spindle, joystick and handwheels); view models get the machine through their use case.

### QML File Conventions (ui/tabs/conversational)

- `ConversationalTabRoot.qml` — navigation shell
- `MainScreen.qml` — program list
- `ChildScreen.qml` — operation list editor for a single program
- `*DetailsView.qml` / `*VisualDetailsView.qml` — per-operation parameter editor (e.g. `FacingVisualDetailsView.qml`)
- `*Parameters.qml` — reusable parameter sub-components (e.g. `CuttingParameters.qml`, `SpindleParameters.qml`)

### Auto-Save Pattern

Every `*DetailsView.qml` calls `editor.save(payload)` with the whole operation when the user changes a value. The use case patches the relevant fields on the in-memory dataclass, then `_save_current_program()` writes it. This is the established pattern for all new operation types.

### Adding a New Operation Type

1. Add a dataclass in `conversational/model/data_types.py` (subclass `TurnableOperation`)
2. Register it in `operation_types` dict
3. Create `<Op>DetailsView.qml` and any `<Op>Parameters.qml` reusable components in `ui/tabs/conversational/`, and its generator in `conversational/gcode/operations/`
4. Add its editor view model to `OperationEditorViewModel.py` (and `EDITORS`), its view to `editorViews` in
   `ChildScreen.qml`, and its edit to `ConversationalUseCase._updaters`; the view saves with `editor.save(payload)`