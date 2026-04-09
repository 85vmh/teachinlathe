import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Item {
    id: root
    anchors.fill: parent

    property int opIndex: -1
    property var opData: null

    signal saveRequested(var updated)
    signal teachXRequested(int index)
    signal teachZRequested(int index)
    signal openNumPadRequested(var field)

    property bool _loading: false

    property real xPos: 0.0
    property real zPos: 0.0
    property string coordType: "absolute"
    property string moveSeq: "xz"

    function applyData(index, data) {
        _loading = true
        opIndex = index
        opData = data || {}

        var det = (opData.position_details || {})
        xPos = (det.x_pos !== undefined) ? det.x_pos : 0.0
        zPos = (det.z_pos !== undefined) ? det.z_pos : 0.0
        coordType = det.coordinate_type || "absolute"
        moveSeq = det.move_sequence || "xz"
        _loading = false
    }

    function emitSave() {
        if (_loading) return
        saveRequested({
            index: opIndex,
            payload: {
                order: (opData && opData.order !== undefined) ? opData.order : 0,
                type: "positionAt",
                generate_gcode: (opData && opData.generate_gcode !== undefined) ? opData.generate_gcode : true,
                is_optional_block: (opData && opData.is_optional_block !== undefined) ? opData.is_optional_block : false,
                position_details: {
                    x_pos: xPos,
                    z_pos: zPos,
                    coordinate_type: coordType,
                    move_sequence: moveSeq
                }
            }
        })
    }

    DoubleValidator {
        id: dblVal
        notation: DoubleValidator.StandardNotation
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 50

        Label {
            text: "Position At"
            font.pixelSize: 18
            font.bold: true
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 30
            Layout.alignment: Qt.AlignTop

            GroupBox {
                title: "Position At"
                font.pixelSize: 16
                Layout.fillWidth: true
                Layout.preferredWidth: 6
                Layout.alignment: Qt.AlignTop

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 24

                    Label {
                        text: "Coordinate Type"
                        font.pixelSize: 16
                        Layout.alignment: Qt.AlignCenter
                    }

                    ColumnLayout {
                        spacing: 20
                        Layout.alignment: Qt.AlignCenter

                        ButtonGroup {
                            id: coordGroup
                        }

                        RadioButton {
                            text: "Relative"
                            checked: root.coordType === "relative"
                            ButtonGroup.group: coordGroup
                            onToggled: if (checked) {
                                root.coordType = "relative"
                                root.emitSave()
                            }
                        }
                        RadioButton {
                            text: "Absolute"
                            checked: root.coordType === "absolute"
                            ButtonGroup.group: coordGroup
                            onToggled: if (checked) {
                                root.coordType = "absolute"
                                root.emitSave()
                            }
                        }
                    }

                    Item { Layout.fillWidth: true }

                    Rectangle {
                        width: 1
                        Layout.alignment: Qt.AlignCenter
                        color: "#cccccc"
                        Layout.fillHeight: true
                    }

                    Item { Layout.fillWidth: true }

                    GridLayout {
                        columns: 3
                        rowSpacing: 20
                        columnSpacing: 20
                        Layout.alignment: Qt.AlignRight
                        Layout.fillWidth: true

                        Label {
                            text: "X pos"
                            Layout.preferredWidth: 60
                            verticalAlignment: Text.AlignVCenter
                        }
                        NumpadField {
                            Layout.preferredWidth: 100
                            settingName: "positionat_x_pos"
                            validatorObject: dblVal
                            value: root.xPos
                            formatter: function (v) {
                                return (v == null) ? "" : Number(v).toFixed(3)
                            }
                            onOpenRequested: root.openNumPadRequested(field)
                            onValueCommitted: { root.xPos = value; root.emitSave() }
                        }
                        Button {
                            text: "TeachIn"
                            onClicked: root.teachXRequested(root.opIndex)
                        }

                        Label {
                            text: "Z pos"
                            Layout.preferredWidth: 60
                            verticalAlignment: Text.AlignVCenter
                        }
                        NumpadField {
                            Layout.preferredWidth: 100
                            settingName: "positionat_z_pos"
                            validatorObject: dblVal
                            value: root.zPos
                            formatter: function (v) {
                                return (v == null) ? "" : Number(v).toFixed(3)
                            }
                            onOpenRequested: root.openNumPadRequested(field)
                            onValueCommitted: { root.zPos = value; root.emitSave() }
                        }
                        Button {
                            text: "TeachIn"
                            onClicked: root.teachZRequested(root.opIndex)
                        }
                    }
                }
            }

            GroupBox {
                title: "Move Sequence"
                font.pixelSize: 16
                Layout.fillWidth: true
                Layout.preferredWidth: 4
                Layout.alignment: Qt.AlignTop

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 10

                    ButtonGroup {
                        id: moveGroup
                    }

                    RadioButton {
                        text: "X then Z"
                        checked: root.moveSeq === "xz"
                        ButtonGroup.group: moveGroup
                        onToggled: if (checked) {
                            root.moveSeq = "xz"
                            root.emitSave()
                        }
                    }
                    RadioButton {
                        text: "Z then X"
                        checked: root.moveSeq === "zx"
                        ButtonGroup.group: moveGroup
                        onToggled: if (checked) {
                            root.moveSeq = "zx"
                            root.emitSave()
                        }
                    }
                    RadioButton {
                        text: "Simultaneous"
                        checked: root.moveSeq === "both"
                        ButtonGroup.group: moveGroup
                        onToggled: if (checked) {
                            root.moveSeq = "both"
                            root.emitSave()
                        }
                    }

                    Item {
                        Layout.fillHeight: true
                    }
                }
            }
        }

        Item {
            Layout.fillHeight: true
        }
    }
}
