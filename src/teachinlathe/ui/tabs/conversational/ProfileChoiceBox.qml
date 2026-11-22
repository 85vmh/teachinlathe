// ProfileChoiceBox.qml — which profile a Profile Roughing or Contour cuts,
// laid over the profile canvas: one of the Define Profiles above it, picked
// as P1, P2, ... in a dropdown with no label, its labels centred, as wide as
// the widest needs. No profile of its id above: nothing picked.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import common
import theme

CanvasBox {
    id: root

    // the profiles above it (the editor's profileIds), and the one it cuts
    property var profileIds: []
    property int profileId: 0
    readonly property var labels: profileIds.map(function(id) { return "P" + id })

    signal profileIdEdited(int value)

    // the widest label, for the dropdown's width
    TextMetrics {
        id: widestLabel
        font: profileCombo.font
        text: root.labels.reduce(function(widest, label) {
            return label.length > widest.length ? label : widest }, "")
    }

    // the dropdown alone, no label: its P1, P2, ... say what it is
    GridLayout {
        columns: 1

        ModelComboBox {
            id: profileCombo
            Layout.preferredWidth: leftPadding + Math.ceil(widestLabel.advanceWidth) + 2 * Theme.spacingSmall
                                   + rightPadding
            Layout.preferredHeight: Theme.inputHeight
            font.pixelSize: Theme.fontBody
            model: root.labels
            selectedIndex: root.profileIds.indexOf(root.profileId)
            displayText: selectedIndex >= 0 ? root.labels[selectedIndex] : "–"
            onPicked: function(index) { root.profileIdEdited(root.profileIds[index]) }
            contentItem: Text {
                leftPadding: Theme.spacingSmall
                rightPadding: Theme.spacingSmall
                text: profileCombo.displayText
                font: profileCombo.font
                color: Theme.foregroundStrong
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            delegate: ItemDelegate {
                required property int index
                required property var modelData
                width: profileCombo.width
                height: Theme.inputHeight
                highlighted: profileCombo.highlightedIndex === index
                contentItem: Text {
                    text: modelData
                    font: profileCombo.font
                    color: Theme.foregroundStrong
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }
    }
}
