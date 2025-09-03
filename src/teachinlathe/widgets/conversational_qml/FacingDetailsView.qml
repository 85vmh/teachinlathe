// FacingDetailsView.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root
    anchors.fill: parent

    // Public API expected by ChildScreen
    property int opIndex: -1
    property var opData: null

    signal saveRequested(var updated)   // { index: int, payload: dict }

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

    // Called by parent to populate the form
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
    IntValidator    { id: intVal;   bottom: -2147483648; top: 2147483647 }
    DoubleValidator { id: dblPos;   notation: DoubleValidator.StandardNotation }  // generic

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10

        // Header
        Label {
            text: (opData && opData.type) ? ("Facing — Op #" + (opData.order !== undefined ? opData.order : "N/A")) : "Facing"
            font.pixelSize: 18
            font.bold: true
        }

        // --- Cutting parameters ---
        GroupBox {
            title: "Cutting Parameters"
            Layout.fillWidth: true

            GridLayout {
                columns: 4
                columnSpacing: 12
                rowSpacing: 8
                anchors.margins: 10
                anchors.fill: parent

                Label { text: "CSS";    Layout.alignment: Qt.AlignVCenter }
                TextField {
                    Layout.preferredWidth: 120
                    text: String(root.css_value)
                    validator: intVal
                    inputMethodHints: Qt.ImhDigitsOnly
                    onEditingFinished: {
                        var v = parseInt(text); if (!isNaN(v)) root.css_value = v
                    }
                }

                Label { text: "Max RPM"; Layout.alignment: Qt.AlignVCenter }
                TextField {
                    Layout.preferredWidth: 120
                    text: String(root.max_speed)
                    validator: intVal
                    inputMethodHints: Qt.ImhDigitsOnly
                    onEditingFinished: {
                        var v = parseInt(text); if (!isNaN(v)) root.max_speed = v
                    }
                }

                Label { text: "Feed (mm/rev)"; Layout.alignment: Qt.AlignVCenter }
                TextField {
                    Layout.preferredWidth: 120
                    text: String(root.feed_rate)
                    validator: dblPos
                    onEditingFinished: {
                        var v = parseFloat(text); if (!isNaN(v)) root.feed_rate = v
                    }
                }

                Label { text: "DOC (mm)"; Layout.alignment: Qt.AlignVCenter }
                TextField {
                    Layout.preferredWidth: 120
                    text: String(root.doc)
                    validator: dblPos
                    onEditingFinished: {
                        var v = parseFloat(text); if (!isNaN(v)) root.doc = v
                    }
                }

                Label { text: "Retract (mm)"; Layout.alignment: Qt.AlignVCenter }
                TextField {
                    Layout.preferredWidth: 120
                    text: String(root.retract)
                    validator: dblPos
                    onEditingFinished: {
                        var v = parseFloat(text); if (!isNaN(v)) root.retract = v
                    }
                }
            }
        }

        // --- Geometry ---
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
                TextField {
                    Layout.preferredWidth: 120
                    text: String(root.x_start)
                    validator: dblPos
                    onEditingFinished: {
                        var v = parseFloat(text); if (!isNaN(v)) root.x_start = v
                    }
                }

                Label { text: "Z start"; Layout.alignment: Qt.AlignVCenter }
                TextField {
                    Layout.preferredWidth: 120
                    text: String(root.z_start)
                    validator: dblPos
                    onEditingFinished: {
                        var v = parseFloat(text); if (!isNaN(v)) root.z_start = v
                    }
                }

                Label { text: "X end"; Layout.alignment: Qt.AlignVCenter }
                TextField {
                    Layout.preferredWidth: 120
                    text: String(root.x_end)
                    validator: dblPos
                    onEditingFinished: {
                        var v = parseFloat(text); if (!isNaN(v)) root.x_end = v
                    }
                }

                Label { text: "Z end"; Layout.alignment: Qt.AlignVCenter }
                TextField {
                    Layout.preferredWidth: 120
                    text: String(root.z_end)
                    validator: dblPos
                    onEditingFinished: {
                        var v = parseFloat(text); if (!isNaN(v)) root.z_end = v
                    }
                }

                Item { Layout.columnSpan: 2 } // spacer

                CheckBox {
                    Layout.columnSpan: 2
                    text: "Set Z0 at Z end"
                    checked: root.z_end_becomes_new_z0
                    onToggled: root.z_end_becomes_new_z0 = checked
                }
            }
        }

        // --- Actions ---
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
