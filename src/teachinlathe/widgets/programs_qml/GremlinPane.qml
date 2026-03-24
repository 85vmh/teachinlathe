import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    property var viewModel
    color: "#f5f5f5"

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 58
            color: "#f0f0f0"
            border.color: "#cccccc"
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                spacing: 8

                Text {
                    text: "Gremlin View"
                    color: "#202020"
                    font.pixelSize: 16
                    font.bold: true
                }

                Item { Layout.fillWidth: true }

                ProgramButton {
                    text: "Zoom In"
                    onClicked: viewModel.zoomGremlinIn()
                }

                ProgramButton {
                    text: "Zoom Out"
                    onClicked: viewModel.zoomGremlinOut()
                }

                ProgramButton {
                    text: "Clear Plot"
                    accentColor: "#7a2d2d"
                    borderColor: "#d16969"
                    onClicked: viewModel.clearGremlinPlot()
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#0f0f0f"
            border.color: "#252525"
            border.width: 1

            Item {
                id: viewport
                objectName: "gremlinViewport"
                anchors.fill: parent
            }
        }
    }
}
