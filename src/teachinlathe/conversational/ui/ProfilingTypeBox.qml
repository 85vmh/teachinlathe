// ProfilingTypeBox.qml — how a profile is roughed (pass type), laid over the
// profile canvas. The 45° passes are offered for ID profiles only.
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import theme 1.0

CanvasBox {
    id: root
    title: (profilingType === "id" ? "ID" : "OD") + " Roughing Strategy"
    accent: Theme.foregroundStrong

    property string profilingType: "od"   // from the profile
    // "axial" | "radial" | "diagonal_interior" | "diagonal_exterior"
    property string passType: "axial"

    signal passTypeEdited(string value)

    ButtonGroup { id: passGroup }

    Repeater {
        model: [
            { value: "axial",             text: "Axial Passes",               idOnly: false },
            { value: "radial",            text: "Radial Passes",              idOnly: false },
            { value: "diagonal_interior", text: "45° Passes toward interior", idOnly: true  },
            { value: "diagonal_exterior", text: "45° Passes toward exterior", idOnly: true  }
        ]
        RadioButton {
            visible: !modelData.idOnly || root.profilingType === "id"
            text: modelData.text
            font.pixelSize: Theme.fontSmall
            checked: root.passType === modelData.value
            ButtonGroup.group: passGroup
            onToggled: if (checked) root.passTypeEdited(modelData.value)
        }
    }
}
