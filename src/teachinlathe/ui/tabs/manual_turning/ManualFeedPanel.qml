import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import common
import theme

Rectangle {
    id: root
    required property var viewModel
    readonly property string panelMode: viewModel.feedPanelMode
    readonly property bool readOnlyMode: panelMode === "ReadOnly"
    readonly property bool resetRequiredMode: panelMode === "ResetRequired"
    readonly property color warningColor: Theme.warning
    readonly property color warningBaseColor: Theme.foreground
    readonly property int warningPulseDurationMs: 200
    property color warningTitleColor: warningBaseColor
    signal openNumPadRequested(Item field)

    onResetRequiredModeChanged: {
        if (root.resetRequiredMode) {
            root.warningTitleColor = root.warningBaseColor
        }
    }

    color: Theme.surfaceSunken

    Rectangle {
        anchors.fill: parent
        color: Theme.surfaceSunken

        StackLayout {
            anchors.fill: parent
            anchors.margins: 10
            currentIndex: root.resetRequiredMode ? 1 : 0

            ColumnLayout {
                spacing: Theme.spacingSmall

                ManualValueRow {
                    label: "Set feed:"
                    unit: "mm/rev"
                    settingName: viewModel.feedSettingName
                    value: viewModel.inputFeed
                    editable: !root.readOnlyMode
                    onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                    onCommitted: function(value) { viewModel.setInputFeed(String(value)) }
                }

                ManualValueRow {
                    visible: root.readOnlyMode
                    label: "Actual feed:"
                    unit: "mm/rev"
                    value: viewModel.actualFeed
                    editable: false
                    valueBold: true
                }

                Item { Layout.fillHeight: true }

                RapidOverrideSelector {
                    Layout.fillWidth: true
                    label: "Rapid Speed"
                    maxSpeed: 6000
                    value: viewModel.rapidOverride
                    fillAvailableWidth: true
                    onSelected: function(v) {
                        viewModel.setRapidOverride(v)
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
                        text: viewModel.feedPanelMessageTitle
                        color: root.warningTitleColor
                        font.pixelSize: Theme.fontTitle
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        Layout.fillWidth: true
                        text: viewModel.feedPanelMessageBody
                        color: root.warningBaseColor
                        font.pixelSize: Theme.fontLarge
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
