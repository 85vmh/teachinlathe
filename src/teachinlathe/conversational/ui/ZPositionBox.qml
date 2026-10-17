// ZPositionBox.qml — one Z position (or, with ``axis`` "x", one X diameter),
// with its TeachIn, laid over the profile canvas; a mark on the canvas
// points an arrow to it, in its accent.
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import touchable_input 1.0
import theme 1.0

CanvasBox {
    id: root

    property string label: ""
    property real   value: 0.0
    property string settingName: ""
    // "z", or "x": an X diameter, taught in as twice the radius read
    property string axis: "z"
    // the label column's width, so boxes stacked together line up
    property real   labelWidth: labelText.implicitWidth
    readonly property real labelImplicitWidth: labelText.implicitWidth

    signal valueEdited(real value)
    signal openNumPadRequested(var field)

    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }

    RowLayout {
        spacing: 20

        Label {
            id: labelText
            Layout.preferredWidth: root.labelWidth
            text: root.label
            color: root.accent
            font.pixelSize: Theme.fontBody
        }
        NumpadField {
            id: valueField
            Layout.preferredWidth: 100
            settingName: root.settingName
            description: root.label
            validatorObject: dblVal
            value: root.value
            formatter: function (v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: function(field) { root.openNumPadRequested(field) }
            onValueCommitted: root.valueEdited(Number(value))
        }
        Button {
            text: "TeachIn"
            onClicked: valueField.commit(root.axis === "x" ? positionsBridge.teachInX() * 2
                                                           : positionsBridge.teachInZ())
        }
    }
}
