// ProfilingOptions.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

GroupBox {
    id: root
    title: "Profiling Options"
    Layout.fillWidth: true
    Layout.minimumWidth: 420
    Layout.preferredWidth: 560
    font.pixelSize: 16

    /* --- Public API --- */
    property var  profilingOptions: null
    property string strategy: "rough"   // "rough" | "finish"
    property real stock_to_leave: 0.0
    property int spring_passes: 0

    signal saveRequested(var payload)

    signal openNumPadRequested(var field)
    signal addFinishRequested()

    property bool readOnly: false
    property bool _loading: false

    function applyData(data) {
        _loading = true
        profilingOptions = data || {}

        print("applyData -> data:\n" + JSON.stringify(opData.profiling_options, null, 2))

        strategy = (profilingOptions.strategy !== undefined) ? String(profilingOptions.strategy) : "rough"
        if (profilingOptions.stock_to_leave_x !== undefined)
            stock_to_leave = Number(profilingOptions.stock_to_leave_x)
        else if (profilingOptions.stock_to_leave_z !== undefined)
            stock_to_leave = Number(profilingOptions.stock_to_leave_z)
        else
            stock_to_leave = 0.0
        spring_passes = (profilingOptions.finish_spring_passes !== undefined) ? Number(profilingOptions.finish_spring_passes) : 0
        _loading = false
    }

    function emitSave() {
        if (_loading) return
        root.saveRequested({
            profiling_options: {
                strategy: strategy,
                stock_to_leave_x: Number(stock_to_leave),
                stock_to_leave_z: Number(stock_to_leave),
                finish_spring_passes: Number(spring_passes)
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
                text: "Roughing"
                font.pixelSize: 15
                checked: root.strategy === "rough"
                ButtonGroup.group: modeGroup
                onToggled: if (checked) {
                    root.strategy = "rough";
                    root.emitSave()
                }
            }
            RadioButton {
                text: "Finishing"
                font.pixelSize: 15
                checked: root.strategy === "finish"
                ButtonGroup.group: modeGroup
                onToggled: if (checked) {
                    root.strategy = "finish";
                    root.emitSave()
                }
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
                radius: 6
                border.width: 1
                border.color: "#bdbdbd"
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
                        columnSpacing: 20
                        rowSpacing: 16

                        Label {
                            text: "Stock to leave"
                            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                            font.pixelSize: 16
                        }
                        NumpadField {
                            Layout.preferredWidth: 100
                            Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                            settingName: "spindle.css.value"
                            value: root.stock_to_leave
                            validatorObject: DoubleValidator {
                                notation: DoubleValidator.StandardNotation
                            }
                            formatter: function (v) {
                                return (v == null) ? "" : Number(v).toFixed(3)
                            }
                            hAlign: Text.AlignRight
                            font.pixelSize: 16
                            onOpenRequested: root.openNumPadRequested(field)
                            onValueCommitted: { root.stock_to_leave = value; root.emitSave() }
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
                            text: "Spring passes"
                            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                            font.pixelSize: 16
                        }
                        NumpadField {
                            Layout.preferredWidth: 50
                            Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                            settingName: "spindle.rpm"
                            value: root.spring_passes
                            validatorObject: IntValidator {
                            }
                            hAlign: Text.AlignRight
                            fontPixelSize: 16
                            onOpenRequested: root.openNumPadRequested(field)
                            onValueCommitted: { root.spring_passes = value; root.emitSave() }
                        }
                    }
                }
            }
        }
    }
}
