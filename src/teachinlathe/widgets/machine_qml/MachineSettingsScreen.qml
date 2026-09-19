import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../app_shell_qml" as Shell
import theme 1.0

// The Machine Settings tab. Replaces the .ui's settingsTab.
Rectangle {
    id: root

    property var viewModel: null
    property var fixturesViewModel: null
    property var positionsViewModel: null

    signal setG28()
    signal goToG28()
    signal setG30()
    signal goToG30()

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
                title: "Predefined Positions"
                Layout.fillWidth: true

                content: RowLayout {
                    spacing: 10
                    Shell.ShellActionButton { text: "Set G28";   onClicked: root.setG28() }
                    Shell.ShellActionButton { text: "Go to G28"; onClicked: root.goToG28() }
                    Rectangle { width: 1; Layout.fillHeight: true; color: Theme.separator }
                    Shell.ShellActionButton { text: "Set G30";   onClicked: root.setG30() }
                    Shell.ShellActionButton { text: "Go to G30"; onClicked: root.goToG30() }
                    Item { Layout.fillWidth: true }
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
                                onSelected: root.fixturesViewModel.selectFixture(index)
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
