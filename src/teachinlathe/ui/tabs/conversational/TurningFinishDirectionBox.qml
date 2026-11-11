import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import common

CanvasBox {
    id: root
    property string direction: "towards_z_minus"
    signal directionEdited(string value)

    ColumnLayout {
        spacing: Theme.spacingSmall
        ModelRadioButton {
            text: "Finish towards Z-"
            checked: root.direction === "towards_z_minus"
            font.pixelSize: Theme.fontBody
            onChosen: root.directionEdited("towards_z_minus")
        }
        ModelRadioButton {
            text: "Finish towards Z+"
            checked: root.direction === "towards_z_plus"
            font.pixelSize: Theme.fontBody
            onChosen: root.directionEdited("towards_z_plus")
        }
    }
}
