import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../conversational_qml"

Rectangle {
    id: root
    property var viewModel: manualViewModel
    signal openNumPadRequested(Item field)

    color: "#f5f5f5"
    border.color: "#ccc"
    border.width: 1
    radius: 6

    TabBar {
        id: tabBar
        anchors.left: parent.left
        anchors.leftMargin: 1
        anchors.right: parent.right
        anchors.rightMargin: 1
        anchors.top: parent.top
        anchors.topMargin: 1
        height: 44
        currentIndex: viewModel ? viewModel.spindleMode : 0
        onCurrentIndexChanged: if (viewModel) viewModel.setSpindleMode(currentIndex)
        background: Rectangle {
            color: "#f5f5f5"
        }

        TabButton {
            text: "RPM"
            font.pixelSize: 18
            contentItem: Text {
                text: parent.text
                font: parent.font
                color: "#202020"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            background: Rectangle {
                color: parent.checked ? "#ffffff" : "#d9d9d9"
                border.color: "#8c8c8c"
                border.width: 1
            }
        }
        TabButton {
            text: "CSS"
            font.pixelSize: 18
            contentItem: Text {
                text: parent.text
                font: parent.font
                color: "#202020"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            background: Rectangle {
                color: parent.checked ? "#ffffff" : "#d9d9d9"
                border.color: "#8c8c8c"
                border.width: 1
            }
        }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.leftMargin: 1
        anchors.right: parent.right
        anchors.rightMargin: 1
        anchors.top: tabBar.bottom
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 1
        color: "#f5f5f5"

        StackLayout {
            anchors.fill: parent
            anchors.margins: 10
            currentIndex: tabBar.currentIndex

            ColumnLayout {
                spacing: 8
                ManualValueRow {
                    label: "Set RPM:"
                    unit: "rev/min"
                    settingName: viewModel ? viewModel.rpmSettingName : ""
                    value: viewModel ? viewModel.inputRpm : "0"
                    editable: true
                    onOpenNumPadRequested: root.openNumPadRequested(field)
                    onCommitted: if (viewModel) viewModel.setInputRpm(String(value))
                }
                ManualValueRow {
                    label: "Actual RPM:"
                    unit: "rev/min"
                    value: viewModel ? viewModel.actualRpm : "0"
                    editable: false
                }
                Item { Layout.fillHeight: true }
            }

            ColumnLayout {
                spacing: 8
                ManualValueRow {
                    label: "Max RPM:"
                    unit: "rev/min"
                    settingName: viewModel ? viewModel.maxRpmSettingName : ""
                    value: viewModel ? viewModel.inputMaxRpm : "0"
                    editable: true
                    onOpenNumPadRequested: root.openNumPadRequested(field)
                    onCommitted: if (viewModel) viewModel.setInputMaxRpm(String(value))
                }
                ManualValueRow {
                    label: "Actual RPM:"
                    unit: "rev/min"
                    value: viewModel ? viewModel.actualRpm : "0"
                    editable: false
                }
                ManualValueRow {
                    label: "Set CSS:"
                    unit: "m/min"
                    settingName: viewModel ? viewModel.cssSettingName : ""
                    value: viewModel ? viewModel.inputCss : "0"
                    editable: true
                    onOpenNumPadRequested: root.openNumPadRequested(field)
                    onCommitted: if (viewModel) viewModel.setInputCss(String(value))
                }
                ManualValueRow {
                    label: "Actual CSS:"
                    unit: "m/min"
                    value: viewModel ? viewModel.actualCss : "0"
                    editable: false
                }
            }
        }
    }
}
