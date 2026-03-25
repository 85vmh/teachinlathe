import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

GroupBox {
    id: root
    title: "Cutting Parameters"
    Layout.fillWidth: true
    Layout.minimumWidth: 360
    Layout.preferredWidth: 520
    font.pixelSize: 16

    property int opIndex: -1
    property var opData: null
    property var cuttingData: ({})

    signal saveRequested(var payload)
    signal openNumPadRequested(var field)

    property real doc: 0.0
    property real retract: 0.0
    property int grooves_count: 1
    property bool _loading: false

    function applyData(index, cuttingParams, fullOp) {
        _loading = true
        opIndex = index
        opData = fullOp || {}
        cuttingData = cuttingParams || {}

        doc = parseFloat(cuttingData.doc !== undefined ? cuttingData.doc : 0.0)
        retract = parseFloat(cuttingData.retract !== undefined ? cuttingData.retract : 0.0)
        grooves_count = Math.max(1, Math.round(cuttingData.grooves_count !== undefined ? Number(cuttingData.grooves_count) : 1))
        _loading = false
    }

    function emitSave() {
        if (_loading) return
        var payload = {
            order: (opData && opData.order !== undefined) ? opData.order : 0,
            type: (opData && opData.type) ? opData.type : "",
            generate_gcode: (opData && opData.generate_gcode !== undefined) ? opData.generate_gcode : true,
            is_optional_block: (opData && opData.is_optional_block !== undefined) ? opData.is_optional_block : false,
            cutting_parameters: {
                doc: doc,
                retract: retract,
                grooves_count: grooves_count
            }
        }
        root.saveRequested({ index: opIndex, payload: payload })
    }

    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }
    IntValidator { id: groovesVal; bottom: 1; top: 9999 }

    GridLayout {
        anchors.fill: parent
        columns: 3
        columnSpacing: 20
        rowSpacing: 20

        Label { text: "Grooves Count"; font.pixelSize: 16 }
        NumpadField {
            Layout.preferredWidth: 100
            settingName: "knurling.grooves_count"
            value: root.grooves_count
            validatorObject: groovesVal
            formatter: function(v) { return (v == null) ? "" : String(Math.max(1, Math.round(Number(v)))) }
            hAlign: Text.AlignRight
            fontPixelSize: 16
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: { root.grooves_count = Math.max(1, Math.round(value)); root.emitSave() }
        }
        Item {}

        Label { text: "Depth of Cut"; font.pixelSize: 16 }
        NumpadField {
            Layout.preferredWidth: 100
            settingName: "knurling.doc"
            value: root.doc
            validatorObject: dblVal
            formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            fontPixelSize: 16
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: { root.doc = value; root.emitSave() }
        }
        Label { text: "(mm/radius)"; font.pixelSize: 16 }

        Label { text: "Retract"; font.pixelSize: 16 }
        NumpadField {
            Layout.preferredWidth: 100
            settingName: "knurling.retract"
            value: root.retract
            validatorObject: dblVal
            formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            fontPixelSize: 16
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: { root.retract = value; root.emitSave() }
        }
        Label { text: "(mm)"; font.pixelSize: 16 }
    }
}
