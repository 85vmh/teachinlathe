// FacingDetailsView.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

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
        spindlePanel.applyData(opIndex, opData)
        cuttingPanel.applyData(opIndex, (opData.cutting_parameters || {}), opData)
        geometryPanel.applyData(opIndex, (opData.geometry_parameters || {}), opData)
        m1Panel.applyData(opData && opData.m1_parameters ? opData.m1_parameters : {})
        extrasPanel.applyData(opIndex, opData)
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

    // ===== Layout: title + two-column parameter grid =====
    ColumnLayout {
        id: col
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 10
        spacing: 24

        Label {
            text: (opData && opData.type) ? ("Facing — Op #" + (opData.order !== undefined ? opData.order : "N/A")) : "Facing"
            font.pixelSize: 18
            font.bold: true
        }

        GridLayout {
            id: detailsGrid
            Layout.fillWidth: true
            columns: 2
            columnSpacing: 30
            rowSpacing: 40
            Layout.alignment: Qt.AlignTop

            // Row 1, column 1
            SpindleParameters {
                id: spindlePanel
                Layout.row: 0
                Layout.column: 0
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.alignment: Qt.AlignTop
                onOpenNumPadRequested: root.openNumPadRequested(field)
                onSaveRequested: function (p) {
                    var merged = root.mergeIntoOp(p.payload || p)
                    root.saveRequested({index: opIndex, payload: merged})
                }
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
                onSaveRequested: function (p) {
                    var merged = root.mergeIntoOp(p.payload || p)
                    root.saveRequested({index: opIndex, payload: merged})
                }
            }

            // Row 2, column 1
            CuttingGeometry {
                id: geometryPanel
                Layout.row: 1
                Layout.column: 0
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.alignment: Qt.AlignTop
                onOpenNumPadRequested: root.openNumPadRequested(field)
                onTeachXRequested: root.teachXRequested(opIndex)
                onTeachZRequested: root.teachZRequested(opIndex)
                onSaveRequested: function (p) {
                    var merged = root.mergeIntoOp(p)
                    root.saveRequested({index: opIndex, payload: merged})
                }
            }

            // Row 2, column 2 intentionally empty.
            Item {
                Layout.row: 1
                Layout.column: 1
                Layout.fillWidth: true
                Layout.preferredWidth: 1
            }

            // Row 3, column 1
            M1Parameters {
                id: m1Panel
                Layout.row: 2
                Layout.column: 0
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.alignment: Qt.AlignTop
                onSaveRequested: function (payload) {
                    var merged = root.mergeIntoOp(payload)
                    root.saveRequested({index: opIndex, payload: merged})
                }
            }

            // Row 3, column 2 intentionally empty.
            Item {
                Layout.row: 2
                Layout.column: 1
                Layout.fillWidth: true
                Layout.preferredWidth: 1
            }

            // Row 4, column 1
            FacingExtras {
                id: extrasPanel
                Layout.row: 3
                Layout.column: 0
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.alignment: Qt.AlignTop
                onSaveRequested: function (p) {
                    var merged = root.mergeIntoOp(p.payload || p)
                    root.saveRequested({index: opIndex, payload: merged})
                }
            }

            // Row 4, column 2 intentionally empty.
            Item {
                Layout.row: 3
                Layout.column: 1
                Layout.fillWidth: true
                Layout.preferredWidth: 1
            }
        }
    }
}
