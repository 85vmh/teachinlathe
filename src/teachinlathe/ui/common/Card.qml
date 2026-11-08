import QtQuick
import theme

// A card: a white box, rounded and outlined, on the window's background. The
// panes and the lists of every screen are one - what goes in it is laid
// Theme.cardInset in (a list) or Theme.paneInset in (a pane's content).
Rectangle {
    color: Theme.surface
    radius: Theme.radius
    border.color: Theme.outline
    border.width: Theme.hairline
}
