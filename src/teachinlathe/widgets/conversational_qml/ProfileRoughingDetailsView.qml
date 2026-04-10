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
        opData  = data || {}

        spindlePanel.applyData(opIndex, opData)
        cuttingPanel.applyData(opIndex, (opData.cutting_parameters || {}), opData)
        profilingParamsPanel.applyData(opIndex, (opData.profiling_parameters || {}), opData)
        profilingTypePanel.applyData(opData.profile_roughing_strategy || {})
        stockToLeavePanel.applyData(opData.stock_to_leave || {})
        m1Panel.applyData(opData.m1_parameters || {})
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

    IntValidator    { id: intVal }
    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 20
        Layout.alignment: Qt.AlignTop

        Label {
            text: (opData && opData.type)
                  ? ("Profile Roughing — Op #" + (opData.order !== undefined ? opData.order : "N/A"))
                  : "Profile Roughing"
            font.pixelSize: 18
            font.bold: true
            Layout.alignment: Qt.AlignTop
        }

        // Row 1: Spindle | Cutting
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
                    root.saveRequested({index: opIndex, payload: merged})
                }
            }

            CuttingParameters {
                id: cuttingPanel
                Layout.fillWidth: true
                Layout.preferredWidth: 4
                Layout.alignment: Qt.AlignTop
                onOpenNumPadRequested: root.openNumPadRequested(field)
                onSaveRequested: function(p) {
                    var merged = root.mergeIntoOp(p.payload || p)
                    root.saveRequested({index: opIndex, payload: merged})
                }
            }
        }

        // Rows 2–3: two columns
        //   Left:  ProfilingParameters (top) + StockToLeave (bottom)
        //   Right: ProfileRoughingStrategy/ProfilingType (top) + M1Parameters (bottom)
        RowLayout {
            Layout.fillWidth: true
            spacing: 30
            Layout.alignment: Qt.AlignTop

            // Left column
            ColumnLayout {
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.alignment: Qt.AlignTop
                spacing: 20

                ProfilingParameters {
                    id: profilingParamsPanel
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    onOpenNumPadRequested: root.openNumPadRequested(field)
                    onSaveRequested: function(p) {
                        var merged = root.mergeIntoOp(p.payload || p)
                        root.saveRequested({index: opIndex, payload: merged})
                    }
                }

                StockToLeave {
                    id: stockToLeavePanel
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    onOpenNumPadRequested: root.openNumPadRequested(field)
                    onSaveRequested: function(p) {
                        var merged = root.mergeIntoOp(p.payload || p)
                        root.saveRequested({index: opIndex, payload: merged})
                    }
                }
            }

            // Right column
            ColumnLayout {
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.alignment: Qt.AlignTop
                spacing: 20

                ProfileRoughingStrategy {
                    id: profilingTypePanel
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    onSaveRequested: function(p) {
                        var merged = root.mergeIntoOp(p)
                        root.saveRequested({index: opIndex, payload: merged})
                    }
                }

                M1Parameters {
                    id: m1Panel
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    onSaveRequested: function(p) {
                        var merged = root.mergeIntoOp(p)
                        root.saveRequested({index: opIndex, payload: merged})
                    }
                }
            }
        }
    }
}
