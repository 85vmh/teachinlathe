import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../conversational_qml"

Rectangle {
    id: root
    property var viewModel: manualViewModel
    readonly property bool readOnlyMode: viewModel ? viewModel.spindlePanelMode === "ReadOnly" : false
    readonly property int selectedSpindleMode: viewModel ? viewModel.spindleMode : 0
    readonly property int headerHeight: 50
    signal openNumPadRequested(Item field)

    color: "#f5f5f5"
    border.color: "#ccc"
    border.width: 1
    radius: 6

    TabBar {
        id: tabBar
        visible: !root.readOnlyMode
        anchors.left: parent.left
        anchors.leftMargin: 1
        anchors.right: parent.right
        anchors.rightMargin: 1
        anchors.top: parent.top
        anchors.topMargin: 1
        height: root.headerHeight
        currentIndex: viewModel ? viewModel.spindleMode : 0
        onCurrentIndexChanged: if (viewModel) viewModel.setSpindleMode(currentIndex)
        background: Rectangle {
            color: "#f5f5f5"
        }

        TabButton {
            text: "RPM"
            height: root.headerHeight
            implicitHeight: root.headerHeight
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
            height: root.headerHeight
            implicitHeight: root.headerHeight
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
        id: readOnlyHeader
        visible: root.readOnlyMode
        anchors.left: parent.left
        anchors.leftMargin: 1
        anchors.right: parent.right
        anchors.rightMargin: 1
        anchors.top: parent.top
        anchors.topMargin: 1
        height: root.headerHeight
        color: "#f5f5f5"

        Text {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: root.headerHeight - 1
            text: "Spindle Mode: " + (viewModel ? viewModel.spindleModeLabel : "RPM")
            color: "#1e2430"
            font.pixelSize: 17
            font.bold: true
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

    Rectangle {
        id: contentArea
        anchors.left: parent.left
        anchors.leftMargin: 1
        anchors.right: parent.right
        anchors.rightMargin: 1
        anchors.top: root.readOnlyMode ? readOnlyHeader.bottom : tabBar.bottom
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 1
        color: "#f5f5f5"

        StackLayout {
            anchors.left: parent.left
            anchors.leftMargin: 10
            anchors.right: parent.right
            anchors.rightMargin: 10
            anchors.top: parent.top
            anchors.topMargin: 10
            anchors.bottom: root.readOnlyMode ? parent.bottom : spindleAngleFooter.top
            anchors.bottomMargin: root.readOnlyMode ? 10 : 0
            currentIndex: root.readOnlyMode ? root.selectedSpindleMode + 2 : root.selectedSpindleMode

            Item {
                ColumnLayout {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    spacing: 0

                    ManualValueRow {
                        label: "Set RPM:"
                        unit: "rev/min"
                        settingName: viewModel ? viewModel.rpmSettingName : ""
                        value: viewModel ? viewModel.inputRpm : "0"
                        editable: true
                        onOpenNumPadRequested: root.openNumPadRequested(field)
                        onCommitted: if (viewModel) viewModel.setInputRpm(String(value))
                    }
                }
            }

            Item {
                ColumnLayout {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    spacing: 20

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
                        label: "Set CSS:"
                        unit: "m/min"
                        settingName: viewModel ? viewModel.cssSettingName : ""
                        value: viewModel ? viewModel.inputCss : "0"
                        editable: true
                        onOpenNumPadRequested: root.openNumPadRequested(field)
                        onCommitted: if (viewModel) viewModel.setInputCss(String(value))
                    }
                }
            }

            ColumnLayout {
                spacing: 6
                ManualValueRow {
                    label: "Set RPM:"
                    unit: "rev/min"
                    value: viewModel ? viewModel.inputRpm : "0"
                    editable: false
                }
                ManualValueRow {
                    label: "Actual RPM:"
                    unit: "rev/min"
                    value: viewModel ? viewModel.actualRpm : "0"
                    editable: false
                    valueBold: true
                }
                Item { Layout.fillHeight: true }
            }

            ColumnLayout {
                spacing: 6
                ManualValueRow {
                    label: "Max RPM:"
                    unit: "rev/min"
                    value: viewModel ? viewModel.inputMaxRpm : "0"
                    editable: false
                }
                ManualValueRow {
                    label: "Actual RPM:"
                    unit: "rev/min"
                    value: viewModel ? viewModel.actualRpm : "0"
                    editable: false
                    valueBold: true
                }
                ManualValueRow {
                    label: "Set CSS:"
                    unit: "m/min"
                    value: viewModel ? viewModel.inputCss : "0"
                    editable: false
                }
                ManualValueRow {
                    label: "Actual CSS:"
                    unit: "m/min"
                    value: viewModel ? viewModel.actualCss : "0"
                    editable: false
                    valueBold: true
                }
            }
        }

        Item {
            id: spindleAngleFooter
            visible: !root.readOnlyMode
            anchors.left: parent.left
            anchors.leftMargin: 10
            anchors.right: parent.right
            anchors.rightMargin: 10
            anchors.bottom: parent.bottom
            height: 50

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: 1
                color: "#ccc"
            }

            ManualSpindleAngle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                value: viewModel ? viewModel.spindleAngleText : "0.0°"
            }
        }
    }
}
