import QtQuick 2.15
import QtQuick.Layouts 1.15
import theme 1.0

// Row 2 — FolderUp button + scrollable breadcrumb + filter toggles.
Rectangle {
    id: root
    property var viewModel

    color: Theme.surfaceSunken
    implicitHeight: 38

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 4
        anchors.rightMargin: 6
        spacing: 4

        // ---- FolderUp button ----
        Rectangle {
            width: 30
            height: 28
            radius: Theme.radiusSmall
            color: upArea.containsMouse && root.viewModel && root.viewModel.canNavigateUp
                   ? Theme.outlineDisabled : "transparent"
            opacity: root.viewModel && root.viewModel.canNavigateUp ? 1.0 : 0.35

            Text {
                anchors.centerIn: parent
                text: "↑"
                color: Theme.foregroundMuted
                font.pixelSize: Theme.fontBody
            }

            MouseArea {
                id: upArea
                anchors.fill: parent
                hoverEnabled: true
                enabled: root.viewModel ? root.viewModel.canNavigateUp : false
                onClicked: if (root.viewModel) root.viewModel.navigateUp()
            }
        }

        // ---- Breadcrumb (scrollable, auto-scrolls to current segment) ----
        Flickable {
            id: breadcrumbFlick
            Layout.fillWidth: true
            height: parent.height
            clip: true
            contentWidth: breadcrumbRow.implicitWidth
            contentHeight: height
            flickableDirection: Flickable.HorizontalFlick
            boundsBehavior: Flickable.StopAtBounds
            interactive: contentWidth > width

            // Scroll to show the rightmost (current) segment when path changes
            onContentWidthChanged: {
                if (contentWidth > width)
                    contentX = contentWidth - width
            }

            Row {
                id: breadcrumbRow
                height: parent.height
                spacing: 0

                Repeater {
                    model: root.viewModel ? root.viewModel.breadcrumbs : []

                    delegate: Row {
                        height: breadcrumbRow.height
                        spacing: 0

                        Text {
                            visible: index > 0
                            anchors.verticalCenter: parent.verticalCenter
                            text: " / "
                            color: Theme.outlineEmphasis
                            font.pixelSize: Theme.fontXSmall
                        }

                        Rectangle {
                            height: parent.height
                            width: segText.implicitWidth + 8
                            color: segArea.containsMouse ? Theme.outlineDisabled : "transparent"
                            radius: 3

                            Text {
                                id: segText
                                anchors.centerIn: parent
                                text: modelData.name
                                color: index === (root.viewModel ? root.viewModel.breadcrumbs.length - 1 : 0)
                                       ? Theme.surfaceInverse : Theme.foregroundMuted
                                font.pixelSize: Theme.fontXSmall
                                font.bold: index === (root.viewModel ? root.viewModel.breadcrumbs.length - 1 : 0)
                            }

                            MouseArea {
                                id: segArea
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: if (root.viewModel) root.viewModel.navigateToBreadcrumb(modelData.path)
                            }
                        }
                    }
                }
            }
        }

        // ---- Filter toggles ----
        Row {
            spacing: 4

            // "Folders" toggle
            Rectangle {
                width: filterFoldersText.implicitWidth + 12
                height: 24
                radius: Theme.radiusSmall
                color: root.viewModel && root.viewModel.showFolders ? Theme.selection : Theme.surfaceSunken
                border.color: root.viewModel && root.viewModel.showFolders ? "#1E88E5" : Theme.outline
                border.width: Theme.hairline

                Text {
                    id: filterFoldersText
                    anchors.centerIn: parent
                    text: "Folders"
                    color: root.viewModel && root.viewModel.showFolders ? Theme.accentStrong : Theme.outlineEmphasis
                    font.pixelSize: Theme.fontXSmall
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: if (root.viewModel) root.viewModel.setShowFolders(!root.viewModel.showFolders)
                }
            }

            // "NGC" / "All" toggle
            Rectangle {
                width: filterNgcText.implicitWidth + 12
                height: 24
                radius: Theme.radiusSmall
                color: root.viewModel && root.viewModel.ngcOnly ? Theme.selection : Theme.surfaceSunken
                border.color: root.viewModel && root.viewModel.ngcOnly ? "#1E88E5" : Theme.outline
                border.width: Theme.hairline
                opacity: root.viewModel && root.viewModel.allowFileFilterToggle ? 1.0 : 0.65

                Text {
                    id: filterNgcText
                    anchors.centerIn: parent
                    text: root.viewModel && root.viewModel.ngcOnly ? root.viewModel.fileFilterLabel : "All"
                    color: root.viewModel && root.viewModel.ngcOnly ? Theme.accentStrong : Theme.foregroundMuted
                    font.pixelSize: Theme.fontXSmall
                }

                MouseArea {
                    anchors.fill: parent
                    enabled: root.viewModel ? root.viewModel.allowFileFilterToggle : false
                    onClicked: root.viewModel.setNgcOnly(!root.viewModel.ngcOnly)
                }
            }
        }
    }
}
