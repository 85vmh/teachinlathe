import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root
    property var viewModel

    SplitView {
        anchors.fill: parent
        orientation: Qt.Horizontal

        GremlinPane {
            viewModel: root.viewModel
            SplitView.preferredWidth: 620
            SplitView.minimumWidth: 420
        }

        ProgramEditorPane {
            viewModel: root.viewModel
            mode: "gremlin"
            SplitView.fillWidth: true
            SplitView.minimumWidth: 420
        }
    }
}
