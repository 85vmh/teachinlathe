import QtQuick
import QtQuick.Layouts
import theme
import "ToolTitles.js" as ToolTitles

// One turning tool, as a card:
//
//       ┌──────────┐
//       │ [insert] │  CCMT 060204
//   #1  │          │  Tip:     80°      Radius:  0.4 mm
//       │          │  Front:   95°
//       │          │  Back:     5°
//       └──────────┘
//
// The drawing is as tall as the card, less a thin padding; the designation
// is as far from the card's top as the drawing is. The ISO designation is
// coloured by part: family blue, size in the insert's own colour, the
// thickness plain, the nose radius green. The tip angle shares the family's
// blue and the tip radius the nose radius's green.
Rectangle {
    id: root

    property var view: null            // TurningToolView
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
    //: Experiment: the figures grid's four columns all one width.
    property bool equalColumns: true

    readonly property color familyColor: Theme.accentStrong
    readonly property color radiusColor: Theme.success

    function deg(v) { return Number(Number(v).toFixed(2)) + "°" }
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
        InsertThumbnail {
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
                text: ToolTitles.richTitle("turning", root.view, Theme)
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

            // Angles in the first two columns, the tip radius in the last
            // two, a rule between them; labels left-aligned, values right-aligned. The
            // last column takes what width is left, so the grid spans the card.
            //
            //   Tip:     80°  │  Radius:  0.4 mm
            //   Front:   95°  │
            //   Back:     5°  │
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
                columns: 4
                rowSpacing: 8
                columnSpacing: 12

                // One column's width when they are all equal: what is left
                // after the gaps.
                readonly property real equalWidth:
                    (width - 3 * columnSpacing) / columns

                component Figure: Text {
                    color: Theme.foreground
                    font.pixelSize: Theme.fontBody
                    Layout.preferredWidth: root.equalColumns ? figures.equalWidth : -1
                    Layout.maximumWidth: root.equalColumns ? figures.equalWidth : Number.POSITIVE_INFINITY

                    Rectangle {
                        anchors.fill: parent
                        visible: root.showGridBorders
                        color: "transparent"
                        border.width: 1
                        border.color: Theme.accent
                    }
                }

                // A round insert has a diameter where the others have a
                // corner.
                Figure {
                    color: root.familyColor
                    text: !root.view ? "" : root.view.isRound ? "Round insert" : "Tip:"
                }
                Figure {
                    Layout.alignment: Qt.AlignRight
                    horizontalAlignment: Text.AlignRight
                    color: root.familyColor
                    text: !root.view || root.view.isRound ? "" : root.deg(root.view.cornerAngle)
                }
                Figure {
                    id: radiusLabel
                    color: root.radiusColor
                    text: !root.view ? "" : root.view.isRound ? "Ø" : "Radius:"
                }
                Figure {
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignRight
                    color: root.radiusColor
                    text: !root.view ? ""
                          : root.mm(root.view.isRound ? root.view.ic : root.view.noseRadiusMm)
                }

                Figure { text: "Front:" }
                Figure {
                    Layout.alignment: Qt.AlignRight
                    horizontalAlignment: Text.AlignRight
                    text: root.view ? root.deg(root.view.frontAngle) : ""
                }
                Figure {}
                Figure {}

                Figure { text: "Back:" }
                Figure {
                    Layout.alignment: Qt.AlignRight
                    horizontalAlignment: Text.AlignRight
                    text: root.view ? root.deg(root.view.backAngle) : ""
                }
                Figure {}
                Figure {}
            }

            // The rule between the angles and the radius, in the middle of
            // the gap - drawn over the grid, so every gap stays one width.
            Rectangle {
                x: figures.x + radiusLabel.x - figures.columnSpacing / 2
                anchors.top: figures.top
                anchors.bottom: figures.bottom
                width: Theme.hairline
                color: Theme.outline
            }
        }
    }
}
