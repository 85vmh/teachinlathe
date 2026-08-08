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
    property real retract: 1.0
    property bool _loading: false

    signal saveRequested(var payload)
    signal openNumPadRequested(var field)

    function applyData(data) {
        _loading = true
        var d = data || {}
        feed_rate = d.feed_rate !== undefined ? Number(d.feed_rate) : 0.1
        retract = d.retract !== undefined ? Number(d.retract) : 1.0
        _loading = false
    }

    function emitSave() {
        if (_loading) return
        root.saveRequested({
            cutting_parameters: {
                feed_rate: Number(feed_rate),
                retract: Number(retract)
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

        Label { text: "Retract"; font.pixelSize: 16 }
        NumpadField {
            Layout.preferredWidth: 100
            settingName: "groove_finishing.retract"
            value: root.retract
            validatorObject: dblVal
            formatter: function(v) { return v == null ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: { root.retract = value; root.emitSave() }
        }
        Label { text: "(mm)"; font.pixelSize: 16 }
    }
}
