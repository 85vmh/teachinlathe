// PartingParameters.qml — two equal 3x2 grids side-by-side (Start | Spacer | End)
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

GroupBox {
    id: root
    title: "Parting Parameters"
    Layout.fillWidth: true
    Layout.minimumWidth: 420
    Layout.preferredWidth: 560
    font.pixelSize: 16

    // bridge
    property int  opIndex: -1
    property var  opData: null
    property var  partingData: ({})
    signal saveRequested(var payload)
    signal openNumPadRequested(var field)
    signal teachXRequested(int index)
    signal teachZRequested(int index)

    // state
    property real x_start: 0.0
    property real x_end:   0.0
    property real z_pos:   0.0
    property real second_feed_x_pos:   0.0
    property real first_feed_rate:   0.0
    property real second_feed_rate:   0.0
    property bool _loading: false

    function applyData(index, partingParams, fullOp) {
        _loading = true
        opIndex = index
        opData = fullOp || {}
        partingData = partingParams || {}
        x_start = parseFloat(partingData.x_start  !== undefined ? partingData.x_start  : 0.0)
        x_end   = parseFloat(partingData.x_end    !== undefined ? partingData.x_end    : 0.0)
        z_pos   = parseFloat(partingData.z_pos    !== undefined ? partingData.z_pos    : 0.0)
        second_feed_x_pos   = parseFloat(partingData.second_feed_x_pos    !== undefined ? partingData.second_feed_x_pos    : 0.0)
        first_feed_rate   = parseFloat(partingData.first_feed_rate    !== undefined ? partingData.first_feed_rate    : 0.0)
        second_feed_rate   = parseFloat(partingData.second_feed_rate    !== undefined ? partingData.second_feed_rate    : 0.0)
        _loading = false
    }

    function emitSave() {
        if (_loading) return
        var payload = {
            order: (opData && opData.order !== undefined) ? opData.order : 0,
            type:  (opData && opData.type) ? opData.type : "",
            generate_gcode: (opData && opData.generate_gcode !== undefined) ? opData.generate_gcode : true,
            is_optional_block: (opData && opData.is_optional_block !== undefined) ? opData.is_optional_block : false,
            parting_parameters: {
                x_start: x_start,
                x_end:   x_end,
                z_pos:   z_pos,
                first_feed_rate:   first_feed_rate,
                second_feed_rate: second_feed_rate,
                second_feed_x_pos: second_feed_x_pos
            }
        }
        root.saveRequested(payload)
    }

    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }

    RowLayout {
        id: outerRow
        anchors.fill: parent
        spacing: 70

        /* LEFT GRID (Start) */
        GridLayout {
            id: leftGrid
            Layout.fillHeight: true
            columns: 3
            columnSpacing: 20
            rowSpacing: 20

            // Row 1
            Label {
                text: "X Start (with Fz 1)"
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                font.pixelSize: 16
            }
            NumpadField {
                Layout.preferredWidth: 100
                Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                settingName: "geometry.x_start"
                validatorObject: dblVal
                value: root.x_start
                formatter: function(v){ return (v==null) ? "" : Number(v).toFixed(3) }
                hAlign: Text.AlignRight
                fontPixelSize: 16
                onOpenRequested: root.openNumPadRequested(field)
                onValueCommitted: { root.x_start = value; root.emitSave() }
            }
            Button {
                text: "TeachIn"
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                onClicked: root.teachXRequested(root.opIndex)
            }

            Label {
                text: "X Start (with Fz 2)"
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                font.pixelSize: 16
            }
            NumpadField {
                Layout.preferredWidth: 100
                Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                settingName: "geometry.x_start"
                validatorObject: dblVal
                value: root.second_feed_x_pos
                formatter: function(v){ return (v==null) ? "" : Number(v).toFixed(3) }
                hAlign: Text.AlignRight
                fontPixelSize: 16
                onOpenRequested: root.openNumPadRequested(field)
                onValueCommitted: { root.second_feed_x_pos = value; root.emitSave() }
            }
            Button {
                text: "TeachIn"
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                onClicked: root.teachXRequested(root.opIndex)
            }

            Label {
                text: "X End"
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                font.pixelSize: 16
            }
            NumpadField {
                Layout.preferredWidth: 100
                Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                settingName: "geometry.x_end"
                validatorObject: dblVal
                value: root.x_end
                formatter: function(v){ return (v==null) ? "" : Number(v).toFixed(3) }
                hAlign: Text.AlignRight
                fontPixelSize: 16
                onOpenRequested: root.openNumPadRequested(field)
                onValueCommitted: { root.x_end = value; root.emitSave() }
            }
            Button {
                text: "TeachIn"
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                onClicked: root.teachZRequested(root.opIndex)
            }

            Label {
                text: "Z Position"
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                font.pixelSize: 16
            }
            NumpadField {
                Layout.preferredWidth: 100
                Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                settingName: "geometry.x_end"
                validatorObject: dblVal
                value: root.z_pos
                formatter: function(v){ return (v==null) ? "" : Number(v).toFixed(3) }
                hAlign: Text.AlignRight
                fontPixelSize: 16
                onOpenRequested: root.openNumPadRequested(field)
                onValueCommitted: { root.z_pos = value; root.emitSave() }
            }
            Button {
                text: "TeachIn"
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                onClicked: root.teachZRequested(root.opIndex)
            }
        }

        /* RIGHT GRID (End) */
        GridLayout {
            id: rightGrid
            Layout.fillHeight: true
            columns: 3
            columnSpacing: 20
            rowSpacing: 20

            // Row 1
            Label {
                text: "1st Feed Rate (Fz 1)"
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                font.pixelSize: 16
            }
            NumpadField {
                Layout.preferredWidth: 100
                Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                settingName: "geometry.x_end"
                validatorObject: dblVal
                value: root.first_feed_rate
                formatter: function(v){ return (v==null) ? "" : Number(v).toFixed(3) }
                hAlign: Text.AlignRight
                fontPixelSize: 16
                onOpenRequested: root.openNumPadRequested(field)
                onValueCommitted: { root.first_feed_rate = value; root.emitSave() }
            }
            Label {
                text: "(mm/rev)"
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                font.pixelSize: 16
            }

            // Row 2
            Label {
                text: "2nd Feed Rate (Fz 2)"
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                font.pixelSize: 16
            }
            NumpadField {
                Layout.preferredWidth: 100
                Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                settingName: "geometry.x_end"
                validatorObject: dblVal
                value: root.second_feed_rate
                formatter: function(v){ return (v==null) ? "" : Number(v).toFixed(3) }
                hAlign: Text.AlignRight
                fontPixelSize: 16
                onOpenRequested: root.openNumPadRequested(field)
                onValueCommitted: { root.second_feed_rate = value; root.emitSave() }
            }
            Label {
                text: "(mm/rev)"
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                font.pixelSize: 16
            }
        }
    }
}
