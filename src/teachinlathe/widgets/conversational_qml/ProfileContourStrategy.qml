import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

GroupBox {
    id: root
    title: "Profiling Type"
    Layout.fillWidth: true
    font.pixelSize: 16

    // "od" | "id" — resolved automatically from the selected DefineProfile
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

    RowLayout {
        anchors.fill: parent
        spacing: 8
        Label { text: "Profile Type:"; font.pixelSize: 15 }
        Label {
            text: root.profiling_type === "id" ? "ID (Boring)" : "OD (Turning)"
            font.pixelSize: 15
            font.bold: true
            color: root.profiling_type === "id" ? "#42A5F5" : "#66BB6A"
        }
    }
}
