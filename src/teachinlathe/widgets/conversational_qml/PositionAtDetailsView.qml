import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."
import "../touchable_input"

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
    property string moveSeq: "xz"
    property bool stopSpindleBeforePositioning: false
    property bool includeM0: false

    function applyData(index, data) {
        _loading = true
        opIndex = index
        opData = data || {}

        var det = (opData.position_details || {})
        xPos = (det.x_pos !== undefined) ? det.x_pos : 0.0
        zPos = (det.z_pos !== undefined) ? det.z_pos : 0.0
        moveSeq = det.move_sequence || "xz"
        stopSpindleBeforePositioning = !!det.stop_spindle_before_positioning
        includeM0 = !!det.include_m0
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
                    move_sequence: moveSeq,
                    stop_spindle_before_positioning: stopSpindleBeforePositioning,
                    include_m0: includeM0
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

            ColumnLayout {
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.alignment: Qt.AlignTop
                spacing: 12

                CheckBox {
                    text: "Stop spindle before positioning"
                    checked: root.stopSpindleBeforePositioning
                    font.pixelSize: 16
                    onToggled: {
                        root.stopSpindleBeforePositioning = checked
                        root.emitSave()
                    }
                }

                GroupBox {
                    title: "Position At"
                    font.pixelSize: 16
                    Layout.fillWidth: true
                    Layout.preferredHeight: positionGrid.implicitHeight + topPadding + bottomPadding + 28
                    Layout.alignment: Qt.AlignTop
                    topPadding: 10
                    bottomPadding: 10
                    leftPadding: 10
                    rightPadding: 10

                    GridLayout {
                        id: positionGrid
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.topMargin: 10
                        columns: 3
                        rowSpacing: 20
                        columnSpacing: 20

                        Label {
                            text: "X pos"
                            Layout.preferredWidth: 60
                            verticalAlignment: Text.AlignVCenter
                        }
                        NumpadField {
                            id: tf_xPos
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
                            onClicked: tf_xPos.commit(positionsBridge.teachInX() * 2)
                        }

                        Label {
                            text: "Z pos"
                            Layout.preferredWidth: 60
                            verticalAlignment: Text.AlignVCenter
                        }
                        NumpadField {
                            id: tf_zPos
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
                            onClicked: tf_zPos.commit(positionsBridge.teachInZ())
                        }
                    }
                }

                CheckBox {
                    text: "Pause program after positioning"
                    checked: root.includeM0
                    font.pixelSize: 16
                    onToggled: {
                        root.includeM0 = checked
                        root.emitSave()
                    }
                }
            }

            GroupBox {
                title: "Move Sequence"
                font.pixelSize: 16
                Layout.fillWidth: true
                Layout.preferredWidth: 1
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
