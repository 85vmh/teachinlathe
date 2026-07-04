import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".."

Item {
    id: root
    property var viewModel
    property var fileSystemViewModel

    SplitView {
        anchors.fill: parent
        orientation: Qt.Horizontal

        FileSystemView {
            viewModel: root.fileSystemViewModel
            SplitView.preferredWidth: parent.width / 2
            SplitView.minimumWidth: 200
        }

        ProgramEditorPane {
            viewModel: root.viewModel
            mode: "files"
            SplitView.fillWidth: true
            SplitView.minimumWidth: 200
        }
    }
}
