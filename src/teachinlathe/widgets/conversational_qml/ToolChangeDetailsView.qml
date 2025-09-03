// ToolChangeDetailsView.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root
    anchors.fill: parent

    // Public API: the details pane must implement these
    // QML will call applyData(index, opDict) to populate, and we emit saveRequested(updated)
    property int opIndex: -1
    property var opData: null

    signal saveRequested(var updated)          // { index: int, payload: dict }
    signal teachXRequested(int index)          // optional; hook in Python if you want
    signal teachZRequested(int index)

    // Internal convenience bindings (safe defaults)
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
        // propagate to editable properties
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

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Label { text: "Tool No"; width: 100; verticalAlignment: Text.AlignVCenter }
                    TextField {
                        id: tfToolNo
                        Layout.preferredWidth: 120
                        inputMethodHints: Qt.ImhDigitsOnly
                        text: String(root.toolNo)
                        onTextChanged: {
                            var n = parseInt(text); if (!isNaN(n)) root.toolNo = n
                        }
                    }

                    Label { text: "Orientation"; width: 100; verticalAlignment: Text.AlignVCenter }
                    ComboBox {
                        id: cbOrientation
                        Layout.preferredWidth: 140
                        model: [1,2,3,4,5,6,7,8]
                        // simple mapping (1-based orientations)
                        Component.onCompleted: {
                            var idx = model.indexOf(root.toolOrient)
                            currentIndex = idx >= 0 ? idx : 0
                        }
                        onCurrentIndexChanged: root.toolOrient = model[currentIndex]
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Label { text: "Back Angle"; width: 100; verticalAlignment: Text.AlignVCenter }
                    SpinBox {
                        id: sbBack
                        Layout.preferredWidth: 120
                        from: 0; to: 180; stepSize: 1
                        value: root.backAngle
                        onValueChanged: root.backAngle = value
                    }

                    Label { text: "Front Angle"; width: 100; verticalAlignment: Text.AlignVCenter }
                    SpinBox {
                        id: sbFront
                        Layout.preferredWidth: 120
                        from: 0; to: 180; stepSize: 1
                        value: root.frontAngle
                        onValueChanged: root.frontAngle = value
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
                    Label { text: "X pos"; width: 100; verticalAlignment: Text.AlignVCenter }
                    TextField {
                        id: tfX
                        Layout.preferredWidth: 140
                        text: String(root.xPos)
                        validator: DoubleValidator { }
                        onEditingFinished: {
                            var v = parseFloat(text); if (!isNaN(v)) root.xPos = v
                        }
                    }
                    Button {
                        text: "Teach X"
                        onClicked: root.teachXRequested(root.opIndex)
                    }

                    Label { text: "Z pos"; width: 100; verticalAlignment: Text.AlignVCenter }
                    TextField {
                        id: tfZ
                        Layout.preferredWidth: 140
                        text: String(root.zPos)
                        validator: DoubleValidator { }
                        onEditingFinished: {
                            var v = parseFloat(text); if (!isNaN(v)) root.zPos = v
                        }
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

                // Move sequence radios (pick strings that your Python expects)
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
                        tool_orientation: root.toolOrient,
                        back_angle:       root.backAngle,
                        front_angle:      root.frontAngle,
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
