import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import theme 1.0
import "../../../conversational/ui"
import common 1.0

// Row 3 — Sortable file list with Name / Size / Modified columns. A file
// swiped left shows Delete (see SwipeRow).
Item {
    id: root
    property var viewModel
    // Swipe to delete. Off where the list only picks a file.
    property bool showActions: true

    // ── Dimensions ─────────────────────────────────────────────────────────
    readonly property int rowHeight:       72
    readonly property int headerHeight:    40
    readonly property int sizeColWidth:    96
    readonly property int modifiedColWidth: 150
    // As wide as the operation list's Delete
    readonly property int deleteWidth:     100
    readonly property int nameLeftMargin:  10
    readonly property int rowRightMargin:  18

    // ── Fonts ───────────────────────────────────────────────────────────────
    readonly property int headerFontSize:  16
    readonly property int itemFontSize:    16
    readonly property int metaFontSize:    16
    readonly property int iconFontSize:    14

    // ── Colors ──────────────────────────────────────────────────────────────
    readonly property color sepColor:  Theme.outline
    readonly property color headerColor: Theme.separator
    readonly property color headerSepColor: Theme.outline
    readonly property color headerTextColor: Theme.surfaceInverse
    readonly property color rowEven:   Theme.surfaceSunken
    readonly property color rowOdd:    Theme.outlineDisabled
    readonly property color rowHover:  Theme.selection
    readonly property color rowSelect: Theme.selection

    // The file row swiped open to its Delete
    property int openSwipeIndex: -1

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ── Header ──────────────────────────────────────────────────────────
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: root.headerHeight
            color: root.headerColor
            radius: Theme.radiusSmall

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: root.nameLeftMargin
                anchors.rightMargin: root.rowRightMargin
                spacing: 0

                // Name
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Text {
                        anchors.centerIn: parent
                        text: "Name" + (root.viewModel ? (root.viewModel.sortColumn === "name"
                              ? (root.viewModel.sortAscending ? " ↑" : " ↓") : "") : "")
                        color: root.headerTextColor
                        font.pixelSize: root.headerFontSize
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    MouseArea { anchors.fill: parent; onClicked: if (root.viewModel) root.viewModel.setSortColumn("name") }
                }

                Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: root.headerSepColor }

                // Size
                Item {
                    Layout.minimumWidth: root.sizeColWidth
                    Layout.preferredWidth: root.sizeColWidth
                    Layout.maximumWidth: root.sizeColWidth
                    Layout.fillHeight: true
                    Text {
                        anchors.centerIn: parent
                        text: "Size" + (root.viewModel ? (root.viewModel.sortColumn === "size"
                              ? (root.viewModel.sortAscending ? " ↑" : " ↓") : "") : "")
                        color: root.headerTextColor
                        font.pixelSize: root.headerFontSize
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    MouseArea { anchors.fill: parent; onClicked: if (root.viewModel) root.viewModel.setSortColumn("size") }
                }

                Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: root.headerSepColor }

                // Modified
                Item {
                    Layout.minimumWidth: root.modifiedColWidth
                    Layout.preferredWidth: root.modifiedColWidth
                    Layout.maximumWidth: root.modifiedColWidth
                    Layout.fillHeight: true
                    Text {
                        anchors.centerIn: parent
                        text: "Modified" + (root.viewModel ? (root.viewModel.sortColumn === "modified"
                              ? (root.viewModel.sortAscending ? " ↑" : " ↓") : "") : "")
                        color: root.headerTextColor
                        font.pixelSize: root.headerFontSize
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    MouseArea { anchors.fill: parent; onClicked: if (root.viewModel) root.viewModel.setSortColumn("modified") }
                }
            }

            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: root.headerSepColor }
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
            onModelChanged: root.openSwipeIndex = -1
            onMovementStarted: root.openSwipeIndex = -1

            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

            delegate: SwipeRow {
                id: fileRow
                width: ListView.view.width
                height: root.rowHeight
                readonly property bool hasFolderCount: modelData.folderFileCountDisplay !== undefined
                                                       && modelData.folderFileCountDisplay !== ""

                // Files only: not folders, and not on mounted media, which
                // this list never deletes from
                actionWidth: root.deleteWidth
                duplicateEnabled: false
                deleteEnabled: root.showActions && !modelData.isUp && !modelData.isDir
                               && !(root.viewModel && root.viewModel.isInMountedMedia)
                swipeSide: root.openSwipeIndex === index ? 1 : 0
                onSwipeOpened: root.openSwipeIndex = index
                onSwipeClosed: if (root.openSwipeIndex === index) root.openSwipeIndex = -1
                onDeleteRequested: {
                    root.openSwipeIndex = -1
                    if (root.viewModel)
                        root.viewModel.deleteEntry(modelData.relativePath)
                }

                contentColor: modelData.isSelected
                              ? root.rowSelect
                              : (rowArea.containsMouse
                                 ? root.rowHover
                                 : (index % 2 === 0 ? root.rowEven : root.rowOdd))
                contentBorderWidth: modelData.isSelected ? 2 : 0
                contentBorderColor: modelData.isSelected ? Theme.accent : "transparent"

                MouseArea {
                    id: rowArea
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: if (root.viewModel) root.viewModel.selectEntry(modelData.relativePath)
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: root.nameLeftMargin
                    anchors.rightMargin: root.rowRightMargin
                    spacing: 0

                    // Name column: its text stays put while the row slides
                    // left over Delete
                    RowLayout {
                        Layout.leftMargin: Math.max(0, fileRow.swipeOffset)
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: Theme.spacingSmall
                        clip: true

                        // Up-arrow text for ".." entry; image icons for dirs and files
                        Text {
                            visible: modelData.isUp
                            text: "↑"
                            color: Theme.warning
                            font.pixelSize: root.iconFontSize
                            font.bold: true
                            Layout.alignment: Qt.AlignVCenter
                            Layout.preferredWidth: 22
                        }
                        Image {
                            visible: !modelData.isUp && modelData.isDir
                            source: Images.url("folder-icon.svg")
                            sourceSize.width: 24; sourceSize.height: 24
                            width: 22; height: 22
                            fillMode: Image.PreserveAspectFit
                            Layout.alignment: Qt.AlignVCenter
                            Layout.preferredWidth: 22
                        }
                        Image {
                            visible: !modelData.isUp && !modelData.isDir
                            source: Images.url("gcode.png")
                            sourceSize.width: 24; sourceSize.height: 24
                            width: 22; height: 22
                            fillMode: Image.PreserveAspectFit
                            Layout.alignment: Qt.AlignVCenter
                            Layout.preferredWidth: 22
                        }

                        Text {
                            Layout.fillWidth: !hasFolderCount
                            Layout.preferredWidth: hasFolderCount ? Math.min(implicitWidth, parent.width * 0.58) : -1
                            text: modelData.name
                            color: modelData.isDir ? Theme.foregroundMuted : Theme.surfaceInverse
                            font.pixelSize: root.itemFontSize
                            font.family: "DejaVu Sans Mono"
                            elide: Text.ElideRight
                            verticalAlignment: Text.AlignVCenter
                        }

                        Text {
                            Layout.fillWidth: true
                            visible: hasFolderCount
                            text: modelData.folderFileCountDisplay || ""
                            color: "#6b7280"
                            font.pixelSize: root.itemFontSize
                            font.family: "DejaVu Sans Mono"
                            elide: Text.ElideRight
                            verticalAlignment: Text.AlignVCenter
                        }
                    }

                    Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: root.sepColor }

                    // Size column — centered, same width as header cell
                    Item {
                        Layout.minimumWidth: root.sizeColWidth
                        Layout.preferredWidth: root.sizeColWidth
                        Layout.maximumWidth: root.sizeColWidth
                        Layout.fillHeight: true
                        Text {
                            anchors.centerIn: parent
                            text: modelData.sizeDisplay
                            color: "#6b7280"
                            font.pixelSize: root.metaFontSize
                        }
                    }

                    Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: root.sepColor }

                    // Modified column — centred, as the header and the
                    // conversational programs' dates
                    Item {
                        Layout.minimumWidth: root.modifiedColWidth
                        Layout.preferredWidth: root.modifiedColWidth
                        Layout.maximumWidth: root.modifiedColWidth
                        Layout.fillHeight: true
                        Text {
                            anchors.centerIn: parent
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
                    height: Theme.hairline
                    color: root.sepColor
                    opacity: 0.5
                }
            }

            Text {
                anchors.centerIn: parent
                visible: fileList.count === 0
                text: "No files found"
                color: Theme.outlineEmphasis
                font.pixelSize: root.itemFontSize
            }
        }

        ScrollFades {
            anchors.fill: parent
            flickable: fileList
            fadeHeight: root.rowHeight
        }

        }  // Item wrapper
    }

    SwipeDismissArea {
        openRow: root.openSwipeIndex >= 0 ? fileList.itemAtIndex(root.openSwipeIndex) : null
        onDismissed: root.openSwipeIndex = -1
    }
}
