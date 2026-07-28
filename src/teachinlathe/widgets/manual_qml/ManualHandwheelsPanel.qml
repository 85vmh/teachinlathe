import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    property var viewModel: manualViewModel

    signal xToggled(bool enabled)
    signal zToggled(bool enabled)

    color: "#f5f5f5"
    border.color: "#ccc"
    border.width: 1
    radius: 6

    Item {
        id: header
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 50

        RowLayout {
            visible: viewModel ? viewModel.handwheelsAllowed : true
            anchors.fill: parent
            anchors.leftMargin: 10
            anchors.rightMargin: 10
            spacing: 6

            Item { Layout.fillWidth: true }

            Text {
                text: "Increment:"
                color: "#1e2430"
                font.pixelSize: 17
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }

            Text {
                text: viewModel ? viewModel.jogIncrement : "0.001"
                color: "#0f172a"
                font.pixelSize: 17
                font.bold: true
                font.family: "Noto Sans Mono"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }

            Text {
                text: "mm"
                color: "#1e2430"
                font.pixelSize: 17
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }

            Item { Layout.fillWidth: true }
        }

        Text {
            visible: !(viewModel ? viewModel.handwheelsAllowed : true)
            anchors.fill: parent
            text: "Disabled"
            color: "#ff9800"
            font.pixelSize: 17
            font.bold: false
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 1
            color: "#ccc"
        }
    }

    HandwheelToggle {
        x: 20
        y: 60
        axisLabel: "X"
        enabled: viewModel ? viewModel.handwheelsAllowed : true
        checked: viewModel ? viewModel.xHandwheelEnabled : true
        onClicked: root.xToggled(checked)
    }

    HandwheelToggle {
        x: 115
        y: 145
        axisLabel: "Z"
        enabled: viewModel ? viewModel.handwheelsAllowed : true
        checked: viewModel ? viewModel.zHandwheelEnabled : true
        onClicked: root.zToggled(checked)
    }
}
