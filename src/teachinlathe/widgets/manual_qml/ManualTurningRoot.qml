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
//   manualViewModel, manualInputBridge, teachInDroViewModel,
//   toolsProvider, appState, cncStore, navigationStore
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../tool_library"
import "../touchable_input"   // SmartNumpadDialog, NumpadField

Item {
    id: root

    Rectangle {
        anchors.fill: parent
        color: "#ffffff"
        z: -1
    }

    // Opens the QML numpad dialog for a NumpadField, using its optional
    // `description` as the title override (falls back to numpad_settings.json).
    function openNumpad(field) {
        numpadDialog.openFor(field, field.settingName, field.description)
    }

    SmartNumpadDialog {
        id: numpadDialog
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
                    x: 340; y: 0; width: 156; height: parent.height
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
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: "#f5f5f5"
                    border.color: "#ccc"
                    border.width: 1
                    radius: 6

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 1
                        spacing: 0

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
        }
    }
}
