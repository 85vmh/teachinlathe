import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."  // NumpadField.qml

Item {
    id: root
    anchors.fill: parent

    property int opIndex: -1
    property var opData: null

    signal saveRequested(var updated)

    signal teachXRequested(int index)

    signal teachZRequested(int index)

    signal openNumPadRequested(var field)

    property bool _loading: false

    property int toolNo: 0
    property int toolOrient: 1
    property int backAngle: 0
    property int frontAngle: 0
    property real xPos: 0.0
    property real zPos: 0.0
    property string coordType: "absolute"
    property string moveSeq: "both"   // "xz", "zx", "both"
    property bool stopSpindle: false

    function applyData(index, data) {
        _loading = true
        opIndex = index
        opData = data || {}

        toolNo = (opData.tool_no !== undefined) ? opData.tool_no : 0
        toolOrient = (opData.tool_orientation !== undefined) ? opData.tool_orientation : 1
        backAngle = (opData.back_angle !== undefined) ? opData.back_angle : 0
        frontAngle = (opData.front_angle !== undefined) ? opData.front_angle : 0

        var det = (opData.toolchange_rules || {})
        xPos = (det.x_pos !== undefined) ? det.x_pos : 0.0
        zPos = (det.z_pos !== undefined) ? det.z_pos : 0.0
        coordType = det.coordinate_type || "absolute"
        moveSeq = det.move_sequence || "xz"
        stopSpindle = (det.stop_spindle !== undefined) ? det.stop_spindle : false
        _loading = false
    }

    function emitSave() {
        if (_loading) return
        var payload = {
            order: (opData && opData.order !== undefined) ? opData.order : 0,
            type: "changeTool",
            generate_gcode: (opData && opData.generate_gcode !== undefined) ? opData.generate_gcode : true,
            is_optional_block: (opData && opData.is_optional_block !== undefined) ? opData.is_optional_block : false,
            tool_no: toolNo,
            tool_orientation: toolOrient,
            back_angle: backAngle,
            front_angle: frontAngle,
            toolchange_rules: {
                x_pos: xPos,
                z_pos: zPos,
                coordinate_type: coordType,
                move_sequence: moveSeq,
                stop_spindle: stopSpindle
            }
        }
        saveRequested({index: opIndex, payload: payload})
    }

    // validators
    IntValidator {
        id: intVal
    }
    DoubleValidator {
        id: dblVal; notation: DoubleValidator.StandardNotation
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

        /* ===== Group 1: Tool ===== */
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

                Item {
                    width: 20
                }
                Label {
                    text: "Orientation:"; width: 90; horizontalAlignment: Text.AlignRight; verticalAlignment: Text.AlignVCenter
                }
                Label {
                    text: String(root.toolOrient); width: 40; verticalAlignment: Text.AlignVCenter
                }

                Item {
                    width: 16
                }
                Label {
                    text: "Back angle:"; width: 90; horizontalAlignment: Text.AlignRight; verticalAlignment: Text.AlignVCenter
                }
                Label {
                    text: String(root.backAngle); width: 40; verticalAlignment: Text.AlignVCenter
                }

                Item {
                    width: 16
                }
                Label {
                    text: "Front angle:"; width: 90; horizontalAlignment: Text.AlignRight; verticalAlignment: Text.AlignVCenter
                }
                Label {
                    text: String(root.frontAngle); width: 40; verticalAlignment: Text.AlignVCenter
                }
            }
        }

        /* ===== Row: Change Position + Move Sequence side-by-side ===== */
        RowLayout {
            id: parentRow
            Layout.fillWidth: true
            spacing: 30
            Layout.alignment: Qt.AlignTop

            /* ===== Group 2A: Change Position ===== */
            GroupBox {
                title: "Change Position"
                font.pixelSize: 16
                Layout.preferredWidth: parentRow.width * 0.6
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop

                /* Row: Left (coord type) + Right (grid X/Z) */
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 24

                    Label {
                        text: "Coordinate Type";
                        font.pixelSize: 16
                        Layout.alignment: Qt.AlignCenter
                    }

                    /* Left column: label + radios (no anchors here) */
                    ColumnLayout {
                        spacing: 20
                        Layout.alignment: Qt.AlignCenter

                        ButtonGroup {
                            id: coordGroup
                        }

                        RadioButton {
                            text: "Relative"
                            checked: root.coordType === "relative"
                            ButtonGroup.group: coordGroup
                            onToggled: if (checked) {
                                root.coordType = "relative";
                                root.emitSave()
                            }
                        }
                        RadioButton {
                            text: "Absolute"
                            checked: root.coordType === "absolute"
                            ButtonGroup.group: coordGroup
                            onToggled: if (checked) {
                                root.coordType = "absolute";
                                root.emitSave()
                            }
                        }
                    }

                    Item {
                        Layout.fillWidth: true
                    }

                    Rectangle {
                        width: 1
                        Layout.alignment: Qt.AlignCenter
                        color: "#cccccc"
                        Layout.fillHeight: true
                    }

                    Item {
                        Layout.fillWidth: true
                    }

                    /* Right column: grid X/Z takes remaining width */
                    GridLayout {
                        id: posGrid
                        columns: 3
                        rowSpacing: 20
                        columnSpacing: 20
                        Layout.alignment: Qt.AlignRight
                        Layout.fillWidth: true

                        // X row
                        Label {
                            text: "X pos"
                            Layout.preferredWidth: 60
                            verticalAlignment: Text.AlignVCenter
                        }
                        NumpadField {
                            Layout.preferredWidth: 100
                            settingName: "toolchange_x_pos"
                            validatorObject: dblVal
                            value: root.xPos
                            formatter: function (v) {
                                return (v == null) ? "" : Number(v).toFixed(3)
                            }
                            onOpenRequested: root.openNumPadRequested(field)
                            onValueCommitted: { root.xPos = value; root.emitSave() }
                        }
                        Button {
                            text: "TeachIn"
                            onClicked: root.teachXRequested(root.opIndex)
                        }

                        // Z row
                        Label {
                            text: "Z pos"
                            Layout.preferredWidth: 60
                            verticalAlignment: Text.AlignVCenter
                        }
                        NumpadField {
                            Layout.preferredWidth: 100
                            settingName: "toolchange_z_pos"
                            validatorObject: dblVal
                            value: root.zPos
                            formatter: function (v) {
                                return (v == null) ? "" : Number(v).toFixed(3)
                            }
                            onOpenRequested: root.openNumPadRequested(field)
                            onValueCommitted: { root.zPos = value; root.emitSave() }
                        }
                        Button {
                            text: "TeachIn"
                            onClicked: root.teachZRequested(root.opIndex)
                        }
                    }
                }
            }

            /* ===== Group 2B: Move Sequence ===== */
            GroupBox {
                title: "Move Sequence"
                font.pixelSize: 16
                Layout.preferredWidth: parentRow.width * 0.4
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop
                // ex: Layout.preferredWidth: 320

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 10

                    ButtonGroup {
                        id: moveGroup
                    }

                    RadioButton {
                        text: "X then Z"
                        checked: root.moveSeq === "xz"
                        ButtonGroup.group: moveGroup
                        onToggled: if (checked) {
                            root.moveSeq = "xz";
                            root.emitSave()
                        }
                    }
                    RadioButton {
                        text: "Z then X"
                        checked: root.moveSeq === "zx"
                        ButtonGroup.group: moveGroup
                        onToggled: if (checked) {
                            root.moveSeq = "zx";
                            root.emitSave()
                        }
                    }
                    RadioButton {
                        text: "Simultaneous"
                        checked: root.moveSeq === "both"
                        ButtonGroup.group: moveGroup
                        onToggled: if (checked) {
                            root.moveSeq = "both";
                            root.emitSave()
                        }
                    }

                    Item {
                        Layout.fillHeight: true
                    }
                }
            }
        }

        /* Stop spindle */
        RowLayout {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            CheckBox {
                text: "Stop spindle"
                checked: root.stopSpindle
                font.pixelSize: 16
                onToggled: { root.stopSpindle = checked; root.emitSave() }
            }
            Item {
                Layout.fillWidth: true
            }
        }
        Item {
            Layout.fillHeight: true
        }
    }
}
