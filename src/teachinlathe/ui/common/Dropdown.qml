import QtQuick
import QtQuick.Controls
import theme

// A dropdown just wide enough for its text and the arrow (the padding on the
// right already holds the arrow), at the input height, its text and its list's
// items at the title size: the program header's Datum and the Manual Turning
// DRO's work offset ("Tool Coordinates in").
// It shows what its model says: selectedIndex bound, picked reported (ModelComboBox).
ModelComboBox {
    id: control

    implicitWidth: leftPadding + contentItem.implicitWidth + rightPadding
    implicitHeight: Theme.inputHeight
    font.pixelSize: Theme.fontTitle

    contentItem: Text {
        leftPadding: Theme.spacingSmall
        rightPadding: Theme.spacingSmall
        text: control.displayText
        font: control.font
        color: Theme.foregroundStrong
        horizontalAlignment: Text.AlignLeft
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    delegate: ItemDelegate {
        required property int index
        required property var modelData
        width: ListView.view ? ListView.view.width : 0
        height: Theme.inputHeight
        text: modelData
        font: control.font
        highlighted: control.highlightedIndex === index
    }
}
