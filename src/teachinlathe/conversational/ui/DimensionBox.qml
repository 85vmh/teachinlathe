// DimensionBox.qml — one dimension's value, laid over the profile canvas;
// the dimension on the canvas points to it, in its colour.
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import touchable_input 1.0
import theme 1.0

CanvasBox {
    id: root
    accent: dimensionColor

    property string label: ""
    property color  dimensionColor: Theme.foreground
    property real   value: 0.0
    property string settingName: ""
    // the label column's width, so boxes stacked together line up
    property real   labelWidth: labelText.implicitWidth
    readonly property real labelImplicitWidth: labelText.implicitWidth

    signal valueEdited(real value)
    signal openNumPadRequested(var field)

    DoubleValidator { id: dblVal; bottom: 0; notation: DoubleValidator.StandardNotation }

    RowLayout {
        spacing: 20

        Label {
            id: labelText
            Layout.preferredWidth: root.labelWidth
            text: root.label
            color: root.dimensionColor
            font.pixelSize: Theme.fontBody
        }
        NumpadField {
            Layout.preferredWidth: 100
            settingName: root.settingName
            description: root.label
            validatorObject: dblVal
            value: root.value
            formatter: function (v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: root.valueEdited(Number(value))
        }
        Label { text: "(mm)"; font.pixelSize: Theme.fontBody }
    }
}
