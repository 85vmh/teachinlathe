"""The QML views hold no state of their own: what a view shows comes from its
view model, and every change goes to the view model, which applies it, saves
it and notifies the view (CLAUDE.md, "Views hold no state").

A view that keeps a copy of its model's data - an ``applyData`` filling its
own properties, an ``opData`` it edits, a control that sets its own value -
shows that copy after the model has moved on: two Drilling operations once
showed each other's depth and feed, the view and its fields reused from one
to the other. These checks read every QML file under ``teachinlathe/ui`` and
fail on the ways that comes about.

What a view may keep - a pan or zoom, a swipe, an animation, the text being
typed in an open numpad, a choice in an open dialog until it is confirmed -
is marked, where its property is declared, with a ``// view state:`` comment
saying what it is; a model value pushed into an item where a binding cannot
be used, with ``// mirrors the model:``.
"""

import os
import re

import pytest

UI_DIR = os.path.join(os.path.dirname(__file__), "..", "src", "teachinlathe", "ui")

#: The marks that let a property be set from JavaScript (see the module docstring).
MARKS = ("view state:", "mirrors the model:")

#: The controls that change their own ``checked`` or ``currentIndex`` on a tap,
#: which cuts the binding to the model: common's Model* are used instead.
RAW_CONTROLS = ("CheckBox", "RadioButton", "Switch", "ComboBox", "ButtonGroup",
                "CheckDelegate", "RadioDelegate", "SwitchDelegate")


def _qml_files():
    for folder, _, names in os.walk(UI_DIR):
        for name in sorted(names):
            if name.endswith(".qml"):
                yield os.path.join(folder, name)


def _rel(path):
    return os.path.relpath(path, UI_DIR)


def _without_comments(text):
    """``text`` with its comments blanked, its lines where they were."""
    text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def _marked(lines, index):
    """Whether line ``index``, or the comment lines right above it, carry a mark."""
    if any(mark in lines[index] for mark in MARKS):
        return True
    k = index - 1
    while k >= 0 and lines[k].strip().startswith("//"):
        if any(mark in lines[k] for mark in MARKS):
            return True
        k -= 1
    return False


def _line_of(code, pos):
    return code.count("\n", 0, pos)


def _violations(path):
    raw = open(path, encoding="utf-8").read()
    lines = raw.split("\n")
    code = _without_comments(raw)
    found = []

    def report(pos, rule):
        found.append(f"{_rel(path)}:{_line_of(code, pos) + 1}: {rule}")

    # 1. No applyData, no opData: a view is not handed a copy of its data.
    for m in re.finditer(r"\b(applyData|opData)\b", code):
        report(m.start(), f"{m.group(1)}: a view binds to its view model, it is not handed a copy")

    # 2. A file does not set its own properties from JavaScript - only the
    # ones marked view state - nor any value, text, checked or currentIndex.
    settable = {}
    for m in re.finditer(r"(?m)^[ \t]*((?:readonly|required|default)\s+)*property\s+[\w<>.]+\s+(\w+)", code):
        if m.group(1) and ("readonly" in m.group(1) or "required" in m.group(1)):
            continue
        settable[m.group(2)] = _marked(lines, _line_of(code, m.start()))
    for m in re.finditer(r"(?<![\w.])(root\.)?(\w+)\s*(=|\+=|-=|\+\+|--)(?![=>])", code):
        name = m.group(2)
        if name not in settable or settable[name]:
            continue
        if re.search(r"\b(var|let|const)\s*$", code[max(0, m.start() - 6):m.start()]):
            continue
        report(m.start(), f"sets its property '{name}': bind it to the view model, "
                          "or mark it '// view state:' if it is the view's own")
    for m in re.finditer(r"\.(value|text|checked|currentIndex)\s*=(?!=)(?!\s*Qt\.binding)", code):
        if _marked(lines, _line_of(code, m.start())):
            continue
        report(m.start(), f"sets a control's '{m.group(1)}': that cuts its binding to the model")

    # 3. No control that sets its own state on a tap: common's ModelCheckBox,
    # ModelRadioButton, ModelComboBox (or Dropdown) instead.
    if not os.path.basename(path).startswith("Model"):
        controls = "|".join(RAW_CONTROLS)
        for m in re.finditer(r"(?:^|:)\s*(" + controls + r")\s*\{", code, re.M):
            report(m.start(1), f"a plain {m.group(1)}: use common's Model* control")
        for m in re.finditer(r"ButtonGroup\.group", code):
            report(m.start(), "a ButtonGroup: Model* buttons follow their model, not a group")
    return found


def test_qml_files_are_found():
    assert len(list(_qml_files())) > 100


@pytest.mark.parametrize("path", list(_qml_files()), ids=_rel)
def test_view_holds_no_state(path):
    violations = _violations(path)
    assert not violations, "\n".join(violations)


def test_the_checks_catch_what_they_are_for(tmp_path):
    """Each kind of state a view must not keep is caught."""
    bad = tmp_path / "Bad.qml"
    bad.write_text("""
import QtQuick
import QtQuick.Controls
Item {
    id: root
    property var opData: null
    property real zEnd: 0
    // view state: a pan
    property real originX: 0
    function applyData(index, data) { opData = data; root.zEnd = data.z_end }
    function pan(dx) { originX += dx }
    function show(v) { field.value = v; field.value = Qt.binding(function() { return 0 }) }
    CheckBox { checked: root.zEnd > 0 }
    component Pick: RadioButton {}
}
""")
    rules = "\n".join(_violations(str(bad)))
    assert "applyData" in rules and "opData" in rules
    assert "sets its property 'zEnd'" in rules
    assert "'originX'" not in rules
    assert rules.count("sets a control's 'value'") == 1
    assert "a plain CheckBox" in rules and "a plain RadioButton" in rules
