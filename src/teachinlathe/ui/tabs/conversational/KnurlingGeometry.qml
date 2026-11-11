import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import common.touchable_input
import theme
import common
import TeachInLathe

TitledCard {
    id: root
    title: "Cutting Geometry"
    Layout.fillWidth: true
    Layout.minimumWidth: 420
    Layout.preferredWidth: 560
    font.pixelSize: Theme.fontBody

    // the operation's geometry_parameters, as its editor has them: all it shows
    property var geometry: ({})
    readonly property var _g: geometry || {}

    // a change to the geometry_parameters: only the fields in it
    signal edited(var changes)
    signal openNumPadRequested(var field)
    signal teachXRequested(int index)
    signal teachZRequested(int index)

    readonly property real x_start: _g.x_start !== undefined ? Number(_g.x_start) : 0.0
    readonly property real z_start: _g.z_start !== undefined ? Number(_g.z_start) : 0.0
    readonly property real z_end: _g.z_end !== undefined ? Number(_g.z_end) : 0.0

    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }

    GridLayout {
        anchors.fill: parent
        columns: 3
        columnSpacing: 20
        rowSpacing: 20

        Label { text: "X Start"; font.pixelSize: Theme.fontBody }
        NumpadField {
            id: tf_x_start
            Layout.preferredWidth: 100
            settingName: "knurling.x_start"
            validatorObject: dblVal
            value: root.x_start
            formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: function(field) { root.openNumPadRequested(field) }
            onValueCommitted: function(value) { root.edited({ x_start: Number(value) }) }
        }
        TeachInButton { onClicked: tf_x_start.commit(PositionsBridge.teachInX() * 2) }

        Label { text: "Z Start"; font.pixelSize: Theme.fontBody }
        NumpadField {
            id: tf_z_start
            Layout.preferredWidth: 100
            settingName: "knurling.z_start"
            validatorObject: dblVal
            value: root.z_start
            formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: function(field) { root.openNumPadRequested(field) }
            onValueCommitted: function(value) { root.edited({ z_start: Number(value) }) }
        }
        TeachInButton { onClicked: tf_z_start.commit(PositionsBridge.teachInZ()) }

        Label { text: "Z End"; font.pixelSize: Theme.fontBody }
        NumpadField {
            id: tf_z_end
            Layout.preferredWidth: 100
            settingName: "knurling.z_end"
            validatorObject: dblVal
            value: root.z_end
            formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: function(field) { root.openNumPadRequested(field) }
            onValueCommitted: function(value) { root.edited({ z_end: Number(value) }) }
        }
        TeachInButton { onClicked: tf_z_end.commit(PositionsBridge.teachInZ()) }
    }
}
