import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "." // NumpadField.qml

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

        print("profiling_options:\n" + JSON.stringify(opData.profiling_options, null, 2))

        spindlePanel.applyData(opIndex, opData)
        cuttingPanel.applyData(opIndex, (opData.cutting_parameters || {}), opData)
        profilingParamsPanel.applyData(opIndex, (opData.profiling_parameters || {}), opData)
        // profilingOptionsPanel.applyData(opIndex, (opData.profiling_options || {}), opData)
        profilingOptionsPanel.applyData(opData.profiling_options || {})
    }

    function mergeIntoOp(payload) {
        var out = JSON.parse(JSON.stringify(opData || {}))
        for (var k in payload) {
            if (k === "index") continue
            if (payload.hasOwnProperty(k)) out[k] = payload[k]
        }
        return out
    }

    IntValidator    { id: intVal }
    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 30
        Layout.alignment: Qt.AlignTop

        Label {
            text: (opData && opData.type) ? ("Profiling — Op #" + (opData.order !== undefined ? opData.order : "N/A")) : "Profiling"
            font.pixelSize: 18
            font.bold: true
            Layout.alignment: Qt.AlignTop
        }

        // Row 1: Spindle | Cutting (top-aligned)
        RowLayout {
            id: firstRow
            Layout.fillWidth: true
            Layout.fillHeight: false
            spacing: 30
            Layout.alignment: Qt.AlignTop

            SpindleParameters {
                id: spindlePanel
                Layout.preferredWidth: firstRow.width * 0.6
                Layout.alignment: Qt.AlignTop
                onOpenNumPadRequested: root.openNumPadRequested(field)
                onSaveRequested: function (p) {
                    var merged = root.mergeIntoOp(p.payload || p)
                    root.saveRequested({index: opIndex, payload: merged})
                }
            }

            CuttingParameters {
                id: cuttingPanel
                Layout.preferredWidth: firstRow.width * 0.4
                Layout.alignment: Qt.AlignTop
                onOpenNumPadRequested: root.openNumPadRequested(field)
                onSaveRequested: function (p) {
                    var merged = root.mergeIntoOp(p.payload || p)
                    root.saveRequested({index: opIndex, payload: merged})
                }
            }
        }

        RowLayout {
            id: secondRow
            Layout.fillWidth: true
            Layout.fillHeight: false
            spacing: 30
            Layout.alignment: Qt.AlignTop

            ProfilingParameters {
                id: profilingParamsPanel
                // cere pixeli sau o expresie numerică validă — nu 0.6 simplu
                Layout.preferredWidth: firstRow.width * 0.6
                Layout.alignment: Qt.AlignTop
                onOpenNumPadRequested: root.openNumPadRequested(field)
                onSaveRequested: function (p) {
                    var merged = root.mergeIntoOp(p.payload || p)
                    root.saveRequested({index: opIndex, payload: merged})
                }
            }

            ProfilingOptions {
                id: profilingOptionsPanel
                Layout.preferredWidth: firstRow.width * 0.4
                Layout.alignment: Qt.AlignTop
                onOpenNumPadRequested: root.openNumPadRequested(field)
                onSaveRequested: function (p) {
                    var merged = root.mergeIntoOp(p.payload || p)
                    root.saveRequested({index: opIndex, payload: merged})
                }
            }
        }
    }
}
