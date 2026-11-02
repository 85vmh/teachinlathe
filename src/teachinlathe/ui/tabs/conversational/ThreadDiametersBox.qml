// ThreadDiametersBox.qml — a thread's Major Ø and Minor Ø in one box, laid
// over the profile canvas. The diameter the thread is measured on comes
// first, with its TeachIn: Major Ø for an OD thread, Minor Ø for an ID one;
// the other one under it, with Calculate (from it and the pitch).
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import common.touchable_input
import theme
import common
import TeachInLathe

CanvasBox {
    id: root

    // "OD" | "ID"
    property string location: "OD"
    property real   majorDiameter: 0.0
    property real   minorDiameter: 0.0
    property color  majorColor: accent
    property color  minorColor: accent

    readonly property bool internal: location === "ID"

    signal majorEdited(real value)
    signal minorEdited(real value)
    signal calculateRequested()
    signal openNumPadRequested(var field)

    DoubleValidator { id: dblVal; bottom: 0; notation: DoubleValidator.StandardNotation }

    // a field's commit sets its value, which ends its binding: bound again
    // after each, so it follows Calculate, the pitch and OD / ID
    function _taughtValue() { return root.internal ? root.minorDiameter : root.majorDiameter }
    function _calculatedValue() { return root.internal ? root.majorDiameter : root.minorDiameter }

    GridLayout {
        columns: 3
        columnSpacing: 20
        rowSpacing: Theme.spacingSmall

        // the diameter taught in
        Label {
            text: root.internal ? "Minor Ø" : "Major Ø"
            color: root.internal ? root.minorColor : root.majorColor
            font.pixelSize: Theme.fontBody
        }
        NumpadField {
            id: taughtField
            Layout.preferredWidth: 100
            settingName: "threading.teach_diam"
            description: root.internal ? "Minor Ø" : "Major Ø"
            validatorObject: dblVal
            value: root._taughtValue()
            formatter: function (v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: function(field) { root.openNumPadRequested(field) }
            onValueCommitted: function(value) {
                if (root.internal) root.minorEdited(Number(value))
                else root.majorEdited(Number(value))
                taughtField.value = Qt.binding(root._taughtValue)
            }
        }
        TeachInButton {
            onClicked: taughtField.commit(PositionsBridge.teachInX() * 2)
        }

        // the diameter calculated from it
        Label {
            text: root.internal ? "Major Ø" : "Minor Ø"
            color: root.internal ? root.majorColor : root.minorColor
            font.pixelSize: Theme.fontBody
        }
        NumpadField {
            id: calculatedField
            Layout.preferredWidth: 100
            settingName: "threading.calc_diam"
            description: root.internal ? "Major Ø" : "Minor Ø"
            validatorObject: dblVal
            value: root._calculatedValue()
            formatter: function (v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: function(field) { root.openNumPadRequested(field) }
            onValueCommitted: function(value) {
                if (root.internal) root.majorEdited(Number(value))
                else root.minorEdited(Number(value))
                calculatedField.value = Qt.binding(root._calculatedValue)
            }
        }
        // Calculate: the TeachIn button's size, a calculator on it
        SquareIconButton {
            iconSource: Images.url("calculate.svg")
            onClicked: root.calculateRequested()
        }
    }
}
