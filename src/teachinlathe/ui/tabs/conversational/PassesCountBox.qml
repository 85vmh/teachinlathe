// PassesCountBox.qml — how many passes an operation takes its stock off in,
// laid over the profile canvas: picked from 1 to maxPasses (the editor's
// maxPassesCount) in a dropdown, as the infeed angle is, its numbers centred,
// as wide as the widest needs.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import common
import theme

CanvasBox {
    id: root

    property int passes: 1
    // the most passes offered
    required property int maxPasses
    // 1 .. maxPasses
    readonly property var counts: Array.from({ length: maxPasses }, function(_, i) { return i + 1 })

    signal passesEdited(int value)

    // the widest count, for the dropdown's width
    TextMetrics { id: widestCount; font: countCombo.font; text: String(root.maxPasses) }

    GridLayout {
        columns: 2
        columnSpacing: Theme.spacing

        Label { text: "Passes count"; font.pixelSize: Theme.fontBody }
        ModelComboBox {
            id: countCombo
            Layout.preferredWidth: leftPadding + Math.ceil(widestCount.advanceWidth) + 2 * Theme.spacingSmall
                                   + rightPadding
            Layout.preferredHeight: Theme.inputHeight
            font.pixelSize: Theme.fontBody
            model: root.counts
            displayText: String(root.passes)
            selectedIndex: root.counts.indexOf(root.passes)
            onPicked: function(index) { root.passesEdited(root.counts[index]) }
            contentItem: Text {
                leftPadding: Theme.spacingSmall
                rightPadding: Theme.spacingSmall
                text: countCombo.displayText
                font: countCombo.font
                color: Theme.foregroundStrong
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            delegate: ItemDelegate {
                required property int index
                required property var modelData
                width: countCombo.width
                height: Theme.inputHeight
                highlighted: countCombo.highlightedIndex === index
                contentItem: Text {
                    text: modelData
                    font: countCombo.font
                    color: Theme.foregroundStrong
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }
    }
}
