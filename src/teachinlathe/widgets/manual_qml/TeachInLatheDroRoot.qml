import QtQuick 2.15
import QtQuick.Controls 2.15

Rectangle {
    id: root

    color: "#ffffff"

    property var viewModel: teachInDroViewModel

    signal toastRequested(string message)
    signal openNumPadRequested(var field)

    QtObject {
        id: zDatumField

        property string settingName: "manual.z-set-datum"
        property string description: "Set Z datum value"
        property var value: 0.0

        function commit(v) {
            value = v
            if (root.viewModel) {
                root.viewModel.zSetDatumValueSelected(v)
            }
            return true
        }

        function defocus() {
        }
    }

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
        setDatumVisible: true
        onSetDatumClicked: if (root.viewModel) root.viewModel.zSetDatumClicked()
        onSetDatumLongPressed: if (root.viewModel) root.viewModel.zSetDatumLongPressed()
    }

    Connections {
        target: root.viewModel
        function onActionRejected(message) {
            root.toastRequested(message)
        }
        function onSetDatumValueInputRequested() {
            root.openNumPadRequested(zDatumField)
        }
    }
}
