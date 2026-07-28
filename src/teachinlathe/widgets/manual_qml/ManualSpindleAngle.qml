import QtQuick 2.15
import QtQuick.Layouts 1.15

RowLayout {
    id: root

    property string value: "0.0°"

    spacing: 8

    Text {
        Layout.preferredWidth: 104
        text: "Orientation:"
        color: "#1e2430"
        font.pixelSize: 17
        horizontalAlignment: Text.AlignRight
        verticalAlignment: Text.AlignVCenter
    }

    Text {
        Layout.preferredWidth: 78
        Layout.preferredHeight: 40
        text: root.value
        color: "#0f172a"
        font.pixelSize: 17
        font.family: "Noto Sans Mono"
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }

    Item {
        Layout.preferredWidth: 66
    }
}
