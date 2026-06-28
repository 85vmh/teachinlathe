// SpindleParameters.qml (two-column, radio-mode switch, top-aligned layout)
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."
import "../touchable_input"

GroupBox {
    id: root
    title: "Spindle Parameters"
    Layout.fillWidth: true
    font.pixelSize: 16
    Layout.minimumWidth: 420
    Layout.preferredWidth: 560

    // ---- bridge to parent
    property int  opIndex: -1
    property var  opData: null
    property bool rpmOnly: false

    signal saveRequested(var updated)

    signal openNumPadRequested(var field)

    // ---- local state
    property string spindleMode: "rpm"   // "rpm" | "css"
    property int    rpm_value: 0
    property real   css_value: 0.0
    property int    css_max_rpm: 0
    property int    directionCache: 1    // +1 = Forward (M3), -1 = Reverse (M4)

    function applyData(index, data) {
        opIndex = index
        opData = data || {}

        var sp = (opData.spindle_parameters || {})
        directionCache = (sp.direction !== undefined) ? sp.direction : 1

        var hasRPM = (sp.rpm_value !== undefined && sp.rpm_value !== null)
        var hasCSS = (sp.css_value !== undefined && sp.css_max_speed !== undefined)

        spindleMode = rpmOnly ? "rpm" : ((sp.mode === "css" || sp.mode === "rpm") ? sp.mode : (hasRPM ? "rpm" : "css"))
        rpm_value = hasRPM ? +sp.rpm_value : 0
        css_value = hasCSS ? +sp.css_value : 0
        css_max_rpm = hasCSS ? +sp.css_max_speed : 0
    }

    function emitSave() {
        if (!opData) return

        var spindle = {direction: directionCache, mode: (rpmOnly ? "rpm" : spindleMode)}
        if (rpmOnly || spindleMode === "rpm") {
            spindle.rpm_value = rpm_value
        } else {
            spindle.css_value = css_value
            spindle.css_max_speed = css_max_rpm
        }

        var payload = {
            order: (opData && opData.order !== undefined) ? opData.order : 0,
            type: (opData && opData.type) ? opData.type : "",
            generate_gcode: (opData && opData.generate_gcode !== undefined) ? opData.generate_gcode : true,
            is_optional_block: (opData && opData.is_optional_block !== undefined) ? opData.is_optional_block : false,
            spindle_parameters: spindle
        }
        root.saveRequested({index: opIndex, payload: payload})
    }

    // ---------- layout ----------
    RowLayout {
        anchors.fill: parent
        spacing: 60
        Layout.alignment: Qt.AlignTop   // ensure whole block sticks to top

        // ------- Left column: Direction radios -------
        ColumnLayout {
            id: leftCol
            Layout.fillHeight: true
            Layout.alignment: Qt.AlignTop
            spacing: 20

            ButtonGroup {
                id: dirGroup
            }

            RadioButton {
                text: "Spin Forward (M3)"
                font.pixelSize: 15
                checked: root.directionCache === 1
                ButtonGroup.group: dirGroup
                onToggled: if (checked) {
                    root.directionCache = 1;
                    root.emitSave()
                }
            }
            RadioButton {
                text: "Spin Reverse (M4)"
                font.pixelSize: 15
                checked: root.directionCache === -1
                ButtonGroup.group: dirGroup
                onToggled: if (checked) {
                    root.directionCache = -1;
                    root.emitSave()
                }
            }
        }

        // ------- Vertical separator -------
        Rectangle {
            width: 1
            color: "#cccccc"
            Layout.fillHeight: true
        }

        // ------- Right column: Mode selector + fields -------
        ColumnLayout {
            id: rightCol
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            spacing: 8

            // Mode selector (replaces tabs)
            RowLayout {
                Layout.fillWidth: true
                spacing: 16
                visible: !root.rpmOnly

                ButtonGroup {
                    id: modeGroup
                }
                RadioButton {
                    text: "RPM Mode"
                    font.pixelSize: 15
                    checked: root.spindleMode === "rpm"
                    ButtonGroup.group: modeGroup
                    onToggled: if (checked) {
                        root.spindleMode = "rpm";
                        root.emitSave()
                    }
                }
                RadioButton {
                    text: "CSS Mode"
                    font.pixelSize: 15
                    checked: root.spindleMode === "css"
                    ButtonGroup.group: modeGroup
                    onToggled: if (checked) {
                        root.spindleMode = "css";
                        root.emitSave()
                    }
                }
                Item {
                    Layout.fillWidth: true
                }
            }

            // Content frame
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
                Layout.preferredHeight: Math.max(
                    rpmItem.visible ? rpmItem.implicitHeight : 0,
                    cssItem.visible ? cssItem.implicitHeight : 0
                ) + 2 * padding
                clip: true

                Item {
                    id: pages
                    anchors.fill: parent

                    // ---- RPM page ----
                    Item {
                        id: rpmItem
                        anchors.fill: parent
                        visible: root.spindleMode === "rpm"
                        implicitHeight: rpmGrid.implicitHeight + 2

                        GridLayout {
                            id: rpmGrid
                            anchors.fill: parent
                            columns: 3
                            columnSpacing: 20
                            rowSpacing: 16

                            Label {
                                text: "Spindle speed"
                                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                                font.pixelSize: 16
                            }
                            NumpadField {
                                Layout.preferredWidth: 100
                                Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                                settingName: "spindle.rpm"
                                value: root.rpm_value
                                validatorObject: IntValidator {
                                }
                                hAlign: Text.AlignRight
                                fontPixelSize: 16
                                onOpenRequested: root.openNumPadRequested(field)
                                onValueCommitted: { root.rpm_value = value; root.emitSave() }
                            }
                            Label {
                                text: "(rpm)"
                                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                                font.pixelSize: 16
                            }
                        }
                    }

                    // ---- CSS page ----
                    Item {
                        id: cssItem
                        anchors.fill: parent
                        visible: !root.rpmOnly && root.spindleMode === "css"
                        implicitHeight: cssGrid.implicitHeight + 2

                        GridLayout {
                            id: cssGrid
                            anchors.fill: parent
                            columns: 3
                            columnSpacing: 20
                            rowSpacing: 16

                            Label {
                                text: "CSS value (Vc)"
                                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                                font.pixelSize: 16
                            }
                            NumpadField {
                                Layout.preferredWidth: 100
                                Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                                settingName: "spindle.css"
                                value: root.css_value
                                validatorObject: DoubleValidator {
                                    notation: DoubleValidator.StandardNotation
                                }
                                formatter: function (v) {
                                    return (v == null) ? "" : Number(v).toFixed(1)
                                }
                                hAlign: Text.AlignRight
                                font.pixelSize: 16
                                onOpenRequested: root.openNumPadRequested(field)
                                onValueCommitted: { root.css_value = value; root.emitSave() }
                            }
                            Label {
                                text: "(m/min)"
                                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                                font.pixelSize: 16
                            }

                            Label {
                                text: "Spindle max speed"
                                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                                font.pixelSize: 16
                            }
                            NumpadField {
                                Layout.preferredWidth: 100
                                Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                                settingName: "spindle.max_rpm"
                                value: root.css_max_rpm
                                validatorObject: IntValidator {
                                }
                                hAlign: Text.AlignRight
                                font.pixelSize: 16
                                onOpenRequested: root.openNumPadRequested(field)
                                onValueCommitted: { root.css_max_rpm = value; root.emitSave() }
                            }
                            Label {
                                text: "(rpm)"
                                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                                font.pixelSize: 16
                            }
                        }
                    }
                }
            }
        }
    }
}
