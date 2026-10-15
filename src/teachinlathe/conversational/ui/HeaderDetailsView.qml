// HeaderDetailsView.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."
import touchable_input 1.0
import theme 1.0

Item {
    id: root
    anchors.fill: parent
    property int fieldFontSize: 16
    readonly property int labelWidth: 150
    readonly property int inputWidth: 90
    readonly property int programNameWidth: 360
    readonly property int inputHeight: 48
    readonly property int inputFontSize: 20
    readonly property int rowGap: 20
    readonly property int columnGap: 8

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
    signal openKeyboardRequested(var field)

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

    // the insert type's dropdown, from the tool editors
    component Choice: ComboBox {
        // just wide enough for its text and the arrow: the padding on the
        // right already holds the arrow
        Layout.preferredWidth: leftPadding + contentItem.implicitWidth + rightPadding
        Layout.preferredHeight: Theme.inputHeight
        font.pixelSize: Theme.fontTitle
        contentItem: Text {
            leftPadding: 8
            rightPadding: 8
            text: parent.displayText
            font: parent.font
            color: Theme.foregroundStrong
            horizontalAlignment: Text.AlignLeft
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        delegate: Component {
            ItemDelegate {
                width: parent ? parent.width : 0
                height: Theme.inputHeight
                text: modelData
                font.pixelSize: Theme.fontTitle
            }
        }
    }

    ColumnLayout {
        id: contentColumn
        anchors.fill: parent
        anchors.margins: 10
        spacing: Theme.innerSpacings

        // Program Details, then On Program Finished as tall
        RowLayout {
            id: topRow
            Layout.fillWidth: true
            spacing: Theme.innerSpacings

            GroupBox {
                id: programDetails
                title: "Program Details"
                Layout.alignment: Qt.AlignTop
                font.pixelSize: root.fieldFontSize

                RowLayout {
                    anchors.fill: parent
                    spacing: Theme.spacing

                    Label {
                        text: "Program name"
                        verticalAlignment: Text.AlignVCenter
                        font.pixelSize: root.fieldFontSize
                    }
                    KeyboardField {
                        Layout.preferredWidth: root.programNameWidth
                        Layout.preferredHeight: root.inputHeight
                        font.pixelSize: root.inputFontSize
                        titleText: "Program name"
                        text: root.programName
                        commitUpdatesText: false
                        onOpenRequested: root.openKeyboardRequested(field)
                        onValueCommitted: {
                            root.programName = value
                            root.emitSave()
                        }
                    }

                    Rectangle {
                        implicitWidth: Theme.hairline
                        Layout.fillHeight: true
                        color: Theme.outline
                    }

                    Label {
                        text: "Datum"
                        verticalAlignment: Text.AlignVCenter
                        font.pixelSize: root.fieldFontSize
                    }
                    // G54..G59, saved as the work offset's P number, 1..6
                    Choice {
                        model: ["G54", "G55", "G56", "G57", "G58", "G59"]
                        currentIndex: (root.datum >= 1 && root.datum <= 6) ? root.datum - 1 : 0
                        onActivated: function(index) { root.datum = index + 1; root.emitSave() }
                    }
                }
            }

            GroupBox {
                title: "On Program Finished"
                Layout.alignment: Qt.AlignTop
                // whatever width Program Details leaves, and as tall
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                Layout.preferredWidth: 0
                Layout.preferredHeight: programDetails.implicitHeight
                font.pixelSize: root.fieldFontSize

                ButtonGroup { id: afterLastGroup }

                // the buttons as wide as their texts, the space left shared
                // out equally between them: first at the left, last at the right
                RowLayout {
                    anchors.fill: parent
                    spacing: 0

                    Repeater {
                        model: [
                            { value: "do_nothing", label: "Do nothing" },
                            { value: "g28",        label: "Retract at <b>G28</b>" },
                            { value: "g30",        label: "Retract at <b>G30</b>" }
                        ]
                        // a stretch, then the button; the first without it
                        RowLayout {
                            spacing: 0
                            Layout.fillWidth: index > 0
                            Item { visible: index > 0; Layout.fillWidth: true }
                            RadioButton {
                                text: modelData.label
                                font.pixelSize: Theme.fontBody
                                ButtonGroup.group: afterLastGroup
                                checked: root.afterLastOperation === modelData.value
                                onToggled: if (checked && root.afterLastOperation !== modelData.value) {
                                    root.afterLastOperation = modelData.value
                                    root.emitSave()
                                }
                            }
                        }
                    }
                }
            }
        }

        GroupBox {
            title: "Workpiece Details"
            Layout.alignment: Qt.AlignTop | Qt.AlignLeft
            font.pixelSize: root.fieldFontSize

            ColumnLayout {
                anchors.fill: parent
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
            }
        }

        Item { Layout.fillHeight: true }
    }
}
