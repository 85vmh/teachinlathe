import QtQuick 2.15
import QtQuick.Controls 2.15
import theme 1.0
import common 1.0
import "ToolTitles.js" as ToolTitles
import "../../conversational/ui"

// The tool holders, two to a row, each:
//
//        ┌──────────────────────────────┐    Offsets
//        │ ┌─────────┐ Turning Tool #1  │ X:  123.123
//   H1   │ │thumbnail│ CCMT 060204      │ Z:  Not set
//        │ │         │ the comment      │
//        │ └─────────┘                  │
//        └──────────────────────────────┘
//
// The box is as tall as a cutting tool's card, its thumbnail the card's.
// Tapping it shows the tool in the cutting-tool list. An empty holder's box
// reads "No tool mounted - Tap to mount a tool"; tapping it asks for the
// tool to mount, which is then picked in the cutting-tool list
// (selectingHolderId says which holder is waiting). The offsets are Manual
// Turning's column: "Not set", orange, until touched off.
//
// Swiped left (see SwipeRow), a holder with a tool slides its box over a
// Delete that unmounts the tool; an empty one slides the whole card over a
// Delete that removes the holder.
ToolLibraryPane {
    id: root

    property var model: null
    //: The holder waiting for a cutting tool to be picked, 0 when none is.
    property int selectingHolderId: 0

    signal mountRequested(int holderId)
    signal unmountRequested(int holderId)
    signal toolRevealRequested(int toolId)
    signal addRequested()
    signal deleteRequested(int holderId)

    //: Off while a holder waits for a tool.
    property bool swipeEnabled: true
    //: The holder card or tool box swiped open to its Delete, or null.
    property var openSwipeRow: null

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
            color: addArea.pressed ? Theme.primaryPressed : Theme.primary
            border.width: Theme.hairline
            border.color: addArea.pressed ? Theme.primaryPressed : Theme.primary

            Text {
                anchors.centerIn: parent
                text: "+"
                color: Theme.foregroundOnAccent
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
        onMovementStarted: root.openSwipeRow = null

        Flow {
            id: holders
            width: flick.width
            spacing: Theme.spacingSmall

            // Whole pixels: a half one at the right edge is clipped off.
            readonly property real itemWidth: Math.floor((width - (root.perRow - 1) * spacing) / root.perRow)

            Repeater {
                model: root.model

                delegate: SwipeRow {
                    id: holder
                    width: holders.itemWidth
                    height: content.implicitHeight + 2 * root.cardPadding
                    contentRadius: Theme.radius
                    contentColor: Theme.surface
                    contentBorderColor: Theme.outline
                    contentBorderWidth: Theme.hairline

                    // Read here: inside the Loader below, `model` is not this one.
                    readonly property int holderId: model.holderId
                    readonly property int toolId: model.toolId
                    readonly property bool selecting: root.selectingHolderId === model.holderId

                    // With a tool, a swipe anywhere on the card moves the
                    // tool's box: the tool goes before the holder can.
                    swipeTarget: toolBox.hasTool ? toolBox : null
                    swipeEnabled: root.swipeEnabled
                    duplicateEnabled: false
                    actionGap: 4
                    actionRadius: Theme.radius
                    swipeSide: root.openSwipeRow === holder ? 1 : 0
                    onSwipeOpened: root.openSwipeRow = holder
                    onSwipeClosed: if (root.openSwipeRow === holder) root.openSwipeRow = null
                    onDeleteRequested: {
                        root.openSwipeRow = null
                        root.deleteRequested(holder.holderId)
                    }

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
                            // Its Delete unmounts the tool. Swiped by the
                            // holder's card, which takes the drags.
                            SwipeRow {
                                id: toolBox
                                width: parent.width - holderLabel.width
                                       - offsets.width - 2 * parent.spacing
                                height: root.boxHeight
                                contentRadius: Theme.radius
                                contentColor: boxArea.pressed ? Theme.hover : Theme.surfaceAlt
                                contentBorderWidth: holder.selecting ? 2 : Theme.hairline
                                contentBorderColor: holder.selecting ? Theme.accent : Theme.outline

                                readonly property bool hasTool: model.toolId !== 0

                                swipeEnabled: false
                                duplicateEnabled: false
                                actionGap: 4
                                actionRadius: Theme.radius
                                swipeSide: root.openSwipeRow === toolBox ? 1 : 0
                                onSwipeOpened: root.openSwipeRow = toolBox
                                onSwipeClosed: if (root.openSwipeRow === toolBox) root.openSwipeRow = null
                                onDeleteRequested: {
                                    root.openSwipeRow = null
                                    root.unmountRequested(holder.holderId)
                                }

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
                                // name and comment ──────────────────────
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

    ScrollFades {
        anchors.fill: flick
        flickable: flick
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
