// ProfilingOptions.qml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import common.touchable_input
import theme
import common

TitledCard {
    id: root
    title: "Profiling Options"
    Layout.fillWidth: true
    Layout.minimumWidth: 420
    Layout.preferredWidth: 560
    font.pixelSize: Theme.fontBody

    /* --- Public API --- */
    // the operation's profiling_options, as its editor has them: all it shows
    property var options: ({})
    readonly property var _o: options || {}
    readonly property string strategy: _o.strategy !== undefined ? String(_o.strategy) : "rough"   // "rough" | "finish"
    readonly property real radial: _o.radial !== undefined ? Number(_o.radial) : 0.0
    readonly property real axial: _o.axial !== undefined ? Number(_o.axial) : 0.0
    readonly property int finish_passes: _o.finish_passes !== undefined ? Number(_o.finish_passes) : 1
    readonly property int spring_passes: _o.finish_spring_passes !== undefined ? Number(_o.finish_spring_passes) : 0

    // a change to the profiling_options: only the fields in it
    signal edited(var changes)
    signal openNumPadRequested(var field)
    signal addFinishRequested()

    property bool readOnly: false

    DoubleValidator {
        id: dblVal; notation: DoubleValidator.StandardNotation
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        // --- master toggle ---
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacingLarge

            ModelRadioButton {
                text: "Roughing"
                font.pixelSize: Theme.fontSmall
                checked: root.strategy === "rough"
                onChosen: root.edited({ strategy: "rough" })
            }
            ModelRadioButton {
                text: "Finishing"
                font.pixelSize: Theme.fontSmall
                checked: root.strategy === "finish"
                onChosen: root.edited({ strategy: "finish" })
            }
            Item {
                Layout.fillWidth: true
            }

            Button {
                text: "Add a finish operation"
                visible: root.strategy === "rough"
                onClicked: root.addFinishRequested()
            }
        }

        Frame {
            id: frameBox
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            padding: 10
            background: Rectangle {
                radius: Theme.radius
                border.width: Theme.hairline
                border.color: Theme.outlineStrong
                color: "transparent"
            }

            Layout.preferredHeight: Math.max(roughItem.implicitHeight, finishItem.implicitHeight) + 2 * padding
            clip: true

            Item {
                id: pages
                anchors.fill: parent

                // ---- roughing page ----
                Item {
                    id: roughItem
                    anchors.fill: parent
                    visible: root.strategy === "rough"
                    implicitHeight: roughGrid.implicitHeight + 2

                    GridLayout {
                        id: roughGrid
                        anchors.fill: parent
                        columns: 3
                        columnSpacing: Theme.spacing
                        rowSpacing: 16

                        Label {
                            text: "Radial"
                            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                            font.pixelSize: Theme.fontBody
                        }
                        NumpadField {
                            Layout.preferredWidth: 100
                            Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                            settingName: "profiling.stock_x"
                            value: root.radial
                            validatorObject: DoubleValidator { notation: DoubleValidator.StandardNotation }
                            formatter: function (v) { return (v == null) ? "" : Number(v).toFixed(3) }
                            hAlign: Text.AlignRight
                            onOpenRequested: function(field) { root.openNumPadRequested(field) }
                            onValueCommitted: function(value) { root.edited({ radial: Number(value) }) }
                        }
                        Label {
                            text: "(mm)"
                            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                            font.pixelSize: Theme.fontBody
                        }

                        Label {
                            text: "Axial"
                            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                            font.pixelSize: Theme.fontBody
                        }
                        NumpadField {
                            Layout.preferredWidth: 100
                            Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                            settingName: "profiling.stock_z"
                            value: root.axial
                            validatorObject: DoubleValidator { notation: DoubleValidator.StandardNotation }
                            formatter: function (v) { return (v == null) ? "" : Number(v).toFixed(3) }
                            hAlign: Text.AlignRight
                            onOpenRequested: function(field) { root.openNumPadRequested(field) }
                            onValueCommitted: function(value) { root.edited({ axial: Number(value) }) }
                        }
                        Label {
                            text: "(mm)"
                            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                            font.pixelSize: Theme.fontBody
                        }
                    }
                }

                // ---- finishing page ----
                Item {
                    id: finishItem
                    anchors.fill: parent
                    visible: root.strategy === "finish"
                    implicitHeight: finishGrid.implicitHeight + 2

                    GridLayout {
                        id: finishGrid
                        anchors.fill: parent
                        columns: 2
                        columnSpacing: 20
                        rowSpacing: 16

                        Label {
                            text: "Finish passes"
                            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                            font.pixelSize: Theme.fontBody
                        }
                        NumpadField {
                            Layout.preferredWidth: 50
                            Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                            settingName: "profiling.finish_passes"
                            value: root.finish_passes
                            validatorObject: IntValidator {
                                bottom: 1
                            }
                            hAlign: Text.AlignRight
                            onOpenRequested: function(field) { root.openNumPadRequested(field) }
                            onValueCommitted: function(value) { root.edited({ finish_passes: Math.max(1, Math.round(value)) }) }
                        }

                        Label {
                            text: "Spring passes"
                            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                            font.pixelSize: Theme.fontBody
                        }
                        NumpadField {
                            Layout.preferredWidth: 50
                            Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                            settingName: "spindle.rpm"
                            value: root.spring_passes
                            validatorObject: IntValidator {
                                bottom: 0
                            }
                            hAlign: Text.AlignRight
                            onOpenRequested: function(field) { root.openNumPadRequested(field) }
                            onValueCommitted: function(value) { root.edited({ finish_spring_passes: Math.max(0, Math.round(value)) }) }
                        }
                    }
                }
            }
        }
    }
}
