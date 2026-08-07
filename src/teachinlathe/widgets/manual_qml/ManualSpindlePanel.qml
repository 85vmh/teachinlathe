import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../conversational_qml"

Rectangle {
    id: root
    property var viewModel: manualViewModel
    readonly property string panelMode: viewModel ? viewModel.spindlePanelMode : "Editable"
    readonly property bool editableMode: panelMode === "Editable"
    readonly property bool runningMode: panelMode === "ReadOnly"
    readonly property bool readOnlyMode: !editableMode
    readonly property int selectedSpindleMode: viewModel ? viewModel.spindleMode : 0
    readonly property int headerHeight: 50
    readonly property color warningColor: "#ff9800"
    readonly property color warningBaseColor: "#1e2430"
    readonly property int warningPulseDurationMs: 200
    property color warningTitleColor: warningBaseColor
    signal openNumPadRequested(Item field)

    function contentIndex() {
        if (root.editableMode) {
            return root.selectedSpindleMode
        }
        if (root.runningMode) {
            return root.selectedSpindleMode + 2
        }
        return 4
    }

    onPanelModeChanged: {
        if (root.panelMode === "CoverOpened" || root.panelMode === "ResetRequired") {
            root.warningTitleColor = root.warningBaseColor
        }
    }

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
            currentIndex: root.contentIndex()

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

            Item {
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10

                    Item { Layout.fillHeight: true }

                    Text {
                        Layout.fillWidth: true
                        text: viewModel ? viewModel.spindlePanelMessageTitle : ""
                        color: root.warningTitleColor
                        font.pixelSize: 20
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        Layout.fillWidth: true
                        text: viewModel ? viewModel.spindlePanelMessageBody : ""
                        color: "#1e2430"
                        font.pixelSize: 18
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        wrapMode: Text.WordWrap
                    }

                    Item { Layout.fillHeight: true }
                }
            }
        }

        SequentialAnimation {
            running: root.panelMode === "CoverOpened" || root.panelMode === "ResetRequired"
            loops: Animation.Infinite

            ColorAnimation {
                target: root
                property: "warningTitleColor"
                to: root.warningColor
                duration: root.warningPulseDurationMs
                easing.type: Easing.InOutQuad
            }

            ColorAnimation {
                target: root
                property: "warningTitleColor"
                to: root.warningBaseColor
                duration: root.warningPulseDurationMs
                easing.type: Easing.InOutQuad
            }
        }

        Item {
            id: spindleAngleFooter
            visible: root.editableMode
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
