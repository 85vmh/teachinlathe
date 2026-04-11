import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

GroupBox {
    id: root
    title: "Profiling Type"
    Layout.fillWidth: true
    font.pixelSize: 16

    property string profiling_type: "od"
    property bool _loading: false

    signal saveRequested(var payload)

    function applyData(data) {
        _loading = true
        profiling_type = (data && data.profiling_type) ? String(data.profiling_type) : "od"
        _loading = false
    }

    function emitSave() {
        if (_loading) return
        root.saveRequested({
            profile_contour_strategy: {
                profiling_type: profiling_type
            }
        })
    }

    ButtonGroup {
        id: contourGroup
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 12

        RadioButton {
            text: "OD Profile Contour"
            font.pixelSize: 16
            checked: root.profiling_type === "od"
            ButtonGroup.group: contourGroup
            onToggled: if (checked) {
                root.profiling_type = "od"
                root.emitSave()
            }
        }

        RadioButton {
            text: "ID Profile Contour"
            font.pixelSize: 16
            checked: root.profiling_type === "id"
            ButtonGroup.group: contourGroup
            onToggled: if (checked) {
                root.profiling_type = "id"
                root.emitSave()
            }
        }
    }
}
