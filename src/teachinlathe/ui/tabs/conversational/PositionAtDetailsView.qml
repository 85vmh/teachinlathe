import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import common.touchable_input
import theme
import common
import TeachInLathe

Item {
    id: root
    anchors.fill: parent

    // The view model of the operation this edits (OperationEditorViewModel.py):
    // the one place what the view shows comes from, and every edit goes to
    required property var editor
    readonly property var op: editor.operation
    readonly property var _det: op.position_details || ({})
    signal teachXRequested(int index)
    signal teachZRequested(int index)
    signal openNumPadRequested(var field)

    readonly property real xPos: _det.x_pos !== undefined ? Number(_det.x_pos) : 0.0
    readonly property real zPos: _det.z_pos !== undefined ? Number(_det.z_pos) : 0.0
    readonly property string moveSeq: _det.move_sequence || "xz"
    readonly property bool stopSpindleBeforePositioning: !!_det.stop_spindle_before_positioning
    readonly property bool includeM0: !!_det.include_m0

    // a change to the position_details: only the fields in ``changes``
    function editDetails(changes) { editor.edit({ position_details: changes }) }

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
            font.pixelSize: Theme.fontLarge
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
                spacing: Theme.margin

                ModelCheckBox {
                    text: "Stop spindle before positioning"
                    checked: root.stopSpindleBeforePositioning
                    font.pixelSize: Theme.fontBody
                    onToggledTo: function(on) { root.editDetails({ stop_spindle_before_positioning: on }) }
                }

                TitledCard {
                    title: "Position At"
                    font.pixelSize: Theme.fontBody
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop

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
                            text: "X Coordinate"
                            Layout.preferredWidth: 100
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
                            onOpenRequested: function(field) { root.openNumPadRequested(field) }
                            onValueCommitted: function(value) { root.editDetails({ x_pos: Number(value) }) }
                        }
                        TeachInButton {
                            onClicked: tf_xPos.commit(PositionsBridge.teachInX() * 2)
                        }

                        Label {
                            text: "Z Coordinate"
                            Layout.preferredWidth: 100
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
                            onOpenRequested: function(field) { root.openNumPadRequested(field) }
                            onValueCommitted: function(value) { root.editDetails({ z_pos: Number(value) }) }
                        }
                        TeachInButton {
                            onClicked: tf_zPos.commit(PositionsBridge.teachInZ())
                        }

                        Item { Layout.preferredHeight: 1 }
                        Item { Layout.preferredHeight: 1 }
                        Item { Layout.preferredHeight: 1 }
                    }
                }

                ModelCheckBox {
                    text: "Pause program after positioning"
                    checked: root.includeM0
                    font.pixelSize: Theme.fontBody
                    onToggledTo: function(on) { root.editDetails({ include_m0: on }) }
                }
            }

            TitledCard {
                title: "Move Sequence"
                font.pixelSize: Theme.fontBody
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.alignment: Qt.AlignTop

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 10

                    ModelRadioButton {
                        text: "X then Z"
                        checked: root.moveSeq === "xz"
                        onChosen: root.editDetails({ move_sequence: "xz" })
                    }
                    ModelRadioButton {
                        text: "Z then X"
                        checked: root.moveSeq === "zx"
                        onChosen: root.editDetails({ move_sequence: "zx" })
                    }
                    ModelRadioButton {
                        text: "Simultaneous"
                        checked: root.moveSeq === "both"
                        onChosen: root.editDetails({ move_sequence: "both" })
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
