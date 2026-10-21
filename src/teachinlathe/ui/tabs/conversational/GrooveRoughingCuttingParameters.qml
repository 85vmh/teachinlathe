import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."
import common.touchable_input 1.0
import theme 1.0

GroupBox {
    id: root
    title: "Cutting Parameters"
    Layout.fillWidth: true
    Layout.minimumWidth: 420
    Layout.preferredWidth: 560
    font.pixelSize: Theme.fontBody

    property real peck_depth: 3.0
    property real retract: 1.0
    property real dwell_time: 0.5
    property bool _loading: false

    signal saveRequested(var payload)
    signal openNumPadRequested(var field)

    function applyData(data) {
        _loading = true
        var d = data || {}
        peck_depth = d.peck_depth !== undefined ? Number(d.peck_depth) : 3.0
        retract = d.retract !== undefined ? Number(d.retract) : 1.0
        dwell_time = d.dwell_time !== undefined ? Number(d.dwell_time) : 0.5
        _loading = false
    }

    function emitSave() {
        if (_loading) return
        root.saveRequested({
            // the feed rate is the operation header's
            cutting_parameters: {
                peck_depth: Number(peck_depth),
                retract: Number(retract),
                dwell_time: Number(dwell_time)
            }
        })
    }

    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }

    GridLayout {
        anchors.fill: parent
        columns: 3
        columnSpacing: 20
        rowSpacing: 16

        Label { text: "Peck Depth"; font.pixelSize: Theme.fontBody }
        NumpadField {
            Layout.preferredWidth: 100
            settingName: "groove_roughing.peck_depth"
            value: root.peck_depth
            validatorObject: dblVal
            formatter: function(v) { return v == null ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: { root.peck_depth = value; root.emitSave() }
        }
        Label { text: "(mm)"; font.pixelSize: Theme.fontBody }

        Label { text: "Retract"; font.pixelSize: Theme.fontBody }
        NumpadField {
            Layout.preferredWidth: 100
            settingName: "groove_roughing.retract"
            value: root.retract
            validatorObject: dblVal
            formatter: function(v) { return v == null ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: { root.retract = value; root.emitSave() }
        }
        Label { text: "(mm)"; font.pixelSize: Theme.fontBody }

        Label { text: "Dwell Time"; font.pixelSize: Theme.fontBody }
        NumpadField {
            Layout.preferredWidth: 100
            settingName: "groove_roughing.dwell_time"
            value: root.dwell_time
            validatorObject: dblVal
            formatter: function(v) { return v == null ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: { root.dwell_time = value; root.emitSave() }
        }
        Label { text: "(sec)"; font.pixelSize: Theme.fontBody }
    }
}
