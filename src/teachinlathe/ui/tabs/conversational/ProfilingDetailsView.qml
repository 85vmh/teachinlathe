import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import common.touchable_input
import theme

Item {
    id: root
    anchors.fill: parent

    // The view model of the operation this edits (OperationEditorViewModel.py).
    property var editor: null
    property int opIndex: -1
    property var opData: null

    signal openNumPadRequested(var field)

    signal teachXRequested(int index)

    signal teachZRequested(int index)

    function applyData(index, data) {
        opIndex = index
        opData = data || {}

        header.applyData(opData)
        cuttingPanel.applyData(opIndex, (opData.cutting_parameters || {}), opData)
        profilingParamsPanel.applyData(opIndex, (opData.profiling_parameters || {}), opData)
        profilingOptionsPanel.applyData(opData.profiling_options || {})
    }

    // Sub-objects merge one level deep, so a part sent alone (the header's
    // feed rate, say) updates its fields and keeps the rest.
    function mergeIntoOp(payload) {
        var out = JSON.parse(JSON.stringify(opData || {}))
        for (var k in payload) {
            if (k === "index" || !payload.hasOwnProperty(k)) continue
            var v = payload[k]
            var cur = out[k]
            if (v && typeof v === "object" && !Array.isArray(v)
                    && cur && typeof cur === "object" && !Array.isArray(cur))
                out[k] = Object.assign({}, cur, v)
            else
                out[k] = v
        }
        opData = out
        return out
    }

    function save(payload) {
        root.editor.save(root.mergeIntoOp(payload))
    }

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
            hasM1: false
            onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            onSpeedsAndFeedsEdited: function(speeds) { root.save({speeds_and_feeds: speeds}) }
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
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                onSaveRequested: function (p) { root.save(p.payload || p) }
            }

            ProfilingOptions {
                id: profilingOptionsPanel
                Layout.fillWidth: true
                Layout.preferredWidth: 4
                Layout.alignment: Qt.AlignTop
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                onSaveRequested: function (p) { root.save(p.payload || p) }
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
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                onSaveRequested: function (p) { root.save(p.payload || p) }
            }

            Item {
                Layout.fillWidth: true
                Layout.preferredWidth: 4
            }
        }

        Item { Layout.fillHeight: true }
    }
}
