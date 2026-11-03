// NumpadButton.qml — a key of the numpad dialogs: NumpadKeypad's keys and
// SmartNumpadDialog's predefined values. Light, outlined and rounded; one
// that stands out (Clear, Input) is given its own colours.
import QtQuick
import QtQuick.Controls
import theme

Button {
    id: root

    property color keyColor: Theme.surface
    property color keyPressedColor: Theme.selection
    property color keyDisabledColor: Theme.outlineDisabled
    property color keyBorderColor: "#9aa3b0"

    font.pixelSize: 24
    // the dialog keeps the focus, so the computer's keyboard goes on typing
    // into it after a tap (and Space or Enter do not press the key tapped)
    focusPolicy: Qt.NoFocus

    background: Rectangle {
        radius: 8
        color: root.enabled ? (root.pressed ? root.keyPressedColor : root.keyColor) : root.keyDisabledColor
        border.color: root.keyBorderColor
        border.width: Theme.hairline
    }
}
