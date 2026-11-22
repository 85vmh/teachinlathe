import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import TeachInLathe
import common

// The Machine Settings tab. Replaces the .ui's settingsTab.
Rectangle {
    id: root

    required property var viewModel
    required property var fixturesViewModel
    property var positionsViewModel: null

    color: Theme.surfaceAlt

    // the pages, in the order of their tabs
    readonly property int machinePage: 0
    readonly property int performancePage: 1

    // view state: the page shown - the machine's settings, or Performance
    // Diagnostics
    property int page: machinePage

    SegmentedTabs {
        id: pages
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.margins: 24
        width: 420
        labels: ["Machine", "Performance"]
        currentIndex: root.page
        onActivated: function(index) { root.page = index }
    }

    // made only while it is shown: its charts draw nothing otherwise
    Loader {
        anchors.fill: parent
        anchors.topMargin: pages.height + 36
        active: root.page === root.performancePage
        source: "DiagnosticsPage.qml"
    }

    Flickable {
        anchors.fill: parent
        anchors.topMargin: pages.height + 36
        contentHeight: content.implicitHeight + 48
        clip: true
        visible: root.page === root.machinePage

        ColumnLayout {
            id: content
            width: parent.width
            anchors.margins: 24
            anchors.left: parent.left
            anchors.right: parent.right
            spacing: 20

            GroupPanel {
                title: "Touchscreen"
                Layout.fillWidth: true

                content: ColumnLayout {
                    ModelCheckBox {
                        text: "Hide pointer"
                        checked: TouchFeedback.hidePointer
                        onToggledTo: function(on) { TouchFeedback.hidePointer = on }
                    }
                    ModelCheckBox {
                        text: "Show touches"
                        checked: TouchFeedback.showTouches
                        onToggledTo: function(on) { TouchFeedback.showTouches = on }
                    }
                }
            }

            GroupPanel {
                title: "Workholding"
                Layout.fillWidth: true

                content: Flickable {
                    implicitHeight: 250
                    contentWidth: fixtureRow.width
                    flickableDirection: Flickable.HorizontalFlick
                    clip: true

                    Row {
                        id: fixtureRow
                        spacing: 10

                        Repeater {
                            model: root.fixturesViewModel
                                   ? root.fixturesViewModel.fixtures : []

                            delegate: FixtureCard {
                                fixture: modelData
                                onSelected: function(index) { root.fixturesViewModel.selectFixture(index) }
                                onTeachRequested: root.fixturesViewModel.teachZMinusLimit()
                            }
                        }
                    }

                    ScrollBar.horizontal: ScrollBar { policy: ScrollBar.AlwaysOn }
                }
            }

            GroupPanel {
                title: "Debugging Tools"
                Layout.fillWidth: true
                content: ToolsRow { viewModel: root.viewModel }
            }
        }
    }
}
