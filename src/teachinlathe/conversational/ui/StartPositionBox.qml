// StartPositionBox.qml — X Start / Z Start of a profile operation, laid over
// the profile canvas.
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import touchable_input 1.0
import theme 1.0

CanvasBox {
    id: root

    property real xStart: 0.0
    property real zStart: 0.0

    signal xStartEdited(real value)
    signal zStartEdited(real value)
    signal openNumPadRequested(var field)

    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }

    GridLayout {
        columns: 3
        columnSpacing: 20
        rowSpacing: 20

        Label { text: "X Start Position"; color: root.accent; font.pixelSize: Theme.fontBody }
        NumpadField {
            id: tf_x_start
            Layout.preferredWidth: 100
            settingName: "pg.x_start"
            validatorObject: dblVal
            value: root.xStart
            formatter: function (v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: root.xStartEdited(Number(value))
        }
        Button {
            text: "TeachIn"
            onClicked: tf_x_start.commit(positionsBridge.teachInX() * 2)
        }

        Label { text: "Z Start Position"; color: root.accent; font.pixelSize: Theme.fontBody }
        NumpadField {
            id: tf_z_start
            Layout.preferredWidth: 100
            settingName: "pg.z_start"
            validatorObject: dblVal
            value: root.zStart
            formatter: function (v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: root.zStartEdited(Number(value))
        }
        Button {
            text: "TeachIn"
            onClicked: tf_z_start.commit(positionsBridge.teachInZ())
        }
    }
}
