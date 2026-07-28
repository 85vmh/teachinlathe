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

    Text {
        x: 15
        y: 10
        width: 91
        height: 36
        text: "Increment:"
        color: "#1e2430"
        font.pixelSize: 17
        verticalAlignment: Text.AlignVCenter
    }

    Text {
        x: 110
        y: 10
        width: 56
        height: 36
        text: viewModel ? viewModel.jogIncrement : "0.001"
        color: "#0f172a"
        font.pixelSize: 16
        font.family: "Noto Sans Mono"
        horizontalAlignment: Text.AlignRight
        verticalAlignment: Text.AlignVCenter
    }

    Text {
        x: 170
        y: 10
        width: 36
        height: 36
        text: "mm"
        color: "#1e2430"
        font.pixelSize: 17
        verticalAlignment: Text.AlignVCenter
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
