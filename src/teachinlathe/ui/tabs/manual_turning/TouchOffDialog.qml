// TouchOffDialog.qml — the value a touch-off is made with, on the frame the
// numpad dialogs share (NumpadPopup): the keypad (NumpadKeypad) alone - no
// predefined values - and left of it a drawing of how the current loaded
// tool is put against the stock for it (TouchOffCanvas); over both, what the
// value is and with which tool (titleText).
//
// Open it with openFor(field): ``field`` a TouchOffField
// (TeachInLatheDroRoot) - its ``axis``, its ``value`` the last one typed.
// Input hands the value to field.commit(value); for a blade's Z with
// field.place set to the point chosen on the canvas.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import common.touchable_input

NumpadPopup {
    id: root

    // the Manual Turning tab's tools (ManualToolsViewModel): the current
    // loaded tool, drawn
    required property var toolsViewModel

    // what the value is - a diameter, the distance to Z0, an axial tool's
    // distance to the centre line - and the current loaded tool's T number
    readonly property string titleText: {
        var what = axis === "z" ? "Distance to Z0"
                 : canvas.isAxial ? "Distance to the center line"
                 : "Measured \u00d8"
        var toolNo = toolsViewModel.currentLoadedToolNo
        return toolNo > 0 ? what + " using T" + toolNo : what
    }
    property string axis: "x"

    // as wide as the keypad's digit keys: 3 columns of 100 px, 24 px apart
    // (NumpadKeypad's keyWidth, buttonSpacing)
    readonly property int keypadWidth: 3 * keypad.keyWidth + 2 * keypad.buttonSpacing
    readonly property int canvasWidth: 460
    readonly property int columnSpacing: 24

    width: keypadWidth + columnSpacing + canvasWidth + leftPadding + rightPadding
    // as high as the title and the keypad
    height: topPadding + bottomPadding + titleLabel.implicitHeight + keypad.buttonSpacing
            + keypad.implicitHeight

    function openFor(field) {
        root.targetField = field
        root.axis = field && field.axis ? field.axis : "x"
        keypad.resetTo(field ? field.value : null)
        canvas.resetPlace()
        root.open()
    }

    function _accept(value) {
        // a blade's Z: the point chosen on the canvas goes with it (a
        // trepanning blade's corner in X is only drawn for now)
        if (root.targetField && root.targetField.place !== undefined)
            root.targetField.place = canvas.needsPlace && root.axis === "z" ? canvas.bladePlace : ""
        if (root.targetField && root.targetField.commit)
            root.targetField.commit(String(value))
        root.close()
    }

    // the title over both, the drawing left of the keypad
    contentItem: ColumnLayout {
        spacing: keypad.buttonSpacing

        Text {
            id: titleLabel
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            text: root.titleText
            font.pixelSize: Theme.fontTitle
            font.bold: true
            color: Theme.foreground
            elide: Text.ElideRight
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: root.columnSpacing

            TouchOffCanvas {
                id: canvas
                Layout.fillWidth: true
                Layout.fillHeight: true
                axis: root.axis
                toolView: root.toolsViewModel.currentLoadedToolView
            }

            NumpadKeypad {
                id: keypad
                Layout.preferredWidth: root.keypadWidth
                Layout.maximumWidth: root.keypadWidth
                Layout.fillHeight: true
                onAccepted: function(value) { root._accept(value) }
            }
        }
    }
}
