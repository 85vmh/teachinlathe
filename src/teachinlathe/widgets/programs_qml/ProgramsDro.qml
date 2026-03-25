import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    property var viewModel
    color: "#eef2f7"
    border.color: "#cfd7e3"
    border.width: 1

    Rectangle {
        anchors.fill: parent
        anchors.margins: 16
        radius: 12
        color: "#ffffff"
        border.color: "#d6dce7"
        border.width: 1

        Column {
            anchors.centerIn: parent
            spacing: 8

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Programs DRO"
                color: "#1e2430"
                font.pixelSize: 20
                font.bold: true
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Placeholder"
                color: "#5a6473"
                font.pixelSize: 13
            }
        }
    }
}
