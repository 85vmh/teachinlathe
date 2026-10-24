// CanvasBox.qml — a titled box laid over the profile canvas, which an
// overlay on the canvas points an arrow to.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
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

    // tapped anywhere but on a control in it
    signal clicked()

    // How long each flash is on, and off between them, in ms, and how many
    // times it flashes: as the Cutting Tools list flashes the tool it
    // scrolls to (CuttingToolsPane).
    readonly property int flashDuration: 100
    readonly property int flashes: 2
    property bool _flashOn: false

    // flashed, to show which box something tapped elsewhere is for
    function flash() {
        flashTimer.ticks = 0
        _flashOn = true
        flashTimer.restart()
    }

    // keeps taps and drags on the box from reaching the canvas under it,
    // which would pan it or fit it to the screen
    MouseArea { anchors.fill: parent; onClicked: root.clicked() }

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

    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: root.accent
        opacity: root._flashOn ? 0.25 : 0
        Behavior on opacity { NumberAnimation { duration: 50 } }
    }

    // On, off, on, off: each tick turns the flash the other way.
    Timer {
        id: flashTimer
        property int ticks: 0
        interval: root.flashDuration
        repeat: true
        onTriggered: {
            ticks += 1
            root._flashOn = ticks % 2 === 0
            if (ticks >= 2 * root.flashes - 1)
                stop()
        }
    }
}
