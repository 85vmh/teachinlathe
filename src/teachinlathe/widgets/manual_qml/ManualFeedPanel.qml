import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../common"

Rectangle {
    id: root
    property var viewModel: manualViewModel
    signal openNumPadRequested(var field)

    color: "#e6e6e6"

    Rectangle {
        anchors.fill: parent
        color: "#e6e6e6"

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 10
            spacing: 8

            ManualValueRow {
                label: "Set feed:"
                unit: "mm/rev"
                settingName: viewModel ? viewModel.feedSettingName : ""
                value: viewModel ? viewModel.inputFeed : "0.10"
                editable: true
                onOpenNumPadRequested: root.openNumPadRequested(field)
                onCommitted: if (viewModel) viewModel.setInputFeed(String(value))
            }

            ManualValueRow {
                label: "Actual feed:"
                unit: "mm/rev"
                value: viewModel ? viewModel.actualFeed : "0.00"
                editable: false
            }

            Item { Layout.fillHeight: true }

            RapidOverrideSelector {
                Layout.alignment: Qt.AlignHCenter
                label: "Rapid Override"
                maxSpeed: 6000
                value: viewModel ? viewModel.rapidOverride : 50
                segmentWidth: 64
                onSelected: function(v) {
                    if (viewModel) viewModel.setRapidOverride(v)
                }
            }
        }
    }
}
