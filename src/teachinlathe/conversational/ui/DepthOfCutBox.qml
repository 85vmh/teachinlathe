// DepthOfCutBox.qml — depth of cut (Ap) and retract, laid over the profile
// canvas, labelled in the colours the toolpath draws cuts and rapids in.
// showDoc: false leaves retract alone, for a single pass.
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import touchable_input 1.0
import theme 1.0

CanvasBox {
    id: root
    property real doc: 0.0
    property real retract: 0.0
    property bool showDoc: true
    // the toolpath's colours: cuts for the depth of cut, rapids for retract
    property color docColor: Theme.foreground
    property color retractColor: Theme.foreground

    accent: docColor

    signal docEdited(real value)
    signal retractEdited(real value)
    signal openNumPadRequested(var field)

    DoubleValidator { id: dblVal; bottom: 0; notation: DoubleValidator.StandardNotation }

    GridLayout {
        columns: 3
        columnSpacing: 20
        rowSpacing: 20

        Label { visible: root.showDoc; text: "Ap"; color: root.docColor; font.pixelSize: Theme.fontBody; font.bold: true }
        NumpadField {
            visible: root.showDoc
            Layout.preferredWidth: 100
            settingName: "cutting.doc"
            validatorObject: dblVal
            value: root.doc
            formatter: function (v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: root.docEdited(Number(value))
        }
        Label { visible: root.showDoc; text: "(mm)"; font.pixelSize: Theme.fontBody }

        Label { text: "Retract"; color: root.retractColor; font.pixelSize: Theme.fontBody }
        NumpadField {
            Layout.preferredWidth: 100
            settingName: "cutting.retract"
            validatorObject: dblVal
            value: root.retract
            formatter: function (v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: root.retractEdited(Number(value))
        }
        Label { text: "(mm)"; font.pixelSize: Theme.fontBody }
    }
}
