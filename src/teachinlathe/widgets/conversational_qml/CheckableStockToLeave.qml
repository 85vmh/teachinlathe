import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."
import "../touchable_input"

GroupBox {
    id: root
    title: ""
    Layout.fillWidth: true
    font.pixelSize: 16

    property real radial: 0.0
    property real axial: 0.0
    property bool stock_to_leave_enabled: false
    property bool _loading: false

    signal saveRequested(var payload)
    signal openNumPadRequested(var field)

    label: CheckBox {
        text: "Stock to Leave"
        checked: root.stock_to_leave_enabled
        font.pixelSize: 16
        onToggled: {
            root.stock_to_leave_enabled = checked
            root.emitSave()
        }
    }

    function applyData(data, enabled) {
        _loading = true
        radial = (data && data.radial !== undefined) ? Number(data.radial) : 0.0
        axial = (data && data.axial !== undefined) ? Number(data.axial) : 0.0
        stock_to_leave_enabled = !!enabled
        _loading = false
    }

    function emitSave() {
        if (_loading) return
        root.saveRequested({
            stock_to_leave_enabled: !!stock_to_leave_enabled,
            stock_to_leave: {
                radial: Number(radial),
                axial: Number(axial)
            }
        })
    }

    GridLayout {
        anchors.fill: parent
        columns: 3
        columnSpacing: 20
        rowSpacing: 16
        enabled: root.stock_to_leave_enabled
        opacity: root.stock_to_leave_enabled ? 1.0 : 0.45

        Label {
            text: "Radial"
            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
            font.pixelSize: 16
        }
        NumpadField {
            Layout.preferredWidth: 100
            Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
            settingName: "profile_contour.stock_to_leave.radial"
            value: root.radial
            validatorObject: DoubleValidator { notation: DoubleValidator.StandardNotation }
            formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            font.pixelSize: 16
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: { root.radial = value; root.emitSave() }
        }
        Label {
            text: "(mm)"
            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
            font.pixelSize: 16
        }

        Label {
            text: "Axial"
            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
            font.pixelSize: 16
        }
        NumpadField {
            Layout.preferredWidth: 100
            Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
            settingName: "profile_contour.stock_to_leave.axial"
            value: root.axial
            validatorObject: DoubleValidator { notation: DoubleValidator.StandardNotation }
            formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            font.pixelSize: 16
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: { root.axial = value; root.emitSave() }
        }
        Label {
            text: "(mm)"
            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
            font.pixelSize: 16
        }
    }
}
