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

    property int opIndex: -1
    property var opData: null
    property var geometryData: ({})

    signal saveRequested(var payload)
    signal openNumPadRequested(var field)
    signal teachXRequested(int index)
    signal teachZRequested(int index)

    property real x_start: 0.0
    property real z_start: 0.0
    property real z_end: 0.0
    property bool _loading: false

    function applyData(index, geometryParams, fullOp) {
        _loading = true
        opIndex = index
        opData = fullOp || {}
        geometryData = geometryParams || {}

        x_start = parseFloat(geometryData.x_start !== undefined ? geometryData.x_start : 0.0)
        z_start = parseFloat(geometryData.z_start !== undefined ? geometryData.z_start : 0.0)
        z_end = parseFloat(geometryData.z_end !== undefined ? geometryData.z_end : 0.0)
        _loading = false
    }

    function emitSave() {
        if (_loading) return
        root.saveRequested({
            order: (opData && opData.order !== undefined) ? opData.order : 0,
            type: (opData && opData.type) ? opData.type : "",
            generate_gcode: (opData && opData.generate_gcode !== undefined) ? opData.generate_gcode : true,
            is_optional_block: (opData && opData.is_optional_block !== undefined) ? opData.is_optional_block : false,
            geometry_parameters: {
                z_start: z_start,
                z_end: z_end,
                x_start: x_start
            }
        })
    }

    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }

    GridLayout {
        anchors.fill: parent
        columns: 3
        columnSpacing: 20
        rowSpacing: 20

        Label { text: "X Start"; font.pixelSize: 16 }
        NumpadField {
            Layout.preferredWidth: 100
            settingName: "knurling.x_start"
            validatorObject: dblVal
            value: root.x_start
            formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            fontPixelSize: 16
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: { root.x_start = value; root.emitSave() }
        }
        Button { text: "TeachIn"; onClicked: root.teachXRequested(root.opIndex) }

        Label { text: "Z Start"; font.pixelSize: 16 }
        NumpadField {
            Layout.preferredWidth: 100
            settingName: "knurling.z_start"
            validatorObject: dblVal
            value: root.z_start
            formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            fontPixelSize: 16
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: { root.z_start = value; root.emitSave() }
        }
        Button { text: "TeachIn"; onClicked: root.teachZRequested(root.opIndex) }

        Label { text: "Z End"; font.pixelSize: 16 }
        NumpadField {
            Layout.preferredWidth: 100
            settingName: "knurling.z_end"
            validatorObject: dblVal
            value: root.z_end
            formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            fontPixelSize: 16
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: { root.z_end = value; root.emitSave() }
        }
        Button { text: "TeachIn"; onClicked: root.teachZRequested(root.opIndex) }
    }
}
