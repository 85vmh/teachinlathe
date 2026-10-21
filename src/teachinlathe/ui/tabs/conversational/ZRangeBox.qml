// ZRangeBox.qml — a Z Start and a Z End together, each with its TeachIn,
// laid over the profile canvas: one box, which the travel between them on
// the canvas points an arrow to.
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import common.touchable_input 1.0
import theme 1.0
import common 1.0

CanvasBox {
    id: root

    property real   zStart: 0.0
    property real   zEnd: 0.0
    property string startLabel: "Z Start"
    property string endLabel: "Z End"
    // each label in its own Z line's colour
    property color  startColor: accent
    property color  endColor: accent
    property string startSettingName: ""
    property string endSettingName: ""
    // the label column's width, so boxes stacked together line up
    property real   labelWidth: labelImplicitWidth
    readonly property real labelImplicitWidth: Math.max(startText.implicitWidth, endText.implicitWidth)

    signal zStartEdited(real value)
    signal zEndEdited(real value)
    signal openNumPadRequested(var field)

    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }

    GridLayout {
        columns: 3
        columnSpacing: 20
        rowSpacing: Theme.spacingSmall

        Label {
            id: startText
            Layout.preferredWidth: root.labelWidth
            text: root.startLabel
            color: root.startColor
            font.pixelSize: Theme.fontBody
        }
        NumpadField {
            id: startField
            Layout.preferredWidth: 100
            settingName: root.startSettingName
            description: root.startLabel
            validatorObject: dblVal
            value: root.zStart
            formatter: function (v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: function(field) { root.openNumPadRequested(field) }
            onValueCommitted: root.zStartEdited(Number(value))
        }
        TeachInButton {
            onClicked: startField.commit(positionsBridge.teachInZ())
        }

        Label {
            id: endText
            Layout.preferredWidth: root.labelWidth
            text: root.endLabel
            color: root.endColor
            font.pixelSize: Theme.fontBody
        }
        NumpadField {
            id: endField
            Layout.preferredWidth: 100
            settingName: root.endSettingName
            description: root.endLabel
            validatorObject: dblVal
            value: root.zEnd
            formatter: function (v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: function(field) { root.openNumPadRequested(field) }
            onValueCommitted: root.zEndEdited(Number(value))
        }
        TeachInButton {
            onClicked: endField.commit(positionsBridge.teachInZ())
        }
    }
}
