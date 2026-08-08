import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."
import "../touchable_input"

GroupBox {
    id: root
    title: "Cutting Parameters"
    Layout.fillWidth: true
    Layout.minimumWidth: 420
    Layout.preferredWidth: 560
    font.pixelSize: 16

    property real feed_rate: 0.1
    property real peck_depth: 3.0
    property real retract: 1.0
    property real dwell_time: 0.5
    property bool _loading: false

    signal saveRequested(var payload)
    signal openNumPadRequested(var field)

    function applyData(data) {
        _loading = true
        var d = data || {}
        feed_rate = d.feed_rate !== undefined ? Number(d.feed_rate) : 0.1
        peck_depth = d.peck_depth !== undefined ? Number(d.peck_depth) : 3.0
        retract = d.retract !== undefined ? Number(d.retract) : 1.0
        dwell_time = d.dwell_time !== undefined ? Number(d.dwell_time) : 0.5
        _loading = false
    }

    function emitSave() {
        if (_loading) return
        root.saveRequested({
            cutting_parameters: {
                feed_rate: Number(feed_rate),
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

        Label { text: "Feed Rate"; font.pixelSize: 16 }
        NumpadField {
            Layout.preferredWidth: 100
            settingName: "turning.feed_rate"
            value: root.feed_rate
            validatorObject: dblVal
            formatter: function(v) { return v == null ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: { root.feed_rate = value; root.emitSave() }
        }
        Label { text: "(mm/rev)"; font.pixelSize: 16 }

        Label { text: "Peck Depth"; font.pixelSize: 16 }
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
        Label { text: "(mm)"; font.pixelSize: 16 }

        Label { text: "Retract"; font.pixelSize: 16 }
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
        Label { text: "(mm)"; font.pixelSize: 16 }

        Label { text: "Dwell Time"; font.pixelSize: 16 }
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
        Label { text: "(sec)"; font.pixelSize: 16 }
    }
}
