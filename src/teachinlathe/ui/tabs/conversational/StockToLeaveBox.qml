// StockToLeaveBox.qml — radial / axial stock to leave, laid over the profile
// canvas; the offset on the canvas points to it, in labelColor.
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import common.touchable_input 1.0
import theme 1.0

CanvasBox {
    id: root
    accent: labelColor

    property color labelColor: Theme.foreground

    property real radial: 0.0
    property real axial: 0.0

    signal radialEdited(real value)
    signal axialEdited(real value)
    signal openNumPadRequested(var field)

    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }

    GridLayout {
        columns: 3
        columnSpacing: 20
        rowSpacing: 20

        Label { text: "Radial"; color: root.labelColor; font.pixelSize: Theme.fontBody }
        NumpadField {
            Layout.preferredWidth: 100
            settingName: "stock_to_leave.radial"
            validatorObject: dblVal
            value: root.radial
            formatter: function (v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: root.radialEdited(Number(value))
        }
        Label { text: "(mm)"; font.pixelSize: Theme.fontBody }

        Label { text: "Axial"; color: root.labelColor; font.pixelSize: Theme.fontBody }
        NumpadField {
            Layout.preferredWidth: 100
            settingName: "stock_to_leave.axial"
            validatorObject: dblVal
            value: root.axial
            formatter: function (v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: root.axialEdited(Number(value))
        }
        Label { text: "(mm)"; font.pixelSize: Theme.fontBody }
    }
}
