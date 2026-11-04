import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
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
        geometryPanel.applyData(opIndex, (opData.geometry_parameters || {}), opData)
    }

    // Sub-objects merge one level deep, so a part sent alone updates its
    // fields and keeps the rest.
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

    ColumnLayout {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 10
        spacing: 40

        // Knurling has no feed rate: the header's is left disabled
        OperationHeader {
            id: header
            feedEnabled: false
            onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            onSpeedsAndFeedsEdited: function(speeds) { root.save({speeds_and_feeds: speeds}) }
            onM1Edited: function(m1) { root.save({m1_parameters: m1}) }
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
                onTeachXRequested: root.teachXRequested(opIndex)
                onTeachZRequested: root.teachZRequested(opIndex)
                onSaveRequested: function(p) { root.save(p) }
            }

            KnurlingCuttingParameters {
                id: cuttingPanel
                Layout.fillWidth: true
                Layout.preferredWidth: 4
                Layout.alignment: Qt.AlignTop
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                onSaveRequested: function(p) { root.save(p.payload || p) }
            }
        }
    }
}
