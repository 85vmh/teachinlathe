// ThreadLocationBox.qml — where a thread is cut, OD or ID, laid over the
// profile canvas: two radio buttons in a row.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import common

CanvasBox {
    id: root
    accent: Theme.foregroundStrong

    // "OD" | "ID"
    property string location: "OD"

    signal locationEdited(string value)

    component LocationButton: ModelRadioButton {
        property string value
        font.pixelSize: Theme.fontBody
        checked: root.location === value
        onChosen: root.locationEdited(value)
    }

    RowLayout {
        spacing: Theme.spacingLarge
        LocationButton { value: "OD"; text: "OD Thread" }
        LocationButton { value: "ID"; text: "ID Thread" }
    }
}
