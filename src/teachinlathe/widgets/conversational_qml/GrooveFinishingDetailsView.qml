import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

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
        spacing: 24
        Layout.alignment: Qt.AlignTop

        Label {
            text: (opData && opData.type)
                  ? ("Groove Finishing - Op #" + (opData.order !== undefined ? opData.order : "N/A"))
                  : "Groove Finishing"
            font.pixelSize: 18
            font.bold: true
        }

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
                onOpenNumPadRequested: root.openNumPadRequested(field)
                onSaveRequested: function(p) {
                    var merged = root.mergeIntoOp(p.payload || p)
                    root.saveRequested({index: opIndex, payload: merged})
                }
            }

            GrooveFinishingCuttingParameters {
                id: cuttingPanel
                Layout.row: 0
                Layout.column: 1
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                onOpenNumPadRequested: root.openNumPadRequested(field)
                onSaveRequested: function(p) {
                    var merged = root.mergeIntoOp(p.payload || p)
                    root.saveRequested({index: opIndex, payload: merged})
                }
            }

            GrooveFinishingParameters {
                id: finishingPanel
                Layout.row: 1
                Layout.column: 0
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                onOpenNumPadRequested: root.openNumPadRequested(field)
                onSaveRequested: function(p) {
                    var merged = root.mergeIntoOp(p.payload || p)
                    root.saveRequested({index: opIndex, payload: merged})
                }
            }
        }
    }
}
