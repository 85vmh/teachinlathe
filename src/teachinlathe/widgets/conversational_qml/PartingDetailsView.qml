// PartingDetailsView.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root
    anchors.fill: parent
    implicitHeight: contentColumn.implicitHeight + 24

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
        opData = out
        return out
    }

    ColumnLayout {
        id: contentColumn
        anchors.fill: parent
        anchors.margins: 12
        spacing: 24

        Label {
            text: (opData && opData.type) ? ("Parting — Op #" + (opData.order !== undefined ? opData.order : "N/A")) : "Parting"
            font.pixelSize: 18
            font.bold: true
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
                Layout.preferredHeight: spindlePanel.implicitHeight
                Layout.alignment: Qt.AlignTop

                SpindleParameters {
                    id: spindlePanel
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    onOpenNumPadRequested: root.openNumPadRequested(field)
                    onSaveRequested: function (p) {
                        var merged = root.mergeIntoOp(p.payload || p)
                        root.saveRequested({index: opIndex, payload: merged})
                    }
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
                Layout.preferredHeight: partingParamsPanel.implicitHeight
                Layout.alignment: Qt.AlignTop

                PartingParameters {
                    id: partingParamsPanel
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    onOpenNumPadRequested: root.openNumPadRequested(field)
                    onSaveRequested: function (p) {
                        var merged = root.mergeIntoOp(p.payload || p)
                        root.saveRequested({index: opIndex, payload: merged})
                    }
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

            // Row 3, column 1
            Item {
                Layout.row: 2
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
                    onSaveRequested: function (p) {
                        var merged = root.mergeIntoOp(p.payload || p)
                        root.saveRequested({index: opIndex, payload: merged})
                    }
                }
            }

            // Row 3, column 2 intentionally empty.
            Item {
                Layout.row: 2
                Layout.column: 1
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                Layout.preferredWidth: 1
            }
        }
    }
}
