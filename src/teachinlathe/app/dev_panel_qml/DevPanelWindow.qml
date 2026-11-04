import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import theme
import TeachInLathe

Window {
    id: root
    width: 250
    minimumWidth: 250
    maximumWidth: 250
    property bool manualExpanded: false
    property bool automaticExpanded: false
    readonly property int contentMargin: 10
    readonly property int bottomSpacing: Theme.spacingSmall
    readonly property int topButtonHeight: 36
    readonly property int sectionHeaderHeight: 40
    readonly property int panelHeight: Math.ceil(
        2 * contentMargin + bottomSpacing + topControls.implicitHeight + Theme.hairline
        + coverControls.implicitHeight + 2 * sectionHeaderHeight
        + Theme.spacingSmall * (4 + (manualExpanded ? 1 : 0)
                                             + (automaticExpanded ? 1 : 0))
        + (manualExpanded ? manualBody.implicitHeight : 0)
        + (automaticExpanded ? automaticBody.implicitHeight : 0))
    height: panelHeight
    visible: true
    // The application is maximised and frameless: without this the panel
    // goes behind it the first time the application is clicked.
    flags: Qt.Window | Qt.WindowStaysOnTopHint
    title: "TeachInLathe Dev Panel"
    color: Theme.surfaceAlt

    readonly property var vm: DevPanelViewModel
    readonly property color textColor: Theme.foregroundStrong
    readonly property color mutedText: "#64748b"
    readonly property color darkFill: "#334155"
    readonly property color green: "#22c55e"
    readonly property color red: "#ef4444"
    readonly property color amber: "#f59e0b"

    ColumnLayout {
        id: panelContent
        x: root.contentMargin
        y: root.contentMargin
        width: root.width - 2 * root.contentMargin
        height: root.panelHeight - 2 * root.contentMargin - root.bottomSpacing
        spacing: Theme.spacingSmall

        RowLayout {
            id: topControls
            Layout.fillWidth: true
            spacing: Theme.spacingSmall
            PanelButton {
                Layout.fillWidth: true
                Layout.preferredHeight: root.topButtonHeight
                text: root.vm.estop ? "E-Stop\nPRESSED" : "E-Stop"
                lit: root.vm.estop
                litColor: root.red
                onClicked: root.vm.setEstop(!root.vm.estop)
            }
            PanelButton {
                Layout.fillWidth: true
                Layout.preferredHeight: root.topButtonHeight
                text: "PwrOn"
                lit: root.vm.powerOn
                litColor: root.green
                enabled: root.vm.powerOn || (root.vm.ncReady && !root.vm.estop)
                onClicked: root.vm.setPowerOn(!root.vm.powerOn)
            }
            PanelButton {
                Layout.fillWidth: true
                Layout.preferredHeight: root.topButtonHeight
                text: "HomeAll"
                lit: pressed
                litColor: root.darkFill
                onPressedChanged: root.vm.setHomeAll(pressed)
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.hairline
            color: Theme.separator
        }

        RowLayout {
            id: coverControls
            Layout.fillWidth: true
            spacing: Theme.spacingSmall
            PanelButton {
                Layout.fillWidth: true
                Layout.preferredHeight: root.topButtonHeight
                text: "Chuck Cover\n" + (root.vm.chuckCoverOpen ? "Open" : "Closed")
                lit: root.vm.chuckCoverOpen
                litColor: root.amber
                onClicked: root.vm.setChuckCoverOpen(!root.vm.chuckCoverOpen)
            }
            PanelButton {
                Layout.fillWidth: true
                Layout.preferredHeight: root.topButtonHeight
                text: root.vm.firstGear ? "Gear 1" : "Gear 2"
                lit: root.vm.firstGear
                litColor: root.darkFill
                onClicked: root.vm.setFirstGear(!root.vm.firstGear)
            }
        }

        SectionHeader {
            text: "Manual Operation"
            expanded: root.manualExpanded
            onClicked: root.manualExpanded = !root.manualExpanded
        }
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: root.manualExpanded ? manualBody.implicitHeight : 0
            clip: true

            ColumnLayout {
                id: manualBody
                width: parent.width
                spacing: Theme.spacingSmall
                visible: root.manualExpanded

                Selector {
                    Layout.fillWidth: true
                    label: "Jog Increment"
                    options: ["off", "0.1", "0.01", "0.001"]
                    names: ["Off", "0.1", "0.01", "0.001"]
                    current: root.vm.jogIncrement
                    onSelected: (option) => root.vm.setJogIncrement(option)
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 130
                    spacing: Theme.spacingSmall
                    Handwheel { Layout.fillWidth: true; axis: "x" }
                    Handwheel { Layout.fillWidth: true; axis: "z" }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 156
                    spacing: Theme.spacingSmall
                    Joystick { Layout.alignment: Qt.AlignVCenter }
                    Rectangle {
                        Layout.preferredWidth: Theme.hairline
                        Layout.fillHeight: true
                        color: Theme.separator
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: Theme.spacingSmall
                        PanelButton {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            text: "Rev"
                            lit: root.vm.spindleLever === "M4"
                            litColor: root.red
                            onClicked: root.vm.setSpindleLever("M4")
                        }
                        PanelButton {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            text: "Stop"
                            lit: root.vm.spindleLever === "stop"
                            onClicked: root.vm.setSpindleLever("stop")
                        }
                        PanelButton {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            text: "Fwd"
                            lit: root.vm.spindleLever === "M3"
                            litColor: root.green
                            onClicked: root.vm.setSpindleLever("M3")
                        }
                    }
                }
            }
        }

        SectionHeader {
            text: "Automatic Operation"
            expanded: root.automaticExpanded
            onClicked: root.automaticExpanded = !root.automaticExpanded
        }
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: root.automaticExpanded ? automaticBody.implicitHeight : 0
            clip: true

            ColumnLayout {
                id: automaticBody
                width: parent.width
                spacing: Theme.spacingSmall
                visible: root.automaticExpanded

                OverrideSlider {
                    Layout.fillWidth: true
                    label: "Feed Override"
                    from: 0
                    to: 120
                    onPercentChanged: root.vm.setFeedOverride(percent)
                }
                OverrideSlider {
                    Layout.fillWidth: true
                    label: "Spindle Override"
                    from: 50
                    to: 120
                    onPercentChanged: root.vm.setSpindleOverride(percent)
                }
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: Theme.hairline
                    color: Theme.separator
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingSmall
                    PanelButton {
                        Layout.fillWidth: true
                        text: "Cycle Abort"
                        lit: pressed
                        litColor: root.red
                        onPressed: root.vm.pressCycleAbort()
                        onReleased: root.vm.releaseCycleAbort()
                        onCanceled: root.vm.releaseCycleAbort()
                    }
                    PanelButton {
                        Layout.fillWidth: true
                        text: "Cycle Start"
                        lit: pressed || root.vm.cycleStartLed
                        litColor: root.green
                        onPressed: root.vm.pressCycleStart()
                        onReleased: root.vm.releaseCycleStart()
                        onCanceled: root.vm.releaseCycleStart()
                    }
                }
            }
        }
    }

    component SectionHeader: Button {
        id: section
        property bool expanded: true
        Layout.fillWidth: true
        Layout.preferredHeight: root.sectionHeaderHeight
        font.pixelSize: Theme.fontSmall
        font.bold: true
        background: Rectangle {
            radius: Theme.radius
            color: section.pressed ? Theme.selection : Theme.surface
            border.color: Theme.separator
        }
        contentItem: RowLayout {
            Text {
                Layout.fillWidth: true
                text: section.text
                color: root.textColor
                font: section.font
            }
            Text {
                text: section.expanded ? "▾" : "▸"
                color: root.textColor
                font.pixelSize: Theme.fontBody
            }
        }
    }

    // ── components ──────────────────────────────────────────────────────────

    component PanelButton: Button {
        id: control
        property bool lit: false
        property color litColor: root.darkFill
        Layout.preferredHeight: 54
        font.pixelSize: Theme.fontSmall
        font.bold: true
        opacity: enabled ? 1.0 : 0.4
        background: Rectangle {
            radius: Theme.radiusLarge
            color: control.lit ? control.litColor : Theme.selection
            border.color: control.lit ? Qt.darker(control.litColor, 1.2) : Theme.separator
        }
        contentItem: Text {
            text: control.text
            color: control.lit ? Theme.surface : root.textColor
            font: control.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }

    component OverrideSlider: ColumnLayout {
        id: overrideSlider
        property string label: ""
        property alias from: slider.from
        property alias to: slider.to
        readonly property int percent: Math.round(slider.value)
        spacing: 4

        RowLayout {
            Layout.fillWidth: true
            Text { text: overrideSlider.label; color: root.textColor; font.pixelSize: Theme.fontSmall; font.bold: true }
            Item { Layout.fillWidth: true }
            Text { text: overrideSlider.percent + "%"; color: root.mutedText; font.pixelSize: Theme.fontSmall; font.bold: true }
        }

        Slider {
            id: slider
            Layout.fillWidth: true
            stepSize: 5
            snapMode: Slider.SnapAlways
            value: 100
        }
    }

    component Selector: ColumnLayout {
        id: selector
        property string label: ""
        property var options: []
        property var names: []
        property string current: ""
        signal selected(string option)
        spacing: 4

        Text { text: selector.label; color: root.mutedText; font.pixelSize: Theme.fontSmall; font.bold: true }

        RowLayout {
            Layout.fillWidth: true
            spacing: 4
            Repeater {
                model: selector.options
                PanelButton {
                    required property int index
                    required property string modelData
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    Layout.preferredWidth: selector.options.length > 0
                                           ? (selector.width - (selector.options.length - 1) * 4)
                                             / selector.options.length : 0
                    Layout.preferredHeight: 40
                    text: selector.names[index]
                    lit: selector.current === modelData
                    onClicked: selector.selected(modelData)
                }
            }
        }
    }

    // Dragged round, or scrolled: one detent per 3.6 degrees, 100 a turn,
    // and per wheel notch.
    component Handwheel: Item {
        id: wheel
        property string axis: "x"
        property real angle: 0
        property real dragAngle: 0
        readonly property real degreesPerDetent: 3.6
        implicitWidth: 104
        implicitHeight: 130

        function turn(detents) {
            if (detents === 0)
                return
            wheel.angle += detents * wheel.degreesPerDetent
            root.vm.turnHandwheel(wheel.axis, detents)
        }

        function pointerAngle(x, y) {
            return Math.atan2(y - face.height / 2, x - face.width / 2) * 180 / Math.PI
        }

        Rectangle {
            id: face
            width: 96
            height: 96
            anchors.horizontalCenter: parent.horizontalCenter
            radius: width / 2
            color: Theme.selection
            border.color: Theme.separator
            border.width: 2

            Item {
                anchors.fill: parent
                rotation: wheel.angle
                Repeater {
                    model: 20
                    Rectangle {
                        id: tick
                        required property int index
                        readonly property bool majorTick: index % 2 === 0
                        width: majorTick ? 2 : 1
                        x: face.width / 2 - width / 2
                        y: 3
                        height: majorTick ? 12 : 5
                        color: root.mutedText
                        transform: Rotation {
                            // Rotation origins are local to this tick, not the dial.
                            origin.x: tick.width / 2
                            origin.y: face.height / 2 - 3
                            angle: index * 18
                        }
                    }
                }
                Rectangle {
                    width: 16
                    height: 16
                    radius: 8
                    x: face.width / 2 - 8
                    y: 18
                    color: root.darkFill
                }
            }

            Text {
                anchors.centerIn: parent
                text: wheel.axis.toUpperCase()
                color: root.textColor
                font.pixelSize: Theme.fontLarge
                font.bold: true
            }

            MouseArea {
                anchors.fill: parent
                onPressed: (mouse) => wheel.dragAngle = wheel.pointerAngle(mouse.x, mouse.y)
                onPositionChanged: (mouse) => {
                    var now = wheel.pointerAngle(mouse.x, mouse.y)
                    // the shortest way round from where the last detent was
                    // taken, so turn after turn adds up
                    var delta = ((now - wheel.dragAngle) % 360 + 540) % 360 - 180
                    var detents = Math.trunc(delta / wheel.degreesPerDetent)
                    if (detents !== 0) {
                        // kept within one turn, as the pointer's angle is
                        wheel.dragAngle = (wheel.dragAngle + detents * wheel.degreesPerDetent) % 360
                        wheel.turn(detents)
                    }
                }
                onWheel: (event) => wheel.turn(event.angleDelta.y > 0 ? 1 : (event.angleDelta.y < 0 ? -1 : 0))
            }
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            text: "MPG " + wheel.axis.toUpperCase()
            color: root.mutedText
            font.pixelSize: Theme.fontSmall
            font.bold: true
        }
    }

    // Laid out as the Manual tab's joystick: X- up, X+ down, Z- left, Z+ right.
    component Joystick: GridLayout {
        columns: 3
        rowSpacing: 6
        columnSpacing: 6

        Item { implicitWidth: 42; implicitHeight: 48 }
        Direction { direction: "x-minus"; text: "X-" }
        Item { implicitWidth: 42; implicitHeight: 48 }

        Direction { direction: "z-minus"; text: "Z-" }
        PanelButton {
            Layout.preferredWidth: 42
            Layout.preferredHeight: 48
            text: "Rapid"
            lit: root.vm.joystickRapid
            litColor: root.amber
            onPressedChanged: root.vm.setJoystickRapid(pressed)
        }
        Direction { direction: "z-plus"; text: "Z+" }

        Item { implicitWidth: 42; implicitHeight: 48 }
        Direction { direction: "x-plus"; text: "X+" }
        Item { implicitWidth: 42; implicitHeight: 48 }
    }

    component Direction: PanelButton {
        property string direction: ""
        Layout.preferredWidth: 42
        Layout.preferredHeight: 48
        lit: root.vm.joystickDirection === direction
        litColor: root.green
        enabled: root.vm.joystickDirection === "" || lit
        onClicked: root.vm.toggleJoystick(direction)
    }
}
