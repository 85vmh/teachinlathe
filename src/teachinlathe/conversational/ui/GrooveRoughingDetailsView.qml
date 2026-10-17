import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."
import theme 1.0

Item {
    id: root
    anchors.fill: parent
    implicitHeight: contentColumn.implicitHeight + 20

    property int opIndex: -1
    property var opData: null

    signal saveRequested(var updated)
    signal openNumPadRequested(var field)

    function applyData(index, data) {
        opIndex = index
        opData = data || {}
        header.applyData(opData, (opData.cutting_parameters || {}).feed_rate)
        cuttingPanel.applyData(opData.cutting_parameters || {})
        roughingPanel.applyData(opData.roughing_parameters || {})
        stockToLeavePanel.applyData(opData.stock_to_leave || {}, !!opData.stock_to_leave_enabled)
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
        root.saveRequested({index: opIndex, payload: root.mergeIntoOp(payload)})
    }

    ColumnLayout {
        id: contentColumn
        anchors.fill: parent
        anchors.margins: 10
        spacing: Theme.margin
        Layout.alignment: Qt.AlignTop

        // Speeds and Feeds and Pause to Inspect, as Facing has them; the
        // feed rate is the cutting_parameters'
        OperationHeader {
            id: header
            onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            onSpindleEdited: function(spindle) { root.save({spindle_parameters: spindle}) }
            onFeedRateEdited: function(value) { root.save({cutting_parameters: {feed_rate: value}}) }
            onM1Edited: function(m1) { root.save({m1_parameters: m1}) }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: 2
            columnSpacing: 30
            rowSpacing: 40

            GrooveRoughingParameters {
                id: roughingPanel
                Layout.row: 0
                Layout.column: 0
                Layout.rowSpan: 2
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.alignment: Qt.AlignTop
                onOpenNumPadRequested: root.openNumPadRequested(field)
                onSaveRequested: function(p) { root.save(p.payload || p) }
            }

            GrooveRoughingCuttingParameters {
                id: cuttingPanel
                Layout.row: 0
                Layout.column: 1
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.alignment: Qt.AlignTop
                onOpenNumPadRequested: root.openNumPadRequested(field)
                onSaveRequested: function(p) { root.save(p.payload || p) }
            }

            CheckableStockToLeave {
                id: stockToLeavePanel
                Layout.row: 1
                Layout.column: 1
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.alignment: Qt.AlignTop
                onOpenNumPadRequested: root.openNumPadRequested(field)
                onSaveRequested: function(p) { root.save(p.payload || p) }
            }
        }

        Item { Layout.fillHeight: true }
    }
}
