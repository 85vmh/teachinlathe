import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import common.touchable_input
import theme
import common

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

    IntValidator    { id: intVal }
    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 30
        Layout.alignment: Qt.AlignTop

        // G7x has no M1: the header leaves that width empty
        OperationHeader {
            id: header
            editor: root.editor
            hasM1: false
            onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
        }

        // Row 1: Profiling parameters | Profiling options (top-aligned)
        RowLayout {
            id: firstRow
            Layout.fillWidth: true
            Layout.fillHeight: false
            spacing: 30
            Layout.alignment: Qt.AlignTop

            ProfilingParameters {
                id: profilingParamsPanel
                Layout.fillWidth: true
                Layout.preferredWidth: 6
                Layout.alignment: Qt.AlignTop
                parameters: root.op.profiling_parameters || ({})
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                onEdited: function(changes) { root.editor.edit({ profiling_parameters: changes }) }
            }

            ProfilingOptions {
                id: profilingOptionsPanel
                Layout.fillWidth: true
                Layout.preferredWidth: 4
                Layout.alignment: Qt.AlignTop
                options: root.op.profiling_options || ({})
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                onEdited: function(changes) { root.editor.edit({ profiling_options: changes }) }
                onAddFinishRequested: root.editor.addFinish()
            }
        }

        // Row 2: Cutting parameters (Ap, retract)
        RowLayout {
            id: secondRow
            Layout.fillWidth: true
            Layout.fillHeight: false
            spacing: 30
            Layout.alignment: Qt.AlignTop

            CuttingParameters {
                id: cuttingPanel
                Layout.fillWidth: true
                Layout.preferredWidth: 6
                Layout.alignment: Qt.AlignTop
                cutting: root.op.cutting_parameters || ({})
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                onEdited: function(changes) { root.editor.edit({ cutting_parameters: changes }) }
            }

            Item {
                Layout.fillWidth: true
                Layout.preferredWidth: 4
            }
        }

        Item { Layout.fillHeight: true }
    }
}
