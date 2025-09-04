// PartingDetailsView.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root
    anchors.fill: parent

    // === Public API (same pattern as Facing) ===
    property int opIndex: -1
    property var opData: null

    // Save bridge (ChildScreen listens and writes to disk)
    signal saveRequested(var updated)
    // Numpad bridge (ChildScreen proxies to Python)
    signal openNumPadRequested(var field)
    // Optional teach signals (ChildScreen connects if available)
    signal teachXRequested(int index)
    signal teachZRequested(int index)

    // === Editable values (mapped to Parting dataclass) ===
    property int   cssValue:   (opData && opData.css_value   !== undefined) ? opData.css_value   : 0
    property int   maxSpeed:   (opData && opData.max_speed   !== undefined) ? opData.max_speed   : 0
    property real  feedRate:   (opData && opData.feed_rate   !== undefined) ? opData.feed_rate   : 0.0

    property real  xStart:     (opData && opData.x_start     !== undefined) ? opData.x_start     : 0.0
    property real  xEnd:       (opData && opData.x_end       !== undefined) ? opData.x_end       : 0.0
    property real  zPos:       (opData && opData.z_pos       !== undefined) ? opData.z_pos       : 0.0
    property real  peckDepth:  (opData && opData.peck_depth  !== undefined) ? opData.peck_depth  : 0.0

    // Parent calls this when a row is selected
    function applyData(index, data) {
        opIndex = index
        opData = data || {}

        cssValue  = (opData.css_value   !== undefined) ? opData.css_value   : 0
        maxSpeed  = (opData.max_speed   !== undefined) ? opData.max_speed   : 0
        feedRate  = (opData.feed_rate   !== undefined) ? opData.feed_rate   : 0.0

        xStart    = (opData.x_start     !== undefined) ? opData.x_start     : 0.0
        xEnd      = (opData.x_end       !== undefined) ? opData.x_end       : 0.0
        zPos      = (opData.z_pos       !== undefined) ? opData.z_pos       : 0.0
        peckDepth = (opData.peck_depth  !== undefined) ? opData.peck_depth  : 0.0
    }

    // Centralized autosave payload (same as other detail views)
    function emitSave() {
        var payload = {
            order:            (opData && opData.order !== undefined) ? opData.order : 0,
            type:             "parting",
            generate_gcode:   (opData && opData.generate_gcode !== undefined) ? opData.generate_gcode : true,
            is_optional_block:(opData && opData.is_optional_block !== undefined) ? opData.is_optional_block : false,

            css_value:   cssValue,
            max_speed:   maxSpeed,
            feed_rate:   feedRate,

            peck_depth:  peckDepth,
            x_start:     xStart,
            x_end:       xEnd,
            z_pos:       zPos
        }
        root.saveRequested({ index: opIndex, payload: payload })
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10

        // === Speeds and Feeds ===
        GroupBox {
            title: "Speeds and Feeds"
            Layout.fillWidth: true

            GridLayout {
                anchors.fill: parent
                anchors.margins: 10
                columns: 4
                columnSpacing: 12
                rowSpacing: 10

                Label { text: "CSS Value"; Layout.alignment: Qt.AlignVCenter }
                NumpadField {
                    id: fldCss
                    Layout.preferredWidth: 120
                    text: String(root.cssValue)
                    settingName: "parting.css"
                    // ask parent to open numpad
                    onOpenRequested: root.openNumPadRequested(field)
                    // commit from numpad -> update value -> autosave
                    onValueCommitted: function(val) { root.cssValue = Number(val) || 0; root.emitSave() }
                }
                Label { text: "m/min"; Layout.alignment: Qt.AlignVCenter }
                Item { } // spacer

                Label { text: "Max Speed"; Layout.alignment: Qt.AlignVCenter }
                NumpadField {
                    id: fldMax
                    Layout.preferredWidth: 120
                    text: String(root.maxSpeed)
                    settingName: "parting.max_rpm"
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: function(val) { root.maxSpeed = parseInt(val) || 0; root.emitSave() }
                }
                Label { text: "rpm"; Layout.alignment: Qt.AlignVCenter }
                Item { }

                Label { text: "Feed rate"; Layout.alignment: Qt.AlignVCenter }
                NumpadField {
                    id: fldFeed
                    Layout.preferredWidth: 120
                    text: String(root.feedRate)
                    settingName: "parting.feed_rate"
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: function(val) { root.feedRate = Number(val) || 0; root.emitSave() }
                }
                Label { text: "mm/rev"; Layout.alignment: Qt.AlignVCenter }
                Item { }
            }
        }

        // === Parting Parameters ===
        GroupBox {
            title: "Parting Parameters"
            Layout.fillWidth: true

            GridLayout {
                anchors.fill: parent
                anchors.margins: 10
                columns: 4
                columnSpacing: 12
                rowSpacing: 10

                // X Start + TeachIn
                Label { text: "X Start:"; Layout.alignment: Qt.AlignVCenter }
                RowLayout {
                    Layout.preferredWidth: 220
                    NumpadField {
                        id: fldXStart
                        Layout.preferredWidth: 120
                        text: String(root.xStart)
                        settingName: "parting.x_start"
                        onOpenRequested: root.openNumPadRequested(field)
                        onValueCommitted: function(val) { root.xStart = Number(val) || 0; root.emitSave() }
                    }
                    Button {
                        text: "TeachIn X"
                        onClicked: root.teachXRequested(root.opIndex)
                    }
                }
                Item { } Item { }

                // Z Position + TeachIn
                Label { text: "Z Position:"; Layout.alignment: Qt.AlignVCenter }
                RowLayout {
                    Layout.preferredWidth: 220
                    NumpadField {
                        id: fldZ
                        Layout.preferredWidth: 120
                        text: String(root.zPos)
                        settingName: "parting.z_pos"
                        onOpenRequested: root.openNumPadRequested(field)
                        onValueCommitted: function(val) { root.zPos = Number(val) || 0; root.emitSave() }
                    }
                    Button {
                        text: "TeachIn Z"
                        onClicked: root.teachZRequested(root.opIndex)
                    }
                }
                Item { } Item { }

                // X End + TeachIn
                Label { text: "X End:"; Layout.alignment: Qt.AlignVCenter }
                RowLayout {
                    Layout.preferredWidth: 220
                    NumpadField {
                        id: fldXEnd
                        Layout.preferredWidth: 120
                        text: String(root.xEnd)
                        settingName: "parting.x_end"
                        onOpenRequested: root.openNumPadRequested(field)
                        onValueCommitted: function(val) { root.xEnd = Number(val) || 0; root.emitSave() }
                    }
                    Button {
                        text: "TeachIn X"
                        onClicked: root.teachXRequested(root.opIndex)
                    }
                }
                Item { } Item { }

                // Peck depth
                Label { text: "Peck depth:"; Layout.alignment: Qt.AlignVCenter }
                NumpadField {
                    id: fldPeck
                    Layout.preferredWidth: 120
                    text: String(root.peckDepth)
                    settingName: "parting.peck_depth"
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: function(val) { root.peckDepth = Number(val) || 0; root.emitSave() }
                }
                Label { text: "mm"; Layout.alignment: Qt.AlignVCenter }
                Item { }
            }
        }
    }
}
