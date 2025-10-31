// CuttingParameters.qml (styled like SpindleParameters inputs)
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

GroupBox {
    id: root
    title: "Cutting Parameters"
    Layout.fillWidth: true
    Layout.minimumWidth: 360
    Layout.preferredWidth: 520
    font.pixelSize: 16

    // bridge
    property int opIndex: -1
    property var opData: null

    signal saveRequested(var updated)

    signal openNumPadRequested(var field)

    // state
    property real feed_rate: 0.0
    property real doc: 0.0
    property real retract: 0.0

    function applyData(index, data) {
        opIndex = index
        opData = data || {}
        feed_rate = parseFloat((opData.feed_rate !== undefined) ? opData.feed_rate : 0.0)
        doc = parseFloat((opData.doc !== undefined) ? opData.doc : 0.0)
        retract = parseFloat((opData.retract !== undefined) ? opData.retract : 0.0)
    }

    function emitSave() {
        if (!opData) return
        var payload = {
            order: (opData && opData.order !== undefined) ? opData.order : 0,
            type: (opData && opData.type) ? opData.type : "",
            generate_gcode: (opData && opData.generate_gcode !== undefined) ? opData.generate_gcode : true,
            is_optional_block: (opData && opData.is_optional_block !== undefined) ? opData.is_optional_block : false,
            feed_rate: feed_rate,
            doc: doc,
            retract: retract
        }
        root.saveRequested({index: opIndex, payload: payload})
    }

    GridLayout {
        id: grid
        anchors.fill: parent
        columns: 3
        columnSpacing: 20
        rowSpacing: 20

        // Feed Rate
        Label {
            text: "Feed rate"
            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
            font.pixelSize: 16
        }
        NumpadField {
            Layout.preferredWidth: 100
            Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
            settingName: "cut.feed_rate"
            value: root.feed_rate
            validatorObject: DoubleValidator {
                notation: DoubleValidator.StandardNotation
            }
            formatter: function (v) {
                return (v == null) ? "" : Number(v).toFixed(3)
            }
            hAlign: Text.AlignRight
            fontPixelSize: 16
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: { root.feed_rate = value; root.emitSave() }
        }
        Label {
            text: "(mm/rev)"
            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
            font.pixelSize: 16
        }

        // Depth of Cut
        Label {
            text: "Depth of Cut"
            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
            font.pixelSize: 16
        }
        NumpadField {
            Layout.preferredWidth: 100
            Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
            settingName: "cut.doc"
            value: root.doc
            validatorObject: DoubleValidator {
                notation: DoubleValidator.StandardNotation
            }
            formatter: function (v) {
                return (v == null) ? "" : Number(v).toFixed(3)
            }
            hAlign: Text.AlignRight
            fontPixelSize: 16
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: { root.doc = value; root.emitSave() }
        }
        Label {
            text: "(mm)"
            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
            font.pixelSize: 16
        }

        // Retract
        Label {
            text: "Retract"
            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
            font.pixelSize: 16
        }
        NumpadField {
            Layout.preferredWidth: 100
            Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
            settingName: "cut.retract"
            value: root.retract
            validatorObject: DoubleValidator {
                notation: DoubleValidator.StandardNotation
            }
            formatter: function (v) {
                return (v == null) ? "" : Number(v).toFixed(3)
            }
            hAlign: Text.AlignRight
            fontPixelSize: 16
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: { root.retract = value; root.emitSave() }
        }
        Label {
            text: "(mm)"
            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
            font.pixelSize: 16
        }
    }
}
