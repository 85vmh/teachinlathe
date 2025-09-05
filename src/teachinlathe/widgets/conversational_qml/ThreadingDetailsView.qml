// ThreadingDetailsView.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Item {
    id: root
    anchors.fill: parent

    property int opIndex: -1
    property var opData: null

    property string location:      (opData && opData.location) ? ("" + opData.location) : "OD"
    property int spindleRpm:       (opData && opData.spindle_rpm !== undefined) ? opData.spindle_rpm : 0
    property real pitch:           (opData && opData.pitch !== undefined) ? opData.pitch : 0.0
    property int starts:           (opData && opData.starts !== undefined) ? opData.starts : 1
    property real majorDiameter:   (opData && opData.major_diameter !== undefined) ? opData.major_diameter : 0.0
    property real minorDiameter:   (opData && opData.minor_diameter !== undefined) ? opData.minor_diameter : 0.0
    property real zStart:          (opData && opData.z_start !== undefined) ? opData.z_start : 0.0
    property real zEnd:            (opData && opData.z_end !== undefined) ? opData.z_end : 0.0
    property real initialDoc:      (opData && opData.initial_doc !== undefined) ? opData.initial_doc : 0.0
    property real retract:         (opData && opData.retract !== undefined) ? opData.retract : 0.0
    property int springPasses:     (opData && opData.spring_passes !== undefined) ? opData.spring_passes : 0

    signal saveRequested(var updated)

    function applyData(index, data) {
        opIndex = index
        opData = data || {}
        location       = (opData.location !== undefined) ? ("" + opData.location) : "OD"
        spindleRpm     = (opData.spindle_rpm !== undefined) ? opData.spindle_rpm : 0
        pitch          = (opData.pitch !== undefined) ? opData.pitch : 0.0
        starts         = (opData.starts !== undefined) ? opData.starts : 1
        majorDiameter  = (opData.major_diameter !== undefined) ? opData.major_diameter : 0.0
        minorDiameter  = (opData.minor_diameter !== undefined) ? opData.minor_diameter : 0.0
        zStart         = (opData.z_start !== undefined) ? opData.z_start : 0.0
        zEnd           = (opData.z_end !== undefined) ? opData.z_end : 0.0
        initialDoc     = (opData.initial_doc !== undefined) ? opData.initial_doc : 0.0
        retract        = (opData.retract !== undefined) ? opData.retract : 0.0
        springPasses   = (opData.spring_passes !== undefined) ? opData.spring_passes : 0
    }

    function emitSave() {
        var payload = {
            order: (opData && opData.order !== undefined) ? opData.order : 0,
            type: "threading",
            generate_gcode: (opData && opData.generate_gcode !== undefined) ? opData.generate_gcode : true,
            is_optional_block: (opData && opData.is_optional_block !== undefined) ? opData.is_optional_block : false,
            location: location,
            spindle_rpm: spindleRpm,
            pitch: pitch,
            starts: starts,
            major_diameter: majorDiameter,
            minor_diameter: minorDiameter,
            z_start: zStart,
            z_end: zEnd,
            initial_doc: initialDoc,
            retract: retract,
            spring_passes: springPasses
        }
        root.saveRequested({ index: root.opIndex, payload: payload })
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10

        GroupBox {
            title: "Thread Location"
            Layout.fillWidth: true
            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 16
                ButtonGroup { id: locGroup }
                RadioButton {
                    text: "External (OD)"
                    checked: root.location === "OD"
                    ButtonGroup.group: locGroup
                    onToggled: if (checked) { root.location = "OD"; root.emitSave() }
                }
                RadioButton {
                    text: "Internal (ID)"
                    checked: root.location === "ID"
                    ButtonGroup.group: locGroup
                    onToggled: if (checked) { root.location = "ID"; root.emitSave() }
                }
            }
        }

        GroupBox {
            title: "Thread Parameters"
            Layout.fillWidth: true
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 8

                RowLayout {
                    spacing: 8
                    Label { text: "Pitch (mm)"; width: 110; verticalAlignment: Text.AlignVCenter }
                    NumpadField {
                        Layout.preferredWidth: 120
                        settingName: "smart_numpad.quick-cycles-thread-pitch-metric"
                        value: root.pitch
                        onOpenRequested: root.openNumPadRequested(field)
                        onValueCommitted: { root.pitch = value; root.emitSave() }
                    }

                    Label { text: "Starts"; width: 80; verticalAlignment: Text.AlignVCenter }
                    ComboBox {
                        id: cbStarts
                        Layout.preferredWidth: 100
                        model: [1,2,3,4,5,6,7,8]
                        Component.onCompleted: {
                            var i = model.indexOf(root.starts)
                            currentIndex = (i >= 0) ? i : 0
                        }
                        onCurrentIndexChanged: { root.starts = model[currentIndex]; root.emitSave() }
                    }

                    Label { text: "Spindle RPM"; width: 110; verticalAlignment: Text.AlignVCenter }
                    NumpadField {
                        Layout.preferredWidth: 120
                        settingName: "smart_numpad.input-rpm-thread"
                        value: root.spindleRpm
                        onOpenRequested: root.openNumPadRequested(field)
                        onValueCommitted: { root.spindleRpm = value; root.emitSave() }
                    }
                }
            }
        }

        GroupBox {
            title: "Diameters"
            Layout.fillWidth: true
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 8

                RowLayout {
                    spacing: 8
                    Label { text: "Major Ø"; width: 110; verticalAlignment: Text.AlignVCenter }
                    NumpadField {
                        Layout.preferredWidth: 140
                        settingName: "smart_numpad.thread-major"
                        value: root.majorDiameter
                        onOpenRequested: root.openNumPadRequested(field)
                        onValueCommitted: { root.majorDiameter = value; root.emitSave() }
                    }

                    Label { text: "Minor Ø"; width: 110; verticalAlignment: Text.AlignVCenter }
                    NumpadField {
                        Layout.preferredWidth: 140
                        settingName: "smart_numpad.thread-minor"
                        value: root.minorDiameter
                        onOpenRequested: root.openNumPadRequested(field)
                        onValueCommitted: { root.minorDiameter = value; root.emitSave() }
                    }
                }
            }
        }

        GroupBox {
            title: "Z Limits"
            Layout.fillWidth: true
            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 12

                Label { text: "Z Start"; width: 110; verticalAlignment: Text.AlignVCenter }
                NumpadField {
                    Layout.preferredWidth: 140
                    settingName: "smart_numpad.thread-z-start"
                    value: root.zStart
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: { root.zStart = value; root.emitSave() }
                }

                Label { text: "Z End"; width: 110; verticalAlignment: Text.AlignVCenter }
                NumpadField {
                    Layout.preferredWidth: 140
                    settingName: "smart_numpad.thread-z-end"
                    value: root.zEnd
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: { root.zEnd = value; root.emitSave() }
                }
            }
        }

        GroupBox {
            title: "Cutting Params"
            Layout.fillWidth: true
            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 12

                Label { text: "Initial DOC (mm/⌀)"; width: 150; verticalAlignment: Text.AlignVCenter }
                NumpadField {
                    Layout.preferredWidth: 120
                    settingName: "smart_numpad.quick-cycles-thread-first-pass"
                    value: root.initialDoc
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: { root.initialDoc = value; root.emitSave() }
                }

                Label { text: "Retract (mm)"; width: 120; verticalAlignment: Text.AlignVCenter }
                NumpadField {
                    Layout.preferredWidth: 120
                    settingName: "smart_numpad.thread-retract"
                    value: root.retract
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: { root.retract = value; root.emitSave() }
                }

                Label { text: "Spring passes"; width: 120; verticalAlignment: Text.AlignVCenter }
                NumpadField {
                    Layout.preferredWidth: 120
                    settingName: "smart_numpad.thread-spring-passes"
                    value: root.springPasses
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: { root.springPasses = Math.round(value); root.emitSave() }
                }
            }
        }
    }
}
