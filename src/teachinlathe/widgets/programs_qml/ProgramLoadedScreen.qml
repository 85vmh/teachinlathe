import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "gcode_viewer"
import "program_loaded/running"

Item {
    id: root
    objectName: "programLoadedScreen"
    property var viewModel

    SplitView {
        anchors.fill: parent
        orientation: Qt.Horizontal

        handle: Rectangle {
            implicitWidth: 6
            implicitHeight: 6
            color: "#ffffff"
        }

        Rectangle {
            color: "#f5f5f5"
            SplitView.preferredWidth: root.width / 2
            SplitView.minimumWidth: 420

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
                        viewModel: programsToolFeedSpeedViewModel
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

        GCodeViewerPane {
            id: gcodePane
            viewModel: root.viewModel
            SplitView.preferredWidth: root.width / 2
            SplitView.minimumWidth: 420
        }
    }

    ProgramCompleteDialog {
        id: completeDialog
        objectName: "programCompleteDialog"
        dialogCenterX: gcodePane.width > 0
            ? root.width - (gcodePane.width / 2)
            : root.width * 0.75
        dialogCenterY: root.height / 2
    }
}
