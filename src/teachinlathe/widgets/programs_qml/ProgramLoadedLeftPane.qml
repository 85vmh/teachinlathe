import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    property var viewModel
    color: "#f5f5f5"

    ColumnLayout {
        anchors.fill: parent
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: false
            Layout.preferredHeight: 220
            spacing: 8

            ProgramsDro {
                Layout.fillHeight: true
                Layout.preferredWidth: 600
                viewModel: root.viewModel
            }

            ProgramsToolFeedSpeed {
                Layout.fillHeight: true
                Layout.fillWidth: true
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
