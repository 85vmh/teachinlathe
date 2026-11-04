import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import common.touchable_input
import theme

CanvasBox {
    id: root
    property real radius: 0.4
    property real depth: 0.4
    property real length: 2.5
    signal fieldEdited(string field, real value)
    signal openNumPadRequested(var field)

    DoubleValidator { id: validator; bottom: 0; notation: DoubleValidator.StandardNotation }
    GridLayout {
        columns: 3
        columnSpacing: Theme.spacing
        rowSpacing: Theme.spacing

        Label { text: "Radius"; font.pixelSize: Theme.fontBody }
        NumpadField {
            Layout.preferredWidth: 100
            settingName: "turning_finish.undercut.radius"
            validatorObject: validator; value: root.radius
            formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: function(field) { root.openNumPadRequested(field) }
            onValueCommitted: function(value) { root.fieldEdited("radius", Number(value)) }
        }
        Label { text: "(mm)"; font.pixelSize: Theme.fontBody }

        Label { text: "Depth"; font.pixelSize: Theme.fontBody }
        NumpadField {
            Layout.preferredWidth: 100
            settingName: "turning_finish.undercut.depth"
            validatorObject: validator; value: root.depth
            formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: function(field) { root.openNumPadRequested(field) }
            onValueCommitted: function(value) { root.fieldEdited("depth", Number(value)) }
        }
        Label { text: "(mm)"; font.pixelSize: Theme.fontBody }

        Label { text: "Length"; font.pixelSize: Theme.fontBody }
        NumpadField {
            Layout.preferredWidth: 100
            settingName: "turning_finish.undercut.length"
            validatorObject: validator; value: root.length
            formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: function(field) { root.openNumPadRequested(field) }
            onValueCommitted: function(value) { root.fieldEdited("length", Number(value)) }
        }
        Label { text: "(mm)"; font.pixelSize: Theme.fontBody }
    }
}
