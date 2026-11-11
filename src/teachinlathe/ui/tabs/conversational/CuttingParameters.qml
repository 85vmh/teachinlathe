// CuttingParameters.qml — an operation's depth of cut and retract
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
    // (the feed rate is the operation header's)
    property var cutting: ({})
    readonly property var _c: cutting || {}

    // a change to the cutting_parameters: only the fields in it
    signal edited(var changes)
    signal openNumPadRequested(var field)

    readonly property real doc: _c.doc !== undefined ? Number(_c.doc) : 0.0
    readonly property real retract: _c.retract !== undefined ? Number(_c.retract) : 0.0

    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }

    GridLayout {
        id: grid
        anchors.fill: parent
        columns: 3
        columnSpacing: Theme.spacing
        rowSpacing: 20

        // Depth of Cut
        Label {
            text: "Depth of Cut (Ap)"
            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
            font.pixelSize: Theme.fontBody
        }
        NumpadField {
            Layout.preferredWidth: 100
            Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
            settingName: "turning.depth_of_cut"
            value: root.doc
            validatorObject: dblVal
            formatter: function (v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: function(field) { root.openNumPadRequested(field) }
            onValueCommitted: function(value) { root.edited({ doc: Number(value) }) }
        }
        Label {
            text: "(mm/radius)"
            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
            font.pixelSize: Theme.fontBody
        }

        // Retract
        Label {
            text: "Retract"
            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
            font.pixelSize: Theme.fontBody
        }
        NumpadField {
            Layout.preferredWidth: 100
            Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
            settingName: "cut.retract"
            value: root.retract
            validatorObject: dblVal
            formatter: function (v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: function(field) { root.openNumPadRequested(field) }
            onValueCommitted: function(value) { root.edited({ retract: Number(value) }) }
        }
        Label {
            text: "(mm)"
            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
            font.pixelSize: Theme.fontBody
        }
    }
}
