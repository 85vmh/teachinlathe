import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import theme
import TeachInLathe

Window {
    id: root
    width: 780
    height: 600
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
        anchors.fill: parent
        anchors.margins: 14
        spacing: Theme.spacing

        // ── machine ─────────────────────────────────────────────────────────
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacing

            PanelButton {
                Layout.fillWidth: true
                text: root.vm.estop ? "E-Stop\nPRESSED" : "E-Stop"
                lit: root.vm.estop
                litColor: root.red
                onClicked: root.vm.setEstop(!root.vm.estop)
            }

            PanelButton {
                Layout.fillWidth: true
                text: root.vm.powerOn ? "Power On" : (root.vm.ncReady ? "Power On\n(NC ready)" : "Power On\n(not ready)")
                lit: root.vm.powerOn
                litColor: root.green
                enabled: root.vm.powerOn || (root.vm.ncReady && !root.vm.estop)
                onClicked: root.vm.setPowerOn(!root.vm.powerOn)
            }

            PanelButton {
                Layout.fillWidth: true
                text: "Home Axes"
                lit: pressed
                litColor: root.darkFill
                onPressedChanged: root.vm.setHomeAll(pressed)
            }

            PanelButton {
                Layout.fillWidth: true
                text: "Chuck Cover\n" + (root.vm.chuckCoverOpen ? "OPEN" : "closed")
                lit: root.vm.chuckCoverOpen
                litColor: root.amber
                onClicked: root.vm.setChuckCoverOpen(!root.vm.chuckCoverOpen)
            }

            PanelButton {
                Layout.fillWidth: true
                text: root.vm.firstGear ? "Gear 1" : "Gear 2"
                lit: root.vm.firstGear
                litColor: root.darkFill
                onClicked: root.vm.setFirstGear(!root.vm.firstGear)
            }
        }

        // ── apron ───────────────────────────────────────────────────────────
        Box {
            Layout.fillWidth: true
            Layout.fillHeight: true
            title: "Apron"

            RowLayout {
                Layout.fillWidth: true
                spacing: 18

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    spacing: 14

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

                    Selector {
                        Layout.fillWidth: true
                        label: "Spindle"
                        options: ["M3", "stop", "M4"]
                        names: ["M3", "Stop", "M4"]
                        current: root.vm.spindleLever
                        onSelected: (option) => root.vm.setSpindleLever(option)
                    }

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
                        Layout.topMargin: 6
                        spacing: Theme.spacing

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
                            // The button's lamp is program_state's LED output.
                            lit: pressed || root.vm.cycleStartLed
                            litColor: root.green
                            onPressed: root.vm.pressCycleStart()
                            onReleased: root.vm.releaseCycleStart()
                            onCanceled: root.vm.releaseCycleStart()
                        }
                    }
                }

                ColumnLayout {
                    Layout.alignment: Qt.AlignTop
                    spacing: 14

                    RowLayout {
                        Layout.alignment: Qt.AlignHCenter
                        spacing: 24
                        Handwheel { axis: "x" }
                        Handwheel { axis: "z" }
                    }

                    Joystick {
                        Layout.alignment: Qt.AlignHCenter
                    }
                }
            }
        }
    }

    // ── components ──────────────────────────────────────────────────────────

    component Box: Rectangle {
        id: box
        property string title: ""
        default property alias content: body.data
        radius: Theme.radiusLarge
        color: Theme.surface
        border.color: Theme.separator

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 14
            spacing: Theme.spacing

            Text {
                text: box.title
                color: root.textColor
                font.pixelSize: Theme.fontLarge
                font.bold: true
            }

            ColumnLayout {
                id: body
                Layout.fillWidth: true
            }

            Item { Layout.fillHeight: true }
        }
    }

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
        implicitWidth: 120
        implicitHeight: 140

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
            width: 110
            height: 110
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
                        required property int index
                        x: face.width / 2 - 1
                        y: 3
                        width: 2
                        height: index % 5 === 0 ? 10 : 5
                        color: root.mutedText
                        transform: Rotation { origin.x: 1; origin.y: face.height / 2 - 3; angle: index * 18 }
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
                    var delta = now - wheel.dragAngle
                    if (delta > 180) delta -= 360
                    if (delta < -180) delta += 360
                    var detents = Math.trunc(delta / wheel.degreesPerDetent)
                    if (detents !== 0) {
                        wheel.dragAngle += detents * wheel.degreesPerDetent
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

        Item { implicitWidth: 64; implicitHeight: 54 }
        Direction { direction: "x-minus"; text: "X-" }
        Item { implicitWidth: 64; implicitHeight: 54 }

        Direction { direction: "z-minus"; text: "Z-" }
        PanelButton {
            Layout.preferredWidth: 64
            text: "Rapid"
            lit: root.vm.joystickRapid
            litColor: root.amber
            onPressedChanged: root.vm.setJoystickRapid(pressed)
        }
        Direction { direction: "z-plus"; text: "Z+" }

        Item { implicitWidth: 64; implicitHeight: 54 }
        Direction { direction: "x-plus"; text: "X+" }
        Item { implicitWidth: 64; implicitHeight: 54 }
    }

    component Direction: PanelButton {
        property string direction: ""
        Layout.preferredWidth: 64
        lit: root.vm.joystickDirection === direction
        litColor: root.green
        enabled: root.vm.joystickDirection === "" || lit
        onClicked: root.vm.toggleJoystick(direction)
    }
}
