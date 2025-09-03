// FacingDetailsView.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."  // for NumpadField.qml

Item {
    id: root
    anchors.fill: parent

    // Contract with parent (ChildScreen)
    property int opIndex: -1
    property var opData: null
    signal saveRequested(var updated)
    signal openNumPadRequested(var field)   // bubbled up to ChildScreen

    // Editable state (mirrors dataclass)
    property int   css_value: 0
    property int   max_speed: 0
    property real  feed_rate: 0.0
    property real  doc: 0.0
    property real  retract: 0.0
    property real  x_start: 0.0
    property real  z_start: 0.0
    property real  x_end: 0.0
    property real  z_end: 0.0
    property bool  z_end_becomes_new_z0: false

    function applyData(index, data) {
        opIndex = index
        opData = data || {}
        css_value = +((opData.css_value !== undefined) ? opData.css_value : 0)
        max_speed = +((opData.max_speed !== undefined) ? opData.max_speed : 0)
        feed_rate = parseFloat((opData.feed_rate !== undefined) ? opData.feed_rate : 0.0)
        doc       = parseFloat((opData.doc !== undefined) ? opData.doc : 0.0)
        retract   = parseFloat((opData.retract !== undefined) ? opData.retract : 0.0)
        x_start   = parseFloat((opData.x_start !== undefined) ? opData.x_start : 0.0)
        z_start   = parseFloat((opData.z_start !== undefined) ? opData.z_start : 0.0)
        x_end     = parseFloat((opData.x_end !== undefined) ? opData.x_end : 0.0)
        z_end     = parseFloat((opData.z_end !== undefined) ? opData.z_end : 0.0)
        z_end_becomes_new_z0 = !!((opData.z_end_becomes_new_z0 !== undefined) ? opData.z_end_becomes_new_z0 : false)
    }

    // Validators
    IntValidator    { id: intVal }
    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10

        Label {
            text: (opData && opData.type) ? ("Facing — Op #" + (opData.order !== undefined ? opData.order : "N/A")) : "Facing"
            font.pixelSize: 18
            font.bold: true
        }

        GroupBox {
            title: "Cutting Parameters"
            Layout.fillWidth: true

            GridLayout {
                columns: 4
                columnSpacing: 12
                rowSpacing: 8
                anchors.margins: 10
                anchors.fill: parent

                Label { text: "CSS"; Layout.alignment: Qt.AlignVCenter }
                NumpadField {
                    Layout.preferredWidth: 140
                    settingName: "smart_numpad.input-css"
                    validatorObject: intVal
                    value: root.css_value
                    formatter: function(v){ return (v===null||v===undefined)?"":String(v) }
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: root.css_value = value
                }

                Label { text: "Max RPM"; Layout.alignment: Qt.AlignVCenter }
                NumpadField {
                    Layout.preferredWidth: 140
                    settingName: "smart_numpad.input-css-max-rpm-2"
                    validatorObject: intVal
                    value: root.max_speed
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: root.max_speed = value
                }

                Label { text: "Feed (mm/rev)"; Layout.alignment: Qt.AlignVCenter }
                NumpadField {
                    Layout.preferredWidth: 140
                    settingName: "smart_numpad.input-feed"
                    validatorObject: dblVal
                    value: root.feed_rate
                    formatter: function(v){ return (v===null||v===undefined)?"":Number(v).toFixed(3) }
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: root.feed_rate = value
                }

                Label { text: "DOC (mm)"; Layout.alignment: Qt.AlignVCenter }
                NumpadField {
                    Layout.preferredWidth: 140
                    settingName: "facing_doc"
                    validatorObject: dblVal
                    value: root.doc
                    formatter: function(v){ return (v===null||v===undefined)?"":Number(v).toFixed(3) }
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: root.doc = value
                }

                Label { text: "Retract (mm)"; Layout.alignment: Qt.AlignVCenter }
                NumpadField {
                    Layout.preferredWidth: 140
                    settingName: "facing_retract"
                    validatorObject: dblVal
                    value: root.retract
                    formatter: function(v){ return (v===null||v===undefined)?"":Number(v).toFixed(3) }
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: root.retract = value
                }
            }
        }

        GroupBox {
            title: "Facing Geometry"
            Layout.fillWidth: true

            GridLayout {
                columns: 4
                columnSpacing: 12
                rowSpacing: 8
                anchors.margins: 10
                anchors.fill: parent

                Label { text: "X start"; Layout.alignment: Qt.AlignVCenter }
                NumpadField {
                    Layout.preferredWidth: 140
                    settingName: "facing_x_start"
                    validatorObject: dblVal
                    value: root.x_start
                    formatter: function(v){ return (v===null||v===undefined)?"":Number(v).toFixed(3) }
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: root.x_start = value
                }

                Label { text: "Z start"; Layout.alignment: Qt.AlignVCenter }
                NumpadField {
                    Layout.preferredWidth: 140
                    settingName: "facing_z_start"
                    validatorObject: dblVal
                    value: root.z_start
                    formatter: function(v){ return (v===null||v===undefined)?"":Number(v).toFixed(3) }
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: root.z_start = value
                }

                Label { text: "X end"; Layout.alignment: Qt.AlignVCenter }
                NumpadField {
                    Layout.preferredWidth: 140
                    settingName: "facing_x_end"
                    validatorObject: dblVal
                    value: root.x_end
                    formatter: function(v){ return (v===null||v===undefined)?"":Number(v).toFixed(3) }
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: root.x_end = value
                }

                Label { text: "Z end"; Layout.alignment: Qt.AlignVCenter }
                NumpadField {
                    Layout.preferredWidth: 140
                    settingName: "facing_z_end"
                    validatorObject: dblVal
                    value: root.z_end
                    formatter: function(v){ return (v===null||v===undefined)?"":Number(v).toFixed(3) }
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: root.z_end = value
                }

                Item { Layout.columnSpan: 2 }
                CheckBox {
                    Layout.columnSpan: 2
                    text: "Set Z0 at Z end"
                    checked: root.z_end_becomes_new_z0
                    onToggled: root.z_end_becomes_new_z0 = checked
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            Item { Layout.fillWidth: true }
            Button {
                text: "Reset"
                onClicked: { if (root.opData) root.applyData(root.opIndex, root.opData) }
            }
            Button {
                text: "Save"
                onClicked: {
                    var payload = {
                        order: (root.opData && root.opData.order !== undefined) ? root.opData.order : 0,
                        type: "facing",
                        generate_gcode: (root.opData && root.opData.generate_gcode !== undefined) ? root.opData.generate_gcode : true,
                        is_optional_block: (root.opData && root.opData.is_optional_block !== undefined) ? root.opData.is_optional_block : false,
                        css_value: root.css_value,
                        max_speed: root.max_speed,
                        feed_rate: root.feed_rate,
                        doc: root.doc,
                        retract: root.retract,
                        x_start: root.x_start,
                        z_start: root.z_start,
                        x_end: root.x_end,
                        z_end: root.z_end,
                        z_end_becomes_new_z0: root.z_end_becomes_new_z0
                    }
                    root.saveRequested({ index: root.opIndex, payload: payload })
                }
            }
        }
    }
}
