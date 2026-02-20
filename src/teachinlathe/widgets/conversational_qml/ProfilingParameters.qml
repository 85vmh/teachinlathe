// CuttingGeometry.qml — two equal 3x2 grids side-by-side (Start | Spacer | End)
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

GroupBox {
    id: root
    title: "Profiling Parameters"
    Layout.fillWidth: true
    Layout.minimumWidth: 420
    Layout.preferredWidth: 560
    font.pixelSize: 16

    // bridge
    property int  opIndex: -1
    property var  opData: null
    property var  profilingParameters: ({})

    signal saveRequested(var payload)

    signal openNumPadRequested(var field)

    signal teachXRequested(int index)

    signal teachZRequested(int index)

    // state
    property int profile_id: 0
    property real x_start: 0.0
    property real z_start: 0.0
    property bool _loading: false

    function applyData(index, parameters, fullOp) {
        _loading = true
        opIndex = index
        opData = fullOp || {}
        profilingParameters = parameters || {}
        profile_id = parseInt(profilingParameters.profile_id !== undefined ? profilingParameters.profile_id : 0)
        x_start = parseFloat(profilingParameters.x_start !== undefined ? profilingParameters.x_start : 0.0)
        z_start = parseFloat(profilingParameters.z_start !== undefined ? profilingParameters.z_start : 0.0)
        _loading = false
    }

    function emitSave() {
        if (_loading) return
        var payload = {
            order: (opData && opData.order !== undefined) ? opData.order : 0,
            type: (opData && opData.type) ? opData.type : "",
            generate_gcode: (opData && opData.generate_gcode !== undefined) ? opData.generate_gcode : true,
            is_optional_block: (opData && opData.is_optional_block !== undefined) ? opData.is_optional_block : false,
            profiling_parameters: {
                profile_id: profile_id,
                x_start: x_start,
                z_start: z_start
            }
        }
        root.saveRequested(payload)
    }

    DoubleValidator {
        id: dblVal; notation: DoubleValidator.StandardNotation
    }

    RowLayout {
        id: outerRow
        anchors.fill: parent
        spacing: 70

        GridLayout {
            id: leftGrid
            Layout.fillHeight: true
            columns: 2
            columnSpacing: 20
            rowSpacing: 20
                Label {
                    text: "Profile ID"
                    Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                    font.pixelSize: 16
                }
                NumpadField {
                    Layout.preferredWidth: 70
                    Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                    settingName: "pg.profile_id"
                    validatorObject: dblVal
                    value: root.profile_id
                    formatter: function (v) {
                        return (v == null) ? "" : Number(v)
                    }
                    hAlign: Text.AlignRight
                    fontPixelSize: 16
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: { root.profile_id = value; root.emitSave() }
                }
        }

        // ------- Vertical separator -------
        Rectangle {
            width: 1
            color: "#cccccc"
            Layout.fillHeight: true
        }

        GridLayout {
            id: rightGrid
            Layout.fillHeight: true
            columns: 3
            columnSpacing: 20
            rowSpacing: 20

            // Row 1
            Label {
                text: "X Start"
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                font.pixelSize: 16
            }
            NumpadField {
                Layout.preferredWidth: 100
                Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                settingName: "pg.x_start"
                validatorObject: dblVal
                value: root.x_start
                formatter: function (v) {
                    return (v == null) ? "" : Number(v).toFixed(3)
                }
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

            // Row 2
            Label {
                text: "Z Start"
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                font.pixelSize: 16
            }
            NumpadField {
                Layout.preferredWidth: 100
                Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                settingName: "pg.z_start"
                validatorObject: dblVal
                value: root.z_start
                formatter: function (v) {
                    return (v == null) ? "" : Number(v).toFixed(3)
                }
                hAlign: Text.AlignRight
                fontPixelSize: 16
                onOpenRequested: root.openNumPadRequested(field)
                onValueCommitted: { root.z_start = value; root.emitSave() }
            }
            Button {
                text: "TeachIn"
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                onClicked: root.teachZRequested(root.opIndex)
            }
        }
    }
}
