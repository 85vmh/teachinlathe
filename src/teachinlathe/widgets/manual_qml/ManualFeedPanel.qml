import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../common"

Rectangle {
    id: root
    property var viewModel: manualViewModel
    readonly property bool readOnlyMode: viewModel ? viewModel.feedPanelMode === "ReadOnly" : false
    signal openNumPadRequested(Item field)

    color: "#f5f5f5"

    Rectangle {
        anchors.fill: parent
        color: "#f5f5f5"

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 10
            spacing: 8

            ManualValueRow {
                label: "Set feed:"
                unit: "mm/rev"
                settingName: viewModel ? viewModel.feedSettingName : ""
                value: viewModel ? viewModel.inputFeed : "0.10"
                editable: !root.readOnlyMode
                onOpenNumPadRequested: root.openNumPadRequested(field)
                onCommitted: if (viewModel) viewModel.setInputFeed(String(value))
            }

            ManualValueRow {
                visible: root.readOnlyMode
                label: "Actual feed:"
                unit: "mm/rev"
                value: viewModel ? viewModel.actualFeed : "0.00"
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
    }
}
