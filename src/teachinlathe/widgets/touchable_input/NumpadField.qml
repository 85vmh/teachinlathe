// NumpadField.qml
import QtQuick 2.15
import QtQuick.Controls 2.15

TextField {
    id: root

    // -------- Public API --------
    property string settingName: ""
    // Optional dialog title override. If set, the SmartNumpad dialog uses this
    // instead of the description coming from numpad_settings.json.
    property string description: ""
    property var    value: null
    property var    metadata: ({})
    property var    formatter: function(v) {
        return (v === null || v === undefined || v === "") ? "" : String(v)
    }
    property var    parser: function(s) {
        var x = parseFloat(s); return isNaN(x) ? null : x
    }
    property var    validatorObject: null

    // control vizual reutilizabil
    property int    hAlign: Text.AlignRight     // aliniere text
    property int    fontPixelSize: 20           // mărimea textului din input
    property string placeholder: ""             // dacă vrei placeholder

    signal openRequested(Item field, string settingName, var currentValue, var meta)
    signal valueCommitted(var value)

    // Guard
    property bool numpadActive: false

    // Comportament
    readOnly: true
    activeFocusOnPress: false
    focus: false
    cursorDelegate: null
    selectByMouse: false

    // Vizual
    implicitHeight: 48
    horizontalAlignment: hAlign
    verticalAlignment: Text.AlignVCenter
    font.pixelSize: fontPixelSize
    placeholderText: placeholder

    // Sync text <-> value
    Component.onCompleted: {
        var t = formatter(value)
        if (text !== t) text = t
    }
    onValueChanged: {
        var t = formatter(value)
        if (text !== t) text = t
    }
    onActiveFocusChanged: if (activeFocus) Qt.inputMethod.hide()

    // Background
    background: Rectangle {
        radius: 2
        border.width: (root.numpadActive || root.activeFocus) ? 2 : 1
        border.color: (root.numpadActive || root.activeFocus) ? "#2a7bff" : "#cccccc"
        color: "#ffffff"
    }

    // Open numpad
    TapHandler {
        acceptedButtons: Qt.LeftButton
        enabled: !root.numpadActive
        onTapped: {
            root.forceActiveFocus()
            root.numpadActive = true
            var meta = Object.assign({}, root.metadata, {
                fieldFontPx: root.fontPixelSize,
                align: root.hAlign,
                description: root.description
            })
            root.openRequested(root, root.settingName, root.value, meta)
        }
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

    function defocus() {
        root.focus = false
        root.numpadActive = false
    }

    function setTextAndParse(s) {
        text = s
        var v = parser(s)
        if (v !== null) commit(v)
    }
}
