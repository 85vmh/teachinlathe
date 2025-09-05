// HeaderDetailsView.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Item {
    id: root
    anchors.fill: parent

    // --- Input model ---
    // Expect either applyProgram(programDict) or applyData(_, programDict)
    property var programData: null          // { id, header: { name, last_edit, datum, units, workpiece{...} } }

    // --- Header fields (editable) ---
    property string programName:  (programData && programData.header && programData.header.name) ? programData.header.name : ""
    property string units:        (programData && programData.header && programData.header.units) ? programData.header.units : "mm"
    property int    datum:        (programData && programData.header && programData.header.datum !== undefined) ? programData.header.datum : 0

    // Workpiece
    property string material:     (programData && programData.header && programData.header.workpiece && programData.header.workpiece.material) ? programData.header.workpiece.material : ""
    property real   extDia:       (programData && programData.header && programData.header.workpiece && programData.header.workpiece.external_diameter !== undefined) ? programData.header.workpiece.external_diameter : 0.0
    property real   intDia:       (programData && programData.header && programData.header.workpiece && programData.header.workpiece.internal_diameter !== undefined) ? programData.header.workpiece.internal_diameter : 0.0
    property real   stickout:     (programData && programData.header && programData.header.workpiece && programData.header.workpiece.stickout_length !== undefined) ? programData.header.workpiece.stickout_length : 0.0

    // --- Bridge signals (same pattern as other detail views) ---
    signal saveRequested(var updated)
    signal openNumPadRequested(var field)

    // Populate from Program object
    function applyProgram(program) {
        programData = program || {}
        programName = (programData.header && programData.header.name) ? programData.header.name : ""
        units       = (programData.header && programData.header.units) ? programData.header.units : "mm"
        datum       = (programData.header && programData.header.datum !== undefined) ? programData.header.datum : 0

        if (programData.header && programData.header.workpiece) {
            var wp = programData.header.workpiece
            material = (wp.material !== undefined) ? wp.material : ""
            extDia   = (wp.external_diameter !== undefined) ? wp.external_diameter : 0.0
            intDia   = (wp.internal_diameter !== undefined) ? wp.internal_diameter : 0.0
            stickout = (wp.stickout_length  !== undefined) ? wp.stickout_length  : 0.0
        } else {
            material = ""
            extDia = intDia = stickout = 0.0
        }
    }

    // Keep compatibility with ChildScreen.receiveDetailsData if you ever pass the full program
    function applyData(index, data) {
        applyProgram(data)
    }

    function emitSave() {
        var payload = {
            type: "header",
            header: {
                name: programName,
                // last_edit is set server-side; omit or leave as previous
                datum: datum,
                units: units,
                workpiece: {
                    material: material,
                    external_diameter: extDia,
                    internal_diameter: intDia,
                    stickout_length:  stickout
                }
            }
        }
        root.saveRequested({ index: -1, payload: payload })
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 12

        GroupBox {
            title: "Program Details"
            Layout.fillWidth: true

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 10

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Label { text: "Program name"; width: 130; verticalAlignment: Text.AlignVCenter }
                    TextField {
                        Layout.fillWidth: true
                        text: root.programName
                        onTextChanged: { root.programName = text; root.emitSave() }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 16

                    // Datum via NumpadField
                    Label { text: "Datum"; width: 130; verticalAlignment: Text.AlignVCenter }
                    NumpadField {
                        Layout.preferredWidth: 140
                        settingName: "smart_numpad.header-datum"
                        value: root.datum
                        onOpenRequested: root.openNumPadRequested(field)
                        onValueCommitted: { root.datum = Math.round(value); root.emitSave() }
                    }

                    // Units radios
                    Label { text: "Units"; width: 80; verticalAlignment: Text.AlignVCenter }
                    ButtonGroup { id: unitsGroup }
                    RadioButton {
                        text: "mm"
                        checked: root.units === "mm"
                        ButtonGroup.group: unitsGroup
                        onToggled: if (checked) { root.units = "mm"; root.emitSave() }
                    }
                    RadioButton {
                        text: "in"
                        checked: root.units === "in"
                        ButtonGroup.group: unitsGroup
                        onToggled: if (checked) { root.units = "in"; root.emitSave() }
                    }
                }
            }
        }

        GroupBox {
            title: "Workpiece Details"
            Layout.fillWidth: true

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 10

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Label { text: "Material"; width: 130; verticalAlignment: Text.AlignVCenter }
                    TextField {
                        Layout.fillWidth: true
                        text: root.material
                        onTextChanged: { root.material = text; root.emitSave() }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    Label { text: "External Ø"; width: 130; verticalAlignment: Text.AlignVCenter }
                    NumpadField {
                        Layout.preferredWidth: 160
                        settingName: "smart_numpad.workpiece-external-dia"
                        value: root.extDia
                        formatter: function(v){ return (v==null)?"":Number(v).toFixed(3) }
                        onOpenRequested: root.openNumPadRequested(field)
                        onValueCommitted: { root.extDia = value; root.emitSave() }
                    }

                    Label { text: "Internal Ø"; width: 130; verticalAlignment: Text.AlignVCenter }
                    NumpadField {
                        Layout.preferredWidth: 160
                        settingName: "smart_numpad.workpiece-internal-dia"
                        value: root.intDia
                        formatter: function(v){ return (v==null)?"":Number(v).toFixed(3) }
                        onOpenRequested: root.openNumPadRequested(field)
                        onValueCommitted: { root.intDia = value; root.emitSave() }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    Label { text: "Stickout length"; width: 130; verticalAlignment: Text.AlignVCenter }
                    NumpadField {
                        Layout.preferredWidth: 160
                        settingName: "smart_numpad.workpiece-stickout"
                        value: root.stickout
                        formatter: function(v){ return (v==null)?"":Number(v).toFixed(3) }
                        onOpenRequested: root.openNumPadRequested(field)
                        onValueCommitted: { root.stickout = value; root.emitSave() }
                    }
                }
            }
        }
    }
}
