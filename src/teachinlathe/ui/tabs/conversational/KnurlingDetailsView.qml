import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme

Item {
    id: root
    anchors.fill: parent

    // The view model of the operation this edits (OperationEditorViewModel.py):
    // the one place what the view shows comes from, and every edit goes to
    required property var editor
    readonly property var op: editor.operation
    signal openNumPadRequested(var field)
    signal teachXRequested(int index)
    signal teachZRequested(int index)

    ColumnLayout {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 10
        spacing: 40

        // Knurling has no feed rate: the header's is left disabled
        OperationHeader {
            id: header
            editor: root.editor
            feedEnabled: false
            onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 30
            Layout.alignment: Qt.AlignTop

            KnurlingGeometry {
                id: geometryPanel
                Layout.fillWidth: true
                Layout.preferredWidth: 6
                Layout.alignment: Qt.AlignTop
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                geometry: root.op.geometry_parameters || ({})
                onTeachXRequested: root.teachXRequested(root.editor.opIndex)
                onTeachZRequested: root.teachZRequested(root.editor.opIndex)
                onEdited: function(changes) { root.editor.edit({ geometry_parameters: changes }) }
            }

            KnurlingCuttingParameters {
                id: cuttingPanel
                Layout.fillWidth: true
                Layout.preferredWidth: 4
                Layout.alignment: Qt.AlignTop
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                cutting: root.op.cutting_parameters || ({})
                onEdited: function(changes) { root.editor.edit({ cutting_parameters: changes }) }
            }
        }
    }
}
