import QtQuick
import QtQuick.Layouts
import theme
import common

// Shown until the machine is out of E-stop, powered and homed. Replaces the
// .ui's pageNotReady.
Rectangle {
    id: root

    required property var viewModel

    color: Theme.surfaceAlt

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 32
        spacing: Theme.margin

        // logo, machine name and state box, in one column the state box's
        // width
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
                text: root.viewModel.machineName
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
                        ok: root.viewModel.estopOk
                        text: root.viewModel.estopText
                    }
                    StatusRow {
                        ok: root.viewModel.powerOk
                        text: root.viewModel.powerText
                    }
                    StatusRow {
                        ok: root.viewModel.xHomed
                        text: root.viewModel.xHomedText
                    }
                    StatusRow {
                        ok: root.viewModel.zHomed
                        text: root.viewModel.zHomedText
                    }
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
