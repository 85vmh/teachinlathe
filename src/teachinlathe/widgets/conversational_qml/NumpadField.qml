// NumpadField.qml
import QtQuick 2.15
import QtQuick.Controls 2.15

TextField {
    id: root

    // -------- Public API (unchanged) --------
    property string settingName: ""
    property var    value: null
    property var    metadata: ({})
    property var    formatter: function(v) {
        return (v === null || v === undefined || v === "") ? "" : String(v)
    }
    property var    parser: function(s) {
        var x = parseFloat(s); return isNaN(x) ? null : x
    }
    property var    validatorObject: null

    signal openRequested(var field, string settingName, var currentValue, var meta)
    signal valueCommitted(var value)

    // Guard to prevent double-open
    property bool numpadActive: false

    // Behavior – still readOnly; we open numpad on tap
    readOnly: true
    activeFocusOnPress: false
    focus: false
    cursorDelegate: null
    selectByMouse: false

    // Keep text in sync with value via the formatter
    Component.onCompleted: {
        var t = formatter(value)
        if (text !== t) text = t
    }
    onValueChanged: {
        var t = formatter(value)
        if (text !== t) text = t
    }
    onActiveFocusChanged: if (activeFocus) Qt.inputMethod.hide()

    // Visuals: blue border while focused or while the numpad popup is open
    background: Rectangle {
        radius: 2
        border.width: (root.numpadActive || root.activeFocus) ? 2 : 1
        // You can swap "#2a7bff" with any theme color you prefer
        border.color: (root.numpadActive || root.activeFocus) ? "#2a7bff" : "#cccccc"
        color: "#ffffff"
    }

    // Tap opens the numpad; we set focus and mark numpadActive immediately
    TapHandler {
        acceptedButtons: Qt.LeftButton
        enabled: !root.numpadActive
        onTapped: {
            root.forceActiveFocus()
            root.numpadActive = true      // instant highlight before Python sets it
            root.openRequested(root, root.settingName, root.value, root.metadata)
        }
        onPressedChanged: if (pressed) Qt.inputMethod.hide()
    }

    // Called from Python after the dialog returns a value
    function commit(v) {
        if (validatorObject && validatorObject.validate) {
            var s = String(v), pos = 0
            var st = validatorObject.validate(s, pos)
            // Accept QML enum (Validator.Acceptable) or raw 2
            if (st !== Validator.Acceptable && st !== 2) return false
        }
        if (value !== v) {
            value = v
        } else {
            var t = formatter(value)
            if (text !== t) text = t
        }
        valueCommitted(value)
        return true
    }

    // Convenience for Python to clear the visual focus when the popup closes
    function defocus() {
        root.focus = false
        root.numpadActive = false
    }

    // Optional: parse directly from text if someone sets it manually
    function setTextAndParse(s) {
        text = s
        var v = parser(s)
        if (v !== null) commit(v)
    }
}
