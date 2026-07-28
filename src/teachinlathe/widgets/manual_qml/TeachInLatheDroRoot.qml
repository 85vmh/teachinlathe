import QtQuick 2.15
import QtQuick.Controls 2.15

Rectangle {
    id: root

    color: "#ffffff"

    property var viewModel: teachInDroViewModel

    ManualModeAxisDro {
        id: xDro
        x: 0
        y: 10
        width: parent.width
        axisLabel: "X"
        primaryValue: root.viewModel ? root.viewModel.xPrimaryValue : "+0000.000"
        secondaryValue: root.viewModel ? root.viewModel.xSecondaryValue : "+0000.000"
        secondaryVisible: root.viewModel ? root.viewModel.xSecondaryVisible : false
        unit: root.viewModel ? root.viewModel.units : "mm"
        onPrimaryClicked: if (root.viewModel) root.viewModel.xPrimaryClicked()
        onZeroClicked: if (root.viewModel) root.viewModel.xZeroClicked()
        onAbsRelClicked: if (root.viewModel) root.viewModel.xAbsRelClicked()
    }

    ManualModeAxisDro {
        id: zDro
        x: 0
        y: 97
        width: parent.width
        axisLabel: "Z"
        primaryValue: root.viewModel ? root.viewModel.zPrimaryValue : "+0000.000"
        secondaryValue: root.viewModel ? root.viewModel.zSecondaryValue : "+0000.000"
        secondaryVisible: root.viewModel ? root.viewModel.zSecondaryVisible : false
        unit: root.viewModel ? root.viewModel.units : "mm"
        onPrimaryClicked: if (root.viewModel) root.viewModel.zPrimaryClicked()
        onZeroClicked: if (root.viewModel) root.viewModel.zZeroClicked()
        onAbsRelClicked: if (root.viewModel) root.viewModel.zAbsRelClicked()
    }
}
