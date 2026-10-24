// GroovePointTag.qml — a groove point's name laid over the profile canvas
// ("P1 XZ", "P2 X"), an arrow from the point on the profile to it, in the
// point's colour (points.js).
import QtQuick
import QtQuick.Controls
import theme
import tabs.conversational
import "points.js" as Points

CanvasBox {
    id: root

    property int    point: 1
    property string axes: "X"

    accent: Points.color(point)

    Label {
        text: Points.name(root.point, root.axes)
        textFormat: Text.RichText
        color: root.accent
        font.pixelSize: Points.fontSize
    }
}
