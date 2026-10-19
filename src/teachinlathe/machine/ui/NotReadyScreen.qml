import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../../app/app_shell_qml" as Shell
import theme 1.0
import common 1.0

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

        // logo, machine name, state box and buttons, in one column the
        // state box's width
        ColumnLayout {
            id: brandColumn
            Layout.alignment: Qt.AlignHCenter
            Layout.fillWidth: true
            Layout.maximumWidth: 620
            spacing: Theme.margin

            // at most 200 px high, its width from the SVG's 1378 x 799
            // viewBox; narrower only if the column is. From the column's
            // width, not the image's own, which the layout sets after.
            Image {
                readonly property real aspect: 1378 / 799
                Layout.alignment: Qt.AlignHCenter
                Layout.preferredHeight: Math.min(200, brandColumn.width / aspect)
                Layout.preferredWidth: Layout.preferredHeight * aspect
                source: Images.url("app_logo.svg")
                sourceSize.height: Math.max(1, Layout.preferredHeight)
                fillMode: Image.PreserveAspectFit
                smooth: true
            }

            Text {
                text: root.viewModel ? root.viewModel.machineName : ""
                font.pixelSize: 44
                font.bold: true
                color: Theme.foreground
                Layout.alignment: Qt.AlignHCenter
            }

            Rectangle {
                Layout.fillWidth: true
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
        }

        Item { Layout.fillHeight: true }

        ToolsRow {
            viewModel: root.viewModel
            Layout.alignment: Qt.AlignHCenter
            Layout.maximumWidth: parent.width
        }
    }
}
