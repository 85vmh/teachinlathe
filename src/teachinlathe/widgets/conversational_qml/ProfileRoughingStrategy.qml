// ProfileRoughingStrategy.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

GroupBox {
    id: root
    title: "Profiling Type"
    Layout.fillWidth: true
    font.pixelSize: 16

    // "od" | "id"
    property string profiling_type: "od"
    // "axial" | "radial" | "diagonal_interior" | "diagonal_exterior"
    property string pass_type: "axial"

    property bool _loading: false

    signal saveRequested(var payload)

    function applyData(data) {
        _loading = true
        profiling_type = (data && data.profiling_type) ? String(data.profiling_type) : "od"
        pass_type      = (data && data.pass_type)      ? String(data.pass_type)      : "axial"
        tabBar.currentIndex = (profiling_type === "id") ? 1 : 0
        _loading = false
    }

    function emitSave() {
        if (_loading) return
        root.saveRequested({
            profile_roughing_strategy: {
                profiling_type: profiling_type,
                pass_type:      pass_type
            }
        })
    }

    ButtonGroup { id: passGroup }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        TabBar {
            id: tabBar
            Layout.fillWidth: true
            implicitHeight: 40
            currentIndex: root.profiling_type === "id" ? 1 : 0

            background: Rectangle {
                color: "transparent"
                border.color: "#bdbdbd"
                border.width: 1
                radius: 4
            }

            onCurrentIndexChanged: {
                if (_loading) return
                var newType = (currentIndex === 0) ? "od" : "id"
                if (newType === root.profiling_type) return
                root.profiling_type = newType
                if (newType === "od" && pass_type !== "axial" && pass_type !== "radial")
                    root.pass_type = "axial"
                root.emitSave()
            }

            TabButton {
                id: odTab
                text: "Profile Turning (OD)"
                font.pixelSize: 15
                height: 40
                background: Rectangle {
                    color: odTab.checked ? "#1E88E5" : "transparent"
                    radius: 4
                }
                contentItem: Text {
                    text: odTab.text
                    font: odTab.font
                    color: odTab.checked ? "white" : "#333333"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }

            TabButton {
                id: idTab
                text: "Profile Boring (ID)"
                font.pixelSize: 15
                height: 40
                background: Rectangle {
                    color: idTab.checked ? "#1E88E5" : "transparent"
                    radius: 4
                }
                contentItem: Text {
                    text: idTab.text
                    font: idTab.font
                    color: idTab.checked ? "white" : "#333333"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }

        // 2×2 grid: col 0 = Axial/Radial, col 1 = 45° interior/exterior
        // 45° buttons use opacity so space is always reserved → constant height for OD and ID
        GridLayout {
            columns: 2
            columnSpacing: 24
            rowSpacing: 6

            RadioButton {
                text: "Axial Passes"
                font.pixelSize: 15
                checked: root.pass_type === "axial"
                ButtonGroup.group: passGroup
                onToggled: if (checked) { root.pass_type = "axial"; root.emitSave() }
            }
            RadioButton {
                text: "45° Passes toward interior"
                font.pixelSize: 15
                opacity: root.profiling_type === "id" ? 1.0 : 0.0
                enabled: root.profiling_type === "id"
                checked: root.pass_type === "diagonal_interior"
                ButtonGroup.group: passGroup
                onToggled: if (checked) { root.pass_type = "diagonal_interior"; root.emitSave() }
            }

            RadioButton {
                text: "Radial Passes"
                font.pixelSize: 15
                checked: root.pass_type === "radial"
                ButtonGroup.group: passGroup
                onToggled: if (checked) { root.pass_type = "radial"; root.emitSave() }
            }
            RadioButton {
                text: "45° Passes toward exterior"
                font.pixelSize: 15
                opacity: root.profiling_type === "id" ? 1.0 : 0.0
                enabled: root.profiling_type === "id"
                checked: root.pass_type === "diagonal_exterior"
                ButtonGroup.group: passGroup
                onToggled: if (checked) { root.pass_type = "diagonal_exterior"; root.emitSave() }
            }
        }
    }
}
