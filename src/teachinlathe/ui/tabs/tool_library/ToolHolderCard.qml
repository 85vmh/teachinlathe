import QtQuick
import theme
import "ToolTitles.js" as ToolTitles

// A tool holder with the cutting tool in it, as the Manual Turning list and
// the conversational Tool Change pick from them:
//
//   ┌─────────────────────────────────────────────────────────────────┐
//   │     ┌─────────┐ Turning CCMT 060202 (comment) │    Offsets      │
//   │ T1  │thumbnail│ Tip:      80°                 │ X:      123.123 │
//   │     │         │ Radius:   0.2 mm              │ Z:     Not set  │
//   │     └─────────┘                               │                 │
//   └─────────────────────────────────────────────────────────────────┘
//
// While either offset is missing the title and the missing value are
// orange. A disabled card is dimmed and cannot be tapped.
Rectangle {
    id: root

    property int toolNo: 0
    property int toolId: 0              // the mounted cutting tool's, 0 when empty
    property string toolCard: ""        // which thumbnail, title and figures draw it
    property var toolView: null
    property string toolComment: ""
    property string xOffset: ""         // as shown, or empty until touched off
    property string zOffset: ""
    property bool selected: false

    signal clicked()

    //: As a cutting tool's card: its thumbnail, and the space round it.
    readonly property int thumbnailSize: 120
    readonly property int cardPadding: 8
    //: The offsets' column, right of the separator.
    readonly property int offsetsWidth: 100

    readonly property bool hasTool: toolId !== 0

    height: thumbnailSize + 2 * cardPadding
    radius: Theme.radius
    color: selected ? Theme.selection : Theme.surface
    border.width: selected ? 2 : Theme.hairline
    border.color: selected ? Theme.accent : Theme.outline
    opacity: enabled || selected || !hasTool ? 1.0 : 0.5

    // The tool numbers' column: as wide as the widest, "T99".
    TextMetrics {
        id: toolNoMetrics
        text: "T99"
        font.pixelSize: Theme.fontLarge
        font.bold: true
    }

    MouseArea {
        anchors.fill: parent
        enabled: root.enabled && !root.selected
        onClicked: root.clicked()
    }

    Text {
        id: toolLabel
        anchors.left: parent.left
        anchors.leftMargin: Theme.spacing
        anchors.verticalCenter: parent.verticalCenter
        // As wide as "T99" whatever the number, centred in it, so the
        // thumbnail starts at the same place on every card.
        width: toolNoMetrics.width
        horizontalAlignment: Text.AlignHCenter
        text: "T" + root.toolNo
        color: Theme.foreground
        font.pixelSize: Theme.fontLarge
        font.bold: true
    }

    Loader {
        id: thumbnail
        visible: root.hasTool
        anchors.left: toolLabel.right
        anchors.leftMargin: Theme.spacingSmall
        anchors.verticalCenter: parent.verticalCenter
        width: root.thumbnailSize
        height: root.thumbnailSize
        sourceComponent: root.hasTool ? root.thumbnails[root.toolCard] || null : null
        onLoaded: item.view = Qt.binding(function() { return root.toolView })
    }

    // The spindle direction, M3 or M4: right of the thumbnail, under the
    // name and figures, its bottom on the thumbnail's.
    SpindleDirectionIcon {
        visible: root.hasTool && clockwise !== null && clockwise !== undefined
        anchors.left: thumbnail.right
        anchors.leftMargin: Theme.spacing
        anchors.bottom: thumbnail.bottom
        clockwise: root.toolView && root.toolView.clockwise !== undefined
                   ? root.toolView.clockwise : null
    }

    // ── The tool: its name, then its figures ────────────────────────────
    Column {
        visible: root.hasTool
        anchors.left: thumbnail.right
        anchors.right: separator.left
        anchors.top: parent.top
        anchors.leftMargin: Theme.spacing
        anchors.rightMargin: Theme.spacing
        anchors.topMargin: root.cardPadding
        spacing: Theme.spacingSmall

        // The name, then the comment in brackets, grey.
        Text {
            width: parent.width
            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
            maximumLineCount: 2
            elide: Text.ElideRight
            textFormat: Text.StyledText
            text: !root.hasTool ? ""
                  : "<b>" + ToolTitles.listTitle(root.toolCard, root.toolView, Theme) + "</b>"
                    + (root.toolComment === "" ? ""
                       : " <font color='" + Theme.foregroundSubtle + "'>("
                         + root.toolComment + ")</font>")
            color: Theme.foreground
            font.pixelSize: Theme.fontLarge
        }

        Column {
            spacing: 4
            Repeater {
                model: root.hasTool ? ToolTitles.figures(root.toolCard, root.toolView, Theme) : []
                delegate: Row {
                    spacing: Theme.spacingSmall
                    Text {
                        width: 70
                        text: modelData.label
                        color: modelData.color
                        font.pixelSize: Theme.fontBody
                    }
                    Text {
                        text: modelData.value
                        color: modelData.color
                        font.pixelSize: Theme.fontBody
                    }
                }
            }
        }
    }

    Text {
        visible: !root.hasTool
        anchors.left: toolLabel.right
        anchors.leftMargin: Theme.spacingSmall
        anchors.verticalCenter: parent.verticalCenter
        text: "No tool mounted"
        color: Theme.foregroundSubtle
        font.pixelSize: Theme.fontBody
        font.bold: true
    }

    // ── The offsets, right of a separator ───────────────────────────────
    Rectangle {
        id: separator
        anchors.right: offsets.left
        anchors.rightMargin: Theme.spacing
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.margins: root.cardPadding
        width: Theme.hairline
        color: Theme.separator
    }

    OffsetsColumn {
        id: offsets
        anchors.right: parent.right
        anchors.rightMargin: Theme.spacing
        anchors.top: parent.top
        anchors.topMargin: root.cardPadding
        width: root.offsetsWidth
        xOffset: root.xOffset
        zOffset: root.zOffset
    }

    Component { id: insertThumbnail; InsertThumbnail { size: root.thumbnailSize; padding: 10 } }
    Component { id: threadingThumbnail; ThreadingInsertThumbnail { size: root.thumbnailSize; padding: 10 } }
    Component { id: bladeThumbnail; BladeThumbnail { size: root.thumbnailSize; padding: 10 } }
    Component { id: drillThumbnail; DrillThumbnail { size: root.thumbnailSize; padding: 10 } }
    Component { id: reamerThumbnail; ReamerThumbnail { size: root.thumbnailSize; padding: 10 } }
    Component { id: tapThumbnail; TapThumbnail { size: root.thumbnailSize; padding: 10 } }

    // The thumbnail for each `toolCard` value.
    readonly property var thumbnails: ({
        "turning": insertThumbnail,
        "threading": threadingThumbnail,
        "blade": bladeThumbnail,
        "drilling": drillThumbnail,
        "reaming": reamerThumbnail,
        "tapping": tapThumbnail
    })
}
