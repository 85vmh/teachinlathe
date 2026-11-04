// StartPointCard.qml
import QtQuick

PrimitiveCard {
    id: root

    iconName: "target.svg"

    StartField { label: "X Start"; field: "x_start"; description: "StartPoint X Start" }
    StartField { label: "Z Start"; field: "z_start"; description: "StartPoint Z Start" }

    component StartField: ProfileField {
        id: cell

        property string field: ""

        settingName: "sp." + root.primIdx + "." + field
        value: root.primData[field] !== undefined ? root.primData[field] : 0
        onOpenRequested: function(numpadField) {
            root.tapped()
            root.openNumPadRequested(numpadField)
        }
        onCommitted: function(committedValue) {
            root.tapped()
            var d = JSON.parse(JSON.stringify(root.primData))
            d[cell.field] = Number(committedValue)
            root.primUpdated(root.primIdx, d)
        }
    }
}
