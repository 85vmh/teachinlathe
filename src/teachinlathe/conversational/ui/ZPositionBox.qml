// ZPositionBox.qml — one Z position, with its TeachIn, laid over the
// profile canvas; a target on the canvas points an arrow to it, in its
// accent.
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

    signal valueEdited(real value)
    signal openNumPadRequested(var field)

    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }

    RowLayout {
        spacing: 20

        Label { text: root.label; color: root.accent; font.pixelSize: Theme.fontBody }
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
            onClicked: valueField.commit(positionsBridge.teachInZ())
        }
    }
}
