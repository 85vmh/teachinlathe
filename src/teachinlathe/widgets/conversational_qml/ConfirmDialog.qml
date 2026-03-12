import QtQuick 2.15
import QtQuick.Controls 2.15

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
    property color confirmColor: "#C62828"
    property color confirmPressedColor: "#B71C1C"

    signal confirmed()
    signal cancelled()

    background: Rectangle {
        radius: 10
        color: "#202225"
        border.color: "#3A3D41"
        border.width: 1
    }

    contentItem: Column {
        id: contentColumn
        spacing: 12
        width: root.contentWidth
        padding: 16

        Text {
            text: root.titleText
            font.pixelSize: 18
            font.bold: true
            color: "white"
        }

        Text {
            width: contentColumn.width - contentColumn.padding * 2
            text: root.messageText
            font.pixelSize: 15
            color: "#cccccc"
            wrapMode: Text.WordWrap
        }

        Rectangle {
            width: contentColumn.width - contentColumn.padding * 2
            height: 1
            color: "#3A3D41"
        }

        Item {
            width: contentColumn.width - contentColumn.padding * 2
            height: 44

            Button {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                text: "Cancel"
                width: 100
                height: 40
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
                height: 40
                contentItem: Text {
                    text: parent.text
                    font: parent.font
                    color: "white"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle {
                    radius: 4
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
