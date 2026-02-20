// PartingDetailsView.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root
    anchors.fill: parent

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
        spindlePanel.applyData(opIndex, opData)
        partingParamsPanel.applyData(opIndex, (opData.parting_parameters || {}), opData)
        edgeBreakPanel.applyData(opIndex, (opData.edge_break || {}), opData)
    }

    function mergeIntoOp(payload) {
        var out = JSON.parse(JSON.stringify(opData || {}))
        for (var k in payload) {
            if (k === "index") continue
            if (payload.hasOwnProperty(k)) out[k] = payload[k]
        }
        return out
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10

        Label {
            text: (opData && opData.type) ? ("Parting — Op #" + (opData.order !== undefined ? opData.order : "N/A")) : "Parting"
            font.pixelSize: 18
            font.bold: true
        }

        SpindleParameters {
                id: spindlePanel
                Layout.preferredWidth: 500
                Layout.alignment: Qt.AlignTop
                onOpenNumPadRequested: root.openNumPadRequested(field)
                onSaveRequested: function (p) {
                    var merged = root.mergeIntoOp(p.payload || p)
                    root.saveRequested({index: opIndex, payload: merged})
                }
        }

        PartingParameters {
                id: partingParamsPanel
                Layout.preferredWidth: 500
                Layout.alignment: Qt.AlignTop
                onOpenNumPadRequested: root.openNumPadRequested(field)
                onSaveRequested: function (p) {
                    var merged = root.mergeIntoOp(p.payload || p)
                    root.saveRequested({index: opIndex, payload: merged})
                }
        }

        EdgeBreak {
                id: edgeBreakPanel
                Layout.preferredWidth: 500
                Layout.alignment: Qt.AlignTop
                onOpenNumPadRequested: root.openNumPadRequested(field)
                onSaveRequested: function (p) {
                    var merged = root.mergeIntoOp(p.payload || p)
                    root.saveRequested({index: opIndex, payload: merged})
                }
        }
    }
}
