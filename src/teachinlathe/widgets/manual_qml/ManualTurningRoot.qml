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

Item {
    id: root

    // ── Layout constants ──────────────────────────────────────────────
    readonly property int droHeight:             190
    readonly property int sectionHeaderHeight:   39
    readonly property int panelHeight:           241
    readonly property int toolListWidth:         800
    readonly property int panelMargin:           5
    readonly property int panelInnerPadding:     4
    readonly property int spindlePanelWidth:     286
    readonly property int handwheelsPanelWidth:  216
    readonly property int joystickPanelWidth:    260

    // ── Joystick proxy properties ─────────────────────────────────────
    property bool rapidMode:              false
    property int  joystickState:          0
    property bool allowsTouchInteraction: true

    function resetAngle() { joystickPanel.resetAngle() }
    function isRotated()  { return joystickPanel.isRotated() }

    onJoystickStateChanged: {
        joystickPanel.joystickState = joystickState
        joystickPanel.allowsTouchInteraction = (joystickState === 0)
    }
    onRapidModeChanged: joystickPanel.rapidMode = rapidMode

    // ── Signals bubbled up from children ─────────────────────────────
    signal openNumPadRequested(var field)
    signal xToggled(bool enabled)
    signal zToggled(bool enabled)
    signal angleFeedToggled(bool enabled)

    // ── Tool list (right side, fixed width, full height) ─────────────
    ToolLibraryView {
        id: toolList
        anchors.right:  parent.right
        anchors.top:    parent.top
        anchors.bottom: parent.bottom
        width: root.toolListWidth
        onOpenNumPadRequested: root.openNumPadRequested(field)
    }

    // ── Divider between manual area and tool list ─────────────────────
    Rectangle {
        id: toolDivider
        anchors.right:  toolList.left
        anchors.top:    parent.top
        anchors.bottom: parent.bottom
        width: 3
        color: "#3a3a3a"
    }

    // ── Left column (fills space left of tool list) ───────────────────
    ColumnLayout {
        anchors.left:   parent.left
        anchors.top:    parent.top
        anchors.bottom: parent.bottom
        anchors.right:  toolDivider.left
        spacing: 0

        // DRO (fixed height — two axis readouts)
        TeachInLatheDroRoot {
            Layout.fillWidth: true
            Layout.preferredHeight: root.droHeight
        }

        // Limits (scalable — fills all remaining vertical space)
        LimitsPanel {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.leftMargin: 5
            Layout.rightMargin: 5
            Layout.topMargin: 4
            Layout.bottomMargin: 4
        }

        // Section headers (fixed height)
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: root.sectionHeaderHeight

            Rectangle {
                anchors.fill: parent
                color: "#efefef"
            }

            // "Spindle" label
            Text {
                x: 70; y: 0; width: 106; height: parent.height
                text: "Spindle"
                font.pixelSize: 18; font.family: "Cantarell"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment:   Text.AlignVCenter
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
                text: "Manual Feed"
                font.pixelSize: 18; font.family: "Cantarell"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment:   Text.AlignVCenter
            }
            // "Automatic Feed" label
            Text {
                x: 680; y: 0; width: 181; height: parent.height
                text: "Automatic Feed"
                font.pixelSize: 18; font.family: "Cantarell"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment:   Text.AlignVCenter
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
        // Original geometry: spindleFrame x=5 w=296, handwheelsFrame x=310 w=216,
        //                    joystick x=540 w=260, feedPanel x=810 w=fill
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: root.panelHeight

            ManualSpindlePanel {
                id: spindlePanel
                x: 5; y: root.panelInnerPadding
                width:  root.spindlePanelWidth
                height: root.panelHeight - 2 * root.panelInnerPadding
                onOpenNumPadRequested: root.openNumPadRequested(field)
            }

            ManualHandwheelsPanel {
                id: handwheelsPanel
                x: 310; y: root.panelInnerPadding
                width:  root.handwheelsPanelWidth
                height: root.panelHeight - 2 * root.panelInnerPadding
                onXToggled: root.xToggled(enabled)
                onZToggled: root.zToggled(enabled)
            }

            // Joystick + Feed share a single bordered box
            Rectangle {
                x: 540; y: root.panelInnerPadding
                width:  parent.width - 540 - root.panelMargin
                height: root.panelHeight - 2 * root.panelInnerPadding
                color: "#e6e6e6"
                border.color: "#0a0a0a"
                border.width: 1
                radius: 8

                ManualJoystickPanel {
                    id: joystickPanel
                    objectName: "manualJoystickPanel"
                    x: 1; y: 1
                    width:  root.joystickPanelWidth
                    height: parent.height - 2
                    onAngleFeedToggled: root.angleFeedToggled(enabled)
                }

                ManualFeedPanel {
                    id: feedPanel
                    x: root.joystickPanelWidth + 1; y: 1
                    width:  parent.width - root.joystickPanelWidth - 2
                    height: parent.height - 2
                    onOpenNumPadRequested: root.openNumPadRequested(field)
                }
            }
        }
    }
}
