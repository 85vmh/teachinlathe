// NewProfilePopup.qml — what a new Define Profile is: the id it gets, and OD or
// ID, which it stays. Closed without a choice, nothing is added.
import QtQuick
import theme

ChoicePopup {
    id: root

    title: "Define Profile"

    readonly property int optionWidth: 180

    property int profileId: 1
    property int insertIndex: 0

    // ``profileType``: "id" or "od"
    signal profileTypeChosen(string profileType, int insertIndex)

    Text {
        width: parent.width
        horizontalAlignment: Text.AlignHCenter
        text: "New Profile: P" + root.profileId
        font.pixelSize: Theme.fontBody
        color: Theme.foreground
    }

    Row {
        spacing: Theme.spacingLarge

        Repeater {
            model: [
                { type: "id", text: "ID Profile" },
                { type: "od", text: "OD Profile" }
            ]

            delegate: ChoiceButton {
                id: option
                required property var modelData

                width: root.optionWidth
                height: Theme.buttonHeightTouch
                text: modelData.text
                font.pixelSize: Theme.fontBody

                contentItem: Text {
                    text: option.text
                    font: option.font
                    color: Theme.foreground
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }

                onClicked: {
                    root.close()
                    root.profileTypeChosen(modelData.type, root.insertIndex)
                }
            }
        }
    }
}
