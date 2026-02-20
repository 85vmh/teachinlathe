// EdgeBreak.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

GroupBox {
    id: root
    title: "Edge Break"
    Layout.fillWidth: true
    Layout.minimumWidth: 420
    Layout.preferredWidth: 560
    font.pixelSize: 16

    /* --- Public API --- */
    property var  partingOptions: null
    property string blend_type: "chamfer"   // "chamfer" | "fillet"
    property real chamfer_width: 0.0
    property real fillet_radius: 0.0

    signal saveRequested(var payload)

    signal openNumPadRequested(var field)

    property bool readOnly: false
    property bool _loading: false

    function applyData(data) {
        _loading = true
        partingOptions = data || {}

        print("applyData -> data:\n" + JSON.stringify(opData.edge_break, null, 2))

        blend_type = (partingOptions.edgeBreak !== undefined) ? String(partingOptions.edgeBreak) : "chamfer"
        chamfer_width = (partingOptions.chamfer_width !== undefined) ? Number(partingOptions.chamfer_width) : 0.0
        fillet_radius = (partingOptions.fillet_radius !== undefined) ? Number(partingOptions.fillet_radius) : 0.0
        _loading = false
    }

    function emitSave() {
        if (_loading) return
        root.saveRequested({
            edge_break: {
                blend_type: blend_type,
                chamfer_width: Number(chamfer_width),
                fillet_radius: Number(fillet_radius),
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
            spacing: 16

            ButtonGroup {
                id: modeGroup
            }
            RadioButton {
                text: "Chamfer"
                font.pixelSize: 15
                checked: root.blend_type === "chamfer"
                ButtonGroup.group: modeGroup
                onToggled: if (checked) {
                    root.blend_type = "chamfer";
                    root.emitSave()
                }
            }
            RadioButton {
                text: "Fillet"
                font.pixelSize: 15
                checked: root.blend_type === "fillet"
                ButtonGroup.group: modeGroup
                onToggled: if (checked) {
                    root.blend_type = "fillet";
                    root.emitSave()
                }
            }
            Item {
                Layout.fillWidth: true
            }
        }

        Frame {
            id: frameBox
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            padding: 10
            background: Rectangle {
                radius: 6
                border.width: 1
                border.color: "#bdbdbd"
                color: "transparent"
            }

            Layout.preferredHeight: Math.max(chamferGrid.implicitHeight, filletGrid.implicitHeight) + 2 * padding
            clip: true

            Item {
                id: pages
                anchors.fill: parent

                // ---- roughing page ----
                Item {
                    id: chamferItem
                    anchors.fill: parent
                    visible: root.blend_type === "chamfer"
                    implicitHeight: chamferGrid.implicitHeight + 2

                    GridLayout {
                        id: chamferGrid
                        anchors.fill: parent
                        columns: 3
                        columnSpacing: 20
                        rowSpacing: 16

                        Label {
                            text: "Chamfer width"
                            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                            font.pixelSize: 16
                        }
                        NumpadField {
                            Layout.preferredWidth: 100
                            Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                            settingName: "spindle.css.value"
                            value: root.chamfer_width
                            validatorObject: DoubleValidator {
                                notation: DoubleValidator.StandardNotation
                            }
                            formatter: function (v) {
                                return (v == null) ? "" : Number(v).toFixed(3)
                            }
                            hAlign: Text.AlignRight
                            font.pixelSize: 16
                            onOpenRequested: root.openNumPadRequested(field)
                            onValueCommitted: { root.chamfer_width = value; root.emitSave() }
                        }
                        Label {
                            text: "(mm)"
                            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                            font.pixelSize: 16
                        }
                    }
                }

                // ---- finishing page ----
                Item {
                    id: filletItem
                    anchors.fill: parent
                    visible: root.blend_type === "fillet"
                    implicitHeight: finishGrid.implicitHeight + 2

                    GridLayout {
                        id: filletGrid
                        anchors.fill: parent
                        columns: 3
                        columnSpacing: 20
                        rowSpacing: 16

                        Label {
                            text: "Fillet radius"
                            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                            font.pixelSize: 16
                        }
                        NumpadField {
                            Layout.preferredWidth: 100
                            Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                            settingName: "spindle.css.maxrpm"
                            value: root.fillet_radius
                            validatorObject: DoubleValidator {
                                notation: DoubleValidator.StandardNotation
                            }
                            formatter: function (v) {
                                return (v == null) ? "" : Number(v).toFixed(3)
                            }
                            hAlign: Text.AlignRight
                            font.pixelSize: 16
                            onOpenRequested: root.openNumPadRequested(field)
                            onValueCommitted: { root.fillet_radius = value; root.emitSave() }
                        }
                        Label {
                            text: "(mm)"
                            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                            font.pixelSize: 16
                        }
                    }
                }
            }
        }
    }
}
