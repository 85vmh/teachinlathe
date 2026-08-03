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
    readonly property bool isG33Threading: opData && opData.type === "g33Threading"
    readonly property string operationTitle: isG33Threading ? "G33 Threading" : "G76 Threading"
    readonly property string defaultThreadType: isG33Threading ? "g33" : "metric"
    readonly property string cuttingParamsSource: isG33Threading ? "G33CuttingParams.qml" : "G76CuttingParams.qml"
    readonly property real finalRadialDepth: Math.abs(root.majorDiameter - root.minorDiameter) / 2.0
    readonly property int roughingPassCount: (root.initialDoc > 0 && root.finalRadialDepth > 0)
                                             ? Math.ceil(Math.pow(root.finalRadialDepth / root.initialDoc, 2))
                                             : 0
    readonly property string roughingPassCountText: root.starts > 1
                                                   ? (root.starts + "x" + root.roughingPassCount + " passes")
                                                   : (root.roughingPassCount + " passes")
    readonly property bool showThreadLengthSummary: root.zStart !== root.zEnd
    readonly property string threadHandText: root.zStart > root.zEnd ? "RH" : "LH"

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
        m1Panel.applyData(opData && opData.m1_parameters ? opData.m1_parameters : {})
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
            thread_type:    (opData && opData.thread_type) ? opData.thread_type : root.defaultThreadType,
            pitch:          root.pitch,
            starts:         root.starts,
            major_diameter: root.majorDiameter,
            minor_diameter: root.minorDiameter,
            z_start:        root.zStart,
            z_end:          root.zEnd,
            initial_doc:    root.initialDoc,
            retract:        root.retract,
            spring_passes:  root.springPasses,
            taper_type:       root.taperType,
            compound_angle:   root.compoundAngle
        })
        if (!root.isG33Threading)
            merged.depth_degression = root.depthDegression
        root.saveRequested({ index: root.opIndex, payload: merged })
    }

    function calculateThreadDiameter() {
        if (typeof threadingDetailsViewModel === "undefined" || !threadingDetailsViewModel)
            return
        var result = threadingDetailsViewModel.calculateThreadDiameter(
            root.location,
            root.pitch,
            root.majorDiameter,
            root.minorDiameter
        )
        if (!result || !result.valid)
            return
        tf_calcDiam.commit(result.calculatedDiameter)
    }

    function formatThreadLength() {
        var length = Math.abs(root.zStart - root.zEnd)
        if (Math.abs(length - Math.round(length)) < 0.0005)
            return String(Math.round(length))
        return Number(length).toFixed(3)
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
                  ? (root.operationTitle + " - Op #" + (opData.order !== undefined ? opData.order : "N/A"))
                  : root.operationTitle
            font.pixelSize: 18
            font.bold: true
        }

        RowLayout {
            id: detailsLayout
            Layout.fillWidth: true
            spacing: 24
            Layout.alignment: Qt.AlignTop

            ColumnLayout {
                id: leftColumn
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                Layout.preferredWidth: 1
                Layout.alignment: Qt.AlignTop
                spacing: 40

                SpindleParameters {
                    id: spindlePanel
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    onOpenNumPadRequested: root.openNumPadRequested(field)
                    onSaveRequested: function (p) {
                        var merged = root.mergeIntoOp(p.payload || p)
                        root.saveRequested({ index: opIndex, payload: merged })
                    }
                }

                GroupBox {
                    id: threadParametersBox
                    title: "Thread Parameters"
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
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

                GroupBox {
                    id: zLimitsBox
                    title: "Z Limits"
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    font.pixelSize: 16

                    RowLayout {
                        anchors.fill: parent
                        spacing: 16

                        GridLayout {
                            columns: 3
                            columnSpacing: 16
                            rowSpacing: 16
                            Layout.alignment: Qt.AlignVCenter

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

                        Rectangle {
                            visible: root.showThreadLengthSummary
                            Layout.fillHeight: true
                            Layout.minimumHeight: 64
                            width: 1
                            color: "#bdbdbd"
                        }

                        GridLayout {
                            visible: root.showThreadLengthSummary
                            Layout.alignment: Qt.AlignVCenter
                            columns: 2
                            columnSpacing: 8
                            rowSpacing: 8

                            Label {
                                text: "Thread Type:"
                                font.pixelSize: 16
                                Layout.alignment: Qt.AlignVCenter
                            }
                            Label {
                                text: root.threadHandText
                                font.pixelSize: 16
                                font.bold: true
                                horizontalAlignment: Text.AlignRight
                                Layout.fillWidth: true
                                Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                            }

                            Label {
                                text: "Thread Length:"
                                font.pixelSize: 16
                                Layout.alignment: Qt.AlignVCenter
                            }
                            Label {
                                text: root.formatThreadLength() + "mm"
                                font.pixelSize: 16
                                horizontalAlignment: Text.AlignRight
                                Layout.fillWidth: true
                                Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                            }
                        }
                    }
                }

                M1Parameters {
                    id: m1Panel
                    visible: root.isG33Threading
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    Layout.alignment: Qt.AlignTop
                    onSaveRequested: function (payload) {
                        var merged = root.mergeIntoOp(payload)
                        root.saveRequested({ index: opIndex, payload: merged })
                    }
                }
            }

            ColumnLayout {
                id: rightColumn
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                Layout.preferredWidth: 1
                Layout.alignment: Qt.AlignTop
                spacing: 40

                GroupBox {
                    id: threadLocationBox
                    title: "Thread Location"
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
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

                GroupBox {
                    id: diametersBox
                    title: "Thread Diameters"
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
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
                            id: tf_calcDiam
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
                        Button {
                            text: "Calculate"
                            onClicked: root.calculateThreadDiameter()
                        }
                    }
                }

                GroupBox {
                    id: cuttingParamsBox
                    title: "Cutting Parameters"
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    font.pixelSize: 16

                    contentItem: Loader {
                        id: cuttingParamsLoader
                        Layout.preferredHeight: item ? item.implicitHeight : 0
                        source: root.cuttingParamsSource
                        onLoaded: item.detailsRoot = root
                    }
                }
            }
        }

        Item { Layout.fillHeight: true }
    }
}
