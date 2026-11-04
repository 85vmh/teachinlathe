import QtQuick
import QtQuick.Layouts
import theme

RowLayout {
    id: root

    property string value: "0.0°"

    spacing: Theme.spacingSmall

    Text {
        Layout.preferredWidth: 104
        text: "Orientation:"
        color: Theme.foreground
        font.pixelSize: Theme.fontLarge
        horizontalAlignment: Text.AlignRight
        verticalAlignment: Text.AlignVCenter
    }

    Text {
        Layout.preferredWidth: 78
        Layout.preferredHeight: Theme.buttonHeight
        text: root.value
        color: Theme.foregroundStrong
        font.pixelSize: Theme.fontLarge
        font.family: "Noto Sans Mono"
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }

    Item {
        Layout.preferredWidth: 66
    }
}
