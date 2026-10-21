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
    property int headerFontSize: 14
    // the operations' rows' font, whose "[#NN]    " the title is indented by,
    // so it starts where the operation names do
    property int itemFontSize: 16

    signal addOperationRequested()

    TextMetrics { id: orderPrefix; font.pixelSize: root.itemFontSize; text: "[#00]    " }

    width: parent ? parent.width : 400
    height: Theme.rowHeight
    radius: 0
    color: Theme.hover
    border.width: 2
    border.color: Theme.dialogBorder

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
                    anchors.leftMargin: 10 + orderPrefix.advanceWidth
                    anchors.right: addButton.left
                    anchors.rightMargin: 8
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Program Operations"
                    font.bold: true
                    font.pixelSize: root.headerFontSize
                    color: Theme.foregroundStrong
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
                    onClicked: root.addOperationRequested()
                }
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
        }
    }
}
