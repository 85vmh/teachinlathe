// ChoicePopup.qml — a modal popup with a title that asks for one of several
// ChoiceButtons. Closed without a choice, nothing happens.
import QtQuick
import QtQuick.Controls
import theme

Popup {
    id: root
    parent: Overlay.overlay
    anchors.centerIn: parent
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    padding: Theme.spacingLarge

    property string title: ""
    default property alias body: bodyColumn.data

    background: Rectangle {
        radius: Theme.radiusXLarge
        color: Theme.surfaceSunken
        border.color: Theme.dialogBorder
        border.width: Theme.hairline
    }

    contentItem: Column {
        id: bodyColumn
        spacing: Theme.spacingLarge

        Text {
            text: root.title
            font.pixelSize: Theme.fontLarge
            font.bold: true
            color: Theme.foreground
        }
    }
}
