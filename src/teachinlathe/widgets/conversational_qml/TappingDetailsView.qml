// TappingDetailsView.qml  (nou – mapează dataclass Tapping)
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root
    anchors.fill: parent

    // API
    property int opIndex: -1
    property var opData:  null

    // dataclass Tapping
    property int   spindleRpm: (opData && opData.spindle_rpm !== undefined) ? opData.spindle_rpm : 200
    property real  pitch:      (opData && opData.pitch       !== undefined) ? opData.pitch       : 1.0
    property real  zStart:     (opData && opData.z_start     !== undefined) ? opData.z_start     : 0.0
    property real  zEnd:       (opData && opData.z_end       !== undefined) ? opData.z_end       : -10.0

    signal saveRequested(var updated)
    signal openNumPadRequested(var field)
    signal teachZRequested(int index)

    function applyData(index, data) {
        opIndex = index
        opData  = data || {}
        spindleRpm = (opData.spindle_rpm !== undefined) ? opData.spindle_rpm : spindleRpm
        pitch      = (opData.pitch       !== undefined) ? opData.pitch       : pitch
        zStart     = (opData.z_start     !== undefined) ? opData.z_start     : zStart
        zEnd       = (opData.z_end       !== undefined) ? opData.z_end       : zEnd
    }

    function payload() {
        return {
            order:            (opData && opData.order !== undefined) ? opData.order : 0,
            type:             "tapping",
            generate_gcode:   (opData && opData.generate_gcode !== undefined) ? opData.generate_gcode : true,
            is_optional_block:(opData && opData.is_optional_block !== undefined) ? opData.is_optional_block : false,
            spindle_rpm:      spindleRpm,
            pitch:            pitch,
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
            title: "Speeds and Pitch"
            Layout.fillWidth: true

            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 12

                Label { text: "Spindle RPM:"; width: 130; verticalAlignment: Text.AlignVCenter }
                NumpadField {
                    id: nfRpm
                    Layout.preferredWidth: 120
                    settingName: "smart_numpad.tapping-rpm"
                    text: String(root.spindleRpm)
                    onOpenRequested: root.openNumPadRequested(nfRpm)
                    onTextChanged: { var v=parseInt(text); if(!isNaN(v)){ root.spindleRpm=v; root.armSave() } }
                }
                Label { text: "rpm" }

                Item { Layout.preferredWidth: 24 }

                Label { text: "Pitch:"; width: 80; verticalAlignment: Text.AlignVCenter }
                NumpadField {
                    id: nfPitch
                    Layout.preferredWidth: 100
                    settingName: "smart_numpad.tapping-pitch"
                    text: String(root.pitch)
                    onOpenRequested: root.openNumPadRequested(nfPitch)
                    onTextChanged: { var v=parseFloat(text); if(!isNaN(v)){ root.pitch=v; root.armSave() } }
                }
                Label { text: "mm" }
                Item { Layout.fillWidth: true }
            }
        }

        GroupBox {
            title: "Positions"
            Layout.fillWidth: true

            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 12

                Label { text: "Z Start:"; width: 100; verticalAlignment: Text.AlignVCenter }
                NumpadField {
                    id: nfZs
                    Layout.preferredWidth: 120
                    settingName: "smart_numpad.tapping-z-start"
                    text: String(root.zStart)
                    onOpenRequested: root.openNumPadRequested(nfZs)
                    onTextChanged: { var v=parseFloat(text); if(!isNaN(v)){ root.zStart=v; root.armSave() } }
                }

                Item { Layout.preferredWidth: 24 }

                Label { text: "Z End:"; width: 100; verticalAlignment: Text.AlignVCenter }
                NumpadField {
                    id: nfZe
                    Layout.preferredWidth: 120
                    settingName: "smart_numpad.tapping-z-end"
                    text: String(root.zEnd)
                    onOpenRequested: root.openNumPadRequested(nfZe)
                    onTextChanged: { var v=parseFloat(text); if(!isNaN(v)){ root.zEnd=v; root.armSave() } }
                }

                Item { Layout.fillWidth: true }

                Button {
                    text: "TeachIn Z"
                    onClicked: root.teachZRequested(root.opIndex)
                }
            }
        }
    }
}
