// PassesCountBox.qml — how many passes an operation takes its stock off in,
// laid over the profile canvas: a whole number, at least one (the domain
// makes less than one one).
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import common.touchable_input
import theme

CanvasBox {
    id: root

    property int passes: 1

    signal passesEdited(int value)
    signal openNumPadRequested(var field)

    IntValidator { id: countVal; bottom: 0; top: 99 }

    GridLayout {
        columns: 2
        columnSpacing: Theme.spacing

        Label { text: "Passes count"; font.pixelSize: Theme.fontBody }
        NumpadField {
            Layout.preferredWidth: 100
            settingName: "profile_contour.passes_count"
            description: "Passes count"
            validatorObject: countVal
            value: root.passes
            formatter: function (v) { return (v == null) ? "" : String(Math.round(Number(v))) }
            hAlign: Text.AlignRight
            onOpenRequested: function(field) { root.openNumPadRequested(field) }
            onValueCommitted: function(value) { root.passesEdited(Math.round(Number(value))) }
        }
    }
}
