// StockToLeave.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

GroupBox {
    id: root
    title: "Stock to Leave"
    Layout.fillWidth: true
    font.pixelSize: 16

    property real stock_to_leave_x: 0.0
    property real stock_to_leave_z: 0.0
    property bool _loading: false

    signal saveRequested(var payload)
    signal openNumPadRequested(var field)

    function applyData(data) {
        _loading = true
        stock_to_leave_x = (data && data.stock_to_leave_x !== undefined) ? Number(data.stock_to_leave_x) : 0.0
        stock_to_leave_z = (data && data.stock_to_leave_z !== undefined) ? Number(data.stock_to_leave_z) : 0.0
        _loading = false
    }

    function emitSave() {
        if (_loading) return
        root.saveRequested({
            stock_to_leave: {
                stock_to_leave_x: Number(stock_to_leave_x),
                stock_to_leave_z: Number(stock_to_leave_z)
            }
        })
    }

    GridLayout {
        anchors.fill: parent
        columns: 3
        columnSpacing: 20
        rowSpacing: 16

        Label {
            text: "Stock to leave X"
            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
            font.pixelSize: 16
        }
        NumpadField {
            Layout.preferredWidth: 100
            Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
            settingName: "stock_to_leave.x"
            value: root.stock_to_leave_x
            validatorObject: DoubleValidator { notation: DoubleValidator.StandardNotation }
            formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            font.pixelSize: 16
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: { root.stock_to_leave_x = value; root.emitSave() }
        }
        Label {
            text: "(mm)"
            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
            font.pixelSize: 16
        }

        Label {
            text: "Stock to leave Z"
            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
            font.pixelSize: 16
        }
        NumpadField {
            Layout.preferredWidth: 100
            Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
            settingName: "stock_to_leave.z"
            value: root.stock_to_leave_z
            validatorObject: DoubleValidator { notation: DoubleValidator.StandardNotation }
            formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            font.pixelSize: 16
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: { root.stock_to_leave_z = value; root.emitSave() }
        }
        Label {
            text: "(mm)"
            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
            font.pixelSize: 16
        }
    }
}
