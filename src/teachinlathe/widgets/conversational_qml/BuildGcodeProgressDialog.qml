import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import theme 1.0

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
        radius: Theme.radiusXLarge
        color: Theme.surfaceSunken
        border.color: Theme.dialogBorder
        border.width: Theme.hairline
    }

    contentItem: ColumnLayout {
        id: contentColumn
        width: root.contentWidth
        spacing: Theme.spacingLarge

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
            color: Theme.foreground
            font.pixelSize: Theme.fontLarge
            font.bold: true
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }

        Text {
            Layout.fillWidth: true
            Layout.leftMargin: 24
            Layout.rightMargin: 24
            text: "Please wait while the program file is built."
            color: Theme.outline
            font.pixelSize: Theme.fontSmall
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
