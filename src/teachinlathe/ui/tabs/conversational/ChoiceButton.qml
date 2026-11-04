// ChoiceButton.qml — one of the answers of a ChoicePopup.
import QtQuick
import QtQuick.Controls
import theme

Button {
    id: root

    background: Rectangle {
        radius: Theme.radiusLarge
        color: root.pressed ? Theme.accentSoft : Theme.surface
        border.color: root.pressed ? Theme.accentBorder : Theme.dialogBorder
        border.width: Theme.hairline
    }
}
