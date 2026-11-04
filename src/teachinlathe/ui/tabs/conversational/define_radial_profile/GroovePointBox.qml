// GroovePointBox.qml — one of a groove's four points, laid over the profile
// canvas, a dot on it pointing an arrow here: P1 where the right flank
// starts, P2 its bottom, P3 the left flank's bottom, P4 where it starts.
// A flank's start (``flankStart``: P1, P4) has its X and Z, each with its
// TeachIn, the flank's angle and the blend on its corner; a bottom (P2, P3)
// its X, with its TeachIn, and its blend: as Parting's edge break, with no
// label, "<- Add Blend" in place of its size while there is none
// (BlendPicker). The labels - the blend's drop-down among them - in one
// column, at its right; the fields lined up after it.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import common.touchable_input
import theme
import common
import TeachInLathe
import tabs.conversational
import "points.js" as Points

CanvasBox {
    id: root

    property int    point: 1               // 1..4
    property bool   flankStart: true       // P1, P4: Z and the angle too
    property real   xValue: 0.0            // a diameter
    property real   zValue: 0.0
    property real   angleValue: 0.0
    property var    blend: ({ type: "none", chamfer_width: 0, fillet_radius: 0 })
    // the numpad's settings: <prefix>.x, .z, .angle, .chamfer_width, .fillet_radius
    property string settingPrefix: ""

    // ``key``: "x", "z" or "angle"
    signal fieldEdited(string key, real value)
    signal blendEdited(string blendType, real chamferWidth, real filletRadius)
    signal openNumPadRequested(var field)

    accent: Points.color(point)

    function _name(axis) { return Points.name(point, axis) }

    // the labels' column - the blend's drop-down in it too - each label at
    // its right, by the field it is for; the fields lined up at its right
    readonly property real labelWidth: Math.max(xLabel.implicitWidth,
                                                root.flankStart ? zLabel.implicitWidth : 0,
                                                root.flankStart ? angleLabel.implicitWidth : 0,
                                                blendPicker.comboWidth)

    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }

    GridLayout {
        columns: 3
        columnSpacing: 20
        // as Stock to Leave's: room between the fields for a finger
        rowSpacing: 20

        Label {
            id: xLabel
            Layout.preferredWidth: root.labelWidth
            horizontalAlignment: Text.AlignRight
            text: root._name("X")
            textFormat: Text.RichText
            color: root.accent
            font.pixelSize: Points.fontSize
        }
        NumpadField {
            id: xField
            Layout.preferredWidth: 100
            settingName: root.settingPrefix + ".x"
            description: "P" + root.point + " X"
            validatorObject: dblVal
            seedNumpadFromValue: true
            value: root.xValue
            formatter: function (v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: function(field) { root.openNumPadRequested(field) }
            onValueCommitted: function(value) { root.fieldEdited("x", Number(value)) }
        }
        TeachInButton {
            onClicked: xField.commit(PositionsBridge.teachInX() * 2)
        }

        Label {
            id: zLabel
            visible: root.flankStart
            Layout.preferredWidth: root.labelWidth
            horizontalAlignment: Text.AlignRight
            text: root._name("Z")
            textFormat: Text.RichText
            color: root.accent
            font.pixelSize: Points.fontSize
        }
        NumpadField {
            id: zField
            visible: root.flankStart
            Layout.preferredWidth: 100
            settingName: root.settingPrefix + ".z"
            description: "P" + root.point + " Z"
            validatorObject: dblVal
            seedNumpadFromValue: true
            value: root.zValue
            formatter: function (v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: function(field) { root.openNumPadRequested(field) }
            onValueCommitted: function(value) { root.fieldEdited("z", Number(value)) }
        }
        TeachInButton {
            visible: root.flankStart
            onClicked: zField.commit(PositionsBridge.teachInZ())
        }

        Label {
            id: angleLabel
            visible: root.flankStart
            Layout.preferredWidth: root.labelWidth
            horizontalAlignment: Text.AlignRight
            text: "Angle"
            color: root.accent
            font.pixelSize: Theme.fontBody
        }
        NumpadField {
            visible: root.flankStart
            Layout.preferredWidth: 100
            settingName: root.settingPrefix + ".angle"
            description: "P" + root.point + " flank angle"
            validatorObject: dblVal
            seedNumpadFromValue: true
            value: root.angleValue
            formatter: function (v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: function(field) { root.openNumPadRequested(field) }
            onValueCommitted: function(value) { root.fieldEdited("angle", Number(value)) }
        }
        Label {
            visible: root.flankStart
            text: "(deg)"
            font.pixelSize: Theme.fontBody
        }

        // the drop-down in the labels' column, the size in the fields'
        BlendPicker {
            id: blendPicker
            Layout.columnSpan: 3
            leadWidth: root.labelWidth
            noneTextColor: root.accent
            noneTextBold: true
            blendType: root.blend && root.blend.type ? (root.blend.type === "radius" ? "fillet" : root.blend.type)
                                                     : "none"
            chamferWidth: root.blend && root.blend.chamfer_width !== undefined ? Number(root.blend.chamfer_width) : 0
            filletRadius: root.blend && root.blend.fillet_radius !== undefined ? Number(root.blend.fillet_radius) : 0
            chamferSettingName: root.settingPrefix + ".chamfer_width"
            filletSettingName: root.settingPrefix + ".fillet_radius"
            onEdited: function(blendType, chamferWidth, filletRadius) {
                root.blendEdited(blendType, chamferWidth, filletRadius)
            }
            onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
        }
    }
}
