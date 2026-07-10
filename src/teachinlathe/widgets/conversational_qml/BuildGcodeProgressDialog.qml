import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Popup {
    id: root
    parent: Overlay.overlay
    modal: true
    focus: true
    closePolicy: Popup.NoAutoClose
    anchors.centerIn: parent
    contentWidth: 360
    contentHeight: contentColumn.implicitHeight
    padding: 0

    background: Rectangle {
        radius: 10
        color: "#202225"
        border.color: "#3A3D41"
        border.width: 1
    }

    contentItem: ColumnLayout {
        id: contentColumn
        width: root.contentWidth
        spacing: 16

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 20
        }

        BusyIndicator {
            Layout.alignment: Qt.AlignHCenter
            running: root.visible
        }

        Text {
            Layout.fillWidth: true
            Layout.leftMargin: 24
            Layout.rightMargin: 24
            text: "Generating G-Code..."
            color: "white"
            font.pixelSize: 18
            font.bold: true
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }

        Text {
            Layout.fillWidth: true
            Layout.leftMargin: 24
            Layout.rightMargin: 24
            text: "Please wait while the program file is built."
            color: "#cccccc"
            font.pixelSize: 14
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 20
        }
    }
}
