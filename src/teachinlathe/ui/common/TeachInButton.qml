import QtQuick
import QtQuick.Controls
import theme

/*
 * The TeachIn button beside a position field: the TeachIn icon, 48 px square
 * - the height of the NumpadField it sits next to. Drawn as the canvas's zoom
 * buttons are (ui/tabs/programs/BackplotIconButton.qml): surfaceAlt, a hairline
 * border, the selection colour while pressed.
 */
Button {
    id: control

    implicitWidth: 48
    implicitHeight: 48
    // leaves a 40 px glyph
    padding: 4
    focusPolicy: Qt.NoFocus
    hoverEnabled: true

    contentItem: Image {
        source: Images.url("teach_in.svg")
        fillMode: Image.PreserveAspectFit
        smooth: true
        // rasterised at the size it is drawn at, so the SVG stays sharp
        sourceSize.width: control.availableWidth
        sourceSize.height: control.availableHeight
        opacity: control.enabled ? 1.0 : 0.4
    }

    background: Rectangle {
        radius: Theme.radius
        color: control.down ? Theme.selection
             : control.hovered ? Theme.hover
             : Theme.surfaceAlt
        border.width: Theme.hairline
        border.color: Theme.separator
    }
}
