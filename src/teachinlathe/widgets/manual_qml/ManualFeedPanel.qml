import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../common"

Rectangle {
    id: root
    property var viewModel: manualViewModel
    readonly property string panelMode: viewModel ? viewModel.feedPanelMode : "Editable"
    readonly property bool readOnlyMode: panelMode === "ReadOnly"
    readonly property bool resetRequiredMode: panelMode === "ResetRequired"
    readonly property color warningColor: "#ff9800"
    readonly property color warningBaseColor: "#1e2430"
    readonly property int warningPulseDurationMs: 200
    property color warningTitleColor: warningBaseColor
    signal openNumPadRequested(Item field)

    onResetRequiredModeChanged: {
        if (root.resetRequiredMode) {
            root.warningTitleColor = root.warningBaseColor
        }
    }

    color: "#f5f5f5"

    Rectangle {
        anchors.fill: parent
        color: "#f5f5f5"

        StackLayout {
            anchors.fill: parent
            anchors.margins: 10
            currentIndex: root.resetRequiredMode ? 1 : 0

            ColumnLayout {
                spacing: 8

                ManualValueRow {
                    label: "Set feed:"
                    unit: "mm/rev"
                    settingName: viewModel ? viewModel.feedSettingName : ""
                    value: viewModel ? viewModel.inputFeed : "0.1"
                    editable: !root.readOnlyMode
                    onOpenNumPadRequested: root.openNumPadRequested(field)
                    onCommitted: if (viewModel) viewModel.setInputFeed(String(value))
                }

                ManualValueRow {
                    visible: root.readOnlyMode
                    label: "Actual feed:"
                    unit: "mm/rev"
                    value: viewModel ? viewModel.actualFeed : "0.0"
                    editable: false
                    valueBold: true
                }

                Item { Layout.fillHeight: true }

                RapidOverrideSelector {
                    Layout.fillWidth: true
                    label: "Rapid Speed"
                    maxSpeed: 6000
                    value: viewModel ? viewModel.rapidOverride : 50
                    fillAvailableWidth: true
                    onSelected: function(v) {
                        if (viewModel) viewModel.setRapidOverride(v)
                    }
                }
            }

            Item {
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10

                    Item { Layout.fillHeight: true }

                    Text {
                        Layout.fillWidth: true
                        text: viewModel ? viewModel.feedPanelMessageTitle : ""
                        color: root.warningTitleColor
                        font.pixelSize: 20
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        Layout.fillWidth: true
                        text: viewModel ? viewModel.feedPanelMessageBody : ""
                        color: root.warningBaseColor
                        font.pixelSize: 17
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        wrapMode: Text.WordWrap
                    }

                    Item { Layout.fillHeight: true }
                }
            }
        }

        SequentialAnimation {
            running: root.resetRequiredMode
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
    }
}
