// TappingDetailsView.qml
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
        spindlePanel.rpmOnly = true
        spindlePanel.applyData(opIndex, opData)
        tappingParamsPanel.applyData(opIndex, (opData.tapping_parameters || {}), opData)
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
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10

        Label {
            text: (opData && opData.type) ? ("Tapping — Op #" + (opData.order !== undefined ? opData.order : "N/A")) : "Tapping"
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

        TappingParameters {
                id: tappingParamsPanel
                Layout.preferredWidth: 500
                Layout.alignment: Qt.AlignTop
                onOpenNumPadRequested: root.openNumPadRequested(field)
                onTeachZRequested: root.teachZRequested(opIndex)
                onSaveRequested: function (p) {
                    var merged = root.mergeIntoOp(p.payload || p)
                    root.saveRequested({index: opIndex, payload: merged})
                }
        }

        M1Parameters {
                id: m1Panel
                Layout.preferredWidth: 500
                Layout.alignment: Qt.AlignTop
                onOpenNumPadRequested: root.openNumPadRequested(field)
                onTeachXRequested: root.teachXRequested(opIndex)
                onTeachZRequested: root.teachZRequested(opIndex)
                onSaveRequested: function (payload) {
                    var merged = root.mergeIntoOp(payload)
                    root.saveRequested({index: opIndex, payload: merged})
                }
            }
    }
}
