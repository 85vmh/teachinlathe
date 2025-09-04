// ThreadingDetailsView.qml  (actualizat cu NumpadField + location & starts deja în fișierul tău curent)
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root
    anchors.fill: parent

    // API
    property int opIndex: -1
    property var opData:  null

    // dataclass Threading
    property string location:     (opData && opData.location      !== undefined) ? opData.location      : "OD"   // "OD" / "ID"
    property int    spindleRpm:   (opData && opData.spindle_rpm   !== undefined) ? opData.spindle_rpm   : 300
    property string threadType:   (opData && opData.thread_type   !== undefined) ? opData.thread_type   : "metric"
    property real   pitch:        (opData && opData.pitch         !== undefined) ? opData.pitch         : 1.0
    property int    starts:       (opData && opData.starts        !== undefined) ? opData.starts        : 1
    property real   majorDia:     (opData && opData.major_diameter!== undefined) ? opData.major_diameter: 10.0
    property real   minorDia:     (opData && opData.minor_diameter!== undefined) ? opData.minor_diameter: 9.0
    property real   zStart:       (opData && opData.z_start       !== undefined) ? opData.z_start       : 0.0
    property real   zEnd:         (opData && opData.z_end         !== undefined) ? opData.z_end         : -10.0
    property real   initialDoc:   (opData && opData.initial_doc   !== undefined) ? opData.initial_doc   : 0.1
    property real   retract:      (opData && opData.retract       !== undefined) ? opData.retract       : 0.05
    property int    springPasses: (opData && opData.spring_passes !== undefined) ? opData.spring_passes : 0

    signal saveRequested(var updated)
    signal openNumPadRequested(var field)
    signal teachXRequested(int index)
    signal teachZRequested(int index)

    function applyData(index, data) {
        opIndex = index
        opData  = data || {}
        // re-prop
        location     = (opData.location       !== undefined) ? opData.location       : location
        spindleRpm   = (opData.spindle_rpm    !== undefined) ? opData.spindle_rpm    : spindleRpm
        threadType   = (opData.thread_type    !== undefined) ? opData.thread_type    : threadType
        pitch        = (opData.pitch          !== undefined) ? opData.pitch          : pitch
        starts       = (opData.starts         !== undefined) ? opData.starts         : starts
        majorDia     = (opData.major_diameter !== undefined) ? opData.major_diameter : majorDia
        minorDia     = (opData.minor_diameter !== undefined) ? opData.minor_diameter : minorDia
        zStart       = (opData.z_start        !== undefined) ? opData.z_start        : zStart
        zEnd         = (opData.z_end          !== undefined) ? opData.z_end          : zEnd
        initialDoc   = (opData.initial_doc    !== undefined) ? opData.initial_doc    : initialDoc
        retract      = (opData.retract        !== undefined) ? opData.retract        : retract
        springPasses = (opData.spring_passes  !== undefined) ? opData.spring_passes  : springPasses
    }

    function payload() {
        return {
            order:            (opData && opData.order !== undefined) ? opData.order : 0,
            type:             "threading",
            generate_gcode:   (opData && opData.generate_gcode !== undefined) ? opData.generate_gcode : true,
            is_optional_block:(opData && opData.is_optional_block !== undefined) ? opData.is_optional_block : false,
            location:         location,           // string "OD"/"ID"
            spindle_rpm:      spindleRpm,
            thread_type:      threadType,
            pitch:            pitch,
            starts:           starts,
            major_diameter:   majorDia,
            minor_diameter:   minorDia,
            z_start:          zStart,
            z_end:            zEnd,
            initial_doc:      initialDoc,
            retract:          retract,
            spring_passes:    springPasses
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
            title: "Thread Location"
            Layout.fillWidth: true
            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 8

                ButtonGroup { id: locGroup }
                RadioButton {
                    text: "External (OD)"
                    checked: root.location === "OD"
                    ButtonGroup.group: locGroup
                    onToggled: if (checked) { root.location = "OD"; root.armSave() }
                }
                RadioButton {
                    text: "Internal (ID)"
                    checked: root.location === "ID"
                    ButtonGroup.group: locGroup
                    onToggled: if (checked) { root.location = "ID"; root.armSave() }
                }
                Item { Layout.fillWidth: true }
            }
        }

        GroupBox {
            title: "Basic Parameters"
            Layout.fillWidth: true

            GridLayout {
                columns: 6
                rowSpacing: 8
                columnSpacing: 10
                anchors.margins: 10
                anchors.fill: parent

                // Spindle RPM
                Label { text: "Spindle RPM:"; Layout.columnSpan: 2; verticalAlignment: Text.AlignVCenter }
                NumpadField {
                    id: nfTrRpm
                    Layout.preferredWidth: 120
                    settingName: "smart_numpad.input-rpm-2"
                    text: String(root.spindleRpm)
                    onOpenRequested: root.openNumPadRequested(nfTrRpm)
                    onTextChanged: { var v=parseInt(text); if(!isNaN(v)){ root.spindleRpm=v; root.armSave() } }
                }
                Item { Layout.columnSpan: 3; Layout.fillWidth: true }

                // Pitch
                Label { text: "Pitch:"; Layout.columnSpan: 2; verticalAlignment: Text.AlignVCenter }
                NumpadField {
                    id: nfPitch
                    Layout.preferredWidth: 100
                    settingName: "smart_numpad.quick-cycles-thread-pitch-metric"
                    text: String(root.pitch)
                    onOpenRequested: root.openNumPadRequested(nfPitch)
                    onTextChanged: { var v=parseFloat(text); if(!isNaN(v)){ root.pitch=v; root.armSave() } }
                }
                Label { text: "mm"; }
                Item { Layout.columnSpan: 2; Layout.fillWidth: true }

                // Starts
                Label { text: "Starts:"; Layout.columnSpan: 2; verticalAlignment: Text.AlignVCenter }
                ComboBox {
                    id: cbStarts
                    Layout.preferredWidth: 90
                    model: [1,2,3,4,5,6,7,8]
                    Component.onCompleted: {
                        var i = model.indexOf(root.starts); currentIndex = i >= 0 ? i : 0
                    }
                    onCurrentIndexChanged: { root.starts = model[currentIndex]; root.armSave() }
                }
                Item { Layout.columnSpan: 3; Layout.fillWidth: true }

                // Major / Minor
                Label { text: (root.location === "OD" ? "Major Dia.:" : "Minor Dia.:"); Layout.columnSpan: 2; verticalAlignment: Text.AlignVCenter }
                NumpadField {
                    id: nfXStart
                    Layout.preferredWidth: 110
                    settingName: "smart_numpad.thread-major"
                    text: String(root.majorDia)
                    onOpenRequested: root.openNumPadRequested(nfXStart)
                    onTextChanged: { var v=parseFloat(text); if(!isNaN(v)){ root.majorDia=v; root.armSave() } }
                }
                Item { }

                Label { text: (root.location === "OD" ? "Minor Dia.:" : "Major Dia.:"); Layout.columnSpan: 2; verticalAlignment: Text.AlignVCenter }
                NumpadField {
                    id: nfXEnd
                    Layout.preferredWidth: 110
                    settingName: "smart_numpad.thread-minor"
                    text: String(root.minorDia)
                    onOpenRequested: root.openNumPadRequested(nfXEnd)
                    onTextChanged: { var v=parseFloat(text); if(!isNaN(v)){ root.minorDia=v; root.armSave() } }
                }
                Item { }

                // Z Start / End
                Label { text: "Z Start:"; Layout.columnSpan: 2; verticalAlignment: Text.AlignVCenter }
                NumpadField {
                    id: nfZs
                    Layout.preferredWidth: 110
                    settingName: "smart_numpad.thread-z-start"
                    text: String(root.zStart)
                    onOpenRequested: root.openNumPadRequested(nfZs)
                    onTextChanged: { var v=parseFloat(text); if(!isNaN(v)){ root.zStart=v; root.armSave() } }
                }
                Item { }

                Label { text: "Z End:"; Layout.columnSpan: 2; verticalAlignment: Text.AlignVCenter }
                NumpadField {
                    id: nfZe
                    Layout.preferredWidth: 110
                    settingName: "smart_numpad.thread-z-end"
                    text: String(root.zEnd)
                    onOpenRequested: root.openNumPadRequested(nfZe)
                    onTextChanged: { var v=parseFloat(text); if(!isNaN(v)){ root.zEnd=v; root.armSave() } }
                }
                Item { }

                // Initial DOC
                Label { text: "First pass (DOC):"; Layout.columnSpan: 2; verticalAlignment: Text.AlignVCenter }
                NumpadField {
                    id: nfInit
                    Layout.preferredWidth: 110
                    settingName: "smart_numpad.quick-cycles-thread-first-pass"
                    text: String(root.initialDoc)
                    onOpenRequested: root.openNumPadRequested(nfInit)
                    onTextChanged: { var v=parseFloat(text); if(!isNaN(v)){ root.initialDoc=v; root.armSave() } }
                }
                Label { text: "mm/⌀" }

                // Retract
                Label { text: "Retract:"; Layout.columnSpan: 2; verticalAlignment: Text.AlignVCenter }
                NumpadField {
                    id: nfRetract
                    Layout.preferredWidth: 110
                    settingName: "smart_numpad.thread-retract"
                    text: String(root.retract)
                    onOpenRequested: root.openNumPadRequested(nfRetract)
                    onTextChanged: { var v=parseFloat(text); if(!isNaN(v)){ root.retract=v; root.armSave() } }
                }
                Label { text: "mm" }

                // Spring passes
                Label { text: "Spring passes:"; Layout.columnSpan: 2; verticalAlignment: Text.AlignVCenter }
                ComboBox {
                    id: cbSpr
                    Layout.preferredWidth: 90
                    model: [0,1,2,3,4,5]
                    Component.onCompleted: {
                        var i = model.indexOf(root.springPasses); currentIndex = i >= 0 ? i : 0
                    }
                    onCurrentIndexChanged: { root.springPasses = model[currentIndex]; root.armSave() }
                }
                Item { Layout.fillWidth: true }
            }
        }
    }
}
