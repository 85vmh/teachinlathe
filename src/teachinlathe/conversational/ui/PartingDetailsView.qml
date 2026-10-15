// PartingDetailsView.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import theme 1.0

Item {
    id: root
    anchors.fill: parent
    implicitHeight: contentColumn.implicitHeight + 20

    // API & data
    property int  opIndex: -1
    property var  opData:  null

    signal saveRequested(var updated)

    signal openNumPadRequested(var field)

    signal teachZRequested(int index)

    function applyData(index, data) {
        opIndex = index
        opData = data || {}

        // populate sub-panels
        header.applyData(opData, (opData.parting_parameters || {}).first_feed_rate)
        partingParamsPanel.applyData(opIndex, (opData.parting_parameters || {}), opData)
        edgeBreakPanel.applyData(opIndex, (opData.edge_break || {}), opData)
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

        // Parting has no M1; the header's feed rate is the first feed rate,
        // the second one stays in Parting Parameters with where it starts
        OperationHeader {
            id: header
            hasM1: false
            onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            onSpindleEdited: function(spindle) { root.save({spindle_parameters: spindle}) }
            onFeedRateEdited: function(value) { root.save({parting_parameters: {first_feed_rate: value}}) }
        }

        GridLayout {
            id: detailsGrid
            Layout.fillWidth: true
            columns: 2
            columnSpacing: 24
            rowSpacing: 40
            Layout.alignment: Qt.AlignTop

            // Row 1, column 1
            Item {
                Layout.row: 0
                Layout.column: 0
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                Layout.preferredWidth: 1
                Layout.preferredHeight: partingParamsPanel.implicitHeight
                Layout.alignment: Qt.AlignTop

                PartingParameters {
                    id: partingParamsPanel
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    onOpenNumPadRequested: root.openNumPadRequested(field)
                    onSaveRequested: function (p) { root.save(p.payload || p) }
                }
            }

            // Row 1, column 2 intentionally empty.
            Item {
                Layout.row: 0
                Layout.column: 1
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                Layout.preferredWidth: 1
            }

            // Row 2, column 1
            Item {
                Layout.row: 1
                Layout.column: 0
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                Layout.preferredWidth: 1
                Layout.preferredHeight: edgeBreakPanel.implicitHeight
                Layout.alignment: Qt.AlignTop

                EdgeBreak {
                    id: edgeBreakPanel
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    onOpenNumPadRequested: root.openNumPadRequested(field)
                    onSaveRequested: function (p) { root.save(p.payload || p) }
                }
            }

            // Row 2, column 2 intentionally empty.
            Item {
                Layout.row: 1
                Layout.column: 1
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                Layout.preferredWidth: 1
            }
        }

        Item { Layout.fillHeight: true }
    }
}
