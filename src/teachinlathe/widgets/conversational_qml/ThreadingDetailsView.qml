// ThreadingDetailsView.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."
import "../touchable_input"

Item {
    id: root
    anchors.fill: parent

    property int opIndex: -1
    property var opData: null

    signal saveRequested(var updated)
    signal openNumPadRequested(var field)
    signal teachXRequested(int index)
    signal teachZRequested(int index)

    // local state
    property string location:     "OD"
    property real   pitch:        0.0
    property int    starts:       1
    property real   majorDiameter: 0.0
    property real   minorDiameter: 0.0
    property real   zStart:       0.0
    property real   zEnd:         0.0
    property real   initialDoc:   0.0
    property real   retract:      0.0
    property int    springPasses: 0
    property real   depthDegression: 1.0
    property int    taperType: 0
    property real   compoundAngle: 0.0
    property bool   _loading:     false
    property var    depthOptions: (function() {
        var a = [];
        for (var v = 1.0; v <= 2.0001; v += 0.1) a.push(v.toFixed(1));
        return a;
    })()

    function applyData(index, data) {
        _loading = true
        opIndex = index
        opData  = data || {}

        spindlePanel.rpmOnly = true
        spindlePanel.applyData(opIndex, opData)

        location      = (opData.location       !== undefined) ? String(opData.location)                : "OD"
        pitch         = (opData.pitch          !== undefined) ? Number(opData.pitch)                   : 0.0
        starts        = (opData.starts         !== undefined) ? Math.round(Number(opData.starts))      : 1
        majorDiameter = (opData.major_diameter !== undefined) ? Number(opData.major_diameter)          : 0.0
        minorDiameter = (opData.minor_diameter !== undefined) ? Number(opData.minor_diameter)          : 0.0
        zStart        = (opData.z_start        !== undefined) ? Number(opData.z_start)                 : 0.0
        zEnd          = (opData.z_end          !== undefined) ? Number(opData.z_end)                   : 0.0
        initialDoc    = (opData.initial_doc    !== undefined) ? Number(opData.initial_doc)             : 0.0
        retract       = (opData.retract        !== undefined) ? Number(opData.retract)                 : 0.0
        springPasses  = (opData.spring_passes  !== undefined) ? Math.round(Number(opData.spring_passes)) : 0
        depthDegression = (opData.depth_degression !== undefined) ? Number(opData.depth_degression)    : 1.0
        taperType       = (opData.taper_type      !== undefined) ? Math.round(Number(opData.taper_type)) : 0
        compoundAngle   = (opData.compound_angle  !== undefined) ? Number(opData.compound_angle)         : 0.0
        _loading = false
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

    function emitSave() {
        if (_loading) return
        var merged = root.mergeIntoOp({
            location:       root.location,
            thread_type:    (opData && opData.thread_type) ? opData.thread_type : "metric",
            pitch:          root.pitch,
            starts:         root.starts,
            major_diameter: root.majorDiameter,
            minor_diameter: root.minorDiameter,
            z_start:        root.zStart,
            z_end:          root.zEnd,
            initial_doc:    root.initialDoc,
            retract:        root.retract,
            spring_passes:  root.springPasses,
            depth_degression: root.depthDegression,
            taper_type:       root.taperType,
            compound_angle:   root.compoundAngle
        })
        root.saveRequested({ index: root.opIndex, payload: merged })
    }

    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }
    IntValidator    { id: intVal; bottom: 1; top: 99 }
    IntValidator    { id: intValNonNeg; bottom: 0; top: 99 }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 24

        Label {
            text: (opData && opData.type)
                  ? ("Threading — Op #" + (opData.order !== undefined ? opData.order : "N/A"))
                  : "Threading"
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
                        root.saveRequested({ index: opIndex, payload: merged })
                    }
                }
            }

            // Row 1, column 2
            Item {
                Layout.row: 0
                Layout.column: 1
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                Layout.preferredWidth: 1
                Layout.preferredHeight: threadLocationBox.implicitHeight
                Layout.alignment: Qt.AlignTop

                GroupBox {
                    id: threadLocationBox
                    title: "Thread Location"
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    font.pixelSize: 16

                    ColumnLayout {
                        spacing: 8
                        ButtonGroup { id: locGroup }
                        RadioButton {
                            text: "External (OD)"
                            font.pixelSize: 15
                            checked: root.location === "OD"
                            ButtonGroup.group: locGroup
                            onToggled: if (checked) { root.location = "OD"; root.emitSave() }
                        }
                        RadioButton {
                            text: "Internal (ID)"
                            font.pixelSize: 15
                            checked: root.location === "ID"
                            ButtonGroup.group: locGroup
                            onToggled: if (checked) { root.location = "ID"; root.emitSave() }
                        }
                    }
                }
            }

            // Row 2, column 1
            Item {
                Layout.row: 1
                Layout.column: 0
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                Layout.preferredWidth: 1
                Layout.preferredHeight: threadParametersBox.implicitHeight
                Layout.alignment: Qt.AlignTop

                GroupBox {
                    id: threadParametersBox
                    title: "Thread Parameters"
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    font.pixelSize: 16

                    GridLayout {
                        columns: 3
                        columnSpacing: 16
                        rowSpacing: 16

                        Label { text: "Pitch"; font.pixelSize: 16; Layout.alignment: Qt.AlignVCenter; Layout.minimumWidth: 80 }
                        NumpadField {
                            Layout.preferredWidth: 100
                            settingName: "threading.metric_pitch"
                            validatorObject: dblVal
                            value: root.pitch
                            formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                            hAlign: Text.AlignRight
                            onOpenRequested: root.openNumPadRequested(field)
                            onValueCommitted: { root.pitch = value; root.emitSave() }
                        }
                        Label { text: "(mm)"; font.pixelSize: 15; Layout.alignment: Qt.AlignVCenter }

                        Label { text: "Starts"; font.pixelSize: 16; Layout.alignment: Qt.AlignVCenter; Layout.minimumWidth: 80 }
                        NumpadField {
                            Layout.preferredWidth: 100
                            settingName: "threading.starts_count"
                            validatorObject: intVal
                            value: root.starts
                            formatter: function(v) { return (v == null) ? "1" : String(Math.max(1, Math.round(Number(v)))) }
                            hAlign: Text.AlignRight
                            onOpenRequested: root.openNumPadRequested(field)
                            onValueCommitted: { root.starts = Math.max(1, Math.round(value)); root.emitSave() }
                        }
                        Item {}
                    }
                }
            }

            // Row 2, column 2
            Item {
                Layout.row: 1
                Layout.column: 1
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                Layout.preferredWidth: 1
                Layout.preferredHeight: diametersBox.implicitHeight
                Layout.alignment: Qt.AlignTop

                GroupBox {
                    id: diametersBox
                    title: "Thread Diameters"
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    font.pixelSize: 16

                    GridLayout {
                        columns: 3
                        columnSpacing: 16
                        rowSpacing: 16

                        // Row 1: TeachIn diameter (Major for OD, Minor for ID)
                        Label {
                            text: root.location === "OD" ? "Major Ø" : "Minor Ø"
                            font.pixelSize: 16
                            Layout.alignment: Qt.AlignVCenter
                            Layout.minimumWidth: 90
                        }
                        NumpadField {
                            id: tf_teachDiam
                            Layout.preferredWidth: 110
                            settingName: "threading.teach_diam"
                            validatorObject: dblVal
                            value: root.location === "OD" ? root.majorDiameter : root.minorDiameter
                            formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                            hAlign: Text.AlignRight
                            onOpenRequested: root.openNumPadRequested(field)
                            onValueCommitted: {
                                if (root.location === "OD") root.majorDiameter = value
                                else root.minorDiameter = value
                                root.emitSave()
                            }
                        }
                        Button { text: "TeachIn"; onClicked: tf_teachDiam.commit(positionsBridge.teachInX() * 2) }

                        // Row 2: Calculate diameter (Minor for OD, Major for ID)
                        Label {
                            text: root.location === "OD" ? "Minor Ø" : "Major Ø"
                            font.pixelSize: 16
                            Layout.alignment: Qt.AlignVCenter
                            Layout.minimumWidth: 90
                        }
                        NumpadField {
                            Layout.preferredWidth: 110
                            settingName: "threading.calc_diam"
                            validatorObject: dblVal
                            value: root.location === "OD" ? root.minorDiameter : root.majorDiameter
                            formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                            hAlign: Text.AlignRight
                            onOpenRequested: root.openNumPadRequested(field)
                            onValueCommitted: {
                                if (root.location === "OD") root.minorDiameter = value
                                else root.majorDiameter = value
                                root.emitSave()
                            }
                        }
                        Button { text: "Calculate" }
                    }
                }
            }

            // Row 3, column 1
            Item {
                Layout.row: 2
                Layout.column: 0
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                Layout.preferredWidth: 1
                Layout.preferredHeight: zLimitsBox.implicitHeight
                Layout.alignment: Qt.AlignTop

                GroupBox {
                    id: zLimitsBox
                    title: "Z Limits"
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    font.pixelSize: 16

                    GridLayout {
                        columns: 3
                        columnSpacing: 16
                        rowSpacing: 16

                        Label { text: "Z Start"; font.pixelSize: 16; Layout.alignment: Qt.AlignVCenter; Layout.minimumWidth: 80 }
                        NumpadField {
                            id: tf_zStart
                            Layout.preferredWidth: 110
                            settingName: "threading.z_start"
                            validatorObject: dblVal
                            value: root.zStart
                            formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                            hAlign: Text.AlignRight
                            onOpenRequested: root.openNumPadRequested(field)
                            onValueCommitted: { root.zStart = value; root.emitSave() }
                        }
                        Button { text: "TeachIn"; onClicked: tf_zStart.commit(positionsBridge.teachInZ()) }

                        Label { text: "Z End"; font.pixelSize: 16; Layout.alignment: Qt.AlignVCenter; Layout.minimumWidth: 80 }
                        NumpadField {
                            id: tf_zEnd
                            Layout.preferredWidth: 110
                            settingName: "threading.z_end"
                            validatorObject: dblVal
                            value: root.zEnd
                            formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                            hAlign: Text.AlignRight
                            onOpenRequested: root.openNumPadRequested(field)
                            onValueCommitted: { root.zEnd = value; root.emitSave() }
                        }
                        Button { text: "TeachIn"; onClicked: tf_zEnd.commit(positionsBridge.teachInZ()) }
                    }
                }
            }

            // Row 3, column 2
            Item {
                Layout.row: 2
                Layout.column: 1
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                Layout.preferredWidth: 1
                Layout.preferredHeight: cuttingParamsBox.implicitHeight
                Layout.alignment: Qt.AlignTop

                GroupBox {
                    id: cuttingParamsBox
                    title: "Cutting Params"
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    font.pixelSize: 16

                    ColumnLayout {
                        spacing: 12

                        RowLayout {
                            spacing: 16
                            Label { text: "Initial DOC"; font.pixelSize: 16; Layout.alignment: Qt.AlignVCenter; Layout.minimumWidth: 120 }
                            NumpadField {
                                Layout.preferredWidth: 110
                                settingName: "threading.first_pass_depth"
                                validatorObject: dblVal
                                value: root.initialDoc
                                formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                                hAlign: Text.AlignRight
                                onOpenRequested: root.openNumPadRequested(field)
                                onValueCommitted: { root.initialDoc = value; root.emitSave() }
                            }
                            Label { text: "(mm/diam)"; font.pixelSize: 15; Layout.alignment: Qt.AlignVCenter }
                        }

                        RowLayout {
                            spacing: 16
                            Label { text: "Retract"; font.pixelSize: 16; Layout.alignment: Qt.AlignVCenter; Layout.minimumWidth: 120 }
                            NumpadField {
                                Layout.preferredWidth: 110
                                settingName: "threading.x_retract"
                                validatorObject: dblVal
                                value: root.retract
                                formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                                hAlign: Text.AlignRight
                                onOpenRequested: root.openNumPadRequested(field)
                                onValueCommitted: { root.retract = value; root.emitSave() }
                            }
                            Label { text: "(mm)"; font.pixelSize: 15; Layout.alignment: Qt.AlignVCenter }
                        }

                        RowLayout {
                            spacing: 16
                            Label { text: "Compound Angle"; font.pixelSize: 16; Layout.alignment: Qt.AlignVCenter; Layout.minimumWidth: 120 }
                            NumpadField {
                                Layout.preferredWidth: 110
                                settingName: "threading.compound_angle"
                                validatorObject: dblVal
                                value: root.compoundAngle
                                formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                                hAlign: Text.AlignRight
                                onOpenRequested: root.openNumPadRequested(field)
                                onValueCommitted: { root.compoundAngle = value; root.emitSave() }
                            }
                            Label { text: "(deg)"; font.pixelSize: 15; Layout.alignment: Qt.AlignVCenter }
                        }

                        RowLayout {
                            spacing: 16
                            Label { text: "Depth Degression"; font.pixelSize: 16; Layout.alignment: Qt.AlignVCenter; Layout.minimumWidth: 120 }
                            ComboBox {
                                Layout.preferredWidth: 110
                                model: root.depthOptions
                                currentIndex: Math.max(0, root.depthOptions.indexOf(Number(root.depthDegression).toFixed(1)))
                                font.pixelSize: 16
                                onActivated: {
                                    root.depthDegression = Number(root.depthOptions[index]);
                                    root.emitSave();
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            spacing: 16
                            Label { text: "Thread Taper"; font.pixelSize: 16; Layout.alignment: Qt.AlignVCenter; Layout.minimumWidth: 120 }
                            ComboBox {
                                Layout.preferredWidth: 140
                                model: ["None", "On entry", "On exit", "Both"]
                                currentIndex: Math.max(0, Math.min(3, root.taperType))
                                font.pixelSize: 16
                                onActivated: { root.taperType = index; root.emitSave(); }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            spacing: 16
                            Label { text: "Spring Passes"; font.pixelSize: 16; Layout.alignment: Qt.AlignVCenter; Layout.minimumWidth: 120 }
                            NumpadField {
                                Layout.preferredWidth: 110
                                settingName: "threading.spring_passes"
                                validatorObject: intValNonNeg
                                value: root.springPasses
                                formatter: function(v) { return (v == null) ? "" : String(Math.round(Number(v))) }
                                hAlign: Text.AlignRight
                                onOpenRequested: root.openNumPadRequested(field)
                                onValueCommitted: { root.springPasses = Math.round(value); root.emitSave() }
                            }
                            Item { Layout.fillWidth: true }
                        }
                    }
                }
            }
        }

        Item { Layout.fillHeight: true }
    }
}
