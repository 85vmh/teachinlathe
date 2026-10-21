// ManualTurningRoot.qml — unified root for the Manual Turning tab.
//
// Layout (responsive):
//   Left column (anchors to left of ManualToolList):
//     • TeachInLatheDroRoot  — fixed height (droHeight)
//     • LimitsPanel          — fills remaining vertical space
//     • Section headers      — fixed height (sectionHeaderHeight)
//     • Control panels       — fixed height (panelHeight): Handwheels,
//                              Joystick + Feed, Spindle
//   Right: ManualToolList — fixed width (toolListWidth), full height
//
// Context properties required (set by app_window.py):
//   manualViewModel, teachInDroViewModel, manualToolsViewModel, appState,
//   cncStore, navigationStore, appShellBridge
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../tool_library"
import common.touchable_input 1.0   // SmartNumpadDialog, NumpadField
import theme 1.0

Item {
    id: root

    // ── Color constants ───────────────────────────────────────────────
    readonly property color pageBackgroundColor: Theme.surface
    readonly property color cardBackgroundColor: Theme.surfaceSunken
    readonly property color cardBorderColor: Theme.outline
    readonly property color angleFeedGlowColor: Theme.warning

    Rectangle {
        anchors.fill: parent
        color: root.pageBackgroundColor
        z: -1
    }

    // Opens the QML numpad dialog for a NumpadField, using its optional
    // `description` as the title override (falls back to numpad_settings.json).
    function openNumpad(field) {
        numpadDialog.openFor(field, field.settingName, field.description)
    }

    // A blade touched off in Z: which of its points was it?
    Connections {
        target: typeof manualToolsViewModel !== "undefined" ? manualToolsViewModel : null
        function onBladePlaceRequested(bladeWidth) {
            bladeZ0ReferenceDialog.bladeWidth = Number(bladeWidth || 0)
            bladeZ0ReferenceDialog.open()
        }
    }

    function formatBladeWidth(value) {
        var width = Number(value || 0)
        return Math.abs(width * 10 - Math.round(width * 10)) < 0.0001
            ? String(Number(width.toFixed(1)))
            : width.toFixed(1)
    }

    SmartNumpadDialog {
        id: numpadDialog
    }

    Dialog {
        id: bladeZ0ReferenceDialog
        modal: true
        closePolicy: Popup.NoAutoClose
        title: "Blade Z0 Reference"
        font.pixelSize: Theme.fontTitle
        property real bladeWidth: 0
        implicitWidth: 520
        implicitHeight: contentColumn.implicitHeight + 96
        x: Math.round((root.width - width) / 2)
        y: Math.round((root.height - height) / 2)

        // -1 the left corner, 0 the middle, 1 the right corner.
        function choose(place) {
            if (typeof manualToolsViewModel !== "undefined" && manualToolsViewModel)
                manualToolsViewModel.setBladePlace(place)
            close()
        }

        contentItem: Item {
            implicitWidth: 480
            implicitHeight: contentColumn.implicitHeight + 36

            ColumnLayout {
                id: contentColumn
                anchors.fill: parent
                anchors.margins: 18
                spacing: 18

                Text {
                    Layout.fillWidth: true
                    text: "Where is the Z0 relative to the " + root.formatBladeWidth(bladeZ0ReferenceDialog.bladeWidth) + "mm thick blade?"
                    font.pixelSize: Theme.fontLarge
                    font.bold: true
                    color: Theme.foreground
                    wrapMode: Text.WordWrap
                    horizontalAlignment: Text.AlignHCenter
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.margin

                    Button {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 64
                        text: "Left Side"
                        font.pixelSize: Theme.fontBody
                        font.bold: true
                        onClicked: bladeZ0ReferenceDialog.choose("-1")
                    }
                    Button {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 64
                        text: "Center"
                        font.pixelSize: Theme.fontBody
                        font.bold: true
                        onClicked: bladeZ0ReferenceDialog.choose("0")
                    }
                    Button {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 64
                        text: "Right Side"
                        font.pixelSize: Theme.fontBody
                        font.bold: true
                        onClicked: bladeZ0ReferenceDialog.choose("1")
                    }
                }
            }
        }
    }

    // ── Layout constants ──────────────────────────────────────────────
    readonly property int droHeight: 190
    readonly property int sectionHeaderHeight: 39
    readonly property int panelHeight: 241
    readonly property int toolListWidth: 600
    readonly property int panelMargin: 6
    readonly property int panelInnerPadding: 6
    // 286 for the RPM/CSS content, then a 1 px divider and the 100 px
    // spindle direction column.
    readonly property int spindlePanelWidth: 387
    readonly property int handwheelsPanelWidth: 216
    readonly property int joystickPanelWidth: 260

    // ── Signals bubbled up from children ─────────────────────────────
    signal openNumPadRequested(Item field)

    RowLayout {
        anchors.fill: parent
        spacing: 6

        // ── Left column ───────────────────────────────────────────────
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            // DRO (fixed height — two axis readouts)
            TeachInLatheDroRoot {
                Layout.fillWidth: true
                Layout.minimumHeight: root.droHeight
                Layout.preferredHeight: root.droHeight
                Layout.maximumHeight: root.droHeight
                onToastRequested: function(message) { appShellBridge.showToast(message) }
                onOpenNumPadRequested: function(field) { root.openNumpad(field) }
            }

            // Limits (scalable — fills all remaining vertical space)
            LimitsPanel {
                Layout.fillWidth: true
                Layout.fillHeight: true
                onOpenNumPadRequested: root.openNumpad(field)
            }

            // Section headers (fixed height), each placed over its panel
            // below: Handwheels, Joystick Automatic Feed, Spindle.
            Item {
                Layout.fillWidth: true
                Layout.minimumHeight: root.sectionHeaderHeight
                Layout.preferredHeight: root.sectionHeaderHeight
                Layout.maximumHeight: root.sectionHeaderHeight

                // "Spindle" label
                Text {
                    x: spindlePanel.x + 70; y: 0; width: 106; height: parent.height
                    text: manualViewModel ? manualViewModel.spindleTitle : "Spindle"
                    font.pixelSize: Theme.fontLarge; font.family: "Cantarell"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                // Spindle override %
                Text {
                    x: spindlePanel.x + 185; y: 0; width: 71; height: parent.height
                    text: manualViewModel ? (manualViewModel.spindleOverridePercent + "%") : "0%"
                    font.pixelSize: Theme.fontLarge; font.family: "Cantarell"
                    verticalAlignment: Text.AlignVCenter
                }
                // "Manual Feed" label
                Text {
                    width: 156; height: parent.height; y: 0
                    x: handwheelsPanel.x + (handwheelsPanel.width - width) / 2
                    text: "Handwheels"
                    font.pixelSize: Theme.fontLarge; font.family: "Cantarell"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                // "Automatic Feed" label
                Text {
                    x: joystickFeedFrame.x + 166; y: 0; width: 181; height: parent.height
                    text: "Joystick Automatic Feed"
                    font.pixelSize: Theme.fontLarge; font.family: "Cantarell"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                // Feed override %
                Text {
                    x: joystickFeedFrame.x + 361; y: 0; width: 76; height: parent.height
                    text: manualViewModel ? (manualViewModel.feedOverridePercent + "%") : "0%"
                    font.pixelSize: Theme.fontLarge; font.family: "Cantarell"
                    verticalAlignment: Text.AlignVCenter
                }
            }

            // Control panels (fixed height)
            RowLayout {
                Layout.fillWidth: true
                Layout.minimumHeight: root.panelHeight
                Layout.preferredHeight: root.panelHeight
                Layout.maximumHeight: root.panelHeight
                spacing: root.panelMargin

                ManualHandwheelsPanel {
                    id: handwheelsPanel
                    Layout.preferredWidth: root.handwheelsPanelWidth
                    Layout.fillHeight: true
                }

                // Joystick + Feed share a single bordered box
                Rectangle {
                    id: joystickFeedFrame
                    readonly property bool angleFeedActive: manualViewModel ? manualViewModel.angleFeedActive : false
                    property color frameBorderColor: root.cardBorderColor
                    property real glowOpacity: 0
                    readonly property int glowDurationMs: 200
                    readonly property int glowBorderWidth: 10
                    readonly property int glowInset: 1
                    readonly property real glowMaxOpacity: 0.7

                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: root.cardBackgroundColor
                    border.color: frameBorderColor
                    border.width: Theme.hairline
                    radius: Theme.radius

                    onAngleFeedActiveChanged: {
                        if (!angleFeedActive) {
                            frameBorderColor = root.cardBorderColor
                            glowOpacity = 0
                        }
                    }

                    SequentialAnimation {
                        running: joystickFeedFrame.angleFeedActive
                        loops: Animation.Infinite

                        ParallelAnimation {
                            ColorAnimation {
                                target: joystickFeedFrame
                                property: "frameBorderColor"
                                to: root.angleFeedGlowColor
                                duration: joystickFeedFrame.glowDurationMs
                                easing.type: Easing.InOutQuad
                            }
                            NumberAnimation {
                                target: joystickFeedFrame
                                property: "glowOpacity"
                                to: joystickFeedFrame.glowMaxOpacity
                                duration: joystickFeedFrame.glowDurationMs
                                easing.type: Easing.InOutQuad
                            }
                        }

                        ParallelAnimation {
                            ColorAnimation {
                                target: joystickFeedFrame
                                property: "frameBorderColor"
                                to: root.cardBorderColor
                                duration: joystickFeedFrame.glowDurationMs
                                easing.type: Easing.InOutQuad
                            }
                            NumberAnimation {
                                target: joystickFeedFrame
                                property: "glowOpacity"
                                to: 0
                                duration: joystickFeedFrame.glowDurationMs
                                easing.type: Easing.InOutQuad
                            }
                        }
                    }

                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: joystickFeedFrame.glowInset
                        radius: Math.max(0, joystickFeedFrame.radius - joystickFeedFrame.glowInset)
                        color: "transparent"
                        opacity: joystickFeedFrame.glowOpacity
                        z: 2

                        Rectangle {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            height: 18
                            gradient: Gradient {
                                GradientStop { position: 0.0; color: root.angleFeedGlowColor }
                                GradientStop { position: 1.0; color: "transparent" }
                            }
                        }

                        Rectangle {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            height: 18
                            gradient: Gradient {
                                GradientStop { position: 0.0; color: "transparent" }
                                GradientStop { position: 1.0; color: root.angleFeedGlowColor }
                            }
                        }

                        Rectangle {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            width: 18
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0.0; color: root.angleFeedGlowColor }
                                GradientStop { position: 1.0; color: "transparent" }
                            }
                        }

                        Rectangle {
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            width: 18
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0.0; color: "transparent" }
                                GradientStop { position: 1.0; color: root.angleFeedGlowColor }
                            }
                        }
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: joystickFeedFrame.glowBorderWidth
                        spacing: 0
                        z: 1

                        ManualJoystickPanel {
                            id: joystickPanel
                            objectName: "manualJoystickPanel"
                            Layout.preferredWidth: root.joystickPanelWidth
                            Layout.fillHeight: true
                            viewModel: manualViewModel
                        }

                        ManualFeedPanel {
                            id: feedPanel
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            onOpenNumPadRequested: root.openNumpad(field)
                        }
                    }
                }

                ManualSpindlePanel {
                    id: spindlePanel
                    Layout.preferredWidth: root.spindlePanelWidth
                    Layout.fillHeight: true
                    onOpenNumPadRequested: root.openNumpad(field)
                }
            }
        }

        ManualToolList {
            id: toolList
            Layout.preferredWidth: root.toolListWidth
            Layout.fillHeight: true
            viewModel: typeof manualToolsViewModel !== "undefined" ? manualToolsViewModel : null
        }
    }
}
