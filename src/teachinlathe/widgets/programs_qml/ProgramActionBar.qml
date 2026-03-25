import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    property var viewModel
    readonly property var actions: viewModel ? viewModel.actions : null
    color: "#f5f5f5"
    border.color: "#cccccc"
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

        Item {
            Layout.fillWidth: true
        }
    }
}
