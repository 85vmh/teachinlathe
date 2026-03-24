import QtQuick 2.15
import QtQuick.Layouts 1.15

// Row 1 — Horizontal location selector.
// Buttons are equally wide, mutually exclusive. A button is highlighted only
// when the browser is at the root of that location.
Rectangle {
    id: root
    property var viewModel

    readonly property var locs: viewModel ? viewModel.locations : []

    color: "#1e1e1e"
    implicitHeight: 42

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Repeater {
            model: root.locs

            delegate: Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                // Button background
                Rectangle {
                    anchors.fill: parent
                    color: modelData.isSelected
                           ? "#1e3a5f"
                           : (locArea.containsMouse && modelData.isAvailable ? "#2d2d2e" : "transparent")

                    // Bottom accent line — marks the selected location
                    Rectangle {
                        anchors.bottom: parent.bottom
                        anchors.left: parent.left
                        anchors.right: parent.right
                        height: 2
                        color: modelData.isSelected ? "#3794ff" : "transparent"
                    }

                    Text {
                        anchors.fill: parent
                        anchors.leftMargin: 4
                        anchors.rightMargin: 4
                        text: modelData.name
                        color: !modelData.isAvailable
                               ? "#555555"
                               : (modelData.isSelected ? "#e8e8e8" : "#b0b0b0")
                        font.pixelSize: 12
                        font.bold: modelData.isSelected
                        elide: Text.ElideRight
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }

                    MouseArea {
                        id: locArea
                        anchors.fill: parent
                        hoverEnabled: true
                        enabled: modelData.isAvailable
                        onClicked: root.viewModel.selectLocation(modelData.name)
                    }
                }

                // Vertical divider between buttons (not after the last one)
                Rectangle {
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.topMargin: 8
                    anchors.bottomMargin: 8
                    width: 1
                    color: "#383838"
                    visible: index < root.locs.length - 1
                }
            }
        }
    }

    // Bottom border
    Rectangle {
        anchors.bottom: parent.bottom
        width: parent.width
        height: 1
        color: "#2e2e2e"
    }
}
