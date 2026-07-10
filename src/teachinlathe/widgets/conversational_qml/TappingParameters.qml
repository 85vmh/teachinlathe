// TappingParameters.qml — two equal 3x2 grids side-by-side (Start | Spacer | End)
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."
import "../touchable_input"

GroupBox {
    id: root
    title: "Tapping Parameters"
    Layout.fillWidth: true
    Layout.minimumWidth: 420
    Layout.preferredWidth: 560
    font.pixelSize: 16

    // bridge
    property int  opIndex: -1
    property var  opData: null
    property var  tappingData: ({})
    signal saveRequested(var payload)
    signal openNumPadRequested(var field)
    signal teachZRequested(int index)

    // state
    property real z_start: 0.0
    property real z_end:   0.0
    property real z_retract:   0.0
    property real peck_depth:   0.0
    property real pitch:   0.0
    property bool _loading: false

    function applyData(index, tappingParams, fullOp) {
        _loading = true
        opIndex = index
        opData = fullOp || {}
        tappingData = tappingParams || {}
        z_start = parseFloat(tappingData.z_start  !== undefined ? tappingData.z_start  : 0.0)
        z_end   = parseFloat(tappingData.z_end    !== undefined ? tappingData.z_end    : 0.0)
        z_retract   = parseFloat(tappingData.z_retract    !== undefined ? tappingData.z_retract    : 0.0)
        peck_depth   = parseFloat(tappingData.peck_depth    !== undefined ? tappingData.peck_depth    : 0.0)
        pitch   = parseFloat(tappingData.pitch    !== undefined ? tappingData.pitch    : 0.0)
        _loading = false
    }

    function emitSave() {
        if (_loading) return
        var payload = {
            order: (opData && opData.order !== undefined) ? opData.order : 0,
            type:  (opData && opData.type) ? opData.type : "",
            generate_gcode: (opData && opData.generate_gcode !== undefined) ? opData.generate_gcode : true,
            is_optional_block: (opData && opData.is_optional_block !== undefined) ? opData.is_optional_block : false,
            tapping_parameters: {
                z_start: z_start,
                z_end:   z_end,
                z_retract:   z_retract,
                peck_depth:   peck_depth,
                pitch: pitch
            }
        }
        root.saveRequested(payload)
    }

    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }

    RowLayout {
        id: outerRow
        anchors.fill: parent
        spacing: 70

        /* LEFT GRID (Start) */
        GridLayout {
            id: leftGrid
            Layout.fillHeight: true
            columns: 3
            columnSpacing: 20
            rowSpacing: 20

            // Row 1
            Label {
                text: "Z Start"
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                font.pixelSize: 16
            }
            NumpadField {
                id: tf_z_start
                Layout.preferredWidth: 100
                Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                settingName: "geometry.z_start"
                validatorObject: dblVal
                value: root.z_start
                formatter: function(v){ return (v==null) ? "" : Number(v).toFixed(3) }
                hAlign: Text.AlignRight
                onOpenRequested: root.openNumPadRequested(field)
                onValueCommitted: { root.z_start = value; root.emitSave() }
            }
            Button {
                text: "TeachIn"
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                onClicked: tf_z_start.commit(positionsBridge.teachInZ())
            }

            Label {
                text: "Z End"
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                font.pixelSize: 16
            }
            NumpadField {
                id: tf_z_end
                Layout.preferredWidth: 100
                Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                settingName: "geometry.z_end"
                validatorObject: dblVal
                value: root.z_end
                formatter: function(v){ return (v==null) ? "" : Number(v).toFixed(3) }
                hAlign: Text.AlignRight
                onOpenRequested: root.openNumPadRequested(field)
                onValueCommitted: { root.z_end = value; root.emitSave() }
            }
            Button {
                text: "TeachIn"
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                onClicked: tf_z_end.commit(positionsBridge.teachInZ())
            }

            Label {
                text: "Z Retract"
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                font.pixelSize: 16
            }
            NumpadField {
                id: tf_z_retract
                Layout.preferredWidth: 100
                Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                settingName: "geometry.z_end"
                validatorObject: dblVal
                value: root.z_retract
                formatter: function(v){ return (v==null) ? "" : Number(v).toFixed(3) }
                hAlign: Text.AlignRight
                onOpenRequested: root.openNumPadRequested(field)
                onValueCommitted: { root.z_retract = value; root.emitSave() }
            }
            Button {
                text: "TeachIn"
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                onClicked: tf_z_retract.commit(positionsBridge.teachInZ())
            }
        }

        /* RIGHT GRID (End) */
        GridLayout {
            id: rightGrid
            Layout.fillHeight: true
            columns: 3
            columnSpacing: 20
            rowSpacing: 20

            // Row 1
            Label {
                text: "Peck Depth"
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                font.pixelSize: 16
            }
            NumpadField {
                Layout.preferredWidth: 100
                Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                settingName: "geometry.x_end"
                validatorObject: dblVal
                value: root.peck_depth
                formatter: function(v){ return (v==null) ? "" : Number(v).toFixed(3) }
                hAlign: Text.AlignRight
                onOpenRequested: root.openNumPadRequested(field)
                onValueCommitted: { root.peck_depth = value; root.emitSave() }
            }
            Label {
                text: "(mm)"
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                font.pixelSize: 16
            }

            // Row 2
            Label {
                text: "Pitch"
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                font.pixelSize: 16
            }
            NumpadField {
                Layout.preferredWidth: 100
                Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                settingName: "geometry.z_end"
                validatorObject: dblVal
                value: root.pitch
                formatter: function(v){ return (v==null) ? "" : Number(v).toFixed(3) }
                hAlign: Text.AlignRight
                onOpenRequested: root.openNumPadRequested(field)
                onValueCommitted: { root.pitch = value; root.emitSave() }
            }
            Label {
                text: "(mm)"
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                font.pixelSize: 16
            }
        }
    }
}
