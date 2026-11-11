// ProfilingParameters.qml — two equal 3x2 grids side-by-side (Start | Spacer | End)
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import common.touchable_input
import theme
import common
import TeachInLathe

TitledCard {
    id: root
    title: "Profiling Parameters"
    Layout.fillWidth: true
    Layout.minimumWidth: 420
    Layout.preferredWidth: 560
    font.pixelSize: Theme.fontBody

    // the operation's profiling_parameters, as its editor has them: all it shows
    property var parameters: ({})
    readonly property var _p: parameters || {}

    // a change to the profiling_parameters: only the fields in it
    signal edited(var changes)
    signal openNumPadRequested(var field)
    signal teachXRequested(int index)
    signal teachZRequested(int index)

    readonly property int profile_id: _p.profile_id !== undefined ? parseInt(_p.profile_id) : 0
    readonly property real x_start: _p.x_start !== undefined ? Number(_p.x_start) : 0.0
    readonly property real z_start: _p.z_start !== undefined ? Number(_p.z_start) : 0.0

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
                    font.pixelSize: Theme.fontBody
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
                    onOpenRequested: function(field) { root.openNumPadRequested(field) }
                    onValueCommitted: function(value) { root.edited({ profile_id: Math.round(value) }) }
                }
        }

        // ------- Vertical separator -------
        Rectangle {
            width: Theme.hairline
            color: Theme.outline
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
                font.pixelSize: Theme.fontBody
            }
            NumpadField {
                id: tf_x_start
                Layout.preferredWidth: 100
                Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                settingName: "pg.x_start"
                validatorObject: dblVal
                value: root.x_start
                formatter: function (v) {
                    return (v == null) ? "" : Number(v).toFixed(3)
                }
                hAlign: Text.AlignRight
                onOpenRequested: function(field) { root.openNumPadRequested(field) }
                onValueCommitted: function(value) { root.edited({ x_start: Number(value) }) }
            }
            TeachInButton {
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                onClicked: tf_x_start.commit(PositionsBridge.teachInX() * 2)
            }

            // Row 2
            Label {
                text: "Z Start"
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                font.pixelSize: Theme.fontBody
            }
            NumpadField {
                id: tf_z_start
                Layout.preferredWidth: 100
                Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                settingName: "pg.z_start"
                validatorObject: dblVal
                value: root.z_start
                formatter: function (v) {
                    return (v == null) ? "" : Number(v).toFixed(3)
                }
                hAlign: Text.AlignRight
                onOpenRequested: function(field) { root.openNumPadRequested(field) }
                onValueCommitted: function(value) { root.edited({ z_start: Number(value) }) }
            }
            TeachInButton {
                Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                onClicked: tf_z_start.commit(PositionsBridge.teachInZ())
            }
        }
    }
}
