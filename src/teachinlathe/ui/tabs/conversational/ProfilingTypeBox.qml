// ProfilingTypeBox.qml — how a profile is roughed (pass type), laid over the
// profile canvas. The 45° passes are offered for ID profiles only, in a
// second column.
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import theme 1.0

CanvasBox {
    id: root
    accent: Theme.foregroundStrong

    property string profilingType: "od"   // from the profile
    // "axial" | "radial" | "diagonal_interior" | "diagonal_exterior"
    property string passType: "axial"

    signal passTypeEdited(string value)

    ButtonGroup { id: passGroup }

    component PassButton: RadioButton {
        property string value
        font.pixelSize: Theme.fontSmall
        checked: root.passType === value
        ButtonGroup.group: passGroup
        onToggled: if (checked) root.passTypeEdited(value)
    }

    // the straight passes; beside them, for an ID profile only, the 45° ones,
    // their arrows pointing the way they go: up-left toward the interior,
    // down-right toward the exterior
    RowLayout {
        spacing: Theme.spacingLarge

        ColumnLayout {
            Layout.alignment: Qt.AlignTop
            spacing: Theme.spacingSmall
            PassButton { value: "axial";  text: "Axial Passes" }
            PassButton { value: "radial"; text: "Radial Passes" }
        }

        ColumnLayout {
            visible: root.profilingType === "id"
            Layout.alignment: Qt.AlignTop
            spacing: Theme.spacingSmall
            PassButton { value: "diagonal_interior"; text: "45° Passes \u2196" }
            PassButton { value: "diagonal_exterior"; text: "45° Passes \u2198" }
        }
    }
}
