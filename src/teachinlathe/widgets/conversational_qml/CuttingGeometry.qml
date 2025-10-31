// CuttingGeometry.qml — two equal 3x2 grids side-by-side (Start | Spacer | End)
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

GroupBox {
    id: root
    title: "Cutting Geometry"
    Layout.fillWidth: true
    Layout.minimumWidth: 420
    Layout.preferredWidth: 560
    font.pixelSize: 16

    // bridge
    property int  opIndex: -1
    property var  opData: null
    property var  geometryData: ({})
    signal saveRequested(var payload)
    signal openNumPadRequested(var field)
    signal teachXRequested(int index)
    signal teachZRequested(int index)

    // state
    property real x_start: 0.0
    property real z_start: 0.0
    property real x_end:   0.0
    property real z_end:   0.0
    property bool _loading: false

    function applyData(index, geometryParams, fullOp) {
        _loading = true
        opIndex = index
        opData = fullOp || {}
        geometryData = geometryParams || {}
        x_start = parseFloat(geometryData.x_start  !== undefined ? geometryData.x_start  : 0.0)
        z_start = parseFloat(geometryData.z_start  !== undefined ? geometryData.z_start  : 0.0)
        x_end   = parseFloat(geometryData.x_end    !== undefined ? geometryData.x_end    : 0.0)
        z_end   = parseFloat(geometryData.z_end    !== undefined ? geometryData.z_end    : 0.0)
        _loading = false
    }

    function emitSave() {
        if (_loading) return
        var payload = {
            order: (opData && opData.order !== undefined) ? opData.order : 0,
            type:  (opData && opData.type) ? opData.type : "",
            generate_gcode: (opData && opData.generate_gcode !== undefined) ? opData.generate_gcode : true,
            is_optional_block: (opData && opData.is_optional_block !== undefined) ? opData.is_optional_block : false,
            geometry_parameters: {
                x_start: x_start,
                z_start: z_start,
                x_end:   x_end,
                z_end:   z_end
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
                text: "X Start"
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                font.pixelSize: 16
            }
            NumpadField {
                Layout.preferredWidth: 100
                Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                settingName: "geometry.x_start"
                validatorObject: dblVal
                value: root.x_start
                formatter: function(v){ return (v==null) ? "" : Number(v).toFixed(3) }
                hAlign: Text.AlignRight
                fontPixelSize: 16
                onOpenRequested: root.openNumPadRequested(field)
                onValueCommitted: { root.x_start = value; root.emitSave() }
            }
            Button {
                text: "TeachIn"
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                onClicked: root.teachXRequested(root.opIndex)
            }

            // Row 2
            Label {
                text: "Z Start"
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                font.pixelSize: 16
            }
            NumpadField {
                Layout.preferredWidth: 100
                Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                settingName: "geometry.z_start"
                validatorObject: dblVal
                value: root.z_start
                formatter: function(v){ return (v==null) ? "" : Number(v).toFixed(3) }
                hAlign: Text.AlignRight
                fontPixelSize: 16
                onOpenRequested: root.openNumPadRequested(field)
                onValueCommitted: { root.z_start = value; root.emitSave() }
            }
            Button {
                text: "TeachIn"
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                onClicked: root.teachZRequested(root.opIndex)
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
                text: "X End"
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                font.pixelSize: 16
            }
            NumpadField {
                Layout.preferredWidth: 100
                Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                settingName: "geometry.x_end"
                validatorObject: dblVal
                value: root.x_end
                formatter: function(v){ return (v==null) ? "" : Number(v).toFixed(3) }
                hAlign: Text.AlignRight
                fontPixelSize: 16
                onOpenRequested: root.openNumPadRequested(field)
                onValueCommitted: { root.x_end = value; root.emitSave() }
            }
            Button {
                text: "TeachIn"
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                onClicked: root.teachXRequested(root.opIndex)
            }

            // Row 2
            Label {
                text: "Z End"
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                font.pixelSize: 16
            }
            NumpadField {
                Layout.preferredWidth: 100
                Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                settingName: "geometry.z_end"
                validatorObject: dblVal
                value: root.z_end
                formatter: function(v){ return (v==null) ? "" : Number(v).toFixed(3) }
                hAlign: Text.AlignRight
                fontPixelSize: 16
                onOpenRequested: root.openNumPadRequested(field)
                onValueCommitted: { root.z_end = value; root.emitSave() }
            }
            Button {
                text: "TeachIn"
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                onClicked: root.teachZRequested(root.opIndex)
            }
        }
    }
}
