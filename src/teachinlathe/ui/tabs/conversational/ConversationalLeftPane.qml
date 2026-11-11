import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import common
import TeachInLathe

Item {
    id: root

    // the program's operations, a row each - OperationListModel: number,
    // title, toolLabel, generateGcode, optionalBlock, stockProblem - a row's index its
    // operation's
    property var operationsModel: null
    property int programDatum: 1          // the work offset's P number: 1 is G54
    property int activeOpIndex: -1

    readonly property int colOpNumW: 50
    readonly property int colGenW: 80
    readonly property int colTypeW: 200
    readonly property int colOptW: 80
    readonly property int colDelW: 100    // the swipe buttons, and where the header's G54 sits
    readonly property int rowH: Theme.rowHeight
    readonly property int opHeaderFontSize: Theme.tableHeaderFontSize

    // view state: the scroll kept over a change of rows
    property real _savedContentY: 0
    // view state: the scroll kept over a change of rows
    property bool _restoreScrollPending: false
    // view state: the scroll kept over a change of rows
    property bool _scrollToLastPending: false
    // view state: the row swiped open
    property int openSwipeIndex: -1       // the operation row swiped open...
    // view state: the row swiped open
    property int openSwipeSide: 0         // ...and to which side: 1 Delete, -1 Duplicate

    // Long press reorder: the row lifted, and how far it has been dragged
    // view state: a reorder drag
    property int dragFrom: -1
    // view state: a reorder drag
    property real dragDy: 0
    readonly property int dragTo: dragFrom < 0 ? -1
        : Math.max(0, Math.min(opsList.count - 1, dragFrom + Math.round(dragDy / rowH)))
    // view state: a reorder drag
    property bool _dragAnimate: true

    signal programHeaderSelected()
    signal operationSelected(int index)
    signal addOperationRequested()
    signal operationTypeChosen(string type, int insertIndex)
    signal defineProfileChosen(string profileType, int insertIndex)
    signal generateToggled(int index, bool checked)
    signal optionalToggled(int index, bool checked)
    signal deleteOperationRequested(int index)
    signal duplicateOperationRequested(int index)
    signal moveOperationRequested(int fromIndex, int toIndex)

    // The operation selected is the view model's (activeOpIndex): a tap on a
    // row only asks for it (operationSelected), and the rows show what
    // activeOpIndex then says. The ListView's own current index is not used:
    // it resets itself whenever its model changes.
    function selectedOperationIndex() {
        return activeOpIndex
    }

    function saveScrollPosition() {
        _savedContentY = opsList.contentY
        _restoreScrollPending = true
    }

    function syncAfterOperationsModelChanged() {
        openSwipeIndex = -1
        var targetY = _restoreScrollPending ? _savedContentY : opsList.contentY
        Qt.callLater(function() {
            // the screen may have been closed since (see ChildScreen.showEditor)
            if (!opsList)
                return
            if (_scrollToLastPending) {
                _restoreScrollPending = false
                _scrollToLastPending = false
                scrollToLastItem()
            } else if (_restoreScrollPending) {
                var maxY = Math.max(0, opsList.contentHeight - opsList.height)
                opsList.contentY = Math.max(0, Math.min(targetY, maxY))
                _restoreScrollPending = false
            }
        })
    }

    function _finishReorder() {
        var from = dragFrom
        var to = dragTo
        // the rows are already where the move puts them: no sliding back
        _dragAnimate = false
        if (from >= 0 && to >= 0 && to !== from) {
            saveScrollPosition()
            moveOperationRequested(from, to)
        }
        dragFrom = -1
        dragDy = 0
        Qt.callLater(function() { if (root) root._dragAnimate = true })
    }

    // The operation row showing its Delete or Duplicate, or null
    readonly property var openSwipeRow: {
        if (openSwipeIndex < 0)
            return null
        var cell = opsList.itemAtIndex(openSwipeIndex)
        return cell ? cell.row : null
    }

    function openAddOperationPopup() {
        root.addOperationRequested()
        if (addOpPopupLoader.active && addOpPopupLoader.item) {
            addOpPopupLoader.item.close()
            addOpPopupLoader.active = false
        }
        addOpPopupLoader.active = true
    }

    function scrollToLastItem() {
        Qt.callLater(function() {
            Qt.callLater(function() {
                if (!opsList || opsList.count <= 0)
                    return
                opsList.positionViewAtEnd()
                // once more, with the last rows now built: the first pass went by
                // contentHeight's estimate before all delegates were built
                Qt.callLater(function() { if (opsList) opsList.positionViewAtEnd() })
            })
        })
    }

    // A program opened again has the same rows as before: its model sends
    // nothing (DataclassListModel.setRows), so the list - new with the screen -
    // takes the operation its editor shows here, scrolled into view.
    Component.onCompleted: Qt.callLater(function() {
        if (!opsList)
            return
        if (activeOpIndex >= 0 && activeOpIndex < opsList.count)
            opsList.positionViewAtIndex(activeOpIndex, ListView.Contain)
    })

    // the rows changed - all of them anew, or some in place: the scroll
    // position and the selection as they are to be after
    Connections {
        target: root.operationsModel
        function onModelReset() { Qt.callLater(root.syncAfterOperationsModelChanged) }
        function onDataChanged() { Qt.callLater(root.syncAfterOperationsModelChanged) }
    }

    Loader {
        id: addOpPopupLoader
        active: false
        visible: active

        sourceComponent: AddOperationPopup {
            id: addPopup
            onOperationChosen: function(type, insertIndex) {
                // a Define Profile is OD or ID from the start: asked first
                if (type === "defineProfile") {
                    newProfilePopup.profileId = ConversationalViewModel.nextProfileId()
                    newProfilePopup.insertIndex = insertIndex
                    newProfilePopup.open()
                    return
                }
                root._scrollToLastPending = true
                root.operationTypeChosen(type, insertIndex)
            }
            onClosed: addOpPopupLoader.active = false
        }

        onLoaded: {
            if (item) {
                item.operationsCount = opsList.count
                var current = root.activeOpIndex
                item.insertAboveIndex = current >= 0 ? current : 0
                item.insertBelowIndex = current >= 0 ? current + 1 : -1
                if (item.open) item.open()
            }
        }
    }

    NewProfilePopup {
        id: newProfilePopup
        onProfileTypeChosen: function(profileType, insertIndex) {
            root._scrollToLastPending = true
            root.defineProfileChosen(profileType, insertIndex)
        }
    }

    Layout.fillWidth: true
    Layout.preferredWidth: 3
    Layout.fillHeight: true
    // no box of its own: the program header's card and the operations' card,
    // the window's background between them (as the file browser's cards)

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.spacingSmall

        ProgramHeader {
            Layout.fillWidth: true
            Layout.preferredHeight: root.rowH
            datum: root.programDatum
            colDelW: root.colDelW
            selected: root.activeOpIndex < 0
            onClicked: root.programHeaderSelected()
        }

        // the operations' card, as the conversational programs list: the
        // column titles and the rows reaching to its outline
        Card {
            id: operationsBox
            Layout.fillWidth: true
            Layout.fillHeight: true

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Theme.cardInset
                spacing: 0

                OperationsListHeader {
                    Layout.fillWidth: true
                    Layout.preferredHeight: root.rowH
                    colOpNumW: root.colOpNumW
                    colGenW: root.colGenW
                    colTypeW: root.colTypeW
                    colOptW: root.colOptW
                    headerFontSize: root.opHeaderFontSize
                    onAddOperationRequested: root.openAddOperationPopup()
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    ListView {
                        id: opsList
                        anchors.fill: parent
                        clip: true
                        model: root.operationsModel
                        interactive: root.dragFrom < 0

                        onMovementStarted: root.openSwipeIndex = -1

                        delegate: Item {
                            id: cell
                            property alias row: opRow
                            // where long press reorder has this row now, against its place
                            readonly property real reorderShift: {
                                var i = operationIndex
                                if (root.dragFrom < 0 || i < 0)
                                    return 0
                                if (i === root.dragFrom)
                                    return root.dragDy
                                if (root.dragFrom < i && i <= root.dragTo)
                                    return -root.rowH
                                if (root.dragTo <= i && i < root.dragFrom)
                                    return root.rowH
                                return 0
                            }
                            readonly property bool lifted: operationIndex >= 0 && operationIndex === root.dragFrom
                            z: lifted ? 10 : 0
                            scale: lifted ? 1.02 : 1
                            transform: Translate {
                                y: cell.reorderShift
                                Behavior on y {
                                    enabled: root._dragAnimate && !cell.lifted
                                    NumberAnimation { duration: 120; easing.type: Easing.OutCubic }
                                }
                            }
                            width: ListView.view ? ListView.view.width : 400
                            height: root.rowH
                            readonly property int operationIndex: index

                            OperationListItem {
                                id: opRow
                                anchors.fill: parent
                                operationIndex: parent.operationIndex
                                number: model.number
                                title: model.title
                                toolLabel: model.toolLabel
                                generateGcode: model.generateGcode
                                optionalBlock: model.optionalBlock
                                stockProblem: model.stockProblem
                                selected: root.activeOpIndex === index
                                colOpNumW: root.colOpNumW
                                colGenW: root.colGenW
                                colTypeW: root.colTypeW
                                colOptW: root.colOptW
                                colDelW: root.colDelW
                                lifted: cell.lifted
                                swipeSide: root.openSwipeIndex === operationIndex ? root.openSwipeSide : 0

                                onGenerateToggled: function(i, checked) {
                                    root.saveScrollPosition()
                                    root.generateToggled(i, checked)
                                }
                                onOptionalToggled: function(i, checked) {
                                    root.saveScrollPosition()
                                    root.optionalToggled(i, checked)
                                }
                                onDeleteClicked: function(i) {
                                    root.openSwipeIndex = -1
                                    root._scrollToLastPending = i === opsList.count - 1
                                    root.deleteOperationRequested(i)
                                }
                                onDuplicateClicked: function(i) {
                                    root.openSwipeIndex = -1
                                    root.saveScrollPosition()
                                    root.duplicateOperationRequested(i)
                                }
                                onReorderStarted: function(i) {
                                    root.openSwipeIndex = -1
                                    root.dragDy = 0
                                    root.dragFrom = i
                                }
                                onReorderMoved: function(i, dy) {
                                    // kept within the list's first and last rows
                                    root.dragDy = Math.max(-i * root.rowH,
                                                           Math.min((opsList.count - 1 - i) * root.rowH, dy))
                                }
                                onReorderFinished: function(i) {
                                    root._finishReorder()
                                }
                                onSwipeOpened: function(side) {
                                    root.openSwipeSide = side
                                    root.openSwipeIndex = operationIndex
                                }
                                onSwipeClosed: {
                                    if (root.openSwipeIndex === operationIndex)
                                        root.openSwipeIndex = -1
                                }
                                onRowTapped: function(i) { root.operationSelected(i) }
                            }
                        }
                    }

                    ScrollFades {
                        anchors.fill: parent
                        flickable: opsList
                        color: Theme.surface
                    }
                }

            }
        }

    }
}
