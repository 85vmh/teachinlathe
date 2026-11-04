// BlendTypePopup.qml — which blend to put on a corner: each type as a button,
// its icon over its name. Choosing one closes it and says which.
import QtQuick
import tabs.conversational
import theme

ChoicePopup {
    id: root

    title: "Blend Type"

    readonly property int optionWidth:   130
    readonly property int optionHeight:  115
    readonly property int optionPadding: 14

    // ``blendType``: "chamfer", "fillet" or "undercut_din509"
    signal blendChosen(string blendType)

    // the corner the blend goes on (Geometry.cornersOf): which way the icons
    // are turned, and whether it can have an undercut
    property var corner: null

    readonly property var options: {
        var types = [
            { type: "chamfer", text: "Chamfer" },
            { type: "fillet",  text: "Fillet" }
        ]
        if (corner && corner.undercutAvailable)
            types.push({ type: "undercut_din509", text: "DIN 509 E" })
        return types
    }

    Row {
        spacing: Theme.spacingLarge

        Repeater {
            model: root.options

            delegate: ChoiceButton {
                id: option
                required property var modelData

                width: root.optionWidth
                height: root.optionHeight
                topPadding: root.optionPadding
                bottomPadding: root.optionPadding

                contentItem: Column {
                    spacing: Theme.spacing

                    // as big as on the cards: the same thickness of line
                    BlendIcon {
                        anchors.horizontalCenter: parent.horizontalCenter
                        blendType: option.modelData.type
                        corner: root.corner
                    }
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: option.modelData.text
                        font.pixelSize: Theme.fontBody
                        color: Theme.foreground
                    }
                }

                onClicked: {
                    root.close()
                    root.blendChosen(modelData.type)
                }
            }
        }
    }
}
