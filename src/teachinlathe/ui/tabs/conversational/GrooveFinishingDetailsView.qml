import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme

Item {
    id: root
    anchors.fill: parent
    implicitHeight: contentColumn.implicitHeight + 20

    // The view model of the operation this edits (OperationEditorViewModel.py).
    property var editor: null
    property int opIndex: -1
    property var opData: null
    signal openNumPadRequested(var field)

    function applyData(index, data) {
        opIndex = index
        opData = data || {}
        spindlePanel.applyData(opIndex, opData)
        cuttingPanel.applyData(opData.cutting_parameters || {})
        finishingPanel.applyData(opData.finishing_parameters || {})
    }

    function mergeIntoOp(payload) {
        var out = JSON.parse(JSON.stringify(opData || {}))
        for (var k in payload) {
            if (k === "index") continue
            if (payload.hasOwnProperty(k)) out[k] = payload[k]
        }
        opData = out
        return out
    }

    ColumnLayout {
        id: contentColumn
        anchors.fill: parent
        anchors.margins: 10
        spacing: Theme.margin
        Layout.alignment: Qt.AlignTop

        GridLayout {
            Layout.fillWidth: true
            columns: 2
            columnSpacing: 30
            rowSpacing: 40

            SpindleParameters {
                id: spindlePanel
                Layout.row: 0
                Layout.column: 0
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                onSaveRequested: function(p) {
                    var merged = root.mergeIntoOp(p.payload || p)
                    root.editor.save(merged)
                }
            }

            GrooveFinishingCuttingParameters {
                id: cuttingPanel
                Layout.row: 0
                Layout.column: 1
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                onSaveRequested: function(p) {
                    var merged = root.mergeIntoOp(p.payload || p)
                    root.editor.save(merged)
                }
            }

            GrooveFinishingParameters {
                id: finishingPanel
                Layout.row: 1
                Layout.column: 0
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                onSaveRequested: function(p) {
                    var merged = root.mergeIntoOp(p.payload || p)
                    root.editor.save(merged)
                }
            }
        }
    }
}
