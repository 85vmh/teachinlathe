import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import common

// Row 2 — the breadcrumb + the filter button, as tall
// as the location tabs above it, every part of it a finger wide. The filter
// button opens, under it, what is shown: the matching files alone (DXF Files,
// NGC Files - fixed where the browser does not let it change) and the folders.
// Its icon has a minus when every filter is on, a plus while one can be.
Item {
    id: root
    required property var viewModel

    implicitHeight: Theme.inputHeight
    // between the bar's parts, and round them (the Theme has no 4)
    readonly property int gap: 4

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: root.gap
        anchors.rightMargin: root.gap
        spacing: root.gap

        // ---- Breadcrumb: scrolls when too long, at its last segment as the
        // path changes (up is its segments, and the list's Up row) ----
        Flickable {
            id: breadcrumbFlick
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: breadcrumbRow.implicitWidth
            contentHeight: height
            flickableDirection: Flickable.HorizontalFlick
            boundsBehavior: Flickable.StopAtBounds
            interactive: contentWidth > width

            // view state: scrolled to the last segment - the folder shown -
            // whenever the path or the bar's width changes
            function showLast() { contentX = Math.max(0, contentWidth - width) }
            onContentWidthChanged: showLast()
            onWidthChanged: showLast()

            Row {
                id: breadcrumbRow
                height: parent.height
                spacing: 0

                Repeater {
                    id: crumbRepeater
                    model: root.viewModel.breadcrumbs

                    delegate: Row {
                        readonly property bool isLast: index === crumbRepeater.count - 1
                        height: breadcrumbRow.height
                        spacing: 0

                        Text {
                            visible: index > 0
                            anchors.verticalCenter: parent.verticalCenter
                            text: "/"
                            color: Theme.outlineEmphasis
                            font.pixelSize: Theme.fontBody
                        }

                        // the whole bar's height and some to each side: a finger's target
                        Rectangle {
                            height: parent.height
                            width: Math.max(segText.implicitWidth + 2 * Theme.spacing, Theme.inputHeight)
                            color: segArea.pressed ? Theme.outlineDisabled : "transparent"
                            radius: Theme.radiusSmall

                            Text {
                                id: segText
                                anchors.centerIn: parent
                                text: modelData.name
                                color: isLast ? Theme.surfaceInverse : Theme.foregroundMuted
                                font.pixelSize: Theme.fontBody
                                font.bold: isLast
                            }

                            MouseArea {
                                id: segArea
                                anchors.fill: parent
                                onClicked: root.viewModel.navigateToBreadcrumb(modelData.path)
                            }
                        }
                    }
                }
            }
        }

        // ---- Filter button, and what it opens ----
        SquareIconButton {
            id: filterButton
            Layout.preferredHeight: root.height - root.gap
            Layout.preferredWidth: Layout.preferredHeight
            Layout.alignment: Qt.AlignVCenter
            iconSource: Images.url(root.viewModel.allFiltersOn ? "filter_all.svg" : "filter_more.svg")
            onClicked: filterPopup.open()

            Popup {
                id: filterPopup
                // under the button, its right edge on the button's
                y: filterButton.height + root.gap
                x: filterButton.width - width
                padding: Theme.spacing
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                background: Rectangle {
                    radius: Theme.radius
                    color: Theme.surface
                    border.color: Theme.dialogBorder
                    border.width: Theme.hairline
                }

                contentItem: Column {
                    spacing: Theme.spacingSmall

                    // the files of the type asked for alone, or all of them
                    ModelCheckBox {
                        text: root.viewModel.fileFilterLabel + " Files"
                        font.pixelSize: Theme.fontBody
                        checked: root.viewModel.ngcOnly
                        enabled: root.viewModel.allowFileFilterToggle
                        onToggledTo: function(on) { root.viewModel.setNgcOnly(on) }
                    }
                    ModelCheckBox {
                        text: "Folders"
                        font.pixelSize: Theme.fontBody
                        checked: root.viewModel.showFolders
                        onToggledTo: function(on) { root.viewModel.setShowFolders(on) }
                    }
                }
            }
        }
    }
}
