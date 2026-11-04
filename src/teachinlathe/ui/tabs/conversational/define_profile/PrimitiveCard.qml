// PrimitiveCard.qml — a primitive's card: its number and its icon, its fields, and
// the button that gives its end corner a blend.
import QtQuick
import QtQuick.Layouts
import tabs.conversational
import theme
import common

ProfileCard {
    id: root

    property string iconName: ""

    // the blend button was pressed: the screen asks which
    signal blendRequested(int idx)

    color:        isSelected ? Theme.selection : Theme.surfaceAlt
    border.color: isSelected ? Theme.accent : Theme.outline

    icon: [
        CardNumber {
            anchors.top: parent.top
            anchors.left: parent.left
            number: root.primIdx + 1
            fill: root.color
        },
        Image {
            anchors.centerIn: parent
            width: CardMetrics.iconSize; height: CardMetrics.iconSize
            sourceSize.width: CardMetrics.iconSize; sourceSize.height: CardMetrics.iconSize
            source: Images.url(root.iconName)
            fillMode: Image.PreserveAspectFit; smooth: true
        }
    ]

    end: [
        // the button as far from it as from the card's edge
        CardDivider {
            overhang: CardMetrics.margin - root.border.width
            Layout.rightMargin: CardMetrics.margin
        },
        BlendButton {
            primData: root.primData
            corner: root.corner
            number: root.primIdx + 1
            onPressedToChoose: {
                root.tapped()
                root.blendRequested(root.primIdx)
            }
        }
    ]
}
