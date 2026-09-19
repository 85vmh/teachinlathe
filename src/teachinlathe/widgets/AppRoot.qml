import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

import "app_shell_qml"
import "machine_qml"
import "manual_qml"
import "programs_qml"
import "conversational_qml" as Conversational

/*
 * The whole window.
 *
 * What used to be a QStackedWidget holding a pageNotReady and a pageReady,
 * the second holding another QStackedWidget of four QWidget tabs, each
 * wrapping a QQuickWidget of its own. It is one scene now, so screens keep
 * their state across a tab change without anything being reparented, raised
 * or repainted by hand.
 *
 * Python finds the screens by objectName to connect their signals; the
 * view models themselves arrive as context properties.
 */
Item {
    id: root

    // Reaching the context properties from here, where nothing shadows them,
    // so they can be bound to screen properties of the same name below.
    readonly property var ctxMachine: machineViewModel
    readonly property var ctxFixtures: fixturesViewModel

    readonly property bool machineReady: ctxMachine ? ctxMachine.machineReady : false

    // MainTabs order, as the bottom bar lists them.
    readonly property var tabOrder: ["manual", "conversational", "programs", "settings"]
    readonly property int currentTabIndex: {
        var idx = tabOrder.indexOf(navigationStore ? navigationStore.currentTab : "manual")
        return idx < 0 ? 0 : idx
    }

    function hideChrome(hideTop, hideBottom) { shell.hideChrome(hideTop, hideBottom) }
    function showChrome() { shell.showChrome() }

    StackLayout {
        anchors.fill: parent
        // Shown until the machine is out of E-stop, powered and homed. The
        // .ui switched these two with a data-bound rule; that rule is now
        // MachineViewModel.machineReady.
        currentIndex: root.machineReady ? 1 : 0

        NotReadyScreen {
            objectName: "notReadyScreen"
            viewModel: root.ctxMachine
        }

        AppShell {
            id: shell

            StackLayout {
                anchors.fill: parent
                currentIndex: root.currentTabIndex

                ManualTurningRoot {
                    objectName: "manualScreen"
                }

                // Root.qml anchors itself to its parent, from when it was the
                // root of a QQuickWidget scene sized to the view. A plain Item
                // for it to fill keeps that working, because anchoring an item
                // the StackLayout manages directly is undefined behaviour.
                Item {
                    Conversational.Root {
                        objectName: "conversationalScreen"
                    }
                }

                ProgramsTabRoot {
                    objectName: "programsScreen"
                }

                MachineSettingsScreen {
                    objectName: "settingsScreen"
                    viewModel: root.ctxMachine
                    fixturesViewModel: root.ctxFixtures
                }
            }
        }
    }
}
