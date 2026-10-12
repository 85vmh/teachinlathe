import QtQuick 2.15
import QtQuick.Controls 2.15
import Qt5Compat.GraphicalEffects
import theme 1.0

// The cutting tools, grouped by type. Each group's header folds the group
// and has a "+" for adding a tool of that type; under it the group's tools
// are cards, two to a row, filling left to right and then down. Tapping a
// card opens the tool. The title bar's buttons unfold or fold every group.
ToolLibraryPane {
    id: root

    property var model: null

    signal addRequested(string toolType)
    signal toolTapped(int toolId)

    //: How far the cards are set in from their category's header.
    readonly property int toolIndent: Theme.margin
    readonly property int cardSpacing: Theme.spacingSmall
    readonly property int summaryCardHeight: Theme.inputHeight

    title: "Cutting Tools"

    // Collapse lines up with the categories' "+" below it: the list's
    // margin plus the "+"'s own from the header's edge.
    headerActionsRightMargin: Theme.spacingSmall + Theme.spacing
    headerActionsSpacing: 3 * Theme.spacingSmall
    headerActions: [
        HeaderButton {
            iconSource: "icons/expand-vertical.svg"
            enabled: root.model ? !root.model.allExpanded : false
            onClicked: root.model.setAllExpanded(true)
        },
        HeaderButton {
            iconSource: "icons/collapse-vertical.svg"
            enabled: root.model ? !root.model.allCollapsed : false
            onClicked: root.model.setAllExpanded(false)
        }
    ]

    // A button the size and look of a category's "+", with an icon in place
    // of the glyph, flooded with the same muted grey. Faded, and deaf to
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

        delegate: Column {
            id: category
            width: ListView.view.width
            spacing: 4

            // Read here: inside the Repeater below, `model` is its own.
            readonly property string card: model.card
            readonly property var tools: model.tools

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
                    model: cards.shown ? category.tools : []

                    delegate: Loader {
                        readonly property var toolView: modelData
                        width: cards.cardWidth
                        // A full card is as tall as its content says.
                        height: item ? (category.card === "summary" ? root.summaryCardHeight
                                                                    : item.implicitHeight) : 0
                        sourceComponent: root.cards[category.card]
                        onLoaded: {
                            item.view = toolView
                            item.tapped.connect(function() { root.toolTapped(toolView.cuttingToolId) })
                        }
                    }
                }
            }
        }
    }

    // Fades at the list's ends, as the program list has them: shown while
    // there is more to scroll to that way.
    Rectangle {
        anchors { left: list.left; right: list.right; top: list.top }
        height: 100
        visible: !list.atYBeginning
        z: 1
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0.0; color: Theme.surfaceSunken }
            GradientStop { position: 1.0; color: "transparent" }
        }
    }

    Rectangle {
        anchors { left: list.left; right: list.right; bottom: list.bottom }
        height: 100
        visible: !list.atYEnd
        z: 1
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0.0; color: "transparent" }
            GradientStop { position: 1.0; color: Theme.surfaceSunken }
        }
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
