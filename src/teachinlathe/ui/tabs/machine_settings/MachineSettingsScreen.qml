import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import TeachInLathe

// The Machine Settings tab. Replaces the .ui's settingsTab.
Rectangle {
    id: root

    required property var viewModel
    required property var fixturesViewModel
    property var positionsViewModel: null

    color: Theme.surfaceAlt

    Flickable {
        anchors.fill: parent
        contentHeight: content.implicitHeight + 48
        clip: true

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
                    CheckBox {
                        text: "Hide pointer"
                        checked: TouchFeedback.hidePointer
                        onToggled: TouchFeedback.hidePointer = checked
                    }
                    CheckBox {
                        text: "Show touches"
                        checked: TouchFeedback.showTouches
                        onToggled: TouchFeedback.showTouches = checked
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
