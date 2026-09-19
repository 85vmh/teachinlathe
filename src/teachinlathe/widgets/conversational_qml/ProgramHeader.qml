import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import theme 1.0

Rectangle {
    id: root

    property bool selected: false

    signal clicked()

    width: parent ? parent.width : 400
    height: Theme.rowHeight
    radius: 0
    color: selected ? Theme.selection : Theme.outlineDisabled
    border.width: selected ? 2 : 0
    border.color: selected ? Theme.accent : "transparent"

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Label {
            text: "              Program Header"
            font.pixelSize: Theme.fontSmall
            font.bold: true
            Layout.leftMargin: 10
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignLeft
            Layout.alignment: Qt.AlignVCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
    }

    TapHandler {
        onTapped: root.clicked()
    }
}
