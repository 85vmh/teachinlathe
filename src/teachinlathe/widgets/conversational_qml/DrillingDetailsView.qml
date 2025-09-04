// DrillingDetailsView.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root
    anchors.fill: parent

    // API & data
    property int  opIndex: -1
    property var  opData:  null

    // dataclass Drilling
    property int   spindleRpm:   (opData && opData.spindle_rpm    !== undefined) ? opData.spindle_rpm  : 300
    property real  feedRate:     (opData && opData.feed_rate      !== undefined) ? opData.feed_rate    : 0.1
    property real  zStart:       (opData && opData.z_start        !== undefined) ? opData.z_start      : 0.0
    property real  zEnd:         (opData && opData.z_end          !== undefined) ? opData.z_end        : 0.0

    signal saveRequested(var updated)
    signal openNumPadRequested(var field)
    // (drilling nu are teach semnale în cerința actuală, deci le omitem)

    // Parent calls this to load data
    function applyData(index, data) {
        opIndex = index
        opData  = data || {}
        spindleRpm = (opData.spindle_rpm !== undefined) ? opData.spindle_rpm : spindleRpm
        feedRate   = (opData.feed_rate   !== undefined) ? opData.feed_rate   : feedRate
        zStart     = (opData.z_start     !== undefined) ? opData.z_start     : zStart
        zEnd       = (opData.z_end       !== undefined) ? opData.z_end       : zEnd
    }

    function payload() {
        return {
            order:            (opData && opData.order !== undefined) ? opData.order : 0,
            type:             "drilling",
            generate_gcode:   (opData && opData.generate_gcode !== undefined) ? opData.generate_gcode : true,
            is_optional_block:(opData && opData.is_optional_block !== undefined) ? opData.is_optional_block : false,
            spindle_rpm:      spindleRpm,
            feed_rate:        feedRate,
            z_start:          zStart,
            z_end:            zEnd
        }
    }
    function armSave() { saveDebounce.restart() }

    Timer {
        id: saveDebounce
        interval: 60; running: false; repeat: false
        onTriggered: root.saveRequested({ index: root.opIndex, payload: root.payload() })
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10

        GroupBox {
            title: "Speeds and Feeds"
            Layout.fillWidth: true

            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 12

                Label { text: "Spindle Speed:"; width: 140; verticalAlignment: Text.AlignVCenter }
                NumpadField {
                    id: nfRpm
                    Layout.preferredWidth: 120
                    settingName: "smart_numpad.input-rpm-2"
                    text: String(root.spindleRpm)
                    onOpenRequested: root.openNumPadRequested(nfRpm)
                    onTextChanged: {
                        var v = parseInt(text); if (!isNaN(v)) { root.spindleRpm = v; root.armSave() }
                    }
                }
                Label { text: "rpm"; width: 50; verticalAlignment: Text.AlignVCenter }

                Item { Layout.preferredWidth: 24 }

                Label { text: "Feed rate:"; width: 110; verticalAlignment: Text.AlignVCenter }
                NumpadField {
                    id: nfFeed
                    Layout.preferredWidth: 100
                    settingName: "smart_numpad.quick-cycles-drill-feed"
                    text: String(root.feedRate)
                    onOpenRequested: root.openNumPadRequested(nfFeed)
                    onTextChanged: {
                        var v = parseFloat(text); if (!isNaN(v)) { root.feedRate = v; root.armSave() }
                    }
                }
                Label { text: "mm/rev"; width: 70; verticalAlignment: Text.AlignVCenter }
                Item { Layout.fillWidth: true }
            }
        }

        GroupBox {
            title: "Drilling Parameters"
            Layout.fillWidth: true

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 8

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Label { text: "Z Start:"; width: 120; verticalAlignment: Text.AlignVCenter }
                    NumpadField {
                        id: nfZStart
                        Layout.preferredWidth: 120
                        settingName: "smart_numpad.z-start"
                        text: String(root.zStart)
                        onOpenRequested: root.openNumPadRequested(nfZStart)
                        onTextChanged: {
                            var v = parseFloat(text); if (!isNaN(v)) { root.zStart = v; root.armSave() }
                        }
                    }

                    Item { Layout.preferredWidth: 20 }

                    Label { text: "Z End:"; width: 120; verticalAlignment: Text.AlignVCenter }
                    NumpadField {
                        id: nfZEnd
                        Layout.preferredWidth: 120
                        settingName: "smart_numpad.z-end"
                        text: String(root.zEnd)
                        onOpenRequested: root.openNumPadRequested(nfZEnd)
                        onTextChanged: {
                            var v = parseFloat(text); if (!isNaN(v)) { root.zEnd = v; root.armSave() }
                        }
                    }

                    Item { Layout.fillWidth: true }
                }
            }
        }
    }
}
