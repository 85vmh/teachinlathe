// HeaderDetailsView.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."
import "../touchable_input"

Item {
    id: root
    anchors.fill: parent
    property int fieldFontSize: 16
    readonly property int labelWidth: 150
    readonly property int inputWidth: 120
    readonly property int programNameWidth: 360
    readonly property int inputHeight: 48
    readonly property int inputFontSize: 20
    readonly property int rowGap: 20
    readonly property int columnGap: 32

    // --- Input model ---
    // Expect either applyProgram(programDict) or applyData(_, programDict)
    property var programData: null          // { id, header: { name, last_edit, datum, units, workpiece{...} } }

    // --- Header fields (editable) ---
    property string programName:  (programData && programData.header && programData.header.name) ? programData.header.name : ""
    property int    datum:        (programData && programData.header && programData.header.datum !== undefined) ? programData.header.datum : 0
    // One of "do_nothing" | "g28" | "g30" — mirrors AfterLastOperation in data_types.py
    property string afterLastOperation: (programData && programData.header && programData.header.after_last_operation) ? programData.header.after_last_operation : "do_nothing"

    // Workpiece
    property string material:     (programData && programData.header && programData.header.workpiece && programData.header.workpiece.material) ? programData.header.workpiece.material : ""
    property real   extDia:       (programData && programData.header && programData.header.workpiece && programData.header.workpiece.external_diameter !== undefined) ? programData.header.workpiece.external_diameter : 0.0
    property real   intDia:       (programData && programData.header && programData.header.workpiece && programData.header.workpiece.internal_diameter !== undefined) ? programData.header.workpiece.internal_diameter : 0.0
    property real   stickout:     (programData && programData.header && programData.header.workpiece && programData.header.workpiece.stickout_length !== undefined) ? programData.header.workpiece.stickout_length : 0.0
    property real   stockLength:  (programData && programData.header && programData.header.workpiece && programData.header.workpiece.stock_length !== undefined) ? programData.header.workpiece.stock_length : 0.0

    // --- Bridge signals (same pattern as other detail views) ---
    signal saveRequested(var updated)
    signal openNumPadRequested(var field)

    // Populate from Program object
    function applyProgram(program) {
        programData = program || {}
        programName = (programData.header && programData.header.name) ? programData.header.name : ""
        datum       = (programData.header && programData.header.datum !== undefined) ? programData.header.datum : 0
        afterLastOperation = (programData.header && programData.header.after_last_operation) ? programData.header.after_last_operation : "do_nothing"

        if (programData.header && programData.header.workpiece) {
            var wp = programData.header.workpiece
            material = (wp.material !== undefined) ? wp.material : ""
            extDia   = (wp.external_diameter !== undefined) ? wp.external_diameter : 0.0
            intDia   = (wp.internal_diameter !== undefined) ? wp.internal_diameter : 0.0
            stickout = (wp.stickout_length  !== undefined) ? wp.stickout_length  : 0.0
            stockLength = (wp.stock_length !== undefined) ? wp.stock_length : 0.0
        } else {
            material = ""
            extDia = intDia = stickout = 0.0
            stockLength = 0.0
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
                units: "mm",
                after_last_operation: afterLastOperation,
                workpiece: {
                    material: material,
                    external_diameter: extDia,
                    internal_diameter: intDia,
                    stickout_length:  stickout,
                    stock_length: stockLength
                }
            }
        }
        root.saveRequested({ index: -1, payload: payload })
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 20

        Label {
            text: "Program Header"
            font.pixelSize: 18
            font.bold: true
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 30
            Layout.alignment: Qt.AlignTop

            ColumnLayout {
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.alignment: Qt.AlignTop
                spacing: 20

                GroupBox {
                    title: "Program Details"
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    font.pixelSize: root.fieldFontSize

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: root.rowGap

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: root.columnGap
                            Label {
                                text: "Program name"
                                Layout.preferredWidth: root.labelWidth
                                verticalAlignment: Text.AlignVCenter
                                font.pixelSize: root.fieldFontSize
                            }
                            TextField {
                                Layout.preferredWidth: root.programNameWidth
                                Layout.preferredHeight: root.inputHeight
                                font.pixelSize: root.inputFontSize
                                text: root.programName
                                onTextChanged: { root.programName = text; root.emitSave() }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: root.columnGap

                            Label {
                                text: "Datum"
                                Layout.preferredWidth: root.labelWidth
                                verticalAlignment: Text.AlignVCenter
                                font.pixelSize: root.fieldFontSize
                            }
                            NumpadField {
                                Layout.preferredWidth: root.inputWidth
                                settingName: "smart_numpad.header-datum"
                                value: root.datum
                                onOpenRequested: root.openNumPadRequested(field)
                                onValueCommitted: { root.datum = Math.round(value); root.emitSave() }
                            }
                        }

                        Item { Layout.preferredHeight: root.rowGap }
                    }
                }

                GroupBox {
                    title: "After the last operation:"
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    font.pixelSize: root.fieldFontSize

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 16

                        ButtonGroup { id: afterLastGroup }

                        Repeater {
                            model: [
                                { value: "do_nothing", label: "Do nothing" },
                                { value: "g28",        label: "Go to G28" },
                                { value: "g30",        label: "Go to G30" }
                            ]
                            RadioButton {
                                text: modelData.label
                                font.pixelSize: root.fieldFontSize
                                ButtonGroup.group: afterLastGroup
                                checked: root.afterLastOperation === modelData.value
                                onToggled: if (checked && root.afterLastOperation !== modelData.value) {
                                    root.afterLastOperation = modelData.value
                                    root.emitSave()
                                }
                            }
                        }

                        Item { Layout.preferredHeight: 8 }
                    }
                }
            }

            GroupBox {
                title: "Workpiece Details"
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.alignment: Qt.AlignTop
                font.pixelSize: root.fieldFontSize

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: root.rowGap

                    GridLayout {
                        columns: 2
                        rowSpacing: root.rowGap
                        columnSpacing: root.columnGap
                        Layout.fillWidth: true

                        Label {
                            text: "External Ø"
                            Layout.preferredWidth: root.labelWidth
                            verticalAlignment: Text.AlignVCenter
                            font.pixelSize: root.fieldFontSize
                        }
                        NumpadField {
                            Layout.preferredWidth: root.inputWidth
                            settingName: "smart_numpad.workpiece-external-dia"
                            value: root.extDia
                            formatter: function(v){ return (v==null)?"":Number(v).toFixed(3) }
                            onOpenRequested: root.openNumPadRequested(field)
                            onValueCommitted: { root.extDia = value; root.emitSave() }
                        }

                        Label {
                            text: "Internal Ø"
                            Layout.preferredWidth: root.labelWidth
                            verticalAlignment: Text.AlignVCenter
                            font.pixelSize: root.fieldFontSize
                        }
                        NumpadField {
                            Layout.preferredWidth: root.inputWidth
                            settingName: "smart_numpad.workpiece-internal-dia"
                            value: root.intDia
                            formatter: function(v){ return (v==null)?"":Number(v).toFixed(3) }
                            onOpenRequested: root.openNumPadRequested(field)
                            onValueCommitted: { root.intDia = value; root.emitSave() }
                        }

                        Label {
                            text: "Stickout length"
                            Layout.preferredWidth: root.labelWidth
                            verticalAlignment: Text.AlignVCenter
                            font.pixelSize: root.fieldFontSize
                        }
                        NumpadField {
                            Layout.preferredWidth: root.inputWidth
                            settingName: "smart_numpad.workpiece-stickout"
                            value: root.stickout
                            formatter: function(v){ return (v==null)?"":Number(v).toFixed(3) }
                            onOpenRequested: root.openNumPadRequested(field)
                            onValueCommitted: { root.stickout = value; root.emitSave() }
                        }

                        Label {
                            text: "Stock Length"
                            Layout.preferredWidth: root.labelWidth
                            verticalAlignment: Text.AlignVCenter
                            font.pixelSize: root.fieldFontSize
                        }
                        NumpadField {
                            Layout.preferredWidth: root.inputWidth
                            settingName: "smart_numpad.workpiece-stock-length"
                            description: "Stock Length"
                            value: root.stockLength
                            formatter: function(v){ return (v==null)?"":Number(v).toFixed(3) }
                            onOpenRequested: root.openNumPadRequested(field)
                            onValueCommitted: { root.stockLength = value; root.emitSave() }
                        }
                    }

                    Item { Layout.preferredHeight: root.rowGap }
                }
            }
        }
    }
}
