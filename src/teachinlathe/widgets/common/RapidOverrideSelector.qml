// RapidOverrideSelector.qml — segmented button bar for feed/speed override
import QtQuick 2.15
import QtQuick.Controls 2.15

Item {
    id: root

    property string label: "Override"
    property int value: 100
    property var steps: [25, 50, 75, 100]
    // When > 0, shows the effective speed next to the label (e.g. "Rapid Override (6000 mm/min)")
    property real maxSpeed: 0
    property bool updateValueOnClick: true
    property bool fillAvailableWidth: false

    signal selected(int newValue)

    property int segmentWidth: 80

    readonly property int barHeight: 42
    readonly property int labelHeight: label_text.implicitHeight
    readonly property real effectiveSegmentWidth: root.steps.length > 0
        ? (root.fillAvailableWidth ? Math.max(0, bar.width / root.steps.length) : root.segmentWidth)
        : 0

    implicitWidth:  steps.length * segmentWidth
    implicitHeight: labelHeight + 4 + barHeight

    readonly property color colorActive:       "#1565c0"
    readonly property color colorActiveText:   "#ffffff"
    readonly property color colorInactive:     "#e8eaf6"
    readonly property color colorInactiveText: "#37474f"
    readonly property color colorBorder:       "#90a4ae"
    readonly property color colorDivider:      "#90a4ae"
    readonly property int   cornerRadius:      10

    Column {
        anchors.fill: parent
        spacing: 4

        // ── label row ─────────────────────────────────────────────────
        Text {
            id: label_text
            width: parent.width
            text: root.maxSpeed > 0
                  ? root.label + " (" + Math.round(root.value / 100 * root.maxSpeed) + " mm/min)"
                  : root.label
            font.pixelSize: 16
            font.bold: true
            color: "#37474f"
            horizontalAlignment: Text.AlignHCenter
        }

        // ── segmented bar ─────────────────────────────────────────────
        Rectangle {
            id: bar
            width: root.fillAvailableWidth ? parent.width : root.steps.length * root.segmentWidth
            height: root.barHeight
            radius: root.cornerRadius
            color: "transparent"

            Row {
                anchors.fill: parent

                Repeater {
                    model: root.steps

                    delegate: Item {
                        id: segmentItem
                        width: root.effectiveSegmentWidth
                        height: bar.height

                        readonly property bool isFirst: index === 0
                        readonly property bool isLast:  index === root.steps.length - 1
                        readonly property bool active:  root.value === modelData
                        readonly property color segColor: active
                            ? root.colorActive
                            : (segmentArea.pressed ? Qt.darker(root.colorInactive, 1.08) : root.colorInactive)

                        // ── fill ──────────────────────────────────────
                        Rectangle {
                            anchors.fill: parent
                            radius: (isFirst || isLast) ? root.cornerRadius : 0
                            color: segmentItem.segColor

                            // First segment: cover the right rounded corners
                            Rectangle {
                                visible: isFirst
                                anchors { right: parent.right; top: parent.top; bottom: parent.bottom }
                                width: root.cornerRadius
                                color: parent.color
                            }

                            // Last segment: cover the left rounded corners
                            Rectangle {
                                visible: isLast
                                anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
                                width: root.cornerRadius
                                color: parent.color
                            }
                        }

                        // ── divider (skip on last segment) ────────────
                        Rectangle {
                            visible: !isLast
                            anchors { right: parent.right; top: parent.top; bottom: parent.bottom }
                            width: 1
                            color: root.colorDivider
                            z: 1
                        }

                        // ── label ─────────────────────────────────────
                        Text {
                            anchors.centerIn: parent
                            text: modelData + "%"
                            font.pixelSize: 16
                            font.bold: segmentItem.active
                            color: segmentItem.active ? root.colorActiveText : root.colorInactiveText
                            z: 2
                        }

                        MouseArea {
                            id: segmentArea
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (root.updateValueOnClick) {
                                    root.value = modelData
                                }
                                root.selected(modelData)
                            }
                        }
                    }
                }
            }

            // ── border overlay (drawn on top of all segments) ─────────
            Rectangle {
                anchors.fill: parent
                radius: root.cornerRadius
                color: "transparent"
                border.color: root.colorBorder
                border.width: 1
                z: 3
            }
        }
    }
}
