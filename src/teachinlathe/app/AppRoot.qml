import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import app_shell_qml
import tabs.machine_settings
import tabs.manual_turning
import tabs.programs
import tabs.tool_library
import tabs.conversational
import TeachInLathe

/*
 * The whole window.
 *
 * What used to be a QStackedWidget holding a pageNotReady and a pageReady,
 * the second holding another QStackedWidget of four QWidget tabs, each
 * wrapping a QQuickWidget of its own. It is one scene now, so screens keep
 * their state across a tab change without anything being reparented, raised
 * or repainted by hand.
 *
 * Each tab binds to its view model, which arrives as a context property;
 * Python holds none of the screens.
 */
Item {
    id: root

    // Reaching the context properties from here, where nothing shadows them,
    // so they can be bound to screen properties of the same name below.
    readonly property var ctxMachine: MachineViewModel
    readonly property var ctxFixtures: FixturesViewModel

    readonly property bool machineReady: ctxMachine ? ctxMachine.machineReady : false

    TouchFeedbackOverlay {
        parent: root.Overlay.overlay
        anchors.fill: parent
        controller: TouchFeedback
    }

    // MainTabs order, as the bottom bar lists them.
readonly property var tabOrder: ["manual", "tools", "conversational", "programs", "settings"]
    readonly property int currentTabIndex: {
        var idx = tabOrder.indexOf(NavigationStore.currentTab || "manual")
        return idx < 0 ? 0 : idx
    }

    StackLayout {
        anchors.fill: parent
        // Shown until the machine is out of E-stop, powered and homed. The
        // .ui switched these two with a data-bound rule; that rule is now
        // MachineViewModel.machineReady.
        currentIndex: root.machineReady ? 1 : 0

        NotReadyScreen {
            viewModel: root.ctxMachine
        }

        AppShell {
            id: shell

            StackLayout {
                anchors.fill: parent
                currentIndex: root.currentTabIndex

                ManualTurningRoot {}

                ToolLibraryRoot {}

                ConversationalTabRoot {}

                ProgramsTabRoot {}

                MachineSettingsScreen {
                    viewModel: root.ctxMachine
                    fixturesViewModel: root.ctxFixtures
                }
            }
        }
    }
}
