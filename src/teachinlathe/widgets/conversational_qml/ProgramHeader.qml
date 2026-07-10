import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property bool selected: false

    signal clicked()

    width: parent ? parent.width : 400
    height: 72
    radius: 0
    color: selected ? "#dbeafe" : "#e5e5e5"
    border.width: selected ? 2 : 0
    border.color: selected ? "#3b82f6" : "transparent"

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Label {
            text: "              Program Header"
            font.pixelSize: 14
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
