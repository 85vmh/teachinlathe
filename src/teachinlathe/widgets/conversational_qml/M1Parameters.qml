// M1Parameters.qml — styled + requested layout (Include → separator → [Grid 3x2 | Stop spindle])
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

GroupBox {
    id: root
    title: "M1 Pause to inspect Parameters"
    Layout.fillWidth: true
    Layout.minimumWidth: 420
    Layout.preferredWidth: 560
    font.pixelSize: 16

    /* --- Public API --- */
    property var  m1Data: null
    property bool include_m1: true
    property real x_inspect: 0.0
    property real z_inspect: 0.0
    property bool stop_spindle: false

    signal saveRequested(var payload)

    signal openNumPadRequested(var field)

    signal teachXRequested()

    signal teachZRequested()

    property bool readOnly: false
    property bool _loading: false

    function applyData(data) {
        _loading = true
        m1Data = data || {}
        include_m1 = (m1Data.include_m1 !== undefined) ? !!m1Data.include_m1 : true
        x_inspect = (m1Data.x_inspect !== undefined) ? Number(m1Data.x_inspect) : 0.0
        z_inspect = (m1Data.z_inspect !== undefined) ? Number(m1Data.z_inspect) : 0.0
        stop_spindle = (m1Data.stop_spindle !== undefined) ? !!m1Data.stop_spindle : false
        _loading = false
    }

    function emitSave() {
        if (_loading) return
        root.saveRequested({
            m1_parameters: {
                include_m1: !!include_m1,
                x_inspect: Number(x_inspect),
                z_inspect: Number(z_inspect),
                stop_spindle: !!stop_spindle
            }
        })
    }

    DoubleValidator {
        id: dblVal; notation: DoubleValidator.StandardNotation
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        // --- master toggle ---
        RowLayout {
            Layout.fillWidth: true
            CheckBox {
                id: includeBox
                text: "Include 'M1' in the generated G-Code"
                checked: root.include_m1
                enabled: !root.readOnly
                onToggled: { root.include_m1 = checked; root.emitSave() }
            }
            Item {
                Layout.fillWidth: true
            }
        }

        // --- horizontal separator ---
        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: "#bdbdbd"
        }

        // --- content row: [ Grid 3x2 | Stop spindle ] ---
        RowLayout {
            id: contentRow
            Layout.fillWidth: true
            spacing: 20

            // LEFT: Grid 3x2 (X/Z Inspect + numpad + TeachIn)
            GridLayout {
                id: gridInspect
                Layout.fillWidth: true
                columns: 3
                columnSpacing: 20
                rowSpacing: 20
                enabled: includeBox.checked && !root.readOnly
                opacity: includeBox.checked ? 1.0 : 0.5

                // Row 1 — X Inspect
                Label {
                    text: "X Inspect"
                    Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                    font.pixelSize: 16
                }
                NumpadField {
                    Layout.preferredWidth: 100
                    Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                    settingName: "m1_x_inspect"
                    validatorObject: dblVal
                    value: root.x_inspect
                    formatter: function (v) {
                        return (v == null) ? "" : Number(v).toFixed(3)
                    }
                    hAlign: Text.AlignRight
                    fontPixelSize: 16
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: { root.x_inspect = value; root.emitSave() }
                }
                Button {
                    text: "TeachIn"
                    Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                    onClicked: root.teachXRequested()
                }

                // Row 2 — Z Inspect
                Label {
                    text: "Z Inspect"
                    Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                    font.pixelSize: 16
                }
                NumpadField {
                    Layout.preferredWidth: 100
                    Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                    settingName: "m1_z_inspect"
                    validatorObject: dblVal
                    value: root.z_inspect
                    formatter: function (v) {
                        return (v == null) ? "" : Number(v).toFixed(3)
                    }
                    hAlign: Text.AlignRight
                    fontPixelSize: 16
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: { root.z_inspect = value; root.emitSave() }
                }
                Button {
                    text: "TeachIn"
                    Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                    onClicked: root.teachZRequested()
                }
            }
        }

        // --- horizontal separator ---
        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: "#bdbdbd"
        }

        RowLayout {
            id: stopSpindle
            Layout.fillWidth: true
            spacing: 20

            CheckBox {
                id: stopSpin
                text: "Stop spindle"
                font.pixelSize: 16
                enabled: includeBox.checked && !root.readOnly
                opacity: includeBox.checked ? 1.0 : 0.5
                checked: root.stop_spindle
                onToggled: { root.stop_spindle = checked; root.emitSave() }
            }
        }
    }
}
