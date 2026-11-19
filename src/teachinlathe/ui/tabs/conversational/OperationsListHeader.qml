import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import common

Rectangle {
    id: root

    property int colOpNumW: 50
    property int colGenW: 80
    property int colTypeW: 200
    property int colOptW: 80
    property int headerFontSize: Theme.tableHeaderFontSize

    signal addOperationRequested()

    width: parent ? parent.width : 400
    height: Theme.rowHeight
    // the card's column titles, as the conversational programs list's
    color: Theme.tableHeader
    radius: Theme.radiusSmall

    Item {
        anchors.fill: parent

        RowLayout {
            anchors.fill: parent
            spacing: 0

            Item {
                Layout.minimumWidth: root.colOpNumW + root.colTypeW
                Layout.fillWidth: true
                Layout.fillHeight: true

                Label {
                    anchors.left: parent.left
                    // the rows' margin: the title starts where their "[#NN]" does
                    anchors.leftMargin: 10
                    anchors.right: addButton.left
                    anchors.rightMargin: 8
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Program Operations"
                    font.bold: true
                    font.pixelSize: root.headerFontSize
                    color: Theme.tableHeaderForeground
                    elide: Text.ElideRight
                }

                OperationIconTextButton {
                    id: addButton
                    anchors.right: parent.right
                    anchors.rightMargin: 8
                    anchors.verticalCenter: parent.verticalCenter
                    iconSource: Images.url("add_op_icon.svg")
                    text: "Add New"
                    tint: Theme.success
                    color: Theme.surface
                    buttonHeight: Theme.buttonHeight
                    iconSize: 28
                    fontPixelSize: 15
                    // 1.3 times as wide as it needs
                    widthScale: 1.3
                    fontBold: true
                    onClicked: root.addOperationRequested()
                }
            }
            Divider { dividerColor: Theme.tableHeaderDivider }

            Label {
                text: "Generate\nGCode"
                font.bold: true
                font.pixelSize: root.headerFontSize
                color: Theme.tableHeaderForeground
                Layout.minimumWidth: root.colGenW
                Layout.preferredWidth: root.colGenW
                Layout.maximumWidth: root.colGenW
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                wrapMode: Text.WordWrap
                maximumLineCount: 2
                Layout.alignment: Qt.AlignVCenter
            }
            Divider { dividerColor: Theme.tableHeaderDivider }

            Label {
                text: "Optional\nBlock"
                font.bold: true
                font.pixelSize: root.headerFontSize
                color: Theme.tableHeaderForeground
                Layout.minimumWidth: root.colOptW
                Layout.preferredWidth: root.colOptW
                Layout.maximumWidth: root.colOptW
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                wrapMode: Text.WordWrap
                maximumLineCount: 2
                Layout.alignment: Qt.AlignVCenter
            }
        }
    }
}
