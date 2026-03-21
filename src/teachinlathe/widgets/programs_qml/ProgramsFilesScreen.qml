import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root
    property var viewModel

    SplitView {
        anchors.fill: parent
        orientation: Qt.Horizontal

        ProgramBrowserPane {
            viewModel: root.viewModel
            SplitView.preferredWidth: 340
            SplitView.minimumWidth: 280
        }

        ProgramEditorPane {
            viewModel: root.viewModel
            mode: "files"
            SplitView.fillWidth: true
            SplitView.minimumWidth: 480
        }
    }
}
