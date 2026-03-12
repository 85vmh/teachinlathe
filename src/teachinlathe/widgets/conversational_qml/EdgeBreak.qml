// EdgeBreak.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

GroupBox {
    id: root
    title: "Edge Break"
    Layout.preferredWidth: 300
    font.pixelSize: 16

    /* --- Public API --- */
    property string blend_type: "none"   // "none" | "chamfer" | "fillet"
    property real chamfer_width: 0.0
    property real fillet_radius: 0.0

    signal saveRequested(var payload)
    signal openNumPadRequested(var field)

    property bool _loading: false

    function applyData(index, data, fullOp) {
        _loading = true
        var d = data || {}
        blend_type    = (d.blend_type    !== undefined) ? String(d.blend_type)    : "none"
        chamfer_width = (d.chamfer_width !== undefined) ? Number(d.chamfer_width) : 0.0
        fillet_radius = (d.fillet_radius !== undefined) ? Number(d.fillet_radius) : 0.0
        _loading = false
    }

    function emitSave() {
        if (_loading) return
        root.saveRequested({
            edge_break: {
                blend_type:    blend_type,
                chamfer_width: Number(chamfer_width),
                fillet_radius: Number(fillet_radius)
            }
        })
    }

    DoubleValidator {
        id: dblVal; notation: DoubleValidator.StandardNotation
    }

    ButtonGroup { id: modeGroup }

    GridLayout {
        anchors.fill: parent
        columns: 3
        columnSpacing: 12
        rowSpacing: 16

        // --- None (spans all columns) ---
        RadioButton {
            text: "None"
            font.pixelSize: 15
            checked: root.blend_type === "none"
            ButtonGroup.group: modeGroup
            Layout.columnSpan: 3
            onToggled: if (checked) { root.blend_type = "none"; root.emitSave() }
        }

        // --- Chamfer ---
        RadioButton {
            text: "Chamfer"
            font.pixelSize: 15
            checked: root.blend_type === "chamfer"
            ButtonGroup.group: modeGroup
            Layout.minimumWidth: 110
            onToggled: if (checked) { root.blend_type = "chamfer"; root.emitSave() }
        }
        NumpadField {
            Layout.preferredWidth: 100
            enabled: root.blend_type === "chamfer"
            settingName: "edge_break.chamfer_width"
            value: root.chamfer_width
            validatorObject: dblVal
            formatter: function (v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            font.pixelSize: 16
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: { root.chamfer_width = value; root.emitSave() }
        }
        Label {
            text: "(mm)"
            font.pixelSize: 15
            opacity: root.blend_type === "chamfer" ? 1.0 : 0.4
        }

        // --- Fillet ---
        RadioButton {
            text: "Fillet"
            font.pixelSize: 15
            checked: root.blend_type === "fillet"
            ButtonGroup.group: modeGroup
            Layout.minimumWidth: 110
            onToggled: if (checked) { root.blend_type = "fillet"; root.emitSave() }
        }
        NumpadField {
            Layout.preferredWidth: 100
            enabled: root.blend_type === "fillet"
            settingName: "edge_break.fillet_radius"
            value: root.fillet_radius
            validatorObject: dblVal
            formatter: function (v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            font.pixelSize: 16
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: { root.fillet_radius = value; root.emitSave() }
        }
        Label {
            text: "(mm)"
            font.pixelSize: 15
            opacity: root.blend_type === "fillet" ? 1.0 : 0.4
        }
    }
}