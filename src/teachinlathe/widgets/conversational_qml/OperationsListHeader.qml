import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."
import theme 1.0

Rectangle {
    id: root

    property bool reorderMode: false
    property int colOpNumW: 50
    property int colGenW: 80
    property int colTypeW: 200
    property int colOptW: 80
    property int colDelW: 100
    property int headerFontSize: 14

    width: parent ? parent.width : 400
    height: Theme.buttonHeight
    radius: 0
    color: Theme.separator

    Item {
        anchors.fill: parent

        RowLayout {
            anchors.fill: parent
            spacing: 0

            Label {
                text: "              Program Operations"
                font.bold: true
                font.pixelSize: root.headerFontSize
                color: Theme.foregroundStrong
                Layout.leftMargin: 10
                Layout.minimumWidth: root.colOpNumW + root.colTypeW
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignLeft
                verticalAlignment: Text.AlignVCenter
                Layout.alignment: Qt.AlignVCenter
            }
            Divider { dividerColor: Theme.outline }

            Label {
                text: "Generate\nGCode"
                font.bold: true
                font.pixelSize: root.headerFontSize
                color: Theme.foregroundStrong
                Layout.minimumWidth: root.colGenW
                Layout.preferredWidth: root.colGenW
                Layout.maximumWidth: root.colGenW
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                wrapMode: Text.WordWrap
                maximumLineCount: 2
                Layout.alignment: Qt.AlignVCenter
            }
            Divider { dividerColor: Theme.outline }

            Label {
                text: "Optional\nBlock"
                font.bold: true
                font.pixelSize: root.headerFontSize
                color: Theme.foregroundStrong
                Layout.minimumWidth: root.colOptW
                Layout.preferredWidth: root.colOptW
                Layout.maximumWidth: root.colOptW
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                wrapMode: Text.WordWrap
                maximumLineCount: 2
                Layout.alignment: Qt.AlignVCenter
            }
            Divider { dividerColor: Theme.outline }

            Label {
                text: root.reorderMode ? "Change\nOrder" : "Delete"
                font.bold: true
                font.pixelSize: root.headerFontSize
                color: Theme.foregroundStrong
                Layout.minimumWidth: root.colDelW
                Layout.preferredWidth: root.colDelW
                Layout.maximumWidth: root.colDelW
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                Layout.alignment: Qt.AlignVCenter
            }
        }
    }
}
