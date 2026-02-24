import QtQuick 2.15

QtObject {
    property real width: 0
    property real height: 0
    property color backgroundColor: "#f5f5f5"

    function paint(ctx) {
        ctx.fillStyle = backgroundColor
        ctx.fillRect(0, 0, width, height)
    }
}
