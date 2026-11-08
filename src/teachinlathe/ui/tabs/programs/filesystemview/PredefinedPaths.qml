import QtQuick
import QtQuick.Layouts
import theme
import common

// A card over the file list: the predefined locations (Generated Programs,
// USB Stick, SyncThing, Home), as tabs equally wide - one highlighted only
// when the browser is at the root of that location - each an icon and its name
// on two lines; under them, in Home alone, the path in it (NavigationBar: up,
// the breadcrumb, the Folders / NGC filters). Every other location is the root
// of a folder of files, with no path to show.
Card {
    id: root
    required property var viewModel

    readonly property var locs: viewModel.locations
    // an icon and two lines of text beside it
    readonly property int tabsHeight: Theme.inputHeight
    readonly property int iconSize: 28
    readonly property int pathHeight: 38
    readonly property bool pathShown: viewModel.isInHome

    implicitHeight: 2 * Theme.cardInset + tabsHeight + (pathShown ? Theme.hairline + pathHeight : 0)

    // a location's name on two lines, broken at its last space:
    // "Generated Programs" over two, "Home" on one
    function twoLines(name) {
        var at = name.lastIndexOf(" ")
        return at > 0 ? name.substring(0, at) + "\n" + name.substring(at + 1) : name
    }

    function iconForLocation(locationType) {
        if (locationType === "generated") {
            return Images.url("generated_programs_folder.svg")
        }
        if (locationType === "usb_stick" || locationType === "mounted_media") {
            return Images.url("usb-stick-folder.svg")
        }
        if (locationType === "syncthing") {
            return Images.url("syncthing-folder.svg")
        }
        if (locationType === "home") {
            return Images.url("home_folder.svg")
        }
        return Images.url("folder-icon.svg")
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.cardInset
        spacing: 0

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: root.tabsHeight
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
                               ? Theme.selection
                               : (locArea.containsMouse && modelData.isAvailable ? Theme.outlineDisabled : "transparent")

                        // Bottom accent line — marks the selected location
                        Rectangle {
                            anchors.bottom: parent.bottom
                            anchors.left: parent.left
                            anchors.right: parent.right
                            height: 2
                            color: modelData.isSelected ? Theme.accent : "transparent"
                        }

                        // the icon and the name beside it, centred in the tab
                        Row {
                            anchors.centerIn: parent
                            spacing: Theme.spacingSmall

                            Image {
                                width: root.iconSize
                                height: root.iconSize
                                sourceSize.width: 64
                                sourceSize.height: 64
                                anchors.verticalCenter: parent.verticalCenter
                                source: root.iconForLocation(modelData.type)
                                fillMode: Image.PreserveAspectFit
                                smooth: true
                                mipmap: true
                                opacity: modelData.isAvailable ? 1.0 : Theme.disabledOpacity
                            }

                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: root.twoLines(modelData.name)
                                color: !modelData.isAvailable
                                       ? Theme.outlineEmphasis
                                       : (modelData.isSelected ? Theme.accentStrong : Theme.foregroundMuted)
                                font.pixelSize: Theme.fontSmall
                                font.bold: modelData.isSelected
                                lineHeight: 0.95
                                horizontalAlignment: Text.AlignLeft
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
                        width: Theme.hairline
                        color: Theme.outline
                        visible: index < root.locs.length - 1
                    }
                }
            }
        }

        Rectangle {
            visible: root.pathShown
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.hairline
            color: Theme.outlineDisabled
        }

        NavigationBar {
            visible: root.pathShown
            viewModel: root.viewModel
            Layout.fillWidth: true
            Layout.preferredHeight: root.pathHeight
        }
    }
}
