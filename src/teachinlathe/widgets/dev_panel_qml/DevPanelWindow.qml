import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Window 2.15
import theme 1.0

Window {
    id: root
    width: 520
    height: 760
    visible: false
    title: "TeachInLathe Dev Panel"
    color: Theme.surfaceAlt

    readonly property color panelBg: Theme.surface
    readonly property color borderColor: Theme.separator
    readonly property color textColor: Theme.foregroundStrong
    readonly property color mutedText: "#64748b"
    readonly property color green: "#22c55e"
    readonly property color red: "#ef4444"
    property string spindleLeverState: "neutral"
    property real jogIncrement: 0.0

    function setSpindleLever(state) {
        spindleLeverState = state
        devPanelViewModel.setSpindleLever(state)
    }

    function setJogIncrement(value) {
        jogIncrement = value
        devPanelViewModel.setFloat("jog.increment", value)
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth

        ColumnLayout {
            width: root.width
            spacing: Theme.spacing
            anchors.margins: 14

            Text {
                Layout.fillWidth: true
                Layout.margins: 14
                text: "TeachInLathe Dev Panel"
                color: root.textColor
                font.pixelSize: 24
                font.bold: true
            }

            Section {
                title: "Cycle"
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacing

                    MomentaryButton {
                        Layout.fillWidth: true
                        text: "Cycle Start"
                        pinName: "button.cycle-start"
                        activeColor: root.green
                        ledActive: devPanelViewModel.cycleStartLed
                    }

                    MomentaryButton {
                        Layout.fillWidth: true
                        text: "Cycle Abort"
                        pinName: "button.cycle-stop"
                        activeColor: root.red
                    }
                }
            }

            Section {
                title: "Machine"
                GridLayout {
                    Layout.fillWidth: true
                    columns: 2
                    columnSpacing: 12
                    rowSpacing: 12

                    ToggleControl {
                        Layout.fillWidth: true
                        text: "E-Stop"
                        pinName: "button.estop"
                        activeColor: root.red
                    }

                    ToggleControl {
                        Layout.fillWidth: true
                        text: "Single Block"
                        pinName: "button.single-block"
                    }

                    MomentaryButton {
                        Layout.fillWidth: true
                        text: "Power On"
                        pinName: "button.power-on"
                        activeColor: root.green
                    }

                    MomentaryButton {
                        Layout.fillWidth: true
                        text: "Power Off"
                        pinName: "button.power-off"
                        activeColor: root.red
                    }
                }
            }

            Section {
                title: "Spindle"
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacing

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingSmall

                        SelectButton {
                            Layout.fillWidth: true
                            text: "Reverse"
                            selected: root.spindleLeverState === "reverse"
                            onClicked: root.setSpindleLever("reverse")
                        }

                        SelectButton {
                            Layout.fillWidth: true
                            text: "Neutral"
                            selected: root.spindleLeverState === "neutral"
                            onClicked: root.setSpindleLever("neutral")
                        }

                        SelectButton {
                            Layout.fillWidth: true
                            text: "Forward"
                            selected: root.spindleLeverState === "forward"
                            onClicked: root.setSpindleLever("forward")
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        columnSpacing: 12
                        rowSpacing: 12

                        ToggleControl {
                            Layout.fillWidth: true
                            text: "Cover Open"
                            pinName: "spindle.cover-opened"
                        }

                        ToggleControl {
                            Layout.fillWidth: true
                            text: "First Gear"
                            pinName: "spindle.is-first-gear"
                        }
                    }
                }
            }

            Section {
                title: "Overrides"
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 14

                    PercentSlider {
                        Layout.fillWidth: true
                        label: "Feed Override"
                        pinName: "override.feed"
                        from: 0
                        to: 120
                        value: 100
                    }

                    PercentSlider {
                        Layout.fillWidth: true
                        label: "Spindle Override"
                        pinName: "override.spindle"
                        from: 50
                        to: 120
                        value: 100
                    }
                }
            }

            Section {
                title: "Jog"
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacing

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        columnSpacing: 12
                        rowSpacing: 12

                        MomentaryButton {
                            Layout.fillWidth: true
                            text: "X Clockwise"
                            pinName: "jog.x-clockwise"
                        }

                        MomentaryButton {
                            Layout.fillWidth: true
                            text: "X Counterclockwise"
                            pinName: "jog.x-counterclockwise"
                        }

                        MomentaryButton {
                            Layout.fillWidth: true
                            text: "Z Clockwise"
                            pinName: "jog.z-clockwise"
                        }

                        MomentaryButton {
                            Layout.fillWidth: true
                            text: "Z Counterclockwise"
                            pinName: "jog.z-counterclockwise"
                        }

                        MomentaryButton {
                            Layout.fillWidth: true
                            text: "X+"
                            pinName: "joystick.x-plus"
                        }

                        MomentaryButton {
                            Layout.fillWidth: true
                            text: "X-"
                            pinName: "joystick.x-minus"
                        }

                        MomentaryButton {
                            Layout.fillWidth: true
                            text: "Z+"
                            pinName: "joystick.z-plus"
                        }

                        MomentaryButton {
                            Layout.fillWidth: true
                            text: "Z-"
                            pinName: "joystick.z-minus"
                        }

                        MomentaryButton {
                            Layout.fillWidth: true
                            text: "Neutral"
                            pinName: "joystick.neutral"
                        }

                        ToggleControl {
                            Layout.fillWidth: true
                            text: "Rapid"
                            pinName: "joystick.rapid"
                        }
                    }

                    Text {
                        text: "Jog Increment"
                        color: root.mutedText
                        font.pixelSize: Theme.fontSmall
                        font.bold: true
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingSmall

                        SelectButton { Layout.fillWidth: true; text: "Off"; selected: root.jogIncrement === 0.0; onClicked: root.setJogIncrement(0.0) }
                        SelectButton { Layout.fillWidth: true; text: "0.1"; selected: root.jogIncrement === 0.1; onClicked: root.setJogIncrement(0.1) }
                        SelectButton { Layout.fillWidth: true; text: "0.01"; selected: root.jogIncrement === 0.01; onClicked: root.setJogIncrement(0.01) }
                        SelectButton { Layout.fillWidth: true; text: "0.001"; selected: root.jogIncrement === 0.001; onClicked: root.setJogIncrement(0.001) }
                    }
                }
            }

            Item { Layout.preferredHeight: 14 }
        }
    }

    component Section: Rectangle {
        id: section
        property string title: ""
        default property alias content: body.data
        Layout.fillWidth: true
        Layout.leftMargin: 14
        Layout.rightMargin: 14
        radius: Theme.radiusLarge
        color: root.panelBg
        border.color: root.borderColor
        implicitHeight: sectionLayout.implicitHeight + 28

        ColumnLayout {
            id: sectionLayout
            anchors.fill: parent
            anchors.margins: 14
            spacing: Theme.spacing

            Text {
                Layout.fillWidth: true
                text: section.title
                color: root.textColor
                font.pixelSize: Theme.fontLarge
                font.bold: true
            }

            ColumnLayout {
                id: body
                Layout.fillWidth: true
                spacing: Theme.spacing
            }
        }
    }

    component MomentaryButton: Button {
        id: control
        property string pinName: ""
        property bool ledActive: false
        property color activeColor: "#334155"
        Layout.preferredHeight: 54
        font.pixelSize: Theme.fontBody
        font.bold: true
        onPressedChanged: devPanelViewModel.setBit(pinName, pressed)
        background: Rectangle {
            radius: Theme.radiusLarge
            color: control.ledActive || control.pressed ? control.activeColor : Theme.selection
            border.color: control.ledActive || control.pressed ? Qt.darker(control.activeColor, 1.2) : root.borderColor
        }
        contentItem: Text {
            text: control.text
            color: control.ledActive || control.pressed ? Theme.surface : root.textColor
            font: control.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            wrapMode: Text.WordWrap
        }
    }

    component ToggleControl: CheckBox {
        id: control
        property string pinName: ""
        property color activeColor: "#334155"
        Layout.preferredHeight: 46
        text: ""
        onCheckedChanged: devPanelViewModel.setBit(pinName, checked)
        indicator: Rectangle {
            x: 0
            y: (control.height - height) / 2
            width: 48
            height: 28
            radius: 14
            color: control.checked ? control.activeColor : Theme.separator
            Rectangle {
                width: 22
                height: 22
                radius: 11
                x: control.checked ? 23 : 3
                y: 3
                color: Theme.surface
            }
        }
        contentItem: Text {
            text: control.text
            color: root.textColor
            font.pixelSize: Theme.fontBody
            verticalAlignment: Text.AlignVCenter
            leftPadding: 58
        }
    }

    component SelectButton: Button {
        id: control
        property bool selected: false
        Layout.preferredHeight: 46
        font.pixelSize: Theme.fontSmall
        font.bold: true
        background: Rectangle {
            radius: Theme.radiusLarge
            color: control.selected ? "#334155" : Theme.selection
            border.color: control.selected ? Theme.foregroundStrong : root.borderColor
        }
        contentItem: Text {
            text: control.text
            color: control.selected ? Theme.surface : root.textColor
            font: control.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }

    component PercentSlider: ColumnLayout {
        id: control
        property string label: ""
        property string pinName: ""
        property real from: 0
        property real to: 120
        property real value: 100
        spacing: 6

        RowLayout {
            Layout.fillWidth: true
            Text { text: control.label; color: root.textColor; font.pixelSize: Theme.fontSmall; font.bold: true }
            Item { Layout.fillWidth: true }
            Text { text: Math.round(slider.value) + "%"; color: root.mutedText; font.pixelSize: Theme.fontSmall; font.bold: true }
        }

        Slider {
            id: slider
            Layout.fillWidth: true
            from: control.from
            to: control.to
            value: control.value
            stepSize: 1
            onMoved: devPanelViewModel.setFloat(control.pinName, value / 100.0)
            Component.onCompleted: devPanelViewModel.setFloat(control.pinName, value / 100.0)
        }
    }
}
