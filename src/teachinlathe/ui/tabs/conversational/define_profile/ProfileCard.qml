// ProfileCard.qml — what a Define Profile's cards have in common: its icon, then a
// divider, its fields and what ends it. See PrimitiveCard and BlendCard.
import QtQuick
import QtQuick.Layouts
import theme

Rectangle {
    id: root

    property var  primData:   ({})
    property int  primIdx:    0
    property bool isSelected: false
    property var  corner:     null

    default property alias fields: fieldsRow.data
    property alias icon: iconCell.data
    property alias end:  endCell.data

    signal primUpdated(int idx, var data)
    signal openNumPadRequested(var field)
    signal tapped()

    radius:       CardMetrics.radius
    border.width: isSelected ? 2 : Theme.hairline
    height:       cardRow.implicitHeight + CardMetrics.padding

    TapHandler { onTapped: root.tapped() }

    RowLayout {
        id: cardRow
        anchors { left: parent.left; right: parent.right; top: parent.top; margins: CardMetrics.margin }
        spacing: 0

        Item {
            id: iconCell
            implicitWidth: CardMetrics.iconArea
            Layout.fillHeight: true
        }

        CardDivider {
            overhang: CardMetrics.margin - root.border.width
            Layout.leftMargin: CardMetrics.margin
        }

        RowLayout {
            id: fieldsRow
            spacing: 0
            Layout.fillWidth: true
        }

        RowLayout {
            id: endCell
            spacing: 0
            // a layout would fill the row, a blend's card having nothing in it
            Layout.fillWidth: false
            Layout.preferredWidth: CardMetrics.endWidth
            Layout.fillHeight: true
        }
    }
}
