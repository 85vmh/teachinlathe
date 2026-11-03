// NumpadPopup.qml — the frame the numpad dialogs share (SmartNumpadDialog,
// the touch-off dialog): modal, in the middle of the window, on the sunken
// ground with its outline, and the field it edits - ``targetField``, a
// NumpadField or one like it - let go when it closes, its defocus() called.
import QtQuick
import QtQuick.Controls
import theme

Popup {
    id: root

    property var targetField: null

    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    parent: Overlay.overlay
    x: parent ? (parent.width  - width)  / 2 : 0
    y: parent ? (parent.height - height) / 2 : 0
    padding: 24

    background: Rectangle {
        color: Theme.surfaceSunken
        border.color: "#9aa3b0"
        border.width: Theme.hairline
        radius: Theme.radiusLarge
    }

    onClosed: {
        if (targetField && targetField.defocus) targetField.defocus()
        targetField = null
    }
}
