// ThreadingDetailsView.qml — G76 Threading: its spindle, thread, Z limits,
// location, diameters and passes in cards. It keeps nothing of its own: all
// it shows is its editor's operation, and every change is the editor's edit,
// which the operation then shows.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import common.touchable_input
import theme
import common
import TeachInLathe

Item {
    id: root
    anchors.fill: parent

    // The view model of the operation this edits (OperationEditorViewModel.py):
    // the one place what the view shows comes from, and every edit goes to
    required property var editor
    readonly property var op: editor.operation

    readonly property string location: op.location !== undefined ? String(op.location) : "OD"
    readonly property real   pitch: Number(op.pitch || 0)
    readonly property int    starts: op.starts !== undefined ? Math.round(Number(op.starts)) : 1
    readonly property real   majorDiameter: Number(op.major_diameter || 0)
    readonly property real   minorDiameter: Number(op.minor_diameter || 0)
    readonly property real   zStart: Number(op.z_start || 0)
    readonly property real   zEnd: Number(op.z_end || 0)
    readonly property real   initialDoc: Number(op.initial_doc || 0)

    readonly property real finalRadialDepth: Math.abs(root.majorDiameter - root.minorDiameter) / 2.0
    readonly property int roughingPassCount: (root.initialDoc > 0 && root.finalRadialDepth > 0)
                                             ? Math.ceil(Math.pow(root.finalRadialDepth / root.initialDoc, 2))
                                             : 0
    readonly property string roughingPassCountText: root.starts > 1
                                                   ? (root.starts + "x" + root.roughingPassCount + " passes")
                                                   : (root.roughingPassCount + " passes")
    readonly property bool showThreadLengthSummary: root.zStart !== root.zEnd
    readonly property string threadHandText: root.zStart > root.zEnd ? "RH" : "LH"
    signal openNumPadRequested(var field)
    signal teachXRequested(int index)
    signal teachZRequested(int index)

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
        spacing: Theme.margin

        RowLayout {
            id: detailsLayout
            Layout.fillWidth: true
            spacing: Theme.margin
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
                    rpmOnly: true
                    speeds: root.op.speeds_and_feeds || ({})
                    onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                    onSpeedsEdited: function(speeds) { root.editor.edit({ speeds_and_feeds: speeds }) }
                }

                TitledCard {
                    id: threadParametersBox
                    title: "Thread Parameters"
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    font.pixelSize: Theme.fontBody

                    GridLayout {
                        columns: 3
                        columnSpacing: Theme.spacing
                        rowSpacing: 16

                        Label { text: "Pitch"; font.pixelSize: Theme.fontBody; Layout.alignment: Qt.AlignVCenter; Layout.minimumWidth: 80 }
                        NumpadField {
                            Layout.preferredWidth: 100
                            settingName: "threading.metric_pitch"
                            validatorObject: dblVal
                            value: root.pitch
                            formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                            hAlign: Text.AlignRight
                            onOpenRequested: function(field) { root.openNumPadRequested(field) }
                            onValueCommitted: function(value) { root.editor.editPitch(Number(value)) }
                        }
                        Label { text: "(mm)"; font.pixelSize: Theme.fontSmall; Layout.alignment: Qt.AlignVCenter }

                        Label { text: "Starts"; font.pixelSize: Theme.fontBody; Layout.alignment: Qt.AlignVCenter; Layout.minimumWidth: 80 }
                        NumpadField {
                            Layout.preferredWidth: 100
                            settingName: "threading.starts_count"
                            validatorObject: intVal
                            value: root.starts
                            formatter: function(v) { return (v == null) ? "1" : String(Math.max(1, Math.round(Number(v)))) }
                            hAlign: Text.AlignRight
                            onOpenRequested: function(field) { root.openNumPadRequested(field) }
                            onValueCommitted: function(value) { root.editor.edit({ starts: Math.max(1, Math.round(value)) }) }
                        }
                        Item {}
                    }
                }

                TitledCard {
                    id: zLimitsBox
                    title: "Z Limits"
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    font.pixelSize: Theme.fontBody

                    RowLayout {
                        anchors.fill: parent
                        spacing: Theme.spacingLarge

                        GridLayout {
                            columns: 3
                            columnSpacing: 16
                            rowSpacing: 16
                            Layout.alignment: Qt.AlignVCenter

                            Label { text: "Z Start"; font.pixelSize: Theme.fontBody; Layout.alignment: Qt.AlignVCenter; Layout.minimumWidth: 80 }
                            NumpadField {
                                id: tf_zStart
                                Layout.preferredWidth: 110
                                settingName: "threading.z_start"
                                validatorObject: dblVal
                                value: root.zStart
                                formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                                hAlign: Text.AlignRight
                                onOpenRequested: function(field) { root.openNumPadRequested(field) }
                                onValueCommitted: function(value) { root.editor.edit({ z_start: Number(value) }) }
                            }
                            TeachInButton { onClicked: tf_zStart.commit(PositionsBridge.teachInZ()) }

                            Label { text: "Z End"; font.pixelSize: Theme.fontBody; Layout.alignment: Qt.AlignVCenter; Layout.minimumWidth: 80 }
                            NumpadField {
                                id: tf_zEnd
                                Layout.preferredWidth: 110
                                settingName: "threading.z_end"
                                validatorObject: dblVal
                                value: root.zEnd
                                formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                                hAlign: Text.AlignRight
                                onOpenRequested: function(field) { root.openNumPadRequested(field) }
                                onValueCommitted: function(value) { root.editor.edit({ z_end: Number(value) }) }
                            }
                            TeachInButton { onClicked: tf_zEnd.commit(PositionsBridge.teachInZ()) }
                        }

                        Rectangle {
                            visible: root.showThreadLengthSummary
                            Layout.fillHeight: true
                            Layout.minimumHeight: 64
                            width: Theme.hairline
                            color: Theme.outlineStrong
                        }

                        GridLayout {
                            visible: root.showThreadLengthSummary
                            Layout.alignment: Qt.AlignVCenter
                            columns: 2
                            columnSpacing: 8
                            rowSpacing: 8

                            Label {
                                text: "Thread Type:"
                                font.pixelSize: Theme.fontBody
                                Layout.alignment: Qt.AlignVCenter
                            }
                            Label {
                                text: root.threadHandText
                                font.pixelSize: Theme.fontBody
                                font.bold: true
                                horizontalAlignment: Text.AlignRight
                                Layout.fillWidth: true
                                Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                            }

                            Label {
                                text: "Thread Length:"
                                font.pixelSize: Theme.fontBody
                                Layout.alignment: Qt.AlignVCenter
                            }
                            Label {
                                text: root.formatThreadLength() + "mm"
                                font.pixelSize: Theme.fontBody
                                horizontalAlignment: Text.AlignRight
                                Layout.fillWidth: true
                                Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                            }
                        }
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

                TitledCard {
                    id: threadLocationBox
                    title: "Thread Location"
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    font.pixelSize: Theme.fontBody

                    ColumnLayout {
                        spacing: Theme.spacingSmall
                        ModelRadioButton {
                            text: "External (OD)"
                            font.pixelSize: Theme.fontSmall
                            checked: root.location === "OD"
                            onChosen: root.editor.edit({ location: "OD" })
                        }
                        ModelRadioButton {
                            text: "Internal (ID)"
                            font.pixelSize: Theme.fontSmall
                            checked: root.location === "ID"
                            onChosen: root.editor.edit({ location: "ID" })
                        }
                    }
                }

                TitledCard {
                    id: diametersBox
                    title: "Thread Diameters"
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    font.pixelSize: Theme.fontBody

                    GridLayout {
                        columns: 3
                        columnSpacing: 16
                        rowSpacing: 16

                        // Row 1: TeachIn diameter (Major for OD, Minor for ID)
                        Label {
                            text: root.location === "OD" ? "Major Ø" : "Minor Ø"
                            font.pixelSize: Theme.fontBody
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
                            onOpenRequested: function(field) { root.openNumPadRequested(field) }
                            onValueCommitted: function(value) {
                                root.editor.edit(root.location === "OD" ? { major_diameter: Number(value) }
                                                                         : { minor_diameter: Number(value) })
                            }
                        }
                        TeachInButton { onClicked: tf_teachDiam.commit(PositionsBridge.teachInX() * 2) }

                        // Row 2: Calculate diameter (Minor for OD, Major for ID)
                        Label {
                            text: root.location === "OD" ? "Minor Ø" : "Major Ø"
                            font.pixelSize: Theme.fontBody
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
                            onOpenRequested: function(field) { root.openNumPadRequested(field) }
                            onValueCommitted: function(value) {
                                root.editor.edit(root.location === "OD" ? { minor_diameter: Number(value) }
                                                                         : { major_diameter: Number(value) })
                            }
                        }
                        Button {
                            text: "Calculate"
                            onClicked: root.editor.calculateDiameter()
                        }
                    }
                }

                TitledCard {
                    id: cuttingParamsBox
                    title: "Cutting Parameters"
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    font.pixelSize: Theme.fontBody

                    contentItem: G76CuttingParams {
                        operation: root.op
                        onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                        onEdited: function(changes) { root.editor.edit(changes) }
                    }
                }
            }
        }

        Item { Layout.fillHeight: true }
    }
}
