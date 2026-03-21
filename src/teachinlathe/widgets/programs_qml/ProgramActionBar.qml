import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    property var viewModel
    property string mdiText: ""
    readonly property var actions: viewModel ? viewModel.actions : null
    color: "#252526"
    border.color: "#404040"
    border.width: 1

    RowLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 16

        ProgramButton {
            text: actions ? actions.startAction.text : "Start Program"
            enabled: actions ? actions.startAction.enabled : false
            active: actions ? actions.startAction.active : false
            onClicked: actions.triggerStart()
        }

        ProgramButton {
            text: actions ? actions.stopAction.text : "Stop Program"
            enabled: actions ? actions.stopAction.enabled : false
            active: actions ? actions.stopAction.active : false
            accentColor: "#7a2d2d"
            borderColor: actions && actions.stopAction.active ? "#ff7b72" : "#d16969"
            onClicked: actions.triggerStop()
        }

        ProgramButton {
            text: actions ? actions.pauseResumeAction.text : "Pause Program"
            enabled: actions ? actions.pauseResumeAction.enabled : false
            active: actions ? actions.pauseResumeAction.active : false
            accentColor: actions && actions.pauseResumeAction.active ? "#946200" : "#6b5d12"
            borderColor: "#d7ba7d"
            onClicked: actions.triggerPauseResume()
        }

        ProgramButton {
            text: actions ? actions.optionalStopAction.text : "Break on M1"
            enabled: actions ? actions.optionalStopAction.enabled : false
            active: actions ? actions.optionalStopAction.checked : false
            accentColor: active ? "#6b5d12" : "#353535"
            borderColor: active ? "#d7ba7d" : "#575757"
            onClicked: {
                if (actions) {
                    actions.setOptionalStopEnabled(!actions.optionalStopAction.checked)
                }
            }
        }

        ProgramButton {
            text: actions ? actions.blockDeleteAction.text : 'Skip "/" Blocks'
            enabled: actions ? actions.blockDeleteAction.enabled : false
            active: actions ? actions.blockDeleteAction.checked : false
            accentColor: active ? "#5a3d00" : "#353535"
            borderColor: active ? "#e0a800" : "#575757"
            onClicked: {
                if (actions) {
                    actions.setBlockDeleteEnabled(!actions.blockDeleteAction.checked)
                }
            }
        }

        Text {
            text: "MDI"
            color: "#d4d4d4"
            font.pixelSize: 14
        }

        Rectangle {
            Layout.preferredWidth: 220
            Layout.preferredHeight: 46
            radius: 8
            color: "#1e1e1e"
            border.color: actions && actions.mdiAction.enabled ? "#5a5a5a" : "#3d3d3d"
            border.width: 2
            opacity: actions && actions.mdiAction.enabled ? 1.0 : 0.6

            TextInput {
                anchors.fill: parent
                anchors.margins: 10
                text: root.mdiText
                color: "#f0f0f0"
                font.family: "DejaVu Sans Mono"
                font.pixelSize: 14
                selectByMouse: true
                enabled: actions ? actions.mdiAction.enabled : false
                onTextChanged: root.mdiText = text
            }
        }

        ProgramButton {
            text: actions ? actions.mdiAction.text : "Run MDI"
            enabled: actions ? actions.mdiAction.enabled : false
            active: false
            accentColor: "#2d7d46"
            borderColor: "#3fb950"
            onClicked: actions.submitMdi(root.mdiText)
        }

        Item { Layout.fillWidth: true }
    }
}
