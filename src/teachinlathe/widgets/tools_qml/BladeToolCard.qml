import QtQuick 2.15
import QtQuick.Layouts 1.15
import theme 1.0

// One blade - parting, grooving, trepanning - as a card, laid out as
// ThreadingToolCard is:
//
//       ┌──────────┐
//       │ [blade]  │  3 mm
//   #6  │          │  Left:    R0.5
//       │          │  Right:   R0.5
//       └──────────┘
//
// The drawing is as tall as the card, less a thin padding; the title is as
// far from the card's top as the drawing is: the blade's width, in its own
// colour. The corner radii are green, as a turning insert's nose radius is.
// Kept short: three cards to a row leave the text little room.
// Narrower than a turning card: three go to a row.
Rectangle {
    id: root

    property var view: null            // BladeToolView
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

    readonly property color radiusColor: Theme.success

    function radius(v) { return "R" + Number(Number(v).toFixed(3)) }

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
        BladeThumbnail {
            id: thumbnail
            view: root.view
            size: parent.height
            padding: 10
        }

        // ── The designation at the top, its figures at the bottom ───────
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
                text: !root.view ? ""
                      : "<font color='" + root.view.bodyColor + "'>"
                        + Number(root.view.bladeWidth.toFixed(3)) + " mm</font>"
                color: Theme.foreground
                font.pixelSize: Theme.fontLarge
                font.bold: true
            }

            // One column of figures, labels left-aligned and values
            // right-aligned, the values taking what width is left:
            //
            //   Left:    R0.5
            //   Right:   R0.5
            Rectangle {
                anchors.fill: figures
                visible: root.showGridBorders
                color: "transparent"
                border.width: 1
                border.color: Theme.danger
            }

            GridLayout {
                id: figures
                // titleTop above the card's bottom.
                anchors.bottom: parent.bottom
                anchors.bottomMargin: root.titleTop - root.padding
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
                    color: root.radiusColor
                    text: "Left:"
                }
                Figure {
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignRight
                    color: root.radiusColor
                    text: root.view ? root.radius(root.view.leftRadius) : ""
                }

                Figure {
                    color: root.radiusColor
                    text: "Right:"
                }
                Figure {
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignRight
                    color: root.radiusColor
                    text: root.view ? root.radius(root.view.rightRadius) : ""
                }
            }
        }
    }
}
