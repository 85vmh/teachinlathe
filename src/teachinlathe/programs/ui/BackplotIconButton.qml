import QtQuick 2.15
import QtQuick.Controls 2.15
import Qt5Compat.GraphicalEffects
import theme 1.0

/*
 * An icon control floating over the backplot.
 *
 * The same button the profile editor puts over its canvas - surfaceAlt on a
 * surfaceSunken ground, separated by its border rather than by contrast,
 * because the two grounds are the same colour. It is a Button rather than the
 * Rectangle-and-MouseArea used there so that zoom in and zoom out keep the
 * auto-repeat they had as text buttons: on a panel this is held down, not
 * clicked thirty times.
 */
Button {
    id: control

    property url iconSource

    /* Recolours the glyph. Left clear, the SVG draws in its own colours.
     * Set, it is flooded with this one - which is how an icon drawn in black
     * says "destructive" without a second copy of the file in red. */
    property color tint: "transparent"
    readonly property bool tinted: tint.a > 0

    /* The border, named apart from the tint rather than following it: a
     * button can be tinted for legibility without claiming to be
     * destructive, and only the one that throws something away should be
     * outlined in its own colour. */
    property color borderTint: Theme.separator

    implicitWidth: 60
    implicitHeight: 60
    // What sizes the icon: the content rect is the button less this, so 10
    // leaves the 40px glyph the profile editor draws.
    padding: 10
    focusPolicy: Qt.NoFocus
    hoverEnabled: true

    contentItem: Item {
        Image {
            id: glyph
            anchors.fill: parent
            source: control.iconSource
            fillMode: Image.PreserveAspectFit
            smooth: true
            // Rasterised at the size it is drawn at; an SVG scaled up from the
            // default source size is the one way these come out soft.
            sourceSize.width: control.availableWidth
            sourceSize.height: control.availableHeight
            // Hidden, not removed, when tinted: ColorOverlay reads it as its
            // source and needs it loaded.
            visible: !control.tinted
            opacity: control.enabled ? 1.0 : 0.4
        }

        ColorOverlay {
            anchors.fill: glyph
            source: glyph
            color: control.tint
            visible: control.tinted
            opacity: control.enabled ? 1.0 : 0.4
        }
    }

    background: Rectangle {
        radius: Theme.radius
        color: control.down ? Theme.selection
             : control.hovered ? Theme.hover
             : Theme.surfaceAlt
        border.width: Theme.hairline
        border.color: control.borderTint
    }
}
