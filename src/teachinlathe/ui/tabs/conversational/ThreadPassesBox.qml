// ThreadPassesBox.qml — how a G33 thread is cut in passes, laid over the
// profile canvas: the first pass's depth (DOC, with how many passes it
// makes), the infeed angle (29° or 29.5°) and the spring passes.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import common.touchable_input
import theme
import common

CanvasBox {
    id: root

    property color docColor: accent
    property real  initialDoc: 0.0
    property real  infeedAngle: 0.0
    property int   springPasses: 0
    // the thread's depth, radial, and its starts: for the passes' count
    property real  finalRadialDepth: 0.0
    property int   starts: 1

    // the roughing passes, as the pass planner makes them: the depth grows as
    // the square root of the pass number
    readonly property int roughingPassCount: (initialDoc > 0 && finalRadialDepth > 0)
                                             ? Math.ceil(Math.pow(finalRadialDepth / initialDoc, 2)) : 0
    readonly property string passCountText: starts > 1
                                            ? (starts + "×" + roughingPassCount + " passes")
                                            : (roughingPassCount + " passes")

    signal initialDocEdited(real value)
    signal infeedAngleEdited(real value)
    signal springPassesEdited(int value)
    signal openNumPadRequested(var field)

    DoubleValidator { id: docVal; bottom: 0; notation: DoubleValidator.StandardNotation }
    // the infeed angles offered; a left-hand thread's offset goes the other
    // way along Z, which the pass planner works out from Z Start / Z End
    readonly property var infeedAngles: [29.0, 29.5]
    IntValidator { id: countVal; bottom: 0; top: 99 }

    GridLayout {
        columns: 3
        columnSpacing: Theme.spacing
        rowSpacing: Theme.spacingSmall

        Label { text: "DOC"; color: root.docColor; font.pixelSize: Theme.fontBody }
        NumpadField {
            Layout.preferredWidth: 100
            settingName: "threading.initial_doc"
            description: "DOC"
            validatorObject: docVal
            value: root.initialDoc
            formatter: function (v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: function(field) { root.openNumPadRequested(field) }
            onValueCommitted: function(value) { root.initialDocEdited(Math.abs(Number(value))) }
        }
        Label { text: "(mm/radius)"; font.pixelSize: Theme.fontBody }

        Item { width: 1; height: 1 }
        Label {
            Layout.columnSpan: 2
            text: "[" + root.passCountText + "]"
            font.pixelSize: Theme.fontSmall
            font.bold: true
        }

        Label { text: "Infeed Angle"; font.pixelSize: Theme.fontBody }
        ModelComboBox {
            id: angleCombo
            Layout.preferredWidth: 100
            Layout.preferredHeight: Theme.inputHeight
            font.pixelSize: Theme.fontBody
            model: root.infeedAngles
            displayText: currentIndex < 0 ? "" : root.infeedAngles[currentIndex] + "°"
            // none shown for an angle not offered (an older operation's)
            selectedIndex: root.infeedAngles.indexOf(Number(root.infeedAngle))
            onPicked: function(index) { root.infeedAngleEdited(root.infeedAngles[index]) }
            delegate: ItemDelegate {
                width: angleCombo.width
                height: Theme.inputHeight
                text: modelData + "°"
                font: angleCombo.font
                highlighted: angleCombo.highlightedIndex === index
            }
        }
        Item { width: 1; height: 1 }

        Label { text: "Spring Passes"; font.pixelSize: Theme.fontBody }
        NumpadField {
            Layout.preferredWidth: 100
            settingName: "threading.spring_passes"
            description: "Spring Passes"
            validatorObject: countVal
            value: root.springPasses
            formatter: function (v) { return (v == null) ? "" : String(Math.round(Number(v))) }
            hAlign: Text.AlignRight
            onOpenRequested: function(field) { root.openNumPadRequested(field) }
            onValueCommitted: function(value) { root.springPassesEdited(Math.round(Number(value))) }
        }
        Item { width: 1; height: 1 }
    }
}
