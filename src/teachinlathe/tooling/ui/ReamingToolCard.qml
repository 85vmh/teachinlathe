import QtQuick 2.15
import theme 1.0
import "ToolTitles.js" as ToolTitles

// One reamer as a card, laid out as DrillingToolCard is:
//
//       ┌──────────┐
//       │ [reamer] │  Ø10 mm
//  #13  │          │
//       │          │
//       └──────────┘
//
// The drawing is as tall as the card, less a thin padding; the title is as
// far from the card's top as the drawing is: the reamer's diameter, in its
// own colour.
// Kept short: three cards to a row leave the text little room.
// Narrower than a turning card: three go to a row.
Rectangle {
    id: root

    property var view: null            // ReamingToolView
    signal tapped()

    //: Height of the insert drawing, in pixels; the card is this plus its padding.
    property real thumbnailSize: 120
    //: Space between the card's edge and what is on it, in pixels.
    property real padding: 8
    //: Distance from the card's top to the designation's, in pixels: the
    //: same as the drawing's.
    property real titleTop: padding

    implicitHeight: Math.max(thumbnailSize + 2 * padding,
                             2 * titleTop + title.implicitHeight)

    radius: Theme.radius
    color: area.pressed ? Theme.hover : Theme.surface
    border.width: Theme.hairline
    border.color: Theme.outline

    MouseArea {
        id: area
        anchors.fill: parent
        onClicked: root.tapped()
    }

    Row {
        anchors.fill: parent
        anchors.margins: root.padding
        spacing: Theme.spacingSmall

        // ── The tool's id, before its drawing ───────────────────────────
        // As wide as a two-digit id whatever its own, so "#1" and "#13"
        // leave the drawings at the same place on every card.
        Text {
            id: toolId
            anchors.verticalCenter: parent.verticalCenter
            width: Math.max(implicitWidth, idWidth.advanceWidth)
            text: root.view ? "#" + root.view.cuttingToolId : ""
            color: Theme.foreground
            font.pixelSize: Theme.fontBody
            font.bold: true

            TextMetrics {
                id: idWidth
                font: toolId.font
                text: "#00"
            }
        }

        // ── The drawing, the card's full height ─────────────────────────
        ReamerThumbnail {
            id: thumbnail
            view: root.view
            size: parent.height
            padding: 10
        }

        // ── The designation at the top ──────────────────────────────────
        Item {
            width: parent.width - toolId.width - thumbnail.width - 2 * parent.spacing
            height: parent.height

            Text {
                id: title
                // titleTop below the card's top.
                anchors.top: parent.top
                anchors.topMargin: root.titleTop - root.padding
                width: parent.width
                elide: Text.ElideRight
                textFormat: Text.StyledText
                text: ToolTitles.richTitle("reaming", root.view, Theme)
                color: Theme.foreground
                font.pixelSize: Theme.fontLarge
                font.bold: true
            }

            // ── The spindle direction, in the bottom right corner ───────
            SpindleDirectionIcon {
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                clockwise: root.view ? root.view.clockwise : null
            }
        }
    }
}
