import QtQuick 2.15
import QtQuick.Controls 2.15
import Qt5Compat.GraphicalEffects
import theme 1.0
import common 1.0
import "../../conversational/ui"

// The cutting tools, grouped by type. Each group's header folds the group
// and has a "+" for adding a tool of that type; under it the group's tools
// are cards, two to a row, filling left to right and then down. Tapping a
// card opens the tool (or, while a holder waits for one, mounts it). The
// title bar's buttons unfold or fold every group. A tool mounted in a
// holder has its card outlined in blue. A card swiped left shows Delete
// (see SwipeRow).
ToolLibraryPane {
    id: root

    property var model: null

    signal addRequested(string toolType)
    signal toolTapped(int toolId)
    signal deleteRequested(int toolId)

    //: Off while a holder waits for a tool, when a tap mounts it.
    property bool swipeEnabled: true
    //: The card swiped open to its Delete, or null.
    property var openSwipeRow: null

    //: How far the cards are set in from their category's header.
    readonly property int toolIndent: Theme.margin
    readonly property int cardSpacing: Theme.spacingSmall
    readonly property int summaryCardHeight: Theme.inputHeight
    readonly property var mountedToolIds: model ? model.mountedToolIds : []
    //: The tool flashed after revealTool() scrolled to it, 0 when none is.
    property int highlightedToolId: 0
    //: How long each flash is on, and off between them, in ms.
    readonly property int highlightDuration: 100
    //: How many times it flashes.
    readonly property int highlightFlashes: 2
    // The tool to flash once the scroll to it has finished.
    property int _pendingHighlightId: 0

    // Scroll to a tool's card - unfolding its category if it is folded -
    // and once there flash it.
    function revealTool(toolId) {
        if (!model)
            return
        var at = model.locate(toolId)
        if (at.length !== 3)
            return
        model.expand(at[2])
        // The unfolded category's cards are laid out on the next polish.
        Qt.callLater(_scrollToCard, at[0], at[1], toolId)
    }

    function _scrollToCard(row, position, toolId) {
        list.positionViewAtIndex(row, ListView.Contain)
        var category = list.itemAtIndex(row)
        if (!category)
            return
        category.layoutCards()
        var card = category.cardAt(position)
        if (!card)
            return
        // In the list's content, as contentY is: the card's middle in the
        // middle of the list, as far as the list goes.
        var cardY = category.y + category.cardsY + card.y
        var target = cardY - (list.height - card.height) / 2
        var top = list.originY
        var bottom = list.originY + Math.max(0, list.contentHeight - list.height)
        highlightTimer.stop()
        highlightedToolId = 0
        _pendingHighlightId = toolId
        scrollAnimation.to = Math.max(top, Math.min(bottom, target))
        scrollAnimation.restart()
    }

    NumberAnimation {
        id: scrollAnimation
        target: list
        property: "contentY"
        duration: 300
        easing.type: Easing.OutCubic
        onFinished: {
            highlightTimer.ticks = 0
            root.highlightedToolId = root._pendingHighlightId
            highlightTimer.restart()
        }
    }

    // On, off, on, off: each tick turns the highlight the other way.
    Timer {
        id: highlightTimer
        property int ticks: 0
        interval: root.highlightDuration
        repeat: true
        onTriggered: {
            ticks += 1
            root.highlightedToolId = ticks % 2 === 0 ? root._pendingHighlightId : 0
            if (ticks >= 2 * root.highlightFlashes - 1)
                stop()
        }
    }

    title: "Cutting Tools"

    // Collapse lines up with the categories' "+" below it: the list's
    // margin plus the "+"'s own from the header's edge.
    headerActionsRightMargin: Theme.spacingSmall + Theme.spacing
    headerActionsSpacing: 3 * Theme.spacingSmall
    headerActions: [
        HeaderButton {
            iconSource: Images.url("expand-vertical.svg")
            enabled: root.model ? !root.model.allExpanded : false
            onClicked: root.model.setAllExpanded(true)
        },
        HeaderButton {
            iconSource: Images.url("collapse-vertical.svg")
            enabled: root.model ? !root.model.allCollapsed : false
            onClicked: root.model.setAllExpanded(false)
        }
    ]

    // A button the size of a category's "+", outlined, with an icon flooded
    // muted grey. Faded, and deaf to
    // taps, while there is nothing for it to do.
    component HeaderButton: Rectangle {
        id: button

        property url iconSource
        signal clicked()

        width: Theme.buttonHeight
        height: Theme.buttonHeight
        radius: Theme.radius
        color: buttonArea.pressed ? Theme.accentSoft : "transparent"
        border.width: Theme.hairline
        border.color: buttonArea.pressed ? Theme.accentBorder : Theme.outlineStrong
        opacity: enabled ? 1.0 : 0.35

        Image {
            id: glyph
            anchors.centerIn: parent
            width: Math.round(parent.width * 0.6)
            height: width
            source: button.iconSource
            sourceSize.width: width
            sourceSize.height: height
            fillMode: Image.PreserveAspectFit
            smooth: true
            // Hidden, not removed: ColorOverlay reads it as its source.
            visible: false
        }

        ColorOverlay {
            anchors.fill: glyph
            source: glyph
            color: Theme.foregroundMuted
        }

        MouseArea {
            id: buttonArea
            anchors.fill: parent
            onClicked: button.clicked()
        }
    }

    ListView {
        id: list
        anchors.fill: parent
        anchors.margins: Theme.spacingSmall
        spacing: 4
        clip: true
        model: root.model
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar {}
        onMovementStarted: root.openSwipeRow = null

        delegate: Column {
            id: category
            width: ListView.view.width
            spacing: 4

            // Read here: inside the Repeater below, `model` is its own.
            readonly property string card: model.card
            readonly property var tools: model.tools
            readonly property real cardsY: cards.y

            function cardAt(position) { return cardRepeater.itemAt(position) }
            // Inside out: the cards, then this column round them, then the
            // list - else a category just unfolded still has its folded
            // height, and the list its old length, until the next frame
            function layoutCards() {
                cards.forceLayout()
                category.forceLayout()
                list.forceLayout()
            }

            // ── Category header ─────────────────────────────────────────
            Rectangle {
                width: parent.width
                height: Theme.rowHeight
                radius: Theme.radius
                color: headerArea.pressed ? Theme.hover : Theme.surface
                border.color: Theme.outline
                border.width: Theme.hairline

                MouseArea {
                    id: headerArea
                    anchors.fill: parent
                    onClicked: root.model.toggle(model.toolType)
                }

                Text {
                    id: chevron
                    anchors.left: parent.left
                    anchors.leftMargin: Theme.spacing
                    anchors.verticalCenter: parent.verticalCenter
                    width: 24
                    text: model.expanded ? "▾" : "▸"
                    color: Theme.foregroundMuted
                    font.pixelSize: Theme.fontLarge
                }

                Text {
                    anchors.left: chevron.right
                    anchors.right: addButton.left
                    anchors.leftMargin: Theme.spacingSmall
                    anchors.rightMargin: Theme.spacing
                    anchors.verticalCenter: parent.verticalCenter
                    text: model.label + "  (" + model.count
                          + (model.count === 1 ? " tool)" : " tools)")
                    elide: Text.ElideRight
                    color: Theme.foreground
                    font.pixelSize: Theme.fontBody
                    font.bold: true
                }

                Rectangle {
                    id: addButton
                    anchors.right: parent.right
                    anchors.rightMargin: Theme.spacing
                    anchors.verticalCenter: parent.verticalCenter
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
                        onClicked: root.addRequested(model.toolType)
                    }
                }
            }

            // ── The category's tools, two cards to a row (turning cards
            // and text lines; the other cards, being narrower, three) ──
            Flow {
                id: cards
                // Not `visible`, which also turns false while an editor
                // covers the list: the cards would be thrown away, the list
                // would shrink under its scroll, and the place would be lost.
                readonly property bool shown: model.expanded && model.count > 0
                visible: shown
                x: root.toolIndent
                width: parent.width - root.toolIndent
                spacing: root.cardSpacing

                readonly property int perRow: category.card === "turning"
                                              || category.card === "summary" ? 2 : 3
                readonly property real cardWidth: (width - (perRow - 1) * spacing) / perRow

                Repeater {
                    id: cardRepeater
                    model: cards.shown ? category.tools : []

                    delegate: SwipeRow {
                        id: swipeRow
                        readonly property var toolView: modelData
                        width: cards.cardWidth
                        height: card.height

                        duplicateEnabled: false
                        actionGap: 4
                        actionRadius: Theme.radius      // as the card's own corners
                        swipeEnabled: root.swipeEnabled
                        swipeSide: root.openSwipeRow === swipeRow ? 1 : 0
                        onSwipeOpened: root.openSwipeRow = swipeRow
                        onSwipeClosed: if (root.openSwipeRow === swipeRow) root.openSwipeRow = null
                        onDeleteRequested: {
                            root.openSwipeRow = null
                            root.deleteRequested(toolView.cuttingToolId)
                        }

                        Loader {
                            id: card
                            width: parent.width
                            // A full card is as tall as its content says.
                            height: item ? (category.card === "summary" ? root.summaryCardHeight
                                                                        : item.implicitHeight) : 0
                            sourceComponent: root.cards[category.card]
                            onLoaded: {
                                item.view = toolView
                                item.tapped.connect(function() { root.toolTapped(toolView.cuttingToolId) })
                            }
                        }

                        // Flashed when revealTool() scrolls to it.
                        Rectangle {
                            anchors.fill: card
                            radius: Theme.radius
                            color: Theme.accent
                            opacity: root.highlightedToolId === toolView.cuttingToolId ? 0.25 : 0
                            Behavior on opacity { NumberAnimation { duration: 50 } }
                        }

                        // A tool mounted in a holder: its card's border blue.
                        Rectangle {
                            anchors.fill: card
                            visible: root.mountedToolIds.indexOf(toolView.cuttingToolId) >= 0
                            color: "transparent"
                            radius: Theme.radius
                            border.width: 2
                            border.color: Theme.accent
                        }
                    }
                }
            }
        }
    }

    ScrollFades {
        anchors.fill: list
        flickable: list
    }

    Component {
        id: turningCard
        TurningToolCard {}
    }

    Component {
        id: threadingCard
        ThreadingToolCard {}
    }

    Component {
        id: bladeCard
        BladeToolCard {}
    }

    Component {
        id: drillingCard
        DrillingToolCard {}
    }

    Component {
        id: reamingCard
        ReamingToolCard {}
    }

    Component {
        id: tappingCard
        TappingToolCard {}
    }

    Component {
        id: summaryCard
        CuttingToolSummaryCard {}
    }

    // The card for each of the model's `card` values.
    readonly property var cards: ({
        "turning": turningCard,
        "threading": threadingCard,
        "blade": bladeCard,
        "drilling": drillingCard,
        "reaming": reamingCard,
        "tapping": tappingCard,
        "summary": summaryCard
    })
}
