// FacingDetailsView.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."
import theme 1.0

Item {
    id: root
    anchors.fill: parent

    property int  opIndex: -1
    property var  opData: null

    signal saveRequested(var updated)

    signal openNumPadRequested(var field)

    signal teachXRequested(int index)

    signal teachZRequested(int index)

    function applyData(index, data) {
        opIndex = index
        opData = data || {}

        // populate sub-panels
        header.applyData(opData, (opData.cutting_parameters || {}).feed_rate)
        cuttingPanel.applyData(opIndex, (opData.cutting_parameters || {}), opData)
        geometryPanel.applyData(opIndex, (opData.geometry_parameters || {}), opData)
        extrasPanel.applyData(opIndex, opData)
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

    // ===== Layout: header, then a two-column parameter grid =====
    ColumnLayout {
        id: col
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 10
        spacing: Theme.margin

        OperationHeader {
            id: header
            onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            onSpindleEdited: function(spindle) { root.save({spindle_parameters: spindle}) }
            onFeedRateEdited: function(value) { root.save({cutting_parameters: {feed_rate: value}}) }
            onM1Edited: function(m1) { root.save({m1_parameters: m1}) }
        }

        GridLayout {
            id: detailsGrid
            Layout.fillWidth: true
            columns: 2
            columnSpacing: 30
            rowSpacing: 40
            Layout.alignment: Qt.AlignTop

            // Row 1, column 1
            CuttingGeometry {
                id: geometryPanel
                Layout.row: 0
                Layout.column: 0
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.alignment: Qt.AlignTop
                onOpenNumPadRequested: root.openNumPadRequested(field)
                onTeachXRequested: root.teachXRequested(opIndex)
                onTeachZRequested: root.teachZRequested(opIndex)
                onSaveRequested: function (p) { root.save(p) }
            }

            // Row 1, column 2
            CuttingParameters {
                id: cuttingPanel
                Layout.row: 0
                Layout.column: 1
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.alignment: Qt.AlignTop
                onOpenNumPadRequested: root.openNumPadRequested(field)
                onSaveRequested: function (p) { root.save(p.payload || p) }
            }

            // Row 2, column 1
            FacingExtras {
                id: extrasPanel
                Layout.row: 1
                Layout.column: 0
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.alignment: Qt.AlignTop
                onSaveRequested: function (p) { root.save(p.payload || p) }
            }

            // Row 2, column 2 intentionally empty.
            Item {
                Layout.row: 1
                Layout.column: 1
                Layout.fillWidth: true
                Layout.preferredWidth: 1
            }
        }
    }
}
