import QtQuick
import QtQuick.Controls
import theme

Rectangle {
    id: root

    color: Theme.surface

    required property var viewModel

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

    // The value measured with the current tool: a diameter in X, the
    // distance to Z0 in Z.
    component TouchOffField: QtObject {
        property string axis
        property string settingName
        property string description
        property var value: 0.0

        function commit(v) {
            value = v
            if (root.viewModel) {
                root.viewModel.touchOff(axis, v)
            }
            return true
        }

        function defocus() {
        }
    }

    TouchOffField {
        id: xTouchOffField
        axis: "x"
        settingName: "smart_numpad.x-offset"
        description: "Measured diameter with current tool"
    }

    TouchOffField {
        id: zTouchOffField
        axis: "z"
        settingName: "smart_numpad.z-offset"
        description: "Distance to Z0 with current tool"
    }

    ManualModeAxisDro {
        id: xDro
        x: 0
        y: 10
        width: parent.width
        axisLabel: "X"
        primaryValue: root.viewModel.xPrimaryValue
        secondaryValue: root.viewModel.xSecondaryValue
        secondaryVisible: root.viewModel.xSecondaryVisible
        unit: root.viewModel.units
        onPrimaryClicked: root.viewModel.xPrimaryClicked()
        onZeroClicked: root.viewModel.xZeroClicked()
        isAbs: root.viewModel.xIsAbs
        onAbsRelClicked: root.viewModel.xAbsRelClicked()
    }

    ManualModeAxisDro {
        id: zDro
        x: 0
        y: 97
        width: parent.width
        axisLabel: "Z"
        primaryValue: root.viewModel.zPrimaryValue
        secondaryValue: root.viewModel.zSecondaryValue
        secondaryVisible: root.viewModel.zSecondaryVisible
        unit: root.viewModel.units
        onPrimaryClicked: root.viewModel.zPrimaryClicked()
        onZeroClicked: root.viewModel.zZeroClicked()
        isAbs: root.viewModel.zIsAbs
        onAbsRelClicked: root.viewModel.zAbsRelClicked()
        setDatumVisible: true
        onSetDatumClicked: root.viewModel.zSetDatumClicked()
        onSetDatumLongPressed: root.viewModel.zSetDatumLongPressed()
    }

    Connections {
        target: root.viewModel
        function onActionRejected(message) {
            root.toastRequested(message)
        }
        function onSetDatumValueInputRequested() {
            root.openNumPadRequested(zDatumField)
        }
        function onTouchOffValueInputRequested(axis) {
            root.openNumPadRequested(axis === "x" ? xTouchOffField : zTouchOffField)
        }
    }
}
