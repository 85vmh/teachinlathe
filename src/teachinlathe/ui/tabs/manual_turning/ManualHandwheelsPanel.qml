import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme

Rectangle {
    id: root
    required property var viewModel

    color: Theme.surfaceSunken
    border.color: Theme.outline
    border.width: Theme.hairline
    radius: Theme.radius

    Item {
        id: header
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 50

        RowLayout {
            visible: viewModel.handwheelsAllowed
            anchors.fill: parent
            anchors.leftMargin: 10
            anchors.rightMargin: 10
            spacing: 6

            Item { Layout.fillWidth: true }

            Text {
                text: "Increment:"
                color: Theme.foreground
                font.pixelSize: Theme.fontLarge
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }

            Text {
                text: viewModel.jogIncrement
                color: Theme.foregroundStrong
                font.pixelSize: Theme.fontLarge
                font.bold: true
                font.family: "Noto Sans Mono"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }

            Text {
                text: "mm"
                color: Theme.foreground
                font.pixelSize: Theme.fontLarge
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }

            Item { Layout.fillWidth: true }
        }

        Text {
            visible: !(viewModel.handwheelsAllowed)
            anchors.fill: parent
            text: "Disabled"
            color: Theme.warning
            font.pixelSize: Theme.fontLarge
            font.bold: false
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: Theme.hairline
            color: Theme.outline
        }
    }

    HandwheelToggle {
        x: 20
        y: 60
        axisLabel: "X"
        enabled: viewModel.handwheelsAllowed
        checked: viewModel.xHandwheelEnabled
        onClicked: root.viewModel.setXHandwheelEnabled(checked)
    }

    HandwheelToggle {
        x: 115
        y: 145
        axisLabel: "Z"
        enabled: viewModel.handwheelsAllowed
        checked: viewModel.zHandwheelEnabled
        onClicked: root.viewModel.setZHandwheelEnabled(checked)
    }
}
