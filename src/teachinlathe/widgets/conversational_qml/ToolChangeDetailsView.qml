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

    property int toolNo:       0
    property int toolOrient:   1
    property int backAngle:    0
    property int frontAngle:   0
    property real xPos:        0.0
    property real zPos:        0.0
    property string coordType: "absolute"
    property string moveSeq:   "xz"
    property bool stopSpindle: false

    function applyData(index, data) {
        _loading = true
        opIndex = index
        opData = data || {}

        toolNo     = (opData.tool_no !== undefined) ? opData.tool_no : 0
        toolOrient = (opData.tool_orientation !== undefined) ? opData.tool_orientation : 1
        backAngle  = (opData.back_angle !== undefined) ? opData.back_angle : 0
        frontAngle = (opData.front_angle !== undefined) ? opData.front_angle : 0

        var det = (opData.toolchange_details || {})
        xPos        = (det.x_pos !== undefined) ? det.x_pos : 0.0
        zPos        = (det.z_pos !== undefined) ? det.z_pos : 0.0
        coordType   = det.coordinate_type || "absolute"
        moveSeq     = det.move_sequence || "xz"
        stopSpindle = (det.stop_spindle !== undefined) ? det.stop_spindle : false
        _loading = false
    }

    function emitSave() {
        if (_loading) return
        var payload = {
            order:        (opData && opData.order !== undefined) ? opData.order : 0,
            type:         "changeTool",
            generate_gcode: (opData && opData.generate_gcode !== undefined) ? opData.generate_gcode : true,
            is_optional_block: (opData && opData.is_optional_block !== undefined) ? opData.is_optional_block : false,
            tool_no:          toolNo,
            tool_orientation: toolOrient,
            back_angle:       backAngle,
            front_angle:      frontAngle,
            toolchange_details: {
                x_pos: xPos,
                z_pos: zPos,
                coordinate_type: coordType,
                move_sequence: moveSeq,
                stop_spindle: stopSpindle
            }
        }
        saveRequested({ index: opIndex, payload: payload })
    }

    // validators
    IntValidator    { id: intVal }
    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10

        GroupBox {
            title: "Tool"
            Layout.fillWidth: true
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 8

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Label { text: "Tool No"; width: 100; verticalAlignment: Text.AlignVCenter }
                    NumpadField {
                        Layout.preferredWidth: 120
                        settingName: "toolchange_tool_no"
                        validatorObject: intVal
                        value: root.toolNo
                        formatter: function(v){ return (v==null) ? "" : String(Math.floor(Number(v))) }
                        onOpenRequested: root.openNumPadRequested(field)
                        onValueCommitted: { root.toolNo = value; root.emitSave() }
                    }

                    Item { width: 20 }
                    Label { text: "Orientation:"; width: 90; horizontalAlignment: Text.AlignRight; verticalAlignment: Text.AlignVCenter }
                    Label { text: String(root.toolOrient); width: 40; verticalAlignment: Text.AlignVCenter }

                    Item { width: 16 }
                    Label { text: "Back angle:"; width: 90; horizontalAlignment: Text.AlignRight; verticalAlignment: Text.AlignVCenter }
                    Label { text: String(root.backAngle); width: 40; verticalAlignment: Text.AlignVCenter }

                    Item { width: 16 }
                    Label { text: "Front angle:"; width: 90; horizontalAlignment: Text.AlignRight; verticalAlignment: Text.AlignVCenter }
                    Label { text: String(root.frontAngle); width: 40; verticalAlignment: Text.AlignVCenter }
                }
            }
        }

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

                    Label { text: "X pos"; width: 100; verticalAlignment: Text.AlignVCenter }
                    NumpadField {
                        Layout.preferredWidth: 140
                        settingName: "toolchange_x_pos"
                        validatorObject: dblVal
                        value: root.xPos
                        formatter: function(v){ return (v==null) ? "" : Number(v).toFixed(3) }
                        onOpenRequested: root.openNumPadRequested(field)
                        onValueCommitted: { root.xPos = value; root.emitSave() }
                    }
                    Button { text: "Teach X"; onClicked: root.teachXRequested(root.opIndex) }

                    Label { text: "Z pos"; width: 100; verticalAlignment: Text.AlignVCenter }
                    NumpadField {
                        Layout.preferredWidth: 140
                        settingName: "toolchange_z_pos"
                        validatorObject: dblVal
                        value: root.zPos
                        formatter: function(v){ return (v==null) ? "" : Number(v).toFixed(3) }
                        onOpenRequested: root.openNumPadRequested(field)
                        onValueCommitted: { root.zPos = value; root.emitSave() }
                    }
                    Button { text: "Teach Z"; onClicked: root.teachZRequested(root.opIndex) }
                }

                RowLayout {
                    Layout.fillWidth: true; spacing: 16
                    Label { text: "Coordinate Type"; width: 150; verticalAlignment: Text.AlignVCenter }
                    ButtonGroup { id: coordGroup }
                    RadioButton {
                        text: "Absolute"; checked: root.coordType === "absolute"; ButtonGroup.group: coordGroup
                        onToggled: if (checked) { root.coordType = "absolute"; root.emitSave() }
                    }
                    RadioButton {
                        text: "Relative"; checked: root.coordType === "relative"; ButtonGroup.group: coordGroup
                        onToggled: if (checked) { root.coordType = "relative"; root.emitSave() }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true; spacing: 16
                    Label { text: "Move Sequence"; width: 150; verticalAlignment: Text.AlignVCenter }
                    ButtonGroup { id: moveGroup }
                    RadioButton {
                        text: "X then Z"; checked: root.moveSeq === "xz"; ButtonGroup.group: moveGroup
                        onToggled: if (checked) { root.moveSeq = "xz"; root.emitSave() }
                    }
                    RadioButton {
                        text: "Z then X"; checked: root.moveSeq === "zx"; ButtonGroup.group: moveGroup
                        onToggled: if (checked) { root.moveSeq = "zx"; root.emitSave() }
                    }
                    RadioButton {
                        text: "Straight"; checked: root.moveSeq === "straight"; ButtonGroup.group: moveGroup
                        onToggled: if (checked) { root.moveSeq = "straight"; root.emitSave() }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true; spacing: 8
                    CheckBox {
                        text: "Stop spindle"
                        checked: root.stopSpindle
                        onToggled: { root.stopSpindle = checked; root.emitSave() }
                    }
                }
            }
        }
    }
}
