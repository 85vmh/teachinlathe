import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import theme 1.0

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

    // Set while a screen is showing full screen: the program run view takes
    // the whole window, the gremlin view keeps the title bar.
    property bool chromeTopHidden: false
    property bool chromeBottomHidden: false

    readonly property int barHeight: Theme.barHeight
    readonly property int contentPadding: 6

    function hideChrome(hideTop, hideBottom) {
        chromeTopHidden = hideTop
        chromeBottomHidden = hideBottom
    }

    function showChrome() {
        chromeTopHidden = false
        chromeBottomHidden = false
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        AppShellTopBar {
            id: topBar
            Layout.fillWidth: true
            Layout.preferredHeight: root.barHeight
            visible: (navigationStore ? navigationStore.headerVisible : true)
                     && !root.chromeTopHidden
        }

        Rectangle {
            id: contentHost
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: Theme.surface

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

    // The drawer used to be a separate top-level QQuickWidget moved into place
    // by resizeEvent; anchoring it to the content host does the same job.
    AppShellEventsDrawer {
        id: drawer
        visible: navigationStore ? navigationStore.logsExpanded : false
        width: Math.min(Math.max(420, root.width / 2), Math.max(0, root.width - 24))
        height: Math.max(0, Math.min(300, contentHost.height - 24)) || 220
        x: root.width - width - 12
        y: contentHost.y + contentHost.height - height
        z: 100
    }

    AppShellToastOverlay {
        anchors.fill: parent
        z: 200
        // The toast is a notification, not a target: clicks belong to the
        // screen underneath it.
        enabled: false
    }
}
