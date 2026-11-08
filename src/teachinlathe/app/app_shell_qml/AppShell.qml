import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import TeachInLathe

/*
 * The application chrome: title bar, the content area, the bottom tab bar,
 * and the two things that float over them - the events drawer and the toast.
 *
 * This used to be AppShellQmlWidget, a QWidget holding one QQuickWidget per
 * bar with a QStackedWidget between them. The bars were already QML; only the
 * box they sat in was not. They are now items in the same scene, which is why
 * the drawer no longer needs its geometry computed in Python.
 *
 * Whatever is declared inside an AppShell becomes the content - see
 * `contentArea` being the default property.
 */
Item {
    id: root

    default property alias content: contentArea.data
    // where a screen puts what it shows in the title bar (AppShellTopBar)
    readonly property alias titleBarArea: topBar.customArea

    // Set while a screen is showing full screen: the program run view takes
    // the whole window, the profile editors keep the title bar.
    readonly property bool chromeTopHidden: AppShellBridge.chromeTopHidden
    readonly property bool chromeBottomHidden: AppShellBridge.chromeBottomHidden

    readonly property int barHeight: Theme.barHeight
    readonly property int contentPadding: Theme.paneGap

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        AppShellTopBar {
            id: topBar
            Layout.fillWidth: true
            Layout.preferredHeight: root.barHeight
            visible: NavigationStore.headerVisible
                     && !root.chromeTopHidden
        }

        Rectangle {
            id: contentHost
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: Theme.windowBackground

            Item {
                id: contentArea
                anchors.fill: parent
                anchors.margins: root.contentPadding
            }
        }

        AppShellBottomBar {
            id: bottomBar
            Layout.fillWidth: true
            Layout.preferredHeight: root.barHeight
            visible: !root.chromeBottomHidden
        }
    }

    // Behind the open drawer, what it covers is dimmed - as behind the
    // Manual tab's menu drawer (the Controls' modal shade). The bottom bar
    // stays available; tapping the dimmed area dismisses the drawer.
    Rectangle {
        z: 99
        width: root.width
        height: root.height - (bottomBar.visible ? bottomBar.height : 0)
        color: "#80000000"
        opacity: NavigationStore.logsExpanded ? 1 : 0
        visible: opacity > 0
        Behavior on opacity { NumberAnimation { duration: 240; easing.type: Easing.OutCubic } }

        MouseArea {
            anchors.fill: parent
            enabled: NavigationStore.logsExpanded
            onClicked: AppShellBridge.toggleLogs()
        }
    }

    AppShellEventsDrawer {
        id: drawer
        // off the screen when closed: hidden there too, so that the events
        // coming in meanwhile make no cards no one sees
        visible: x < root.width
        width: Math.round(root.width / 3)
        height: root.height - (bottomBar.visible ? bottomBar.height : 0)
        x: root.width
        y: 0
        z: 100

        states: State {
            name: "open"
            when: NavigationStore.logsExpanded
            PropertyChanges { target: drawer; x: root.width - drawer.width }
        }

        transitions: Transition {
            NumberAnimation {
                properties: "x"
                duration: 240
                easing.type: Easing.OutCubic
            }
        }
    }

    AppShellToastOverlay {
        anchors.fill: parent
        z: 200
        // The toast is a notification, not a target: clicks belong to the
        // screen underneath it.
        enabled: false
    }
}
