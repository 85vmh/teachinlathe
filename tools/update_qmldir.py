#!/usr/bin/env python3
"""Write the qmldir of every directory with QML in it.

Every such directory is a QML module named after its path from an import
directory - src/teachinlathe/ui (``tabs.conversational``, ``theme``) or
src/teachinlathe/app (``app_shell_qml``) - and its qmldir lists every
component in it, a ``pragma Singleton`` one as a singleton. A QML file
missing from its qmldir cannot be used from another directory, so run this
after adding, renaming or removing one.

    tools/update_qmldir.py           write the qmldirs that differ
    tools/update_qmldir.py --check   only say which differ; exit 1 if any
"""

import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent / "src" / "teachinlathe"
IMPORT_DIRS = (PACKAGE / "ui", PACKAGE / "app")


def module_uri(directory: Path):
    """The module a directory is, or None for an import directory itself."""
    for root in IMPORT_DIRS:
        try:
            parts = directory.relative_to(root).parts
        except ValueError:
            continue
        return ".".join(parts) if parts else None
    return None


def qmldir_for(directory: Path, uri: str) -> str:
    lines = [f"module {uri}"]
    for qml in sorted(directory.glob("*.qml")):
        if not qml.stem[:1].isupper():
            continue
        singleton = "singleton " if "pragma Singleton" in qml.read_text(encoding="utf-8") else ""
        lines.append(f"{singleton}{qml.stem} 1.0 {qml.name}")
    return "\n".join(lines) + "\n"


def main() -> int:
    check = "--check" in sys.argv[1:]
    stale = []
    for directory in sorted({qml.parent for qml in PACKAGE.rglob("*.qml")}):
        uri = module_uri(directory)
        if uri is None:
            continue
        path = directory / "qmldir"
        content = qmldir_for(directory, uri)
        if path.exists() and path.read_text(encoding="utf-8") == content:
            continue
        stale.append(path.relative_to(PACKAGE.parent.parent))
        if not check:
            path.write_text(content, encoding="utf-8")
    verb = "out of date" if check else "written"
    for path in stale:
        print(f"{verb}: {path}")
    return 1 if check and stale else 0


if __name__ == "__main__":
    sys.exit(main())
