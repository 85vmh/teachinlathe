// ToolChangeDetailsView.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."  // for NumpadField.qml

Item {
    id: root
    anchors.fill: parent

    // Public API: the details pane must implement these
    // Parent will call applyData(index, opDict) to populate, and we emit saveRequested(updated)
    property int opIndex: -1
    property var opData: null

    signal saveRequested(var updated)          // { index: int, payload: dict }
    signal teachXRequested(int index)          // optional; hook in Python if you want
    signal teachZRequested(int index)
    signal openNumPadRequested(var field)      // bubble NumpadField taps up to ChildScreen

    // Internal state (safe defaults)
    property int toolNo:          (opData && opData.tool_no !== undefined) ? opData.tool_no : 0
    property int toolOrient:      (opData && opData.tool_orientation !== undefined) ? opData.tool_orientation : 1
    property int backAngle:       (opData && opData.back_angle !== undefined) ? opData.back_angle : 0
    property int frontAngle:      (opData && opData.front_angle !== undefined) ? opData.front_angle : 0

    property real xPos:           (opData && opData.toolchange_details && opData.toolchange_details.x_pos !== undefined) ? opData.toolchange_details.x_pos : 0.0
    property real zPos:           (opData && opData.toolchange_details && opData.toolchange_details.z_pos !== undefined) ? opData.toolchange_details.z_pos : 0.0
    property string coordType:    (opData && opData.toolchange_details && opData.toolchange_details.coordinate_type) ? opData.toolchange_details.coordinate_type : "absolute"
    property string moveSeq:      (opData && opData.toolchange_details && opData.toolchange_details.move_sequence) ? opData.toolchange_details.move_sequence : "xz"
    property bool stopSpindle:    (opData && opData.toolchange_details && opData.toolchange_details.stop_spindle !== undefined) ? opData.toolchange_details.stop_spindle : false

    // Called by parent to populate the form
    function applyData(index, data) {
        opIndex = index
        opData = data || {}
        toolNo      = (opData.tool_no !== undefined) ? opData.tool_no : 0
        toolOrient  = (opData.tool_orientation !== undefined) ? opData.tool_orientation : 1
        backAngle   = (opData.back_angle !== undefined) ? opData.back_angle : 0
        frontAngle  = (opData.front_angle !== undefined) ? opData.front_angle : 0
        xPos        = (opData.toolchange_details && opData.toolchange_details.x_pos !== undefined) ? opData.toolchange_details.x_pos : 0.0
        zPos        = (opData.toolchange_details && opData.toolchange_details.z_pos !== undefined) ? opData.toolchange_details.z_pos : 0.0
        coordType   = (opData.toolchange_details && opData.toolchange_details.coordinate_type) ? opData.toolchange_details.coordinate_type : "absolute"
        moveSeq     = (opData.toolchange_details && opData.toolchange_details.move_sequence) ? opData.toolchange_details.move_sequence : "xz"
        stopSpindle = (opData.toolchange_details && opData.toolchange_details.stop_spindle !== undefined) ? opData.toolchange_details.stop_spindle : false
    }

    // Validators
    IntValidator    { id: intVal }
    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10

        // === Group: Tool ===
        GroupBox {
            title: "Tool"
            Layout.fillWidth: true
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 8

                // Row: Tool No (numpad) + read-only tool info (orientation/angles)
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Label { text: "Tool No"; width: 100; verticalAlignment: Text.AlignVCenter }

                    // Editable via custom numpad
                    NumpadField {
                        id: nfToolNo
                        Layout.preferredWidth: 120
                        settingName: "toolchange_tool_no"
                        validatorObject: intVal
                        value: root.toolNo
                        // optional formatting (plain int as string)
                        formatter: function(v){ return (v===null||v===undefined) ? "" : String(Math.floor(Number(v))) }
                        onOpenRequested: root.openNumPadRequested(field)
                        onValueCommitted: root.toolNo = value
                    }

                    // Read-only info about the selected tool (no editing here)
                    Item { width: 20 } // spacer
                    Label {
                        text: "Orientation:"
                        width: 90
                        horizontalAlignment: Text.AlignRight
                        verticalAlignment: Text.AlignVCenter
                    }
                    Label {
                        text: String(root.toolOrient)
                        width: 40
                        verticalAlignment: Text.AlignVCenter
                    }

                    Item { width: 16 }
                    Label {
                        text: "Back angle:"
                        width: 90
                        horizontalAlignment: Text.AlignRight
                        verticalAlignment: Text.AlignVCenter
                    }
                    Label {
                        text: String(root.backAngle)
                        width: 40
                        verticalAlignment: Text.AlignVCenter
                    }

                    Item { width: 16 }
                    Label {
                        text: "Front angle:"
                        width: 90
                        horizontalAlignment: Text.AlignRight
                        verticalAlignment: Text.AlignVCenter
                    }
                    Label {
                        text: String(root.frontAngle)
                        width: 40
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }

        // === Group: Change Position ===
        GroupBox {
            title: "Change Position"
            Layout.fillWidth: true
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 8

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    // X position (numpad) + Teach X
                    Label { text: "X pos"; width: 100; verticalAlignment: Text.AlignVCenter }
                    NumpadField {
                        id: nfX
                        Layout.preferredWidth: 140
                        settingName: "toolchange_x_pos"
                        validatorObject: dblVal
                        value: root.xPos
                        formatter: function(v){ return (v===null||v===undefined) ? "" : Number(v).toFixed(3) }
                        onOpenRequested: root.openNumPadRequested(field)
                        onValueCommitted: root.xPos = value
                    }
                    Button {
                        text: "Teach X"
                        onClicked: root.teachXRequested(root.opIndex)
                    }

                    // Z position (numpad) + Teach Z
                    Label { text: "Z pos"; width: 100; verticalAlignment: Text.AlignVCenter }
                    NumpadField {
                        id: nfZ
                        Layout.preferredWidth: 140
                        settingName: "toolchange_z_pos"
                        validatorObject: dblVal
                        value: root.zPos
                        formatter: function(v){ return (v===null||v===undefined) ? "" : Number(v).toFixed(3) }
                        onOpenRequested: root.openNumPadRequested(field)
                        onValueCommitted: root.zPos = value
                    }
                    Button {
                        text: "Teach Z"
                        onClicked: root.teachZRequested(root.opIndex)
                    }
                }

                // Coordinate type radios
                RowLayout {
                    Layout.fillWidth: true; spacing: 16
                    Label { text: "Coordinate Type"; width: 150; verticalAlignment: Text.AlignVCenter }
                    ButtonGroup { id: coordGroup }
                    RadioButton {
                        text: "Absolute"; checked: root.coordType === "absolute"; ButtonGroup.group: coordGroup
                        onToggled: if (checked) root.coordType = "absolute"
                    }
                    RadioButton {
                        text: "Relative"; checked: root.coordType === "relative"; ButtonGroup.group: coordGroup
                        onToggled: if (checked) root.coordType = "relative"
                    }
                }

                // Move sequence radios (strings must match what Python expects)
                RowLayout {
                    Layout.fillWidth: true; spacing: 16
                    Label { text: "Move Sequence"; width: 150; verticalAlignment: Text.AlignVCenter }
                    ButtonGroup { id: moveGroup }
                    RadioButton {
                        text: "X then Z"; checked: root.moveSeq === "xz"; ButtonGroup.group: moveGroup
                        onToggled: if (checked) root.moveSeq = "xz"
                    }
                    RadioButton {
                        text: "Z then X"; checked: root.moveSeq === "zx"; ButtonGroup.group: moveGroup
                        onToggled: if (checked) root.moveSeq = "zx"
                    }
                    RadioButton {
                        text: "Straight"; checked: root.moveSeq === "straight"; ButtonGroup.group: moveGroup
                        onToggled: if (checked) root.moveSeq = "straight"
                    }
                }

                // Stop spindle
                RowLayout {
                    Layout.fillWidth: true; spacing: 8
                    CheckBox {
                        id: cbStopSpindle
                        text: "Stop spindle"
                        checked: root.stopSpindle
                        onToggled: root.stopSpindle = checked
                    }
                }
            }
        }

        // Actions
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            Item { Layout.fillWidth: true }
            Button {
                text: "Reset"
                onClicked: {
                    if (root.opData) root.applyData(root.opIndex, root.opData)
                }
            }
            Button {
                text: "Save"
                onClicked: {
                    var payload = {
                        order:        (root.opData && root.opData.order !== undefined) ? root.opData.order : 0,
                        type:         "changeTool",
                        generate_gcode: (root.opData && root.opData.generate_gcode !== undefined) ? root.opData.generate_gcode : true,
                        is_optional_block: (root.opData && root.opData.is_optional_block !== undefined) ? root.opData.is_optional_block : false,
                        tool_no:          root.toolNo,
                        tool_orientation: root.toolOrient,   // read-only here, still part of payload
                        back_angle:       root.backAngle,    // read-only here, still part of payload
                        front_angle:      root.frontAngle,   // read-only here, still part of payload
                        toolchange_details: {
                            x_pos: root.xPos,
                            z_pos: root.zPos,
                            coordinate_type: root.coordType,
                            move_sequence: root.moveSeq,
                            stop_spindle: root.stopSpindle
                        }
                    }
                    root.saveRequested({ index: root.opIndex, payload: payload })
                }
            }
        }
    }
}
