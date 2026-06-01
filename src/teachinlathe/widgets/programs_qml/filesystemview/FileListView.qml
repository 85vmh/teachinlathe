import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

// Row 3 — Sortable file list with Name / Size / Modified columns.
Item {
    id: root
    property var viewModel

    // ── Dimensions ─────────────────────────────────────────────────────────
    readonly property int rowHeight:       60
    readonly property int headerHeight:    36
    readonly property int sizeColWidth:    96
    readonly property int modifiedColWidth: 160
    readonly property int nameLeftMargin:  10
    readonly property int colRightPad:     10

    // ── Fonts ───────────────────────────────────────────────────────────────
    readonly property int headerFontSize:  16
    readonly property int itemFontSize:    14
    readonly property int metaFontSize:    14
    readonly property int iconFontSize:    14

    // ── Colors ──────────────────────────────────────────────────────────────
    readonly property color sepColor:  "#e0e0e0"
    readonly property color rowEven:   "#ffffff"
    readonly property color rowOdd:    "#f9f9f9"
    readonly property color rowHover:  "#e8f4fd"
    readonly property color rowSelect: "#dbeafe"

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ── Header ──────────────────────────────────────────────────────────
        Rectangle {
            Layout.fillWidth: true
            height: root.headerHeight
            color: "#eeeeee"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: root.nameLeftMargin
                anchors.rightMargin: 0
                spacing: 0

                // Name
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "Name" + (root.viewModel ? (root.viewModel.sortColumn === "name"
                              ? (root.viewModel.sortAscending ? " ↑" : " ↓") : "") : "")
                        color: (root.viewModel ? root.viewModel.sortColumn === "name" : false)
                               ? "#202020" : "#9e9e9e"
                        font.pixelSize: root.headerFontSize
                        font.bold: root.viewModel ? root.viewModel.sortColumn === "name" : false
                    }
                    MouseArea { anchors.fill: parent; onClicked: if (root.viewModel) root.viewModel.setSortColumn("name") }
                }

                Rectangle { width: 1; Layout.fillHeight: true; color: root.sepColor }

                // Size
                Item {
                    width: root.sizeColWidth
                    Layout.fillHeight: true
                    Text {
                        anchors.centerIn: parent
                        text: "Size" + (root.viewModel ? (root.viewModel.sortColumn === "size"
                              ? (root.viewModel.sortAscending ? " ↑" : " ↓") : "") : "")
                        color: (root.viewModel ? root.viewModel.sortColumn === "size" : false)
                               ? "#202020" : "#9e9e9e"
                        font.pixelSize: root.headerFontSize
                        font.bold: root.viewModel ? root.viewModel.sortColumn === "size" : false
                    }
                    MouseArea { anchors.fill: parent; onClicked: if (root.viewModel) root.viewModel.setSortColumn("size") }
                }

                Rectangle { width: 1; Layout.fillHeight: true; color: root.sepColor }

                // Modified
                Item {
                    width: root.modifiedColWidth
                    Layout.fillHeight: true
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.right: parent.right
                        anchors.rightMargin: root.colRightPad
                        text: "Modified" + (root.viewModel ? (root.viewModel.sortColumn === "modified"
                              ? (root.viewModel.sortAscending ? " ↑" : " ↓") : "") : "")
                        color: (root.viewModel ? root.viewModel.sortColumn === "modified" : false)
                               ? "#202020" : "#9e9e9e"
                        font.pixelSize: root.headerFontSize
                        font.bold: root.viewModel ? root.viewModel.sortColumn === "modified" : false
                    }
                    MouseArea { anchors.fill: parent; onClicked: if (root.viewModel) root.viewModel.setSortColumn("modified") }
                }
            }

            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: root.sepColor }
        }

        // ── File list ────────────────────────────────────────────────────────
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

        ListView {
            id: fileList
            anchors.fill: parent
            clip: true
            model: root.viewModel ? root.viewModel.entries : []

            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

            delegate: Item {
                width: ListView.view.width
                height: root.rowHeight

                // Alternating background
                Rectangle {
                    anchors.fill: parent
                    color: modelData.isSelected
                           ? root.rowSelect
                           : (rowArea.containsMouse
                              ? root.rowHover
                              : (index % 2 === 0 ? root.rowEven : root.rowOdd))
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: root.nameLeftMargin
                    anchors.rightMargin: 0
                    spacing: 0

                    // Name column
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 8
                        clip: true

                        // Up-arrow text for ".." entry; image icons for dirs and files
                        Text {
                            visible: modelData.isUp
                            text: "↑"
                            color: "#f59e0b"
                            font.pixelSize: root.iconFontSize
                            font.bold: true
                            Layout.alignment: Qt.AlignVCenter
                            Layout.preferredWidth: 22
                        }
                        Image {
                            visible: !modelData.isUp && modelData.isDir
                            source: "../../../images/folder-icon.svg"
                            sourceSize.width: 24; sourceSize.height: 24
                            width: 22; height: 22
                            fillMode: Image.PreserveAspectFit
                            Layout.alignment: Qt.AlignVCenter
                            Layout.preferredWidth: 22
                        }
                        Image {
                            visible: !modelData.isUp && !modelData.isDir
                            source: "../../../images/gcode.png"
                            sourceSize.width: 24; sourceSize.height: 24
                            width: 22; height: 22
                            fillMode: Image.PreserveAspectFit
                            Layout.alignment: Qt.AlignVCenter
                            Layout.preferredWidth: 22
                        }

                        Text {
                            Layout.fillWidth: true
                            text: modelData.name
                            color: modelData.isDir ? "#4f4f4f" : "#202020"
                            font.pixelSize: root.itemFontSize
                            font.family: "DejaVu Sans Mono"
                            elide: Text.ElideRight
                            verticalAlignment: Text.AlignVCenter
                        }
                    }

                    Rectangle { width: 1; height: parent.height; color: root.sepColor }

                    // Size column — centered, same width as header cell
                    Item {
                        width: root.sizeColWidth
                        height: parent.height
                        Text {
                            anchors.centerIn: parent
                            text: modelData.sizeDisplay
                            color: "#6b7280"
                            font.pixelSize: root.metaFontSize
                        }
                    }

                    Rectangle { width: 1; height: parent.height; color: root.sepColor }

                    // Modified column — right-aligned, same width as header cell
                    Item {
                        width: root.modifiedColWidth
                        height: parent.height
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.right: parent.right
                            anchors.rightMargin: root.colRightPad
                            text: modelData.modifiedDisplay
                            color: "#6b7280"
                            font.pixelSize: root.metaFontSize
                        }
                    }
                }

                // Row bottom separator
                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 1
                    color: root.sepColor
                    opacity: 0.5
                }

                MouseArea {
                    id: rowArea
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: if (root.viewModel) root.viewModel.selectEntry(modelData.relativePath)
                }
            }

            Text {
                anchors.centerIn: parent
                visible: fileList.count === 0
                text: "No files found"
                color: "#9e9e9e"
                font.pixelSize: root.itemFontSize
            }
        }

        // Top fade — appears when content is scrolled above the viewport
        Rectangle {
            anchors { left: parent.left; right: parent.right; top: parent.top }
            height: root.rowHeight
            visible: fileList.contentY > 0
            z: 1
            gradient: Gradient {
                orientation: Gradient.Vertical
                GradientStop { position: 0.0; color: "#f5f5f5" }
                GradientStop { position: 1.0; color: "transparent" }
            }
        }

        // Bottom fade — appears when content extends below the viewport
        Rectangle {
            anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
            height: root.rowHeight
            visible: fileList.contentY + fileList.height < fileList.contentHeight - 1
            z: 1
            gradient: Gradient {
                orientation: Gradient.Vertical
                GradientStop { position: 0.0; color: "transparent" }
                GradientStop { position: 1.0; color: "#f5f5f5" }
            }
        }

        }  // Item wrapper
    }
}
