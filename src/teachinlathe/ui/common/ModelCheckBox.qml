// ModelCheckBox.qml — a CheckBox that shows what its model says, and only
// asks for a change: ``checked`` is bound by its user to the model, a tap
// reports ``toggledTo`` the other way, and the box follows once the model
// has it. A plain CheckBox checks itself on a tap, which cuts that binding
// off - it then shows its own state, not the model's (see the "View holds
// no state" rules in CLAUDE.md). Use it, not CheckBox.
import QtQuick
import QtQuick.Controls

CheckBox {
    // asked to be checked (true) or unchecked (false)
    signal toggledTo(bool checked)

    checkable: false
    onClicked: toggledTo(!checked)
}
