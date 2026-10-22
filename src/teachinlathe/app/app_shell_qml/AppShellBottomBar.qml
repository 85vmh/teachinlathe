import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import TeachInLathe

Rectangle {
    id: root
    color: Theme.surfaceAlt
    readonly property string currentTab: AppShellBridge.currentTab
    readonly property bool logsExpanded: AppShellBridge.logsExpanded
    readonly property var tabs: [
        { id: "manual", label: "Manual Turning" },
        { id: "tools", label: "Tool Library" },
        { id: "conversational", label: "Conversational" },
        { id: "programs", label: "Programs" },
        { id: "settings", label: "Machine Settings" }
    ]
    readonly property int currentIndex: {
        for (var i = 0; i < tabs.length; ++i)
            if (tabs[i].id === currentTab) return i
        return -1
    }
    // How long the highlight takes to slide to a newly chosen tab, in ms -
    // whether it was tapped or a screen switched to it (Generate G-code, Back
    // to Conversational).
    readonly property int slideDurationMs: 250

    // The tab the highlight is on. It follows currentIndex only once the
    // window has shown the new tab: the first time a tab comes up, building
    // and drawing it holds up a frame or two, and a slide started alongside
    // that work stalls and then jumps. Started after it, it runs smooth.
    property int shownIndex: currentIndex
    property bool _slidePending: false
    onCurrentIndexChanged: {
        if (highlight._ready && root.visible && root.Window.window)
            _slidePending = true
        else
            shownIndex = currentIndex
    }
    Connections {
        target: root.Window.window
        function onFrameSwapped() {
            if (!root._slidePending)
                return
            root._slidePending = false
            root.shownIndex = root.currentIndex
        }
    }

    // The current tab's highlight - its fill and the bar along its top - one
    // for the whole row, so that changing tab slides it across rather than
    // lighting the new tab up in place.
    Rectangle {
        id: highlight
        // through count: itemAt() says nothing when the tabs are created
        readonly property Item tab: root.shownIndex >= 0 && tabRepeater.count > root.shownIndex
                                    ? tabRepeater.itemAt(root.shownIndex) : null
        visible: tab !== null
        x: tab ? row.x + tab.x : 0
        y: tab ? row.y + tab.y : 0
        width: tab ? tab.width : 0
        height: tab ? tab.height : 0
        color: Theme.accentSoft

        // Not on the first placement, nor while the bar comes back from full
        // screen: only a change of tab moves it.
        property bool _ready: false
        Component.onCompleted: Qt.callLater(function() { highlight._ready = true })
        Behavior on x {
            enabled: highlight._ready && root.visible
            NumberAnimation { duration: root.slideDurationMs; easing.type: Easing.OutCubic }
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: 3
            color: Theme.primary
        }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: Theme.hairline
        color: Theme.separator
    }

    RowLayout {
        id: row
        anchors.fill: parent
        anchors.leftMargin: 12
        anchors.rightMargin: 12
        spacing: 6

        Repeater {
            id: tabRepeater
            model: root.tabs

            delegate: Item {
                Layout.preferredWidth: 200
                Layout.fillHeight: true

                Text {
                    anchors.centerIn: parent
                    text: modelData.label
                    color: root.currentTab === modelData.id ? Theme.foreground : Theme.foregroundSubtle
                    font.pixelSize: Theme.fontBody
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: AppShellBridge.activateTab(modelData.id)
                }
            }
        }

        Item { Layout.fillWidth: true }

        Rectangle {
            Layout.preferredWidth: 150
            Layout.fillHeight: true
            color: eventsArea.pressed || root.logsExpanded ? Theme.hover : "transparent"

            Text {
                anchors.centerIn: parent
                text: root.logsExpanded ? "Close Events" : "Events"
                color: Theme.foregroundSubtle
                font.pixelSize: Theme.fontBody
            }

            MouseArea {
                id: eventsArea
                anchors.fill: parent
                onClicked: AppShellBridge.toggleLogs()
            }
        }
    }
}
