import QtQuick 2.15
import QtQuick.Controls 2.15
import Qt5Compat.GraphicalEffects
import theme 1.0
import "ToolTitles.js" as ToolTitles

// The tool holders, two to a row, each:
//
//        ┌──────────────────────────────┐    Offsets
//        │ ┌─────────┐ Turning Tool #1  │ X:  123.123
//   H1   │ │thumbnail│ CCMT 060204      │ Z:  Not set
//        │ │         │ the comment      │
//        │ └─────────┘              [🗑] │
//        └──────────────────────────────┘
//
// The box is as tall as a cutting tool's card, its thumbnail the card's.
// Tapping it shows the tool in the cutting-tool list. An empty holder's box
// reads "No tool mounted - Tap to mount a tool"; tapping it asks for the
// tool to mount, which is then picked in the cutting-tool list
// (selectingHolderId says which holder is waiting). The offsets are Manual
// Turning's column: "Not set", orange, until touched off.
ToolLibraryPane {
    id: root

    property var model: null
    //: The holder waiting for a cutting tool to be picked, 0 when none is.
    property int selectingHolderId: 0

    signal mountRequested(int holderId)
    signal unmountRequested(int holderId)
    signal toolRevealRequested(int toolId)
    signal addRequested()

    //: As a cutting tool's card: its thumbnail, the space round what is on
    //: it, and so its height.
    readonly property int thumbnailSize: 120
    readonly property int boxPadding: 8
    readonly property int boxHeight: thumbnailSize + 2 * boxPadding
    readonly property int perRow: 2
    //: Above and below the box, inside the holder's card.
    readonly property int cardPadding: 4

    // The holder numbers' column: as wide as the widest, "H99".
    TextMetrics {
        id: holderNoMetrics
        text: "H99"
        font.pixelSize: Theme.fontLarge
        font.bold: true
    }
    //: The offsets' column, right of the box - as Manual Turning's.
    readonly property int offsetsWidth: 100

    title: "Tool Holders"

    // The cutting tools' categories' "+", lined up with the boxes' right
    // edge as theirs is with the list's: a new holder, numbered after the
    // last.
    headerActionsRightMargin: Theme.spacingSmall + Theme.spacing
    headerActions: [
        Rectangle {
            width: Theme.buttonHeight
            height: Theme.buttonHeight
            radius: Theme.radius
            color: addArea.pressed ? Theme.accentSoft : "transparent"
            border.width: Theme.hairline
            border.color: addArea.pressed ? Theme.accentBorder : Theme.outlineStrong

            Text {
                anchors.centerIn: parent
                text: "+"
                color: Theme.foregroundMuted
                font.pixelSize: Theme.fontTitle
                font.bold: true
            }

            MouseArea {
                id: addArea
                anchors.fill: parent
                onClicked: root.addRequested()
            }
        }
    ]

    Flickable {
        id: flick
        anchors.fill: parent
        anchors.margins: Theme.spacingSmall
        contentHeight: holders.height
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar {}

        Flow {
            id: holders
            width: flick.width
            spacing: Theme.spacingSmall

            // Whole pixels: a half one at the right edge is clipped off.
            readonly property real itemWidth: Math.floor((width - (root.perRow - 1) * spacing) / root.perRow)

            Repeater {
                model: root.model

                delegate: Rectangle {
                    id: holder
                    width: holders.itemWidth
                    height: content.implicitHeight + 2 * root.cardPadding
                    radius: Theme.radius
                    color: Theme.surface
                    border.color: Theme.outline
                    border.width: Theme.hairline

                    // Read here: inside the Loader below, `model` is not this one.
                    readonly property int holderId: model.holderId
                    readonly property int toolId: model.toolId
                    readonly property bool selecting: root.selectingHolderId === model.holderId

                    Column {
                        id: content
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.leftMargin: Theme.spacing
                        anchors.rightMargin: Theme.spacing
                        anchors.topMargin: root.cardPadding
                        spacing: Theme.spacingSmall

                        Row {
                            width: parent.width
                            spacing: Theme.spacing

                            // As wide as "H99" whatever the number, centred
                            // in it, so every box starts at the same place.
                            Text {
                                id: holderLabel
                                anchors.verticalCenter: toolBox.verticalCenter
                                width: holderNoMetrics.width
                                horizontalAlignment: Text.AlignHCenter
                                text: "H" + model.holderId
                                color: Theme.foreground
                                font.pixelSize: Theme.fontLarge
                                font.bold: true
                            }

                            // ── The mounted tool ────────────────────────
                            Rectangle {
                                id: toolBox
                                width: parent.width - holderLabel.width
                                       - offsets.width - 2 * parent.spacing
                                height: root.boxHeight
                                radius: Theme.radius
                                color: boxArea.pressed ? Theme.hover : Theme.surfaceAlt
                                border.width: holder.selecting ? 2 : Theme.hairline
                                border.color: holder.selecting ? Theme.accent : Theme.outline

                                readonly property bool hasTool: model.toolId !== 0

                                // Under the delete button, which takes its own taps.
                                MouseArea {
                                    id: boxArea
                                    anchors.fill: parent
                                    onClicked: {
                                        if (toolBox.hasTool)
                                            root.toolRevealRequested(holder.toolId)
                                        else
                                            root.mountRequested(holder.holderId)
                                    }
                                }

                                // ── With a tool: the thumbnail, then its
                                // name and comment; the button that takes
                                // it out in the corner ──────────────────
                                Loader {
                                    id: thumbnail
                                    visible: toolBox.hasTool
                                    x: root.boxPadding
                                    y: root.boxPadding
                                    width: root.thumbnailSize
                                    height: root.thumbnailSize
                                    readonly property var toolView: model.toolView
                                    sourceComponent: toolBox.hasTool ? root.thumbnails[model.toolCard] || null : null
                                    onLoaded: item.view = Qt.binding(function() { return toolView })
                                }

                                // In place of the thumbnail's frame: a line
                                // between it and the text.
                                Rectangle {
                                    id: thumbnailSeparator
                                    visible: toolBox.hasTool
                                    x: thumbnail.x + thumbnail.width + root.boxPadding
                                    anchors.top: parent.top
                                    anchors.bottom: parent.bottom
                                    anchors.margins: root.boxPadding
                                    width: Theme.hairline
                                    color: Theme.separator
                                }

                                Column {
                                    id: toolText
                                    visible: toolBox.hasTool
                                    anchors.left: thumbnailSeparator.right
                                    anchors.right: parent.right
                                    anchors.top: parent.top
                                    anchors.leftMargin: root.boxPadding
                                    anchors.rightMargin: root.boxPadding
                                    anchors.topMargin: root.boxPadding
                                    spacing: 4

                                    // What it is and its number, bold, then its
                                    // designation, plain.
                                    // Too long, the middle goes: the start and
                                    // the number stay.
                                    Text {
                                        width: parent.width
                                        elide: Text.ElideMiddle
                                        text: !toolBox.hasTool ? ""
                                              : ToolTitles.kindTitle(model.toolCard, model.toolView)
                                                + " #" + model.toolId
                                        color: Theme.foreground
                                        font.pixelSize: Theme.fontBody
                                        font.bold: true
                                    }

                                    Text {
                                        width: parent.width
                                        elide: Text.ElideMiddle
                                        textFormat: Text.StyledText
                                        text: !toolBox.hasTool ? ""
                                              : ToolTitles.richTitle(model.toolCard, model.toolView, Theme)
                                        color: Theme.foreground
                                        font.pixelSize: Theme.fontBody
                                    }

                                    Text {
                                        width: parent.width
                                        visible: text !== ""
                                        text: model.toolComment
                                        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                        maximumLineCount: 2
                                        elide: Text.ElideRight
                                        color: Theme.foregroundSubtle
                                        font.pixelSize: Theme.fontSmall
                                    }
                                }

                                Rectangle {
                                    id: deleteButton
                                    visible: toolBox.hasTool
                                    anchors.right: parent.right
                                    anchors.bottom: parent.bottom
                                    anchors.margins: root.boxPadding
                                    width: Theme.buttonHeight
                                    height: Theme.buttonHeight
                                    radius: Theme.radius
                                    color: deleteArea.pressed ? Theme.dangerSoft : Theme.surface
                                    border.width: Theme.hairline
                                    border.color: Theme.danger

                                    Image {
                                        id: deleteGlyph
                                        anchors.centerIn: parent
                                        width: Math.round(parent.width * 0.6)
                                        height: width
                                        source: "icons/delete.svg"
                                        sourceSize.width: width
                                        sourceSize.height: height
                                        // Hidden, not removed: ColorOverlay reads it as its source.
                                        visible: false
                                    }

                                    ColorOverlay {
                                        anchors.fill: deleteGlyph
                                        source: deleteGlyph
                                        color: Theme.danger
                                    }

                                    MouseArea {
                                        id: deleteArea
                                        anchors.fill: parent
                                        onClicked: root.unmountRequested(holder.holderId)
                                    }
                                }

                                // ── Empty ───────────────────────────────
                                Column {
                                    visible: !toolBox.hasTool
                                    anchors.centerIn: parent
                                    spacing: 4

                                    Text {
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        text: holder.selecting ? "Select the tool to mount" : "No tool mounted"
                                        color: holder.selecting ? Theme.accentStrong : Theme.foreground
                                        font.pixelSize: Theme.fontBody
                                        font.bold: true
                                    }
                                    Text {
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        visible: !holder.selecting
                                        text: "Tap to mount a tool"
                                        color: Theme.foregroundSubtle
                                        font.pixelSize: Theme.fontSmall
                                    }
                                }
                            }

                            // ── Offsets, right of the box, as Manual
                            // Turning shows them ────────────────────────
                            OffsetsColumn {
                                id: offsets
                                width: root.offsetsWidth
                                y: root.boxPadding
                                xOffset: model.xOffset
                                zOffset: model.zOffset
                            }
                        }
                    }
                }
            }
        }
    }

    Component { id: insertThumbnail; InsertThumbnail { size: root.thumbnailSize; padding: 10; framed: false } }
    Component { id: threadingThumbnail; ThreadingInsertThumbnail { size: root.thumbnailSize; padding: 10; framed: false } }
    Component { id: bladeThumbnail; BladeThumbnail { size: root.thumbnailSize; padding: 10; framed: false } }
    Component { id: drillThumbnail; DrillThumbnail { size: root.thumbnailSize; padding: 10; framed: false } }
    Component { id: reamerThumbnail; ReamerThumbnail { size: root.thumbnailSize; padding: 10; framed: false } }
    Component { id: tapThumbnail; TapThumbnail { size: root.thumbnailSize; padding: 10; framed: false } }

    // The thumbnail for each of the holder model's `toolCard` values; a
    // "summary" tool has none.
    readonly property var thumbnails: ({
        "turning": insertThumbnail,
        "threading": threadingThumbnail,
        "blade": bladeThumbnail,
        "drilling": drillThumbnail,
        "reaming": reamerThumbnail,
        "tapping": tapThumbnail
    })
}
