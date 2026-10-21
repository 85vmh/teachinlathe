import QtQuick 2.15
import QtQuick.Controls 2.15
import theme 1.0

Popup {
    id: root
    parent: Overlay.overlay
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    anchors.centerIn: parent
    contentWidth: 360
    contentHeight: contentColumn.implicitHeight
    padding: 0

    property string titleText: "Confirm"
    property string messageText: ""
    property string confirmText: "Confirm"
    property color confirmColor: Theme.danger
    property color confirmPressedColor: Theme.dangerPressed

    signal confirmed()
    signal cancelled()

    background: Rectangle {
        radius: Theme.radiusXLarge
        color: Theme.surfaceSunken
        border.color: Theme.dialogBorder
        border.width: Theme.hairline
    }

    contentItem: Column {
        id: contentColumn
        spacing: Theme.spacing
        width: root.contentWidth
        padding: 16

        Text {
            text: root.titleText
            font.pixelSize: Theme.fontLarge
            font.bold: true
            color: Theme.foreground
        }

        Text {
            width: contentColumn.width - contentColumn.padding * 2
            text: root.messageText
            font.pixelSize: Theme.fontSmall
            color: Theme.foregroundMuted
            wrapMode: Text.WordWrap
        }

        Rectangle {
            width: contentColumn.width - contentColumn.padding * 2
            height: Theme.hairline
            color: Theme.separator
        }

        Item {
            width: contentColumn.width - contentColumn.padding * 2
            height: 44

            Button {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                text: "Cancel"
                width: 100
                height: Theme.buttonHeight
                onClicked: {
                    root.cancelled()
                    root.close()
                }
            }

            Button {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                text: root.confirmText
                width: 120
                height: Theme.buttonHeight
                contentItem: Text {
                    text: parent.text
                    font: parent.font
                    color: Theme.foregroundOnAccent
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle {
                    radius: Theme.radiusSmall
                    color: parent.pressed ? root.confirmPressedColor : root.confirmColor
                }
                onClicked: {
                    root.confirmed()
                    root.close()
                }
            }
        }
    }
}
