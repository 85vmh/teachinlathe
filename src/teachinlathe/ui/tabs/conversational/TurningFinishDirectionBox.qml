import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme

CanvasBox {
    id: root
    property string direction: "towards_z_minus"
    signal directionEdited(string value)

    ButtonGroup { id: directions }
    ColumnLayout {
        spacing: Theme.spacingSmall
        RadioButton {
            text: "Finish towards Z-"
            checked: root.direction === "towards_z_minus"
            ButtonGroup.group: directions
            font.pixelSize: Theme.fontBody
            onToggled: if (checked) root.directionEdited("towards_z_minus")
        }
        RadioButton {
            text: "Finish towards Z+"
            checked: root.direction === "towards_z_plus"
            ButtonGroup.group: directions
            font.pixelSize: Theme.fontBody
            onToggled: if (checked) root.directionEdited("towards_z_plus")
        }
    }
}
