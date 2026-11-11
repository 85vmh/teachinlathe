// SpindleParameters.qml — the spindle's direction, mode and speed, in two
// columns: G76 Threading's. It shows ``speeds`` - the operation's
// speeds_and_feeds - and keeps nothing of its own: an edit reports the
// whole speeds_and_feeds, with the change.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import common.touchable_input
import tabs.tool_library
import theme
import common
import "speeds.js" as Speeds

TitledCard {
    id: root
    title: "Spindle Parameters"
    Layout.fillWidth: true
    font.pixelSize: Theme.fontBody
    Layout.minimumWidth: 420
    Layout.preferredWidth: 560

    // the operation's speeds_and_feeds, as its editor has them
    property var  speeds: ({})
    property bool rpmOnly: false

    // the whole speeds_and_feeds, with the change made
    signal speedsEdited(var speeds)
    signal openNumPadRequested(var field)

    readonly property var _read: Speeds.read(speeds, rpmOnly, null)
    readonly property string spindleMode: _read.mode
    readonly property int    rpm_value: _read.rpm_value
    readonly property real   css_value: _read.css_value
    readonly property int    css_max_rpm: _read.css_max_speed
    // "M3" forward, "M4" reverse
    readonly property string direction: _read.direction

    function _edit(changes) {
        root.speedsEdited(Speeds.edited(_read, changes, false, false))
    }

    // ---------- layout ----------
    RowLayout {
        anchors.fill: parent
        spacing: 30
        Layout.alignment: Qt.AlignTop   // ensure whole block sticks to top

        // ------- Left column: Direction -------
        ColumnLayout {
            id: leftCol
            Layout.fillHeight: true
            Layout.alignment: Qt.AlignTop
            spacing: 20

            // M3 then M4, as the cutting-tool editors pick a tool's.
            SpindleDirectionPicker {
                clockwise: root.direction === "M3"
                onPicked: function(clockwise) { root._edit({ direction: clockwise ? "M3" : "M4" }) }
            }
        }

        // ------- Vertical separator -------
        Rectangle {
            width: Theme.hairline
            color: Theme.outline
            Layout.fillHeight: true
        }

        // ------- Right column: Mode selector + fields -------
        ColumnLayout {
            id: rightCol
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            spacing: Theme.spacingSmall

            // Mode selector (replaces tabs)
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spacingLarge
                visible: !root.rpmOnly

                ModelRadioButton {
                    text: "RPM Mode"
                    font.pixelSize: Theme.fontSmall
                    checked: root.spindleMode === "rpm"
                    onChosen: root._edit({ mode: "rpm" })
                }
                ModelRadioButton {
                    text: "CSS Mode"
                    font.pixelSize: Theme.fontSmall
                    checked: root.spindleMode === "css"
                    onChosen: root._edit({ mode: "css" })
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
                    radius: Theme.radius
                    border.width: Theme.hairline
                    border.color: Theme.outlineStrong
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
                                font.pixelSize: Theme.fontBody
                            }
                            NumpadField {
                                Layout.preferredWidth: 100
                                Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                                settingName: "spindle.rpm"
                                value: root.rpm_value
                                validatorObject: IntValidator {
                                }
                                hAlign: Text.AlignRight
                                onOpenRequested: function(field) { root.openNumPadRequested(field) }
                                onValueCommitted: function(value) { root._edit({ rpm_value: Math.round(value) }) }
                            }
                            Label {
                                text: "(rpm)"
                                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                                font.pixelSize: Theme.fontBody
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
                                font.pixelSize: Theme.fontBody
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
                                onOpenRequested: function(field) { root.openNumPadRequested(field) }
                                onValueCommitted: function(value) { root._edit({ css_value: Number(value) }) }
                            }
                            Label {
                                text: "(m/min)"
                                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                                font.pixelSize: Theme.fontBody
                            }

                            Label {
                                text: "Spindle max speed"
                                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                                font.pixelSize: Theme.fontBody
                            }
                            NumpadField {
                                Layout.preferredWidth: 100
                                Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                                settingName: "spindle.max_rpm"
                                value: root.css_max_rpm
                                validatorObject: IntValidator {
                                }
                                hAlign: Text.AlignRight
                                onOpenRequested: function(field) { root.openNumPadRequested(field) }
                                onValueCommitted: function(value) { root._edit({ css_max_speed: Math.round(value) }) }
                            }
                            Label {
                                text: "(rpm)"
                                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                                font.pixelSize: Theme.fontBody
                            }
                        }
                    }
                }
            }
        }
    }
}
