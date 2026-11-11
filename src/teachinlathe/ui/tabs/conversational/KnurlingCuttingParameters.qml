import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import common.touchable_input
import theme
import common

TitledCard {
    id: root
    title: "Cutting Parameters"
    Layout.fillWidth: true
    Layout.minimumWidth: 360
    Layout.preferredWidth: 520
    font.pixelSize: Theme.fontBody

    // the operation's cutting_parameters, as its editor has them: all it shows
    property var cutting: ({})
    readonly property var _c: cutting || {}

    // a change to the cutting_parameters: only the fields in it
    signal edited(var changes)
    signal openNumPadRequested(var field)

    readonly property real doc: _c.doc !== undefined ? Number(_c.doc) : 0.0
    readonly property real retract: _c.retract !== undefined ? Number(_c.retract) : 0.0
    readonly property int grooves_count: Math.max(1, Math.round(_c.grooves_count !== undefined ? Number(_c.grooves_count) : 1))

    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }
    IntValidator { id: groovesVal; bottom: 1; top: 9999 }

    GridLayout {
        anchors.fill: parent
        columns: 3
        columnSpacing: Theme.spacing
        rowSpacing: 20

        Label { text: "Grooves Count"; font.pixelSize: Theme.fontBody }
        NumpadField {
            Layout.preferredWidth: 100
            settingName: "knurling.grooves_count"
            value: root.grooves_count
            validatorObject: groovesVal
            formatter: function(v) { return (v == null) ? "" : String(Math.max(1, Math.round(Number(v)))) }
            hAlign: Text.AlignRight
            onOpenRequested: function(field) { root.openNumPadRequested(field) }
            onValueCommitted: function(value) { root.edited({ grooves_count: Math.max(1, Math.round(value)) }) }
        }
        Item {}

        Label { text: "Depth of Cut"; font.pixelSize: Theme.fontBody }
        NumpadField {
            Layout.preferredWidth: 100
            settingName: "knurling.doc"
            value: root.doc
            validatorObject: dblVal
            formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: function(field) { root.openNumPadRequested(field) }
            onValueCommitted: function(value) { root.edited({ doc: Number(value) }) }
        }
        Label { text: "(mm/radius)"; font.pixelSize: Theme.fontBody }

        Label { text: "Retract"; font.pixelSize: Theme.fontBody }
        NumpadField {
            Layout.preferredWidth: 100
            settingName: "knurling.retract"
            value: root.retract
            validatorObject: dblVal
            formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: function(field) { root.openNumPadRequested(field) }
            onValueCommitted: function(value) { root.edited({ retract: Number(value) }) }
        }
        Label { text: "(mm)"; font.pixelSize: Theme.fontBody }
    }
}
