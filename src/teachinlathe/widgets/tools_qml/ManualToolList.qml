import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import theme 1.0

// The Manual Turning screen's tools: the tool holders as LinuxCNC numbers
// them, one to a row, all or only the recently used. The one in the
// spindle is selected; tapping another loads it. Each is a ToolHolderCard.
//
// Nothing is edited here: the offsets come from touching off.
Item {
    id: root

    property var viewModel: null        // ManualToolsViewModel

    readonly property int listSpacing: Theme.spacingSmall

    Rectangle { anchors.fill: parent; color: Theme.surfaceSunken }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ── Header: which tools ─────────────────────────────────────────
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 60
            color: Theme.separator

            // Centred in what the selector leaves of the header.
            Text {
                anchors.left: selector.right
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                horizontalAlignment: Text.AlignHCenter
                text: "Tools"
                color: Theme.surfaceInverse
                font.pixelSize: Theme.fontLarge
                font.bold: true
            }

            Row {
                id: selector
                anchors.left: parent.left
                anchors.leftMargin: 8
                anchors.verticalCenter: parent.verticalCenter
                spacing: 6

                Repeater {
                    model: [{ text: "All tools", recent: false, width: 120 },
                            { text: "Recently used", recent: true, width: 150 }]
                    delegate: Rectangle {
                        readonly property bool active: root.viewModel
                                                       && root.viewModel.recentOnly === modelData.recent
                        width: modelData.width
                        height: 46
                        radius: Theme.radiusLarge
                        color: active ? Theme.surfaceSunken : Theme.outlineStrong
                        border.color: active ? Theme.outlineEmphasis : "#b0b0b0"
                        border.width: Theme.hairline

                        Text {
                            anchors.centerIn: parent
                            text: modelData.text
                            color: Theme.surfaceInverse
                            font.pixelSize: Theme.fontSmall
                            font.bold: parent.active
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: if (root.viewModel) root.viewModel.recentOnly = modelData.recent
                        }
                    }
                }
            }
        }

        // ── The tools ───────────────────────────────────────────────────
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            ListView {
                id: list
                anchors.fill: parent
                anchors.margins: root.listSpacing
                spacing: root.listSpacing
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar {}
                model: root.viewModel ? root.viewModel.toolsModel : null

                delegate: ToolHolderCard {
                    width: ListView.view.width
                    toolNo: model.toolNo
                    toolId: model.toolId
                    toolCard: model.toolCard
                    toolView: model.toolView
                    toolComment: model.toolComment
                    xOffset: model.xOffset
                    zOffset: model.zOffset
                    selected: model.current
                    // Feeding: only the tool in the spindle stays live.
                    enabled: model.selectable
                    onClicked: root.viewModel.selectTool(model.toolNo)
                }
            }

            // Fades at the list's ends, as the other lists have them.
            Rectangle {
                anchors { left: parent.left; right: parent.right; top: parent.top }
                height: 80
                visible: !list.atYBeginning
                z: 1
                gradient: Gradient {
                    orientation: Gradient.Vertical
                    GradientStop { position: 0.0; color: Theme.surfaceSunken }
                    GradientStop { position: 1.0; color: "transparent" }
                }
            }

            Rectangle {
                anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
                height: 80
                visible: !list.atYEnd
                z: 1
                gradient: Gradient {
                    orientation: Gradient.Vertical
                    GradientStop { position: 0.0; color: "transparent" }
                    GradientStop { position: 1.0; color: Theme.surfaceSunken }
                }
            }
        }
    }
}
