import QtQuick
import QtQuick.Controls
import theme

/*
 * A square button with an icon, beside a field: 48 px square - the height of
 * the NumpadField it sits next to. Drawn as the canvas's zoom buttons are
 * (ui/tabs/programs/BackplotIconButton.qml): surfaceAlt, a hairline border,
 * the selection colour while pressed. TeachIn's (TeachInButton), Calculate's.
 */
Button {
    id: control

    // the icon, Images.url("...")
    property url iconSource

    implicitWidth: 48
    implicitHeight: 48
    // leaves a 40 px glyph
    padding: 4
    focusPolicy: Qt.NoFocus
    hoverEnabled: true

    contentItem: Image {
        source: control.iconSource
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
