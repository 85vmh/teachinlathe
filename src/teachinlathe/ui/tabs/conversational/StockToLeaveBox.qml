// StockToLeaveBox.qml — radial / axial stock to leave, laid over the profile
// canvas; the offset on the canvas points to it, in labelColor. Under the
// inputs, past a line, a button in the box's colour for what is done with
// that stock (actionText; none without one): Turning's Add Finishing
// Operation, Profile Roughing's Add Profile Contour.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import common
import common.touchable_input
import theme

CanvasBox {
    id: root
    accent: labelColor

    property color labelColor: Theme.foreground

    property real radial: 0.0
    property real axial: 0.0
    // the button under the inputs: its text ("" for none)
    property string actionText: ""

    signal radialEdited(real value)
    signal axialEdited(real value)
    signal openNumPadRequested(var field)
    signal actionClicked()

    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }

    ColumnLayout {
        spacing: Theme.spacingSmall

        GridLayout {
            columns: 3
            columnSpacing: Theme.spacing
            rowSpacing: 20

            Label { text: "Radial"; color: root.labelColor; font.pixelSize: Theme.fontBody }
            NumpadField {
                Layout.preferredWidth: 100
                settingName: "stock_to_leave.radial"
                validatorObject: dblVal
                value: root.radial
                formatter: function (v) { return (v == null) ? "" : Number(v).toFixed(3) }
                hAlign: Text.AlignRight
                onOpenRequested: function(field) { root.openNumPadRequested(field) }
                onValueCommitted: function(value) { root.radialEdited(Number(value)) }
            }
            Label { text: "(mm)"; font.pixelSize: Theme.fontBody }

            Label { text: "Axial"; color: root.labelColor; font.pixelSize: Theme.fontBody }
            NumpadField {
                Layout.preferredWidth: 100
                settingName: "stock_to_leave.axial"
                validatorObject: dblVal
                value: root.axial
                formatter: function (v) { return (v == null) ? "" : Number(v).toFixed(3) }
                hAlign: Text.AlignRight
                onOpenRequested: function(field) { root.openNumPadRequested(field) }
                onValueCommitted: function(value) { root.axialEdited(Number(value)) }
            }
            Label { text: "(mm)"; font.pixelSize: Theme.fontBody }
        }

        Divider {
            visible: root.actionText !== ""
            orientation: Qt.Horizontal
        }
        OperationIconTextButton {
            visible: root.actionText !== ""
            Layout.fillWidth: true
            text: root.actionText
            tint: root.accent
            borderTint: root.accent
            color: Theme.surface
            buttonHeight: Theme.buttonHeight
            fontBold: true
            onClicked: root.actionClicked()
        }
    }
}
