import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root
    property var viewModel

    SplitView {
        anchors.fill: parent
        orientation: Qt.Horizontal

        ProgramLoadedLeftPane {
            viewModel: root.viewModel
            SplitView.preferredWidth: root.width / 2
            SplitView.minimumWidth: 420
        }

        ProgramEditorPane {
            viewModel: root.viewModel
            mode: "gremlin"
            SplitView.preferredWidth: root.width / 2
            SplitView.minimumWidth: 420
        }
    }
}
