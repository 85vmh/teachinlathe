// M1Parameters.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."
import theme 1.0

GroupBox {
    id: root
    title: "Pause to Inspect"
    Layout.fillWidth: true
    Layout.minimumWidth: 420
    Layout.preferredWidth: 560
    font.pixelSize: Theme.fontBody

    /* --- Public API --- */
    property var    m1Data: null
    property bool   include_m1: true
    property string inspect_position: "G28"
    property bool   stop_spindle: false

    signal saveRequested(var payload)

    property bool readOnly: false
    property bool _loading: false

    function applyData(data) {
        _loading = true
        m1Data = data || {}
        include_m1       = (m1Data.include_m1       !== undefined) ? !!m1Data.include_m1       : true
        inspect_position = (m1Data.inspect_position !== undefined) ? m1Data.inspect_position   : "G28"
        stop_spindle     = (m1Data.stop_spindle     !== undefined) ? !!m1Data.stop_spindle     : false
        _loading = false
    }

    function emitSave() {
        if (_loading) return
        root.saveRequested({
            m1_parameters: {
                include_m1:       !!include_m1,
                inspect_position: inspect_position,
                stop_spindle:     !!stop_spindle
            }
        })
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        // --- master toggle ---
        RowLayout {
            Layout.fillWidth: true
            CheckBox {
                id: includeBox
                text: "Allow inspection after each pass"
                checked: root.include_m1
                enabled: !root.readOnly
                onToggled: { root.include_m1 = checked; root.emitSave() }
            }
            Item { Layout.fillWidth: true }
        }

        // --- horizontal separator ---
        Rectangle {
            Layout.fillWidth: true
            height: Theme.hairline
            color: Theme.outlineStrong
        }

        // --- Inspect position radio buttons ---
        // each takes half the row, so what the texts leave falls between them
        RowLayout {
            Layout.fillWidth: true
            spacing: 20
            enabled: includeBox.checked && !root.readOnly
            opacity: includeBox.checked ? 1.0 : 0.5

            RadioButton {
                id: rbG28
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                text: "Retract at <b>G28</b>"
                font.pixelSize: Theme.fontBody
                checked: root.inspect_position === "G28"
                onToggled: if (checked) { root.inspect_position = "G28"; root.emitSave() }
            }

            RadioButton {
                id: rbG30
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                text: "Retract at <b>G30</b>"
                font.pixelSize: Theme.fontBody
                checked: root.inspect_position === "G30"
                onToggled: if (checked) { root.inspect_position = "G30"; root.emitSave() }
            }
        }

    }
}
