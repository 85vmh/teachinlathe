import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import common
import TeachInLathe

// The Events list: the machine's messages and the application's, newest on
// top, filtered by the tabs at the top.
Rectangle {
    id: root
    color: Theme.surfaceSunken
    border.color: Theme.outline
    border.width: Theme.hairline

    readonly property var filters: EventsViewModel.filters

    function severityColor(severity) {
        return severity === "error" ? Theme.danger
             : severity === "warning" ? Theme.warning
             : Theme.foregroundMuted
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 10

        // the title in the middle, Delete (all of them) on the right
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.buttonHeight

            Text {
                anchors.centerIn: parent
                text: "Events"
                color: Theme.foregroundStrong
                font.pixelSize: Theme.fontTitle
                font.bold: true
            }

            // drawn as the Tool Library's "+", the swipe's delete icon in red
            OperationIconTextButton {
                anchors { right: parent.right; verticalCenter: parent.verticalCenter }
                width: Theme.buttonHeight
                compact: true
                iconSource: Images.url("delete_icon.svg")
                tint: Theme.danger
                borderTint: Theme.danger
                color: Theme.surface
                buttonHeight: Theme.buttonHeight
                iconSize: 28
                onClicked: EventsViewModel.clear()
            }
        }

        SegmentedTabs {
            Layout.fillWidth: true
            labels: root.filters.map(f => f.label)
            fontPixelSize: Theme.fontSmall
            currentIndex: root.filters.findIndex(f => f.id === EventsViewModel.filter)
            onActivated: index => EventsViewModel.setFilter(root.filters[index].id)
        }

        Text {
            text: AppShellBridge.statusSummary
            color: Theme.foregroundMuted
            font.pixelSize: Theme.fontSmall
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        ListView {
            id: list
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 4
            model: EventsViewModel.model

            // the one card open to its whole text, by its event's id; -1 none
            property int expandedId: -1

            // One card per event, its text at most two lines, cut with an
            // ellipsis. A tap on a cut one opens it to the whole text and
            // closes the one open before; a tap on the open one closes it.
            delegate: Card {
                id: row
                required property int eventId
                required property string time
                required property string severity
                required property string categoryLabel
                required property string text
                required property int count

                readonly property bool expanded: list.expandedId === row.eventId
                // cut at two lines - or open, cut when closed
                readonly property bool expandable: row.expanded || message.truncated

                width: ListView.view.width
                height: content.implicitHeight + 12
                clip: true
                Behavior on height { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }

                MouseArea {
                    anchors.fill: parent
                    onClicked: list.expandedId = (row.expandable && !row.expanded) ? row.eventId : -1
                }
                color: row.severity === "error" ? Theme.dangerSoft : Theme.surface

                // the severity, as a bar on the left, inside the outline
                Rectangle {
                    width: 4
                    anchors { left: parent.left; top: parent.top; bottom: parent.bottom; margins: 3 }
                    radius: 2
                    color: root.severityColor(row.severity)
                }

                RowLayout {
                    id: content
                    anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter
                              leftMargin: 12; rightMargin: 8 }
                    spacing: 8

                    Text {
                        text: row.time
                        color: Theme.foregroundFaint
                        font.pixelSize: Theme.fontSmall
                        Layout.alignment: Qt.AlignTop
                    }

                    Text {
                        text: row.categoryLabel
                        color: Theme.foregroundMuted
                        font.pixelSize: Theme.fontSmall
                        font.bold: true
                        Layout.preferredWidth: 92
                        Layout.alignment: Qt.AlignTop
                    }

                    Text {
                        id: message
                        text: row.text
                        color: row.severity === "info" ? Theme.foreground : root.severityColor(row.severity)
                        font.pixelSize: Theme.fontLarge
                        wrapMode: Text.Wrap
                        maximumLineCount: row.expanded ? 1000 : 2
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }

                    Text {
                        visible: row.count > 1
                        text: "×" + row.count
                        color: Theme.foregroundMuted
                        font.pixelSize: Theme.fontSmall
                        font.bold: true
                        Layout.alignment: Qt.AlignTop
                    }
                }
            }

            Text {
                anchors.centerIn: parent
                visible: list.count === 0
                text: "No events"
                color: Theme.foregroundFaint
                font.pixelSize: Theme.fontBody
            }
        }
    }
}
