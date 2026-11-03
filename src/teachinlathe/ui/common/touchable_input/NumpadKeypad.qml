// NumpadKeypad.qml — the numeric keypad of the numpad dialogs: the value
// typed so far beside ← and Clear, a divider, the digits with ± and ".", and
// Input at the bottom, which sends ``accepted`` with the value.
//
// resetTo(value, formatter) starts it on a value, selected: the first key
// typed replaces it. SmartNumpadDialog has it in its numpad mode; the
// touch-off dialog (TouchOffDialog) has it alone. Its keys have a fixed size,
// so its implicitHeight is the height it needs, shown or not.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import common

ColumnLayout {
    id: root

    property string buffer: ""
    // the value it was started on, as yet untouched: a key replaces it
    property bool   bufferSelected: false
    // "int": no decimal point
    property string valueType: ""

    // the value typed, and ← and Clear beside it, as tall
    readonly property int displayHeight: 60
    // the digit keys, ± and "."
    readonly property int keyWidth: 100
    readonly property int keyHeight: 80
    readonly property int inputHeight: 70
    readonly property int buttonSpacing: 24

    signal accepted(string value)

    spacing: buttonSpacing

    // Starts on ``value`` - as ``formatter`` writes it, if given - selected;
    // on nothing when there is none, or it is 0.
    function resetTo(value, formatter) {
        var text = ""
        if (value !== null && value !== undefined && value !== "") {
            text = formatter ? String(formatter(value)) : String(value)
            var number = Number(text)
            if (!isFinite(number) || number === 0) text = ""
        }
        root.buffer = text
        root.bufferSelected = text.length > 0
    }

    function _appendToken(token) {
        if (root.bufferSelected) {
            root.buffer = token === "." ? "0." : String(token)
            root.bufferSelected = false
            return
        }
        root.buffer += String(token)
    }

    function _backspace() {
        if (root.bufferSelected) {
            root.buffer = ""
            root.bufferSelected = false
            return
        }
        root.buffer = root.buffer.slice(0, -1)
    }

    function _clearBuffer() {
        root.buffer = ""
        root.bufferSelected = false
    }

    function _toggleSign() {
        if (root.buffer.length === 0) {
            root.buffer = "-"
            root.bufferSelected = false
            return
        }
        root.buffer = root.buffer.charAt(0) === "-"
                    ? root.buffer.slice(1)
                    : "-" + root.buffer
    }

    // a key with an icon - and its text after it, if it has one - the two
    // together in the middle of the key
    component IconKey: NumpadButton {
        id: iconKey
        property url iconSource
        // px, as drawn: the icons' marks as tall as each other
        property int iconHeight: 24
        // its text's, the colour its icon is drawn in
        property color textColor: Theme.foreground
        contentItem: Item {
            Row {
                anchors.centerIn: parent
                spacing: 10
                // greyed out with the key
                opacity: iconKey.enabled ? 1 : 0.35

                Image {
                    anchors.verticalCenter: parent.verticalCenter
                    source: iconKey.iconSource
                    sourceSize.height: iconKey.iconHeight
                    fillMode: Image.PreserveAspectFit
                }
                Text {
                    visible: iconKey.text !== ""
                    anchors.verticalCenter: parent.verticalCenter
                    text: iconKey.text
                    font: iconKey.font
                    color: iconKey.textColor
                }
            }
        }
    }

    // a key of the digits' grid
    component GridKey: NumpadButton {
        width: root.keyWidth
        height: root.keyHeight
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: root.buttonSpacing

        Label {
            Layout.fillWidth: true
            Layout.preferredHeight: root.displayHeight
            text: root.buffer
            horizontalAlignment: Text.AlignRight
            verticalAlignment: Text.AlignVCenter
            padding: 10
            font.pixelSize: 24
            font.family: "Noto Sans Mono"
            color: root.bufferSelected ? Theme.surface : "#141414"
            background: Rectangle {
                color: root.bufferSelected ? Theme.focusBorder : Theme.surfaceSunken
                border.color: root.bufferSelected ? "#1d4ed8" : "#77767b"
                radius: 5
            }
        }
        IconKey {
            Layout.preferredWidth: 60
            Layout.preferredHeight: root.displayHeight
            iconSource: Images.url("numpad_backspace.svg")
            // its arrow fills 38 of the icon's 52 px
            iconHeight: 32
            onClicked: root._backspace()
        }
        IconKey {
            Layout.preferredWidth: 80
            Layout.preferredHeight: root.displayHeight
            iconSource: Images.url("numpad_clear.svg")
            // red: it throws the value away
            keyColor: Theme.danger
            keyPressedColor: Theme.dangerPressed
            keyBorderColor: Theme.dangerPressed
            onClicked: root._clearBuffer()
        }
    }

    // between the value and the digits
    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 1
        color: Theme.outline
    }

    // a Grid, not a GridLayout: its keys all as wide, whatever their text;
    // in the middle of the keypad
    Grid {
        Layout.alignment: Qt.AlignHCenter
        Layout.preferredWidth: 3 * root.keyWidth + 2 * root.buttonSpacing
        Layout.preferredHeight: 4 * root.keyHeight + 3 * root.buttonSpacing
        columns: 3
        columnSpacing: root.buttonSpacing
        rowSpacing: root.buttonSpacing

        Repeater {
            model: ["7", "8", "9", "4", "5", "6", "1", "2", "3"]
            delegate: GridKey {
                text: modelData
                onClicked: root._appendToken(modelData)
            }
        }

        GridKey {
            text: "±"
            onClicked: root._toggleSign()
        }
        GridKey {
            text: "0"
            onClicked: root._appendToken("0")
        }
        GridKey {
            text: "."
            // An int setting takes no decimals.
            enabled: root.valueType !== "int"
                     && (root.bufferSelected || root.buffer.indexOf(".") === -1)
            onClicked: root._appendToken(".")
        }
    }

    Item {
        Layout.fillHeight: true
    }

    IconKey {
        Layout.fillWidth: true
        Layout.preferredHeight: root.inputHeight
        text: "Input"
        iconSource: Images.url("numpad_input.svg")
        iconHeight: 32
        // green: the main action, as Cycle Start is
        keyColor: Theme.primary
        keyPressedColor: Theme.primaryPressed
        keyDisabledColor: Theme.primaryDisabled
        keyBorderColor: Theme.primaryPressed
        textColor: "white"
        enabled: root.buffer.length > 0 && root.buffer !== "-" && root.buffer !== "."
        onClicked: root.accepted(root.buffer)
    }
}
