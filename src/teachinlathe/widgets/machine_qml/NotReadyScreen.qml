import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../app_shell_qml" as Shell
import theme 1.0

// Shown until the machine is out of E-stop, powered and homed. Replaces the
// .ui's pageNotReady.
Rectangle {
    id: root

    property var viewModel: null

    color: Theme.surfaceAlt

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 32
        spacing: Theme.margin

        Text {
            text: "WEILER"
            font.pixelSize: 44
            font.bold: true
            color: Theme.foreground
            Layout.alignment: Qt.AlignHCenter
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignHCenter
            Layout.maximumWidth: 620
            implicitHeight: stateColumn.implicitHeight + 40
            radius: Theme.radiusXLarge
            color: "white"
            border.width: Theme.hairline
            border.color: Theme.separator

            Column {
                id: stateColumn
                anchors.centerIn: parent
                spacing: Theme.spacingLarge

                StatusRow {
                    ok: root.viewModel ? root.viewModel.estopOk : false
                    text: root.viewModel ? root.viewModel.estopText : ""
                }
                StatusRow {
                    ok: root.viewModel ? root.viewModel.powerOk : false
                    text: root.viewModel ? root.viewModel.powerText : ""
                }
                StatusRow {
                    ok: root.viewModel ? root.viewModel.xHomed : false
                    text: root.viewModel ? root.viewModel.xHomedText : ""
                }
                StatusRow {
                    ok: root.viewModel ? root.viewModel.zHomed : false
                    text: root.viewModel ? root.viewModel.zHomedText : ""
                }
            }
        }

        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: Theme.spacing

            Shell.ShellActionButton {
                text: "E-Stop"
                implicitWidth: 150
                implicitHeight: Theme.headerHeight
                onClicked: root.viewModel.toggleEstop()
            }
            Shell.ShellActionButton {
                text: "Power"
                implicitWidth: 150
                implicitHeight: Theme.headerHeight
                // Powering on with the E-stop engaged does nothing; say so
                // rather than letting the press fail silently.
                enabled: root.viewModel
                         ? (root.viewModel.powerOk || root.viewModel.canPowerOn)
                         : false
                onClicked: root.viewModel.togglePower()
            }
            Shell.ShellActionButton {
                text: "Home X"
                implicitWidth: 150
                implicitHeight: Theme.headerHeight
                enabled: root.viewModel ? root.viewModel.canHome : false
                onClicked: root.viewModel.homeAxis("x")
            }
            Shell.ShellActionButton {
                text: "Home Z"
                implicitWidth: 150
                implicitHeight: Theme.headerHeight
                enabled: root.viewModel ? root.viewModel.canHome : false
                onClicked: root.viewModel.homeAxis("z")
            }
        }

        Item { Layout.fillHeight: true }

        ToolsRow {
            viewModel: root.viewModel
            Layout.alignment: Qt.AlignHCenter
            Layout.maximumWidth: parent.width
        }
    }
}
