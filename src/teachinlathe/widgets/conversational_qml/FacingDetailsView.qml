import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."  // NumpadField.qml

Item {
    id: root
    anchors.fill: parent

    property int opIndex: -1
    property var opData: null
    signal saveRequested(var updated)
    signal openNumPadRequested(var field)

    property bool _loading: false

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
        _loading = true
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
        _loading = false
    }

    function emitSave() {
        if (_loading) return
        var payload = {
            order: (opData && opData.order !== undefined) ? opData.order : 0,
            type: "facing",
            generate_gcode: (opData && opData.generate_gcode !== undefined) ? opData.generate_gcode : true,
            is_optional_block: (opData && opData.is_optional_block !== undefined) ? opData.is_optional_block : false,
            css_value: css_value,
            max_speed: max_speed,
            feed_rate: feed_rate,
            doc: doc,
            retract: retract,
            x_start: x_start,
            z_start: z_start,
            x_end: x_end,
            z_end: z_end,
            z_end_becomes_new_z0: z_end_becomes_new_z0
        }
        saveRequested({ index: opIndex, payload: payload })
    }

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
                    settingName: "facing_css"
                    validatorObject: intVal
                    value: root.css_value
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: { root.css_value = value; root.emitSave() }
                }

                Label { text: "Max RPM"; Layout.alignment: Qt.AlignVCenter }
                NumpadField {
                    Layout.preferredWidth: 140
                    settingName: "facing_max_rpm"
                    validatorObject: intVal
                    value: root.max_speed
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: { root.max_speed = value; root.emitSave() }
                }

                Label { text: "Feed (mm/rev)"; Layout.alignment: Qt.AlignVCenter }
                NumpadField {
                    Layout.preferredWidth: 140
                    settingName: "facing_feed"
                    validatorObject: dblVal
                    value: root.feed_rate
                    formatter: function(v){ return (v==null)?"":Number(v).toFixed(3) }
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: { root.feed_rate = value; root.emitSave() }
                }

                Label { text: "DOC (mm)"; Layout.alignment: Qt.AlignVCenter }
                NumpadField {
                    Layout.preferredWidth: 140
                    settingName: "facing_doc"
                    validatorObject: dblVal
                    value: root.doc
                    formatter: function(v){ return (v==null)?"":Number(v).toFixed(3) }
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: { root.doc = value; root.emitSave() }
                }

                Label { text: "Retract (mm)"; Layout.alignment: Qt.AlignVCenter }
                NumpadField {
                    Layout.preferredWidth: 140
                    settingName: "facing_retract"
                    validatorObject: dblVal
                    value: root.retract
                    formatter: function(v){ return (v==null)?"":Number(v).toFixed(3) }
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: { root.retract = value; root.emitSave() }
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
                    formatter: function(v){ return (v==null)?"":Number(v).toFixed(3) }
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: { root.x_start = value; root.emitSave() }
                }

                Label { text: "Z start"; Layout.alignment: Qt.AlignVCenter }
                NumpadField {
                    Layout.preferredWidth: 140
                    settingName: "facing_z_start"
                    validatorObject: dblVal
                    value: root.z_start
                    formatter: function(v){ return (v==null)?"":Number(v).toFixed(3) }
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: { root.z_start = value; root.emitSave() }
                }

                Label { text: "X end"; Layout.alignment: Qt.AlignVCenter }
                NumpadField {
                    Layout.preferredWidth: 140
                    settingName: "facing_x_end"
                    validatorObject: dblVal
                    value: root.x_end
                    formatter: function(v){ return (v==null)?"":Number(v).toFixed(3) }
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: { root.x_end = value; root.emitSave() }
                }

                Label { text: "Z end"; Layout.alignment: Qt.AlignVCenter }
                NumpadField {
                    Layout.preferredWidth: 140
                    settingName: "facing_z_end"
                    validatorObject: dblVal
                    value: root.z_end
                    formatter: function(v){ return (v==null)?"":Number(v).toFixed(3) }
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: { root.z_end = value; root.emitSave() }
                }

                Item { Layout.columnSpan: 2 }
                CheckBox {
                    Layout.columnSpan: 2
                    text: "Set Z0 at Z end"
                    checked: root.z_end_becomes_new_z0
                    onToggled: { root.z_end_becomes_new_z0 = checked; root.emitSave() }
                }
            }
        }
    }
}
