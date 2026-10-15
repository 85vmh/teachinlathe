// CanvasBox.qml — a titled box laid over the profile canvas, which an
// overlay on the canvas points an arrow to.
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import theme 1.0
import "profile_canvas/arrow.js" as Arrow

Rectangle {
    id: root

    property string title: ""
    property color accent: Theme.accentStrong
    default property alias content: body.data

    // where on the canvas the box sits, for the arrow pointing to it
    readonly property var rect: ({ x: x, y: y, width: width, height: height })

    implicitWidth: column.implicitWidth + 2 * Theme.spacing
    implicitHeight: column.implicitHeight + 2 * Theme.spacing
    width: implicitWidth
    height: implicitHeight
    radius: Theme.radius
    color: Theme.surface
    border.color: accent
    border.width: Arrow.lineWidth   // as thick as the arrows pointing to it

    // keeps taps and drags on the box from reaching the canvas under it,
    // which would pan it or fit it to the screen
    MouseArea { anchors.fill: parent }

    ColumnLayout {
        id: column
        anchors.fill: parent
        anchors.margins: Theme.spacing
        spacing: Theme.spacingSmall

        Label {
            visible: root.title !== ""
            text: root.title
            font.pixelSize: Theme.fontBody
            font.bold: true
            color: root.accent
        }

        ColumnLayout {
            id: body
            spacing: Theme.spacingSmall
        }
    }
}
