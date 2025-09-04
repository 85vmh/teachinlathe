import QtQuick 2.15
import QtQuick.Controls 2.15

TextField {
    id: root

    // Public API
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

    property bool numpadActive: false

    readOnly: true
    activeFocusOnPress: false
    focus: false
    cursorDelegate: null
    selectByMouse: false

    Component.onCompleted: {
        var t = formatter(value)
        if (text !== t) text = t
    }
    onValueChanged: {
        var t = formatter(value)
        if (text !== t) text = t
    }
    onActiveFocusChanged: if (activeFocus) Qt.inputMethod.hide()

    TapHandler {
        acceptedButtons: Qt.LeftButton
        enabled: !root.numpadActive
        onTapped: root.openRequested(root, root.settingName, root.value, root.metadata)
        onPressedChanged: if (pressed) Qt.inputMethod.hide()
    }

    function commit(v) {
        if (validatorObject && validatorObject.validate) {
            var s = String(v), pos = 0
            var st = validatorObject.validate(s, pos)
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

    function setTextAndParse(s) {
        text = s
        var v = parser(s)
        if (v !== null) commit(v)
    }
}
