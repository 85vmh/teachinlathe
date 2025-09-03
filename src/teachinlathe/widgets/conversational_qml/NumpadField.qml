// NumpadField.qml
import QtQuick 2.15
import QtQuick.Controls 2.15

TextField {
    id: root

    // Public API
    property string settingName: ""          // used by SmartNumPadDialog
    property var    value: null              // numeric value bound from outside
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

    // Appearance / behavior: never open OSK
    readOnly: true
    activeFocusOnPress: false
    focus: false
    cursorDelegate: null
    selectByMouse: false

    // IMPORTANT: do NOT bind text directly to formatter(value) to avoid loops.
    // Keep text as a plain property and drive it from value changes.
    // Initialize once:
    Component.onCompleted: {
        var t = formatter(value)
        if (text !== t) text = t
    }

    // Single source of truth: when value changes, update text if needed
    onValueChanged: {
        var t = formatter(value)
        if (text !== t) text = t
    }

    // We no longer mirror text -> value (readOnly + custom numpad handles input).
    // Removing onTextChanged avoids binding loops when someone sets text.

    // Hide OSK if somehow focused
    onActiveFocusChanged: if (activeFocus) Qt.inputMethod.hide()

    // Tap opens custom numpad
    TapHandler {
        acceptedButtons: Qt.LeftButton
        onTapped: root.openRequested(root, root.settingName, root.value, root.metadata)
        onPressedChanged: if (pressed) Qt.inputMethod.hide()
    }

    // Called by numpad / Python to commit a new value
    function commit(v) {
        // optional validation
        if (validatorObject && validatorObject.validate) {
            var s = String(v), pos = 0
            var st = validatorObject.validate(s, pos)
            if (st !== Validator.Acceptable && st !== 2) return false
        }
        if (value !== v) {
            value = v; // onValueChanged will refresh text
        } else {
            // same value, still ensure text matches formatter
            var t = formatter(value)
            if (text !== t) text = t
        }
        valueCommitted(value)
        return true
    }

    // Optional helper if you EVER need to set text first (not recommended):
    function setTextAndParse(s) {
        text = s
        var v = parser(s)
        if (v !== null) commit(v)
    }
}
