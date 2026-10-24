// GroovingBox.qml — a groove operation's own parameters, laid over the
// profile canvas: the strategy and, for Groove Roughing (showOffsets), where
// its first plunges go - Initial Offset apart either side of the groove's
// middle - and how far apart the plunges after them are (Afterwards Offset).
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import common.touchable_input
import theme

CanvasBox {
    id: root

    property string strategy: "start_center"
    property real   initialOffset: 0.0
    property real   afterwardsOffset: 0.0

    signal strategyEdited(string value)
    signal initialOffsetEdited(real value)
    signal afterwardsOffsetEdited(real value)
    signal openNumPadRequested(var field)

    property bool   showOffsets: true

    // [{label, value}]: Groove Roughing's by default
    property var strategies: [
        { label: "Start Center", value: "start_center" },
        { label: "Start Right", value: "start_right" },
        { label: "Start Left", value: "start_left" }
    ]

    DoubleValidator { id: dblVal; bottom: 0; notation: DoubleValidator.StandardNotation }

    GridLayout {
        columns: 3
        columnSpacing: 20
        rowSpacing: 20

        Label { text: "Strategy"; color: root.accent; font.pixelSize: Theme.fontBody }
        ComboBox {
            id: strategyCombo
            Layout.columnSpan: 2
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.inputHeight
            font.pixelSize: Theme.fontBody
            // as wide as its longest strategy, whatever else is in the box
            implicitContentWidthPolicy: ComboBox.WidestText
            model: root.strategies
            textRole: "label"
            currentIndex: {
                for (var i = 0; i < root.strategies.length; i++)
                    if (root.strategies[i].value === root.strategy) return i
                return 0
            }
            onActivated: function(index) { root.strategyEdited(root.strategies[index].value) }
            delegate: ItemDelegate {
                width: strategyCombo.width
                height: Theme.inputHeight
                text: modelData.label
                font: strategyCombo.font
                highlighted: strategyCombo.highlightedIndex === index
            }
        }

        Label {
            visible: root.showOffsets
            text: "Initial Offset"; color: root.accent; font.pixelSize: Theme.fontBody
        }
        NumpadField {
            visible: root.showOffsets
            Layout.preferredWidth: 100
            settingName: "groove_roughing.initial_offset"
            description: "Initial Offset"
            validatorObject: dblVal
            value: root.initialOffset
            formatter: function(v) { return v == null ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: function(field) { root.openNumPadRequested(field) }
            onValueCommitted: function(value) { root.initialOffsetEdited(Number(value)) }
        }
        Label { visible: root.showOffsets; text: "(mm)"; font.pixelSize: Theme.fontBody }

        Label {
            visible: root.showOffsets
            text: "Afterwards Offset"; color: root.accent; font.pixelSize: Theme.fontBody
        }
        NumpadField {
            visible: root.showOffsets
            Layout.preferredWidth: 100
            settingName: "groove_roughing.afterwards_offset"
            description: "Afterwards Offset"
            validatorObject: dblVal
            value: root.afterwardsOffset
            formatter: function(v) { return v == null ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: function(field) { root.openNumPadRequested(field) }
            onValueCommitted: function(value) { root.afterwardsOffsetEdited(Number(value)) }
        }
        Label { visible: root.showOffsets; text: "(mm)"; font.pixelSize: Theme.fontBody }

    }
}
