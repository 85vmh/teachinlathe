// ZPositionBox.qml — one Z position (or, with ``axis`` "x", one X diameter),
// with its TeachIn, laid over the profile canvas; a mark on the canvas
// points an arrow to it, in its accent.
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

    property string label: ""
    property real   value: 0.0
    property string settingName: ""
    property bool pointLabel: false
    property int point: 1
    // "z", or "x": an X diameter, taught in as twice the radius read
    property string axis: "z"
    // the button after the value: TeachIn, or - given ``actionText`` - an
    // action of the screen's own, reported by actionRequested
    property string actionText: ""
    signal actionRequested()
    // the label column's width, so boxes stacked together line up
    property real   labelWidth: labelText.implicitWidth
    readonly property real labelImplicitWidth: labelText.implicitWidth

    signal valueEdited(real value)
    signal openNumPadRequested(var field)

    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }

    RowLayout {
        spacing: 20

        Label {
            id: labelText
            Layout.preferredWidth: root.labelWidth
            text: root.pointLabel ? Points.name(root.point, root.axis) : root.label
            textFormat: root.pointLabel ? Text.RichText : Text.PlainText
            color: root.accent
            font.pixelSize: root.pointLabel ? Points.fontSize : Theme.fontBody
        }
        NumpadField {
            id: valueField
            Layout.preferredWidth: 100
            settingName: root.settingName
            description: root.pointLabel ? "P" + root.point + " " + root.axis.toUpperCase() : root.label
            validatorObject: dblVal
            value: root.value
            formatter: function (v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: function(field) { root.openNumPadRequested(field) }
            onValueCommitted: function(value) { root.valueEdited(Number(value)) }
        }
        Button {
            visible: root.actionText !== ""
            text: root.actionText
            onClicked: root.actionRequested()
        }
        TeachInButton {
            visible: root.actionText === ""
            onClicked: valueField.commit(root.axis === "x" ? PositionsBridge.teachInX() * 2
                                                           : PositionsBridge.teachInZ())
        }
    }
}
