import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import tabs.tool_library
import theme
import common

Item {
    id: root
    anchors.fill: parent

    // The view model of the operation this edits (OperationEditorViewModel.py).
    property var editor: null
    property int opIndex: -1
    property var opData: null
    signal openNumPadRequested(var field)

    property bool _loading: false

    property int toolNo: 0
    // The tool the operations before this one leave in: not one to pick.
    property int previousToolNo: 0
    property int toolOrient: 1
    property int backAngle: 0
    property int frontAngle: 0
    property string toolchangePosition: "G28"

    function applyData(index, data) {
        _loading = true
        opIndex = index
        opData = data || {}

        toolNo = (opData.tool_no !== undefined) ? opData.tool_no : 0
        previousToolNo = (opData.previous_tool_no !== undefined) ? opData.previous_tool_no : 0
        toolOrient = (opData.tool_orientation !== undefined) ? opData.tool_orientation : 1
        backAngle = (opData.back_angle !== undefined) ? opData.back_angle : 0
        frontAngle = (opData.front_angle !== undefined) ? opData.front_angle : 0
        toolchangePosition = opData.toolchange_position || "G28"
        _loading = false
    }

    function emitSave() {
        if (_loading) return
        root.editor.save({
            order: (opData && opData.order !== undefined) ? opData.order : 0,
            type: "changeTool",
            generate_gcode: (opData && opData.generate_gcode !== undefined) ? opData.generate_gcode : true,
            is_optional_block: (opData && opData.is_optional_block !== undefined) ? opData.is_optional_block : false,
            tool_no: toolNo,
            tool_orientation: toolOrient,
            back_angle: backAngle,
            front_angle: frontAngle,
            toolchange_position: toolchangePosition
        })
    }

    //: ToolHolderCard's height: its thumbnail and the padding round it.
    readonly property int cardHeight: 136

    readonly property var toolsModel: editor ? editor.touchedOffTools : null

    //: In from the view's sides; only the separator runs edge to edge.
    readonly property int sideMargin: 10

    ColumnLayout {
        anchors.fill: parent
        anchors.topMargin: 10
        anchors.bottomMargin: 10
        spacing: 0

        GroupBox {
            id: positionBox
            title: "Tool Change Position"
            font.pixelSize: Theme.fontBody
            Layout.fillWidth: true
            Layout.leftMargin: root.sideMargin
            Layout.rightMargin: root.sideMargin

            // No margins of its own: the GroupBox pads it alike above and
            // below, and margins on top of that pushed the row down.
            RowLayout {
                anchors.fill: parent
                spacing: 20

                RadioButton {
                    text: "Position stored in G28"
                    checked: root.toolchangePosition === "G28"
                    onToggled: if (checked) {
                        root.toolchangePosition = "G28"
                        root.emitSave()
                    }
                }

                RadioButton {
                    text: "Position stored in G30"
                    checked: root.toolchangePosition === "G30"
                    onToggled: if (checked) {
                        root.toolchangePosition = "G30"
                        root.emitSave()
                    }
                }
            }
        }

        // As the box's title above it, and lined up with it.
        Label {
            Layout.topMargin: 40
            Layout.leftMargin: root.sideMargin + positionBox.leftPadding
            Layout.rightMargin: root.sideMargin
            text: "Tools with measured offsets"
            font: positionBox.font
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.topMargin: Theme.margin
            Layout.preferredHeight: Theme.hairline
            color: Theme.separator
        }

        // The tools touched off, two to a row; all the height left.
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.leftMargin: root.sideMargin
            Layout.rightMargin: root.sideMargin

            GridView {
                id: toolsGrid
                anchors.fill: parent
                anchors.topMargin: Theme.spacingSmall
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar {}
                model: root.toolsModel
                cellWidth: Math.floor(width / 2)
                cellHeight: root.cardHeight + Theme.spacingSmall

                delegate: Item {
                    width: toolsGrid.cellWidth
                    height: toolsGrid.cellHeight

                    ToolHolderCard {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.rightMargin: index % 2 === 0 ? Theme.spacingSmall / 2 : 0
                        anchors.leftMargin: index % 2 === 1 ? Theme.spacingSmall / 2 : 0
                        toolNo: model.toolNo
                        toolId: model.toolId
                        toolCard: model.toolCard
                        toolView: model.toolView
                        toolComment: model.toolComment
                        xOffset: model.xOffset
                        zOffset: model.zOffset
                        selected: model.toolNo === root.toolNo
                        enabled: model.toolNo !== root.previousToolNo
                        onClicked: {
                            root.toolNo = model.toolNo
                            root.emitSave()
                        }
                    }
                }
            }

            ScrollFades {
                anchors.fill: parent
                flickable: toolsGrid
                fadeHeight: 80
                color: Theme.surface
            }

            Label {
                anchors.centerIn: parent
                visible: toolsGrid.count === 0
                text: "No tools touched off: set the offsets in Manual Turning."
                color: Theme.foregroundSubtle
                font.pixelSize: Theme.fontBody
            }
        }
    }
}
