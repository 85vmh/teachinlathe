// ModelRadioButton.qml — a RadioButton that shows what its model says, and
// only asks for a change: ``checked`` is bound by its user to the model
// (``checked: model.choice === "a"``), a tap on one not checked reports
// ``chosen``, and the buttons follow once the model has it. A plain
// RadioButton - or a ButtonGroup - checks and unchecks the buttons itself,
// which cuts those bindings off (see the "View holds no state" rules in
// CLAUDE.md). Use it, without a ButtonGroup, not RadioButton.
import QtQuick
import QtQuick.Controls

RadioButton {
    // asked to be the one checked
    signal chosen()

    checkable: false
    onClicked: if (!checked) chosen()
}
