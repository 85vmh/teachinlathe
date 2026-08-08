import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../touchable_input"

Rectangle {
    id: root

    property var primData: ({})
    property int primIdx: 0
    property bool isSelected: false

    signal primUpdated(int idx, var data)
    signal deleteRequested(int idx)
    signal openNumPadRequested(var field)
    signal tapped()

    color: isSelected ? "#dbeafe" : "#f5f7fb"
    radius: 8
    border.color: isSelected ? "#3b82f6" : "#cccccc"
    border.width: isSelected ? 2 : 1
    height: content.implicitHeight + 24

    TapHandler { onTapped: root.tapped() }
    IntValidator { id: intVal; bottom: 1; top: 999 }
    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }

    function _commit(key, value) {
        var d = JSON.parse(JSON.stringify(primData || {}))
        d.type = "repeat"
        d[key] = value
        root.primUpdated(primIdx, d)
    }

    RowLayout {
        id: content
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 12
        spacing: 10

        Label {
            text: (primIdx + 1) + ". Repeat"
            font.pixelSize: 16
            font.bold: true
            Layout.preferredWidth: 92
        }

        Label { text: "Primitive"; font.pixelSize: 14 }
        NumpadField {
            Layout.preferredWidth: 72
            settingName: "radial_profile.repeat_primitive_id"
            validatorObject: intVal
            value: primData.repeat_primitive_id !== undefined ? primData.repeat_primitive_id : 1
            formatter: function(v) { return v == null ? "" : String(Math.round(Number(v))) }
            hAlign: Text.AlignHCenter
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: root._commit("repeat_primitive_id", Math.round(value))
        }

        Label { text: "Count"; font.pixelSize: 14 }
        NumpadField {
            Layout.preferredWidth: 72
            settingName: "radial_profile.repeat_count"
            validatorObject: intVal
            value: primData.repeat_count !== undefined ? primData.repeat_count : 1
            formatter: function(v) { return v == null ? "" : String(Math.round(Number(v))) }
            hAlign: Text.AlignHCenter
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: root._commit("repeat_count", Math.round(value))
        }

        Label { text: "Z Offset"; font.pixelSize: 14 }
        NumpadField {
            Layout.preferredWidth: 100
            settingName: "radial_profile.repeat_z_offset"
            validatorObject: dblVal
            seedNumpadFromValue: true
            value: primData.z_offset !== undefined ? primData.z_offset : 0
            formatter: function(v) { return v == null ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: root._commit("z_offset", Number(value))
        }

        Item { Layout.fillWidth: true }

        Button {
            text: "Delete"
            Layout.preferredWidth: 84
            onClicked: root.deleteRequested(primIdx)
        }
    }
}
