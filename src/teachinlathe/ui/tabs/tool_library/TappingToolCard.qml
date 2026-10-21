import QtQuick
import QtQuick.Layouts
import theme
import "ToolTitles.js" as ToolTitles

// One tap as a card, laid out as DrillingToolCard is:
//
//       ┌──────────┐
//       │  [tap]   │  M10x1.5
//  #12  │          │  Pitch:   1.5
//       │          │  Thread:   RH
//       └──────────┘
//
// The drawing is as tall as the card, less a thin padding; the title is as
// far from the card's top as the drawing is: the thread's designation, in
// the tap's own colour. The pitch is green, as a threading insert's is.
// Kept short: three cards to a row leave the text little room.
// Narrower than a turning card: three go to a row.
Rectangle {
    id: root

    property var view: null            // TappingToolView
    signal tapped()

    //: Height of the insert drawing, in pixels; the card is this plus its padding.
    property real thumbnailSize: 120
    //: Space between the card's edge and what is on it, in pixels.
    property real padding: 8
    //: Distance from the card's top to the designation's, and from the
    //: card's bottom to the figures', in pixels: the same as the drawing's.
    property real titleTop: padding

    //: Debug: outline the figures grid and each of its cells.
    property bool showGridBorders: false

    readonly property color pitchColor: Theme.success

    implicitHeight: Math.max(thumbnailSize + 2 * padding,
                             2 * titleTop + title.implicitHeight + Theme.spacingSmall
                             + figures.implicitHeight)

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
        // leave the figures the same width and every card's grid lines up.
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
        TapThumbnail {
            id: thumbnail
            view: root.view
            size: parent.height
            padding: 10
        }

        // ── The designation, its figures under it ───────────────────────
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
                text: ToolTitles.richTitle("tapping", root.view, Theme)
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

            // One column of figures, labels left-aligned and values
            // right-aligned, the values taking what width is left:
            //
            //   Pitch:   1.5
            //   Thread:   RH
            Rectangle {
                anchors.fill: figures
                visible: root.showGridBorders
                color: "transparent"
                border.width: 1
                border.color: Theme.danger
            }

            GridLayout {
                id: figures
                // Under the title, leaving the bottom right corner to the
                // spindle direction.
                anchors.top: title.bottom
                anchors.topMargin: Theme.spacingSmall
                width: parent.width
                columns: 2
                rowSpacing: 8
                columnSpacing: 12

                component Figure: Text {
                    color: Theme.foreground
                    font.pixelSize: Theme.fontBody

                    Rectangle {
                        anchors.fill: parent
                        visible: root.showGridBorders
                        color: "transparent"
                        border.width: 1
                        border.color: Theme.accent
                    }
                }

                Figure {
                    color: root.pitchColor
                    text: "Pitch:"
                }
                Figure {
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignRight
                    color: root.pitchColor
                    text: root.view ? String(Number(root.view.pitch.toFixed(3))) : ""
                }

                Figure { text: "Thread:" }
                Figure {
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignRight
                    text: root.view ? (root.view.rightHand ? "RH" : "LH") : ""
                }
            }
        }
    }
}
