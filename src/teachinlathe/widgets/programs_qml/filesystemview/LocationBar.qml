import QtQuick 2.15
import QtQuick.Layouts 1.15

// Row 1 — Horizontal location selector.
// Buttons are equally wide, mutually exclusive. A button is highlighted only
// when the browser is at the root of that location.
Rectangle {
    id: root
    property var viewModel

    readonly property var locs: viewModel ? viewModel.locations : []

    color: "#f0f0f0"
    implicitHeight: 60

    function iconForLocation(locationType) {
        if (locationType === "generated") {
            return "../../../images/generated_programs_folder.svg"
        }
        if (locationType === "usb_stick" || locationType === "mounted_media") {
            return "../../../images/usb-stick-folder.svg"
        }
        if (locationType === "syncthing") {
            return "../../../images/syncthing-folder.svg"
        }
        if (locationType === "home") {
            return "../../../images/home_folder.svg"
        }
        return "../../../images/folder-icon.svg"
    }

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
                           ? "#dbeafe"
                           : (locArea.containsMouse && modelData.isAvailable ? "#e8e8e8" : "transparent")

                    // Bottom accent line — marks the selected location
                    Rectangle {
                        anchors.bottom: parent.bottom
                        anchors.left: parent.left
                        anchors.right: parent.right
                        height: 2
                        color: modelData.isSelected ? "#1E88E5" : "transparent"
                    }

                    Column {
                        anchors.fill: parent
                        anchors.leftMargin: 4
                        anchors.rightMargin: 4
                        anchors.topMargin: 6
                        anchors.bottomMargin: 6
                        spacing: 2

                        Image {
                            width: 32
                            height: 32
                            sourceSize.width: 64
                            sourceSize.height: 64
                            anchors.horizontalCenter: parent.horizontalCenter
                            source: root.iconForLocation(modelData.type)
                            fillMode: Image.PreserveAspectFit
                            smooth: true
                            mipmap: true
                            opacity: modelData.isAvailable ? 1.0 : 0.35
                        }

                        Text {
                            width: parent.width
                            text: modelData.name
                            color: !modelData.isAvailable
                                   ? "#9e9e9e"
                                   : (modelData.isSelected ? "#1565C0" : "#4f4f4f")
                            font.pixelSize: 12
                            font.bold: modelData.isSelected
                            elide: Text.ElideRight
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
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
                    color: "#cccccc"
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
        color: "#dddddd"
    }
}
