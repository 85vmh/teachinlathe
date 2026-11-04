// FieldCell.qml — an equal share of a primitive card's row between its dividers:
// a label and its input, the two in the middle. The label's width is fixed, so
// the inputs line up from one card to the next whatever the label says.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme

Item {
    id: root

    property string label: ""
    default property alias input: cellRow.data
    // where the label starts and the input ends, in this cell
    readonly property real contentLeft: cellRow.x
    readonly property real contentRight: cellRow.x + cellRow.width

    Layout.fillWidth: true
    Layout.preferredWidth: 0
    implicitHeight: cellRow.implicitHeight

    RowLayout {
        id: cellRow
        anchors.centerIn: parent
        spacing: Theme.spacingSmall

        // a label longer than its place goes on to the left, its input stays
        Label {
            text: root.label
            font.pixelSize: Theme.fontBody
            Layout.preferredWidth: CardMetrics.labelWidth
            horizontalAlignment: implicitWidth > CardMetrics.labelWidth ? Text.AlignRight : Text.AlignLeft
        }
    }
}
