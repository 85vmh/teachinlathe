import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../touchable_input"

RowLayout {
    id: root
    property string label: ""
    property string unit: ""
    property string settingName: ""
    property var value: ""
    property bool editable: true

    signal openNumPadRequested(Item field)
    signal committed(var value)

    spacing: 8

    Text {
        Layout.preferredWidth: 104
        text: root.label
        color: "#1e2430"
        font.pixelSize: 17
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
        Layout.preferredHeight: 40
        visible: !root.editable
        text: String(root.value)
        color: "#0f172a"
        font.pixelSize: 17
        font.family: "Noto Sans Mono"
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }

    Text {
        Layout.preferredWidth: 66
        text: root.unit
        color: "#1e2430"
        font.pixelSize: 16
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
