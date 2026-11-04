import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import common.touchable_input
import theme
import common
import TeachInLathe
import "define_radial_profile/points.js" as Points

CanvasBox {
    id: root
    property int point: 1
    property string settingPrefix: "turning"
    property color pointColor: point === 1 ? "#1565c0" : "#00838f"
    property real xValue: 0
    property real zValue: 0
    signal fieldEdited(string axis, real value)
    signal openNumPadRequested(var field)

    accent: pointColor

    function _name(axis) { return Points.name(point, axis) }
    readonly property real labelWidth: Math.max(xLabel.implicitWidth, zLabel.implicitWidth)

    DoubleValidator { id: validator; notation: DoubleValidator.StandardNotation }

    GridLayout {
        columns: 3
        columnSpacing: Theme.spacing
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
            Layout.preferredWidth: 96
            settingName: root.settingPrefix + ".p" + root.point + "x"
            description: "P" + root.point + " X"
            validatorObject: validator
            seedNumpadFromValue: true
            value: root.xValue
            formatter: function(v) { return v == null ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: function(field) { root.openNumPadRequested(field) }
            onValueCommitted: function(value) { root.fieldEdited("x", Number(value)) }
        }
        TeachInButton { onClicked: xField.commit(PositionsBridge.teachInX() * 2) }

        Label {
            id: zLabel
            Layout.preferredWidth: root.labelWidth
            horizontalAlignment: Text.AlignRight
            text: root._name("Z")
            textFormat: Text.RichText
            color: root.accent
            font.pixelSize: Points.fontSize
        }
        NumpadField {
            id: zField
            Layout.preferredWidth: 96
            settingName: root.settingPrefix + ".p" + root.point + "z"
            description: "P" + root.point + " Z"
            validatorObject: validator
            seedNumpadFromValue: true
            value: root.zValue
            formatter: function(v) { return v == null ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: function(field) { root.openNumPadRequested(field) }
            onValueCommitted: function(value) { root.fieldEdited("z", Number(value)) }
        }
        TeachInButton { onClicked: zField.commit(PositionsBridge.teachInZ()) }
    }
}
