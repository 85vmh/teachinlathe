// ToolPickerPopup.qml — picks the tool an operation cuts with, laid out as
// Add Operation's popup: the tools Manual Turning has touched off, two to a
// row, scrolling - but only those the operation can cut with (toolNos, which
// its editor works out). Tapping one selects it; Use Tool hands its T number
// on, with where the tool change goes - G28 or G30 - picked between the
// buttons; Cancel closes. A tool other than the one in now, for an operation
// whose tool the ones below it cut with too, asks first whether it is for
// this operation only or for it and those below - never those above.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQml.Models
import tabs.tool_library
import theme

Popup {
    id: root
    parent: Overlay.overlay
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    anchors.centerIn: parent

    // as wide as a Tool Change's details, so two cards fit side by side as
    // they do there; the operation sets it to its details' width
    contentWidth: 1000
    contentHeight: column.implicitHeight
    padding: 0

    // The T numbers shown - of those in toolsModel - the operation editor's
    // suitableToolNos
    property var toolNos: []
    onToolNosChanged: shown.refilter()
    // the tool in now, selected when the popup opens; 0 for none
    property int currentToolNo: 0
    // how many operations cut with the operation's tool from it down, it
    // included
    property int toolUsers: 0
    property int selectedToolNo: 0
    // where the machine goes to change the tool, "G28" or "G30": the Change
    // Tool's now, picked again in the popup
    property string currentToolchangePosition: "G28"
    property string toolchangePosition: "G28"

    // scope: "this" for this operation only, "below" for it and those below
    // cutting with its tool, "all" for every one cutting with it
    signal toolChosen(int toolNo, string toolchangePosition, string scope)

    function _choose() {
        // the same tool - a new tool change position, a move confirmed - is
        // the tool's, so all its operations'; another, for a tool the ones
        // below cut with too, is asked about
        if (selectedToolNo === currentToolNo) {
            toolChosen(selectedToolNo, toolchangePosition, "all")
            close()
        } else if (toolUsers <= 1) {
            toolChosen(selectedToolNo, toolchangePosition, "this")
            close()
        } else {
            scopeQuestion.open()
        }
    }

    readonly property int buttonWidth: 180
    readonly property int buttonHeight: Theme.buttonHeightTouch
    readonly property int buttonFontSize: 16
    //: ToolHolderCard's height: its thumbnail and the padding round it.
    readonly property int cardHeight: 136
    // three and a half rows show, so a list longer than that is seen to go
    // on - it scrolls
    readonly property real visibleRows: 3.5

    // The tools a program can change to (the operation editor's touchedOffTools).
    property var toolsModel: null

    onAboutToShow: {
        selectedToolNo = currentToolNo
        toolchangePosition = currentToolchangePosition === "G30" ? "G30" : "G28"
        shown.refilter()
    }

    function _allowed(toolNo) {
        return !!toolNos && toolNos.indexOf(toolNo) >= 0
    }

    background: Rectangle {
        radius: Theme.radiusXLarge
        color: Theme.surfaceSunken
        border.color: Theme.dialogBorder
        border.width: Theme.hairline
    }

    // the touched-off tools, only the allowed kinds
    DelegateModel {
        id: shown
        model: root.toolsModel
        groups: [ DelegateModelGroup { id: allowedGroup; name: "allowed" } ]
        filterOnGroup: "allowed"
        items.onChanged: refilter()

        function refilter() {
            for (var i = 0; i < items.count; i++) {
                var it = items.get(i)
                it.inAllowed = root._allowed(it.model.toolNo)
            }
        }

        delegate: Item {
            width: toolsGrid.cellWidth
            height: toolsGrid.cellHeight

            ToolHolderCard {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.rightMargin: index % 2 === 0 ? Theme.spacingSmall / 2 : 0
                anchors.leftMargin: index % 2 === 1 ? Theme.spacingSmall / 2 : 0
                toolNo: model.toolNo
                toolId: model.toolId
                toolCard: model.toolCard
                toolView: model.toolView
                toolComment: model.toolComment
                xOffset: model.xOffset
                zOffset: model.zOffset
                selected: model.toolNo === root.selectedToolNo
                onClicked: root.selectedToolNo = model.toolNo
            }
        }
    }

    contentItem: Column {
        id: column
        spacing: 24
        width: root.contentWidth
        padding: 16

        Row {
            spacing: 12
            Text {
                anchors.baseline: note.baseline
                text: "Select the Tool"
                font.pixelSize: Theme.fontLarge
                font.bold: true
                color: Theme.foreground
            }
            Text {
                id: note
                textFormat: Text.StyledText
                text: "(Only the <b>measured tools</b> suitable for this operation are shown)"
                font.pixelSize: Theme.fontBody
                color: Theme.foregroundSubtle
            }
        }

        Item {
            width: column.width - column.padding * 2
            height: root.visibleRows * (root.cardHeight + Theme.spacingSmall)

            GridView {
                id: toolsGrid
                anchors.fill: parent
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                model: shown
                cellWidth: Math.floor(width / 2)
                cellHeight: root.cardHeight + Theme.spacingSmall
            }

            // none to show: a note in the list's place
            Label {
                anchors.centerIn: parent
                visible: toolsGrid.count === 0
                text: "There are no measured tools to show."
                color: Theme.foregroundSubtle
                font.pixelSize: Theme.fontLarge
            }
        }

        Rectangle {
            width: column.width - column.padding * 2
            height: Theme.hairline
            color: Theme.separator
        }

        // Cancel on the left, Use Tool on the right, where the tool change
        // goes in between
        Item {
            width: column.width - column.padding * 2
            height: Math.max(root.buttonHeight, positionBox.implicitHeight)

            GroupBox {
                id: positionBox
                anchors.centerIn: parent
                title: "When doing a tool change"
                font.pixelSize: Theme.fontBody
                // the title centred over the box
                label: Label {
                    width: positionBox.width
                    horizontalAlignment: Text.AlignHCenter
                    text: positionBox.title
                    font: positionBox.font
                    color: Theme.foreground
                    elide: Text.ElideRight
                }

                RowLayout {
                    spacing: 20
                    RadioButton {
                        text: "Move to <b>G28</b>"
                        font.pixelSize: Theme.fontBody
                        checked: root.toolchangePosition === "G28"
                        onToggled: if (checked) root.toolchangePosition = "G28"
                    }
                    RadioButton {
                        text: "Move to <b>G30</b>"
                        font.pixelSize: Theme.fontBody
                        checked: root.toolchangePosition === "G30"
                        onToggled: if (checked) root.toolchangePosition = "G30"
                    }
                }
            }

            Button {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                text: "Cancel"
                width: root.buttonWidth
                height: root.buttonHeight
                font.pixelSize: root.buttonFontSize
                onClicked: root.close()
            }

            Button {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                text: "Use Tool"
                width: root.buttonWidth
                height: root.buttonHeight
                font.pixelSize: root.buttonFontSize
                // a tool picked, and one there is to pick
                enabled: root.selectedToolNo > 0 && toolsGrid.count > 0
                onClicked: root._choose()
            }
        }
    }

    // for this operation only, or for it and those below cutting with its tool
    Popup {
        id: scopeQuestion
        parent: Overlay.overlay
        modal: true
        focus: true
        anchors.centerIn: parent
        padding: 24
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            radius: Theme.radiusXLarge
            color: Theme.surfaceSunken
            border.color: Theme.dialogBorder
            border.width: Theme.hairline
        }

        contentItem: Column {
            spacing: 24

            Text {
                textFormat: Text.StyledText
                text: "This tool is also used by <b>" + (root.toolUsers - 1)
                      + (root.toolUsers === 2 ? " operation" : " operations") + " below</b>.<br>"
                      + "Use <b>T" + root.selectedToolNo + "</b> for:"
                font.pixelSize: Theme.fontLarge
                color: Theme.foreground
            }

            Row {
                spacing: 16
                Button {
                    text: "This operation"
                    width: root.buttonWidth
                    height: root.buttonHeight
                    font.pixelSize: root.buttonFontSize
                    onClicked: {
                        root.toolChosen(root.selectedToolNo, root.toolchangePosition, "this")
                        scopeQuestion.close()
                        root.close()
                    }
                }
                Button {
                    text: "This and the ones below"
                    width: root.buttonWidth
                    height: root.buttonHeight
                    font.pixelSize: root.buttonFontSize
                    onClicked: {
                        root.toolChosen(root.selectedToolNo, root.toolchangePosition, "below")
                        scopeQuestion.close()
                        root.close()
                    }
                }
            }
        }
    }
}
