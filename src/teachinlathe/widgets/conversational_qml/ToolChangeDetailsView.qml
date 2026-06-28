import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."
import "../touchable_input"

Item {
    id: root
    anchors.fill: parent

    property int opIndex: -1
    property var opData: null

    signal saveRequested(var updated)
    signal openNumPadRequested(var field)

    property bool _loading: false

    property int toolNo: 0
    property int toolOrient: 1
    property int backAngle: 0
    property int frontAngle: 0
    property string toolchangePosition: "G28"

    function applyData(index, data) {
        _loading = true
        opIndex = index
        opData = data || {}

        toolNo = (opData.tool_no !== undefined) ? opData.tool_no : 0
        toolOrient = (opData.tool_orientation !== undefined) ? opData.tool_orientation : 1
        backAngle = (opData.back_angle !== undefined) ? opData.back_angle : 0
        frontAngle = (opData.front_angle !== undefined) ? opData.front_angle : 0
        toolchangePosition = opData.toolchange_position || "G28"
        _loading = false
    }

    function emitSave() {
        if (_loading) return
        saveRequested({
            index: opIndex,
            payload: {
                order: (opData && opData.order !== undefined) ? opData.order : 0,
                type: "changeTool",
                generate_gcode: (opData && opData.generate_gcode !== undefined) ? opData.generate_gcode : true,
                is_optional_block: (opData && opData.is_optional_block !== undefined) ? opData.is_optional_block : false,
                tool_no: toolNo,
                tool_orientation: toolOrient,
                back_angle: backAngle,
                front_angle: frontAngle,
                toolchange_position: toolchangePosition
            }
        })
    }

    IntValidator {
        id: intVal
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 50

        Label {
            text: "Tool Change"
            font.pixelSize: 18
            font.bold: true
        }

        GroupBox {
            title: "Tool"
            font.pixelSize: 16
            Layout.fillWidth: true

            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Layout.alignment: Qt.AlignTop

                Label {
                    text: "Tool No"
                    width: 120
                    verticalAlignment: Text.AlignVCenter
                    font.pixelSize: 16
                }
                NumpadField {
                    Layout.preferredWidth: 50
                    settingName: "toolchange_tool_no"
                    validatorObject: intVal
                    value: root.toolNo
                    fontPixelSize: 16
                    formatter: function (v) {
                        return (v == null) ? "" : String(Math.floor(Number(v)))
                    }
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: { root.toolNo = value; root.emitSave() }
                }

                Item { width: 20 }

                Label {
                    text: "Orientation:"; width: 90; horizontalAlignment: Text.AlignRight; verticalAlignment: Text.AlignVCenter
                }
                Label {
                    text: String(root.toolOrient); width: 40; verticalAlignment: Text.AlignVCenter
                }

                Item { width: 16 }

                Label {
                    text: "Back angle:"; width: 90; horizontalAlignment: Text.AlignRight; verticalAlignment: Text.AlignVCenter
                }
                Label {
                    text: String(root.backAngle); width: 40; verticalAlignment: Text.AlignVCenter
                }

                Item { width: 16 }

                Label {
                    text: "Front angle:"; width: 90; horizontalAlignment: Text.AlignRight; verticalAlignment: Text.AlignVCenter
                }
                Label {
                    text: String(root.frontAngle); width: 40; verticalAlignment: Text.AlignVCenter
                }
            }
        }

        GroupBox {
            title: "Tool Change Position"
            font.pixelSize: 16
            Layout.fillWidth: true

            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
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

        Item {
            Layout.fillHeight: true
        }
    }
}
