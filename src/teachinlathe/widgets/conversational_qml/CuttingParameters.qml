// CuttingParameters.qml (fixed: nested payload + full op context + loading guard)
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

    // bridge
    property int  opIndex: -1
    property var  opData: null              // FULL OP (nu doar cutting)
    property var  cuttingData: ({})         // doar sub-structura cutting_parameters

    signal saveRequested(var payload)
    signal openNumPadRequested(var field)

    // state
    property real feed_rate: 0.0
    property real doc: 0.0
    property real retract: 0.0
    property bool _loading: false

    // compat cu FacingDetailsView:
    // cuttingPanel.applyData(opIndex, (opData.cutting_parameters || {}), opData)
    function applyData(index, cuttingParams, fullOp) {
        _loading = true
        opIndex = index
        opData  = fullOp || {}
        cuttingData = cuttingParams || {}

        feed_rate = parseFloat(cuttingData.feed_rate !== undefined ? cuttingData.feed_rate : 0.0)
        doc       = parseFloat(cuttingData.doc       !== undefined ? cuttingData.doc       : 0.0)
        retract   = parseFloat(cuttingData.retract   !== undefined ? cuttingData.retract   : 0.0)
        _loading = false
    }

    function emitSave() {
        if (_loading) return
        var payload = {
            order: (opData && opData.order !== undefined) ? opData.order : 0,
            type:  (opData && opData.type)  ? opData.type  : "",
            generate_gcode: (opData && opData.generate_gcode !== undefined) ? opData.generate_gcode : true,
            is_optional_block: (opData && opData.is_optional_block !== undefined) ? opData.is_optional_block : false,
            cutting_parameters: {
                feed_rate: feed_rate,
                doc:       doc,
                retract:   retract
            }
        }
        // FacingDetailsView interceptează și face mergeIntoOp(p.payload || p)
        root.saveRequested({ index: opIndex, payload: payload })
    }

    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }

    GridLayout {
        id: grid
        anchors.fill: parent
        columns: 3
        columnSpacing: 20
        rowSpacing: 20

        // Feed Rate
        Label {
            text: "Feed rate (Fz)"
            font.pixelSize: 16
        }
        NumpadField {
            Layout.preferredWidth: 100
            Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
            settingName: "cut.feed_rate"
            value: root.feed_rate
            validatorObject: dblVal
            formatter: function (v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            fontPixelSize: 16
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: { root.feed_rate = value; root.emitSave() }
        }
        Label {
            text: "(mm/rev)"
            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
            font.pixelSize: 16
        }

        // Depth of Cut
        Label {
            text: "Depth of Cut (Ap)"
            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
            font.pixelSize: 16
        }
        NumpadField {
            Layout.preferredWidth: 100
            Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
            settingName: "cut.doc"
            value: root.doc
            validatorObject: dblVal
            formatter: function (v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            fontPixelSize: 16
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: { root.doc = value; root.emitSave() }
        }
        Label {
            text: "(mm/radius)"
            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
            font.pixelSize: 16
        }

        // Retract
        Label {
            text: "Retract"
            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
            font.pixelSize: 16
        }
        NumpadField {
            Layout.preferredWidth: 100
            Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
            settingName: "cut.retract"
            value: root.retract
            validatorObject: dblVal
            formatter: function (v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            fontPixelSize: 16
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: { root.retract = value; root.emitSave() }
        }
        Label {
            text: "(mm)"
            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
            font.pixelSize: 16
        }
    }
}
