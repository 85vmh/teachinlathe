import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Item {
    id: root
    anchors.fill: parent

    property int opIndex: -1
    property var opData: null

    signal saveRequested(var updated)
    signal openNumPadRequested(var field)
    signal teachXRequested(int index)
    signal teachZRequested(int index)

    function applyData(index, data) {
        opIndex = index
        opData = data || {}

        spindlePanel.applyData(opIndex, opData)
        cuttingPanel.applyData(opIndex, (opData.cutting_parameters || {}), opData)
        geometryPanel.applyData(opIndex, (opData.geometry_parameters || {}), opData)
        m1Panel.applyData(opData && opData.m1_parameters ? opData.m1_parameters : {})
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
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 10
        spacing: 40

        Label {
            text: (opData && opData.type) ? ("SinglePoint Knurling - Op #" + (opData.order !== undefined ? opData.order : "N/A")) : "SinglePoint Knurling"
            font.pixelSize: 18
            font.bold: true
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 30
            Layout.alignment: Qt.AlignTop

            SpindleParameters {
                id: spindlePanel
                Layout.fillWidth: true
                Layout.preferredWidth: 6
                Layout.alignment: Qt.AlignTop
                onOpenNumPadRequested: root.openNumPadRequested(field)
                onSaveRequested: function(p) {
                    var merged = root.mergeIntoOp(p.payload || p)
                    root.saveRequested({ index: opIndex, payload: merged })
                }
            }

            KnurlingCuttingParameters {
                id: cuttingPanel
                Layout.fillWidth: true
                Layout.preferredWidth: 4
                Layout.alignment: Qt.AlignTop
                onOpenNumPadRequested: root.openNumPadRequested(field)
                onSaveRequested: function(p) {
                    var merged = root.mergeIntoOp(p.payload || p)
                    root.saveRequested({ index: opIndex, payload: merged })
                }
            }
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
                onOpenNumPadRequested: root.openNumPadRequested(field)
                onTeachXRequested: root.teachXRequested(opIndex)
                onTeachZRequested: root.teachZRequested(opIndex)
                onSaveRequested: function(p) {
                    var merged = root.mergeIntoOp(p)
                    root.saveRequested({ index: opIndex, payload: merged })
                }
            }

            M1Parameters {
                id: m1Panel
                Layout.fillWidth: true
                Layout.preferredWidth: 4
                Layout.alignment: Qt.AlignTop
                onSaveRequested: function(payload) {
                    var merged = root.mergeIntoOp(payload)
                    root.saveRequested({ index: opIndex, payload: merged })
                }
            }
        }
    }
}
