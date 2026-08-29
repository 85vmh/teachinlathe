// ManualTurningRoot.qml — unified root for the Manual Turning tab.
//
// Layout (responsive):
//   Left column (anchors to left of ToolLibraryView):
//     • TeachInLatheDroRoot  — fixed height (droHeight)
//     • LimitsPanel          — fills remaining vertical space
//     • Section headers      — fixed height (sectionHeaderHeight)
//     • Control panels       — fixed height (panelHeight)
//   Right: ToolLibraryView — fixed width (toolListWidth), full height
//
// Context properties required (set by mainwindow.py):
//   manualViewModel, teachInDroViewModel, toolsProvider, appState,
//   cncStore, navigationStore
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../tool_library"
import "../touchable_input"   // SmartNumpadDialog, NumpadField

Item {
    id: root

    // ── Color constants ───────────────────────────────────────────────
    readonly property color pageBackgroundColor: "#ffffff"
    readonly property color cardBackgroundColor: "#f5f5f5"
    readonly property color cardBorderColor: "#ccc"
    readonly property color angleFeedGlowColor: "#ff9800"
    property var _pendingKeyboardField: null

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

    function openKeyboard(field) {
        if (!field)
            return
        root._pendingKeyboardField = field
        if (!keyboardDialogLoader.active)
            keyboardDialogLoader.active = true
        if (keyboardDialogLoader.item) {
            keyboardDialogLoader.item.openFor(field, field.titleText)
            root._pendingKeyboardField = null
        }
    }

    function openBladeZ0ReferenceDialog(bladeWidth) {
        bladeZ0ReferenceDialog.bladeWidth = Number(bladeWidth || 0)
        bladeZ0ReferenceDialog.open()
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

    Loader {
        id: keyboardDialogLoader
        active: false
        source: "../touchable_input/QwertyKeyboardDialog.qml"

        onLoaded: {
            if (item && root._pendingKeyboardField) {
                item.openFor(root._pendingKeyboardField, root._pendingKeyboardField.titleText)
                root._pendingKeyboardField = null
            }
        }
    }

    Dialog {
        id: bladeZ0ReferenceDialog
        modal: true
        closePolicy: Popup.NoAutoClose
        title: "Blade Z0 Reference"
        font.pixelSize: 20
        property real bladeWidth: 0
        implicitWidth: 520
        implicitHeight: contentColumn.implicitHeight + 96
        x: Math.round((root.width - width) / 2)
        y: Math.round((root.height - height) / 2)

        function choose(reference) {
            if (toolLibraryViewModel)
                toolLibraryViewModel.saveCurrentToolBladeZ0Reference(reference)
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
                    font.pixelSize: 18
                    font.bold: true
                    color: "#1e2430"
                    wrapMode: Text.WordWrap
                    horizontalAlignment: Text.AlignHCenter
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 24

                    Button {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 64
                        text: "Left Side"
                        font.pixelSize: 16
                        font.bold: true
                        onClicked: bladeZ0ReferenceDialog.choose("left")
                    }
                    Button {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 64
                        text: "Center"
                        font.pixelSize: 16
                        font.bold: true
                        onClicked: bladeZ0ReferenceDialog.choose("center")
                    }
                    Button {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 64
                        text: "Right Side"
                        font.pixelSize: 16
                        font.bold: true
                        onClicked: bladeZ0ReferenceDialog.choose("right")
                    }
                }
            }
        }
    }

    // ── Layout constants ──────────────────────────────────────────────
    readonly property int droHeight: 190
    readonly property int sectionHeaderHeight: 39
    readonly property int panelHeight: 241
    readonly property int toolListWidth: 800
    readonly property int panelMargin: 6
    readonly property int panelInnerPadding: 6
    readonly property int spindlePanelWidth: 286
    readonly property int handwheelsPanelWidth: 216
    readonly property int joystickPanelWidth: 260

    // ── Signals bubbled up from children ─────────────────────────────
    signal openNumPadRequested(Item field)
    signal toastRequested(string message)

    signal xToggled(bool enabled)

    signal zToggled(bool enabled)

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
                onToastRequested: function(message) { root.toastRequested(message) }
                onOpenNumPadRequested: function(field) { root.openNumpad(field) }
            }

            // Limits (scalable — fills all remaining vertical space)
            LimitsPanel {
                Layout.fillWidth: true
                Layout.fillHeight: true
                onOpenNumPadRequested: root.openNumpad(field)
            }

            // Section headers (fixed height)
            Item {
                Layout.fillWidth: true
                Layout.minimumHeight: root.sectionHeaderHeight
                Layout.preferredHeight: root.sectionHeaderHeight
                Layout.maximumHeight: root.sectionHeaderHeight

                // "Spindle" label
                Text {
                    x: 70; y: 0; width: 106; height: parent.height
                    text: manualViewModel ? manualViewModel.spindleTitle : "Spindle"
                    font.pixelSize: 18; font.family: "Cantarell"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                // Spindle override %
                Text {
                    x: 185; y: 0; width: 71; height: parent.height
                    text: manualViewModel ? (manualViewModel.spindleOverridePercent + "%") : "0%"
                    font.pixelSize: 18; font.family: "Cantarell"
                    verticalAlignment: Text.AlignVCenter
                }
                // "Manual Feed" label
                Text {
                    x: 320; y: 0; width: 156; height: parent.height
                    text: "Handwheels"
                    font.pixelSize: 18; font.family: "Cantarell"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                // "Automatic Feed" label
                Text {
                    x: 680; y: 0; width: 181; height: parent.height
                    text: "Joystick Automatic Feed"
                    font.pixelSize: 18; font.family: "Cantarell"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                // Feed override %
                Text {
                    x: 875; y: 0; width: 76; height: parent.height
                    text: manualViewModel ? (manualViewModel.feedOverridePercent + "%") : "0%"
                    font.pixelSize: 18; font.family: "Cantarell"
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

                ManualSpindlePanel {
                    id: spindlePanel
                    Layout.preferredWidth: root.spindlePanelWidth
                    Layout.fillHeight: true
                    onOpenNumPadRequested: root.openNumpad(field)
                }

                ManualHandwheelsPanel {
                    id: handwheelsPanel
                    Layout.preferredWidth: root.handwheelsPanelWidth
                    Layout.fillHeight: true
                    onXToggled: root.xToggled(enabled)
                    onZToggled: root.zToggled(enabled)
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
                    border.width: 1
                    radius: 6

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
            }
        }

        ToolLibraryView {
            id: toolList
            Layout.preferredWidth: root.toolListWidth
            Layout.fillHeight: true
            onOpenNumPadRequested: root.openNumpad(field)
            onOpenKeyboardRequested: root.openKeyboard(field)
        }
    }
}
