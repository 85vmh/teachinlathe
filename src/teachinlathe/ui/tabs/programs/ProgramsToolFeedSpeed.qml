import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import tabs.programs.program_loaded
import theme

// Sits between the top bar and the backplot. Shows, each in its own box, the
// spindle state, the movement speed and the current / upcoming tool.
// Calculations live in the view model; this component only displays
// formatted values.
Item {
    id: root

    required property var viewModel
    property var actions: null
    property var simulationViewModel: null
    property bool simulation: false
    readonly property bool moving: viewModel.state === "running" || viewModel.state === "held"

    // --- Metrics -----------------------------------------------------------
    property int inputHeight: 40
    property int cssInputHeight: 30
    property int cssSpacing: 6
    property int boxPadding: Theme.spacingSmall
    property int boxHorizontalPadding: 16
    property int labelWidth: 80
    property int valueBoxWidth: 100
    property int unitsWidth: 72
    property int optionSpacing: 28
    property int toolBoxWidth: 236
    property int toolColumnWidth: 58
    property int toolTimerArrowSpacing: 0
    property int toolArrowHorizontalPadding: 4
    // Every box is as tall as the spindle's in CSS mode, the tallest content
    // (the RPM and the surface speed, one over the other).
    readonly property int boxHeight: 2 * root.cssInputHeight + root.cssSpacing + 2 * root.boxPadding

    implicitHeight: root.boxHeight
    implicitWidth: boxesRow.implicitWidth

    // One of the boxes: the card styling around its contents.
    component Box: Rectangle {
        default property alias content: contentRow.data
        Layout.preferredHeight: root.boxHeight
        Layout.preferredWidth: contentRow.implicitWidth + 2 * root.boxHorizontalPadding
        color: Theme.hover
        border.color: Theme.separator
        border.width: Theme.hairline
        radius: Theme.radius

        RowLayout {
            id: contentRow
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left
            anchors.leftMargin: root.boxHorizontalPadding
            spacing: Theme.spacingSmall
        }
    }

    RowLayout {
        id: boxesRow
        anchors.fill: parent
        spacing: Theme.spacingSmall

        // ---- Spindle ------------------------------------------------------
        Box {
            RowLayout {
                Layout.preferredWidth: root.labelWidth
                Layout.preferredHeight: Theme.buttonHeight
                spacing: 0

                Text {
                    Layout.fillWidth: true
                    text: "S"
                    color: Theme.foreground
                    font.pixelSize: 40
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }

                Text {
                    Layout.alignment: Qt.AlignLeft | Qt.AlignBottom
                    text: "(" + (root.viewModel.spindleOverridePercent) + "%)"
                    color: Theme.foregroundSubtle
                    font.pixelSize: Theme.fontSmall
                }
            }

            // RPM mode — single box, same height as the feed box.
            RowLayout {
                Layout.alignment: Qt.AlignVCenter
                visible: !(root.viewModel.spindleIsCss)
                spacing: Theme.spacingSmall

                OutlinedValue {
                    Layout.preferredWidth: root.valueBoxWidth
                    Layout.preferredHeight: root.inputHeight
                    fontSize: 25
                    text: root.viewModel.spindleRpmText
                }

                Text {
                    Layout.preferredWidth: root.unitsWidth
                    text: "RPM"
                    color: Theme.foregroundSubtle
                    font.pixelSize: Theme.fontTitle
                    verticalAlignment: Text.AlignVCenter
                }
            }

            // CSS mode — two shorter boxes (RPM + surface speed), tighter spacing.
            ColumnLayout {
                Layout.alignment: Qt.AlignVCenter
                visible: root.viewModel.spindleIsCss
                spacing: root.cssSpacing

                RowLayout {
                    spacing: Theme.spacingSmall

                    OutlinedValue {
                        Layout.preferredWidth: root.valueBoxWidth
                        Layout.preferredHeight: root.cssInputHeight
                        fontSize: 18
                        text: root.viewModel.spindleRpmText
                    }

                    Text {
                        Layout.preferredWidth: root.unitsWidth
                        text: "RPM"
                        color: Theme.foregroundSubtle
                        font.pixelSize: Theme.fontBody
                        verticalAlignment: Text.AlignVCenter
                    }
                }

                RowLayout {
                    spacing: Theme.spacingSmall

                    OutlinedValue {
                        Layout.preferredWidth: root.valueBoxWidth
                        Layout.preferredHeight: root.cssInputHeight
                        fontSize: 18
                        text: root.viewModel.cssValueText
                    }

                    Text {
                        Layout.preferredWidth: root.unitsWidth
                        text: "m/min"
                        color: Theme.foregroundSubtle
                        font.pixelSize: Theme.fontBody
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }

        // ---- Movement: Feed / Rapid ---------------------------------------
        Box {
            RowLayout {
                Layout.preferredWidth: root.labelWidth
                Layout.preferredHeight: Theme.buttonHeight
                spacing: 0

                Text {
                    Layout.fillWidth: true
                    text: root.viewModel.movementLetter
                    color: Theme.foreground
                    font.pixelSize: 40
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }

                Text {
                    Layout.alignment: Qt.AlignRight | Qt.AlignBottom
                    text: "(" + (root.viewModel.movementOverridePercent) + "%)"
                    color: Theme.foregroundSubtle
                    font.pixelSize: Theme.fontSmall
                }
            }

            OutlinedValue {
                Layout.preferredWidth: root.valueBoxWidth
                Layout.preferredHeight: root.inputHeight
                Layout.alignment: Qt.AlignVCenter
                fontSize: 25
                text: root.viewModel.movementValueText
            }

            Text {
                Layout.preferredWidth: root.unitsWidth
                text: root.viewModel.movementUnitsText
                color: Theme.foregroundSubtle
                font.pixelSize: Theme.fontTitle
                verticalAlignment: Text.AlignVCenter
            }
        }

        // ---- Tool: current and next, with the time until the next tool change.
        Box {
            Layout.preferredWidth: root.toolBoxWidth

            ColumnLayout {
                Layout.preferredWidth: root.toolColumnWidth
                Layout.minimumWidth: root.toolColumnWidth
                Layout.maximumWidth: root.toolColumnWidth
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                spacing: 8

                Text {
                    Layout.fillWidth: true
                    text: "Current"
                    color: Theme.foregroundSubtle
                    font.pixelSize: Theme.fontBody
                    horizontalAlignment: Text.AlignHCenter
                }

                Text {
                    Layout.fillWidth: true
                    text: root.viewModel.currentLoadedToolText
                    color: Theme.foreground
                    font.pixelSize: 26
                    horizontalAlignment: Text.AlignHCenter
                }
            }

            Item {
                Layout.fillWidth: true
                Layout.minimumWidth: 56
                Layout.preferredWidth: 80
                Layout.preferredHeight: 50
                visible: root.viewModel.hasNextTool

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottom: toolArrow.top
                    anchors.bottomMargin: root.toolTimerArrowSpacing
                    visible: text !== ""
                    text: root.viewModel.nextToolTimeText
                    color: Theme.foreground
                    font.pixelSize: Theme.fontSmall
                    font.family: "monospace"
                }

                Canvas {
                    id: toolArrow
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.leftMargin: root.toolArrowHorizontalPadding
                    anchors.rightMargin: root.toolArrowHorizontalPadding
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.verticalCenterOffset: 16
                    height: 16
                    implicitWidth: 80
                    onWidthChanged: requestPaint()
                    onPaint: {
                        var ctx = getContext("2d")
                        var middle = height / 2
                        var tip = width - 2
                        ctx.clearRect(0, 0, width, height)
                        ctx.strokeStyle = Theme.foregroundSubtle
                        ctx.lineWidth = 2
                        ctx.lineCap = "round"
                        ctx.lineJoin = "round"
                        ctx.beginPath()
                        ctx.moveTo(1, middle)
                        ctx.lineTo(tip, middle)
                        ctx.lineTo(tip - 7, middle - 6)
                        ctx.moveTo(tip, middle)
                        ctx.lineTo(tip - 7, middle + 6)
                        ctx.stroke()
                    }
                }
            }

            ColumnLayout {
                Layout.preferredWidth: root.toolColumnWidth
                Layout.minimumWidth: root.toolColumnWidth
                Layout.maximumWidth: root.toolColumnWidth
                Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                visible: root.viewModel.hasNextTool
                spacing: 8

                Text {
                    Layout.fillWidth: true
                    text: "Next"
                    color: Theme.foregroundSubtle
                    font.pixelSize: Theme.fontBody
                    horizontalAlignment: Text.AlignHCenter
                }

                Text {
                    Layout.fillWidth: true
                    text: root.viewModel.nextToolText
                    color: Theme.foreground
                    font.pixelSize: 26
                    horizontalAlignment: Text.AlignHCenter
                }
            }
        }

        // Program options live beside S/F/T in both modes. They no longer
        // consume a separate bar below the code viewer.
        Item { Layout.fillWidth: true }

        LedToggleButton {
            Layout.leftMargin: root.optionSpacing
            text: "Break on M1"
            enabled: root.simulation
                     ? !!root.simulationViewModel && !root.moving && !root.simulationViewModel.loading
                     : !!root.actions && root.actions.optionalStopAction.enabled
            checked: root.simulation
                     ? !!root.simulationViewModel && root.simulationViewModel.optionalStop
                     : !!root.actions && root.actions.optionalStopAction.checked
            onClicked: {
                if (root.simulation)
                    root.simulationViewModel.setOptionalStop(!checked)
                else
                    root.actions.setOptionalStopEnabled(!checked)
            }
        }

        LedToggleButton {
            Layout.leftMargin: root.optionSpacing
            Layout.rightMargin: 16
            text: "Skip / Blocks"
            enabled: root.simulation
                     ? !!root.simulationViewModel && !root.moving && !root.simulationViewModel.loading
                     : !!root.actions && root.actions.blockDeleteAction.enabled
            checked: root.simulation
                     ? !!root.simulationViewModel && root.simulationViewModel.blockDelete
                     : !!root.actions && root.actions.blockDeleteAction.checked
            onClicked: {
                if (root.simulation)
                    root.simulationViewModel.setBlockDelete(!checked)
                else
                    root.actions.setBlockDeleteEnabled(!checked)
            }
        }

    }
}
