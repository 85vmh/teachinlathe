import QtQuick
import QtQuick.Controls
import theme

// A card with its title inside it: a rounded, outlined box whose top is a
// band on the lighter grey, the title in it, a line under it, and the
// content on white below. A GroupBox, so what was one is one of these by
// its type's name alone - its title, its content, its label if it brings its
// own (a check box, say) all stay as they were.
GroupBox {
    id: control

    //: the title band's height
    property int bandHeight: 32

    font.pixelSize: Theme.fontBody
    padding: Theme.paneInset
    topPadding: bandHeight + Theme.paneInset

    label: Text {
        x: Theme.paneInset
        width: control.availableWidth
        height: control.bandHeight
        text: control.title
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
        color: Theme.foregroundStrong
        font.pixelSize: Theme.fontSmall
        font.bold: true
    }

    background: Item {
        Rectangle {
            anchors.fill: parent
            radius: Theme.radiusLarge
            color: Theme.surface
        }

        // the band: rounded at the card's corners only - a square strip
        // covers its rounded bottom
        Rectangle {
            width: parent.width
            height: control.bandHeight
            radius: Theme.radiusLarge
            color: Theme.surfaceAlt
        }
        Rectangle {
            y: control.bandHeight - Theme.radiusLarge
            width: parent.width
            height: Theme.radiusLarge
            color: Theme.surfaceAlt
        }
        Rectangle {
            y: control.bandHeight
            width: parent.width
            height: Theme.hairline
            color: Theme.separator
        }

        // the outline last, over the band's corners
        Rectangle {
            anchors.fill: parent
            radius: Theme.radiusLarge
            color: "transparent"
            border.color: Theme.outline
            border.width: Theme.hairline
        }
    }
}
