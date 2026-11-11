// ProfileField.qml — a card's number: its label and the input the numpad edits.
import QtQuick
import QtQuick.Layouts
import common.touchable_input

FieldCell {
    id: root

    property string settingName: ""
    property string description: ""
    property var value: null

    signal openRequested(var field)
    signal committed(var value)

    NumpadField {
        description: root.description
        Layout.preferredWidth: CardMetrics.inputWidth
        settingName: root.settingName
        validatorObject: DoubleValidator { notation: DoubleValidator.StandardNotation }
        seedNumpadFromValue: true
        value: root.value
        formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
        hAlign: Text.AlignRight
        onOpenRequested: function(field) { root.openRequested(field) }
        onValueCommitted: function(value) { root.committed(value) }
    }
}
