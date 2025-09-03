// NumpadField.qml
import QtQuick 2.15
import QtQuick.Controls 2.15

// A TextField-lookalike that never opens the OSK and delegates input to a custom numpad.
TextField {
    id: root

    // Public API
    property string settingName: ""          // used by SmartNumPadDialog to pick context
    property var    value: null              // bound numeric value
    property var    metadata: ({})           // extra context if needed

    // Formatting/parsing hooks
    property var formatter: function(v) {
        return (v === null || v === undefined || v === "") ? "" : String(v)
    }
    property var parser: function(s) {
        var x = parseFloat(s); return isNaN(x) ? null : x
    }
    property var validatorObject: null       // optional: e.g. DoubleValidator{...}

    signal openRequested(var field, string settingName, var currentValue, var meta)
    signal valueCommitted(var value)         // emitted after commit()

    // Look & behavior
    readOnly: true                   // critical: blocks native editing/OSK
    activeFocusOnPress: false
    focus: false
    cursorDelegate: null
    selectByMouse: false
    text: formatter(value)

    // If someone focuses it programmatically, still hide OSK
    onActiveFocusChanged: if (activeFocus) Qt.inputMethod.hide()

    // If Python sets 'text' directly (e.g. setSelectedValue), keep 'value' in sync
    onTextChanged: {
        var v = parser(text)
        if (v !== null && v !== value) value = v
    }

    // Tap opens the custom numpad via parent
    TapHandler {
        acceptedButtons: Qt.LeftButton
        onTapped: root.openRequested(root, root.settingName, root.value, root.metadata)
        onPressedChanged: if (pressed) Qt.inputMethod.hide()
    }

    // Programmatic updates from numpad/Python
    function commit(v) {
        // optional validation
        if (validatorObject && validatorObject.validate) {
            var s = String(v), pos = 0
            var st = validatorObject.validate(s, pos)
            // Qt5: Acceptable === 2 in some bindings; keep both checks
            if (st !== Validator.Acceptable && st !== 2) return false
        }
        value = v
        text  = formatter(v)   // keep UI text synced
        valueCommitted(value)
        return true
    }
}
