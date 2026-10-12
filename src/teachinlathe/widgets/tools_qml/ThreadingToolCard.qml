import QtQuick 2.15
import QtQuick.Layouts 1.15
import theme 1.0

// One threading tool, as a card - TurningToolCard's layout:
//
//       ┌──────────┐
//       │ [insert] │  16ER 1.5
//   #8  │          │  Type:   External
//       │          │  Pitch:    1.5 mm
//       └──────────┘
//
// The drawing is as tall as the card, less a thin padding; the designation
// is as far from the card's top as the drawing is. The designation is
// coloured by part: size in the insert's own colour, the insert blue, the
// pitch green. The type shares the insert's blue and the pitch its green.
// Narrower than a turning card: three go to a row.
Rectangle {
    id: root

    property var view: null            // ThreadingToolView
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

    readonly property color familyColor: Theme.accentStrong
    readonly property color pitchColor: Theme.success

    function mm(v) { return Number(Number(v).toFixed(3)) + " mm" }

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
        ThreadingInsertThumbnail {
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
                      : "<font color='" + root.view.insertBodyColor + "'>" + root.view.sizeCode + "</font>"
                        + "<font color='" + root.familyColor + "'>" + root.view.hand + "</font> "
                        + "<font color='" + root.pitchColor + "'>" + root.view.pitchText + "</font>"
                color: Theme.foreground
                font.pixelSize: Theme.fontLarge
                font.bold: true
            }

            // One column of figures, labels left-aligned and values
            // right-aligned, the values taking what width is left:
            //
            //   Type:   External
            //   Pitch:    1.5 mm
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
                    color: root.familyColor
                    text: "Type:"
                }
                Figure {
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignRight
                    color: root.familyColor
                    text: root.view ? root.view.kind : ""
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
                    text: root.view ? root.mm(root.view.pitch) : ""
                }
            }
        }
    }
}
