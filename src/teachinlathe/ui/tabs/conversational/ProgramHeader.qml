import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import common

Rectangle {
    id: root

    property bool selected: false
    property int  datum: 1               // the work offset's P number: 1 is G54 ... 6 is G59
    // as the operations' rows: their font, their "[#NN]" and gap, their margin
    property int  itemFontSize: 16
    property int  colDelW: 100           // the G54 sits centred half of this in from the right

    signal clicked()

    width: parent ? parent.width : 400
    height: Theme.rowHeight
    radius: 0
    color: tap.pressed ? Theme.accentSoft
         : selected ? Theme.selection : hover.hovered ? Theme.hover : Theme.surface
    border.width: selected ? 2 : Theme.hairline
    border.color: selected ? Theme.accent : Theme.outlineStrong

    component Part: Label {
        font.pixelSize: root.itemFontSize
        color: Theme.foreground
    }

    Part {
        anchors.left: parent.left
        anchors.leftMargin: 10
        anchors.verticalCenter: parent.verticalCenter
        text: "[#00]    Program Header"
    }

    // the work coordinate system - the origin symbol and its G code in bold -
    // near the right edge
    RowLayout {
        anchors.horizontalCenter: parent.right
        anchors.horizontalCenterOffset: -root.colDelW / 2 - 24
        anchors.verticalCenter: parent.verticalCenter
        spacing: 0

        Image {
            source: Images.url("set_datum.svg")
            Layout.preferredWidth: 20
            Layout.preferredHeight: 20
            sourceSize.width: 20
            sourceSize.height: 20
            fillMode: Image.PreserveAspectFit
            smooth: true
        }
        Part { text: " G" + (53 + root.datum); font.bold: true }
    }

    Canvas {
        anchors.right: parent.right
        anchors.rightMargin: 12
        anchors.verticalCenter: parent.verticalCenter
        width: 12
        height: 20

        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            ctx.strokeStyle = Theme.accentStrong
            ctx.lineWidth = 2
            ctx.lineCap = "round"
            ctx.lineJoin = "round"
            ctx.beginPath()
            ctx.moveTo(3, 3)
            ctx.lineTo(10, height / 2)
            ctx.lineTo(3, height - 3)
            ctx.stroke()
        }
    }

    HoverHandler {
        id: hover
        cursorShape: Qt.PointingHandCursor
    }

    TapHandler {
        id: tap
        onTapped: root.clicked()
    }
}
