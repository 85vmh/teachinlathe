// PeckBox.qml — Drilling's Peck Depth and, under it, the Dwell Time at the
// bottom of each peck, picked from a list; laid over the profile canvas, the
// peck's dimension on the canvas pointing to it, in its colour.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import common.touchable_input
import theme

CanvasBox {
    id: root
    accent: color

    property color color: Theme.foreground
    property real  peckDepth: 0.0
    property real  dwellTime: 0.0
    // the dwell times offered, in seconds
    property var   dwellTimes: [0, 0.1, 0.2, 0.3, 0.5, 1, 1.5, 2, 3]
    // the numpad's setting for the peck depth
    property string peckSettingName: "drilling.peck_depth"

    signal peckDepthEdited(real value)
    signal dwellTimeEdited(real value)
    signal openNumPadRequested(var field)

    DoubleValidator { id: dblVal; bottom: 0; notation: DoubleValidator.StandardNotation }

    GridLayout {
        columns: 3
        columnSpacing: 20
        rowSpacing: 20

        Label { text: "Peck Depth"; color: root.color; font.pixelSize: Theme.fontBody }
        NumpadField {
            id: peckField
            Layout.preferredWidth: 100
            settingName: root.peckSettingName
            description: "Peck Depth"
            validatorObject: dblVal
            value: root.peckDepth
            formatter: function (v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: function(field) { root.openNumPadRequested(field) }
            onValueCommitted: function(value) { root.peckDepthEdited(Number(value)) }
        }
        Label { text: "(mm)"; font.pixelSize: Theme.fontBody }

        Label { text: "Dwell Time"; color: root.color; font.pixelSize: Theme.fontBody }
        ComboBox {
            id: dwellCombo
            // as big as the Peck Depth field
            Layout.preferredWidth: peckField.width
            Layout.preferredHeight: peckField.height
            font.pixelSize: peckField.fontPixelSize
            model: root.dwellTimes
            displayText: Number(root.dwellTime).toFixed(1)
            // the time the op has, or the nearest offered
            currentIndex: {
                var best = 0
                for (var i = 1; i < root.dwellTimes.length; i++)
                    if (Math.abs(root.dwellTimes[i] - root.dwellTime) < Math.abs(root.dwellTimes[best] - root.dwellTime))
                        best = i
                return best
            }
            onActivated: function(index) { root.dwellTimeEdited(Number(root.dwellTimes[index])) }
            contentItem: Text {
                text: dwellCombo.displayText
                font: dwellCombo.font
                color: Theme.foregroundStrong
                horizontalAlignment: Text.AlignRight
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
            delegate: ItemDelegate {
                width: dwellCombo.width
                height: Theme.inputHeight
                text: Number(modelData).toFixed(1)
                font: dwellCombo.font
                highlighted: dwellCombo.highlightedIndex === index
            }
        }
        Label { text: "(sec)"; font.pixelSize: Theme.fontBody }
    }
}
