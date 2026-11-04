import QtQuick
import theme

QtObject {
    property real width: 0
    property real height: 0
    property color backgroundColor: Theme.surfaceSunken

    function paint(ctx) {
        ctx.fillStyle = backgroundColor
        ctx.fillRect(0, 0, width, height)
    }
}
