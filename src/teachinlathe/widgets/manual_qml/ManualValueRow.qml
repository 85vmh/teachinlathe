import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../touchable_input"
import theme 1.0

RowLayout {
    id: root
    property string label: ""
    property string unit: ""
    property string settingName: ""
    property var value: ""
    property bool editable: true
    property bool valueBold: false

    signal openNumPadRequested(Item field)
    signal committed(var value)

    spacing: Theme.spacingSmall

    Text {
        Layout.preferredWidth: 104
        text: root.label
        color: Theme.foreground
        font.pixelSize: Theme.fontLarge
        horizontalAlignment: Text.AlignRight
        verticalAlignment: Text.AlignVCenter
    }

    NumpadField {
        id: input
        Layout.preferredWidth: 78
        visible: root.editable
        enabled: root.editable
        value: root.value
        settingName: root.settingName
        hAlign: Text.AlignHCenter
        formatter: function(v) { return (v === null || v === undefined) ? "" : String(v) }
        parser: function(s) { return String(s) }
        onOpenRequested: root.openNumPadRequested(field)
        onValueCommitted: root.committed(value)
    }

    Text {
        Layout.preferredWidth: 78
        Layout.preferredHeight: Theme.buttonHeight
        visible: !root.editable
        text: String(root.value)
        color: Theme.foregroundStrong
        font.pixelSize: Theme.fontLarge
        font.bold: root.valueBold
        font.family: "Noto Sans Mono"
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }

    Text {
        Layout.preferredWidth: 66
        text: root.unit
        color: Theme.foreground
        font.pixelSize: Theme.fontBody
        verticalAlignment: Text.AlignVCenter
    }

    function setDisplayValue(v) {
        root.value = v
        if (root.editable) {
            input.value = v
            input.text = input.formatter(v)
        }
    }
}
