import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme

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

        // always running: the Basic style fades it in and out with running,
        // and a fade back in begun as the popup opens again is lost - from
        // the second time on it stayed invisible. Closed, it is not drawn.
        BusyIndicator {
            Layout.alignment: Qt.AlignHCenter
            running: true
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
