import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    property var viewModel
    property string mode: "files"

    color: "#ffffff"

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        ProgramEditorToolbar {
            Layout.fillWidth: true
            viewModel: root.viewModel
            mode: root.mode
        }

        Loader {
            Layout.fillWidth: true
            Layout.fillHeight: true
            sourceComponent: viewModel && viewModel.hasExecutionStack ? executionComponent : editorComponent
        }

        ProgramActionBar {
            Layout.fillWidth: true
            visible: root.mode === "gremlin"
            Layout.preferredHeight: visible ? 90 : 0
            viewModel: root.viewModel
        }
    }

    Component {
        id: editorComponent

        ProgramContentFrame {
            filePath: viewModel ? viewModel.currentFilePath : ""
            Layout.fillWidth: true
            Layout.fillHeight: true

            GCodeTextArea {
                Layout.fillWidth: true
                Layout.fillHeight: true
                viewModel: root.viewModel
                content: viewModel ? viewModel.currentFileContent : ""
                editable: viewModel ? viewModel.editMode : false
                highlightLine: viewModel ? viewModel.mainHighlightLine : 0
                highlightColor: "#3A86FF"
                highlightWidth: 1
                centerOnHighlight: false
                emptyText: "Select a G-code file"
                onContentEdited: function(text) {
                    if (viewModel) {
                        viewModel.updateCurrentContent(text)
                    }
                }
            }
        }
    }

    Component {
        id: executionComponent

        ProgramExecutionStack {
            viewModel: root.viewModel
        }
    }
}
