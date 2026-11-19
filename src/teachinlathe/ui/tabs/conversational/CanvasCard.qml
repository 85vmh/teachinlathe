// CanvasCard.qml — the box an operation's details draw their canvas in: a
// card on the window's background, what is put in it Theme.canvasBoxPadding
// in from its outline (the canvas anchors.fill: parent).
import QtQuick
import theme
import common

Card {
    default property alias content: body.data

    Item {
        id: body
        anchors.fill: parent
        anchors.margins: Theme.canvasBoxPadding
    }
}
