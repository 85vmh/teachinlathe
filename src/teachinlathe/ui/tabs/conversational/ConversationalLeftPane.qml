import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import common

Rectangle {
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
    readonly property int opHeaderFontSize: 14

    property real _savedContentY: 0
    property bool _restoreScrollPending: false
    property bool _scrollToLastPending: false
    property int openSwipeIndex: -1       // the operation row swiped open...
    property int openSwipeSide: 0         // ...and to which side: 1 Delete, -1 Duplicate

    // Long press reorder: the row lifted, and how far it has been dragged
    property int dragFrom: -1
    property real dragDy: 0
    readonly property int dragTo: dragFrom < 0 ? -1
        : Math.max(0, Math.min(opsList.count - 1, dragFrom + Math.round(dragDy / rowH)))
    property bool _dragAnimate: true

    signal programHeaderSelected()
    signal operationSelected(int index)
    signal addOperationRequested()
    signal operationTypeChosen(string type, int insertIndex)
    signal generateToggled(int index, bool checked)
    signal optionalToggled(int index, bool checked)
    signal deleteOperationRequested(int index)
    signal duplicateOperationRequested(int index)
    signal moveOperationRequested(int fromIndex, int toIndex)

    function selectedOperationIndex() {
        return opsList.currentIndex
    }

    function setCurrentOperationIndex(index) {
        opsList.currentIndex = index >= 0 && index < opsList.count ? index : -1
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
                setCurrentOperationIndex(activeOpIndex)
                scrollToLastItem()
            } else if (_restoreScrollPending) {
                var maxY = Math.max(0, opsList.contentHeight - opsList.height)
                opsList.contentY = Math.max(0, Math.min(targetY, maxY))
                _restoreScrollPending = false
                setCurrentOperationIndex(activeOpIndex)
            } else {
                setCurrentOperationIndex(activeOpIndex)
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

    onActiveOpIndexChanged: setCurrentOperationIndex(activeOpIndex)

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
                root._scrollToLastPending = true
                root.operationTypeChosen(type, insertIndex)
            }
            onClosed: addOpPopupLoader.active = false
        }

        onLoaded: {
            if (item) {
                item.operationsCount = opsList.count
                var current = opsList.currentIndex
                item.insertAboveIndex = current >= 0 ? current : 0
                item.insertBelowIndex = current >= 0 ? current + 1 : -1
                if (item.open) item.open()
            }
        }
    }

    Layout.fillWidth: true
    Layout.preferredWidth: 3
    Layout.fillHeight: true
    color: Theme.surface
    radius: Theme.radius
    border.color: Theme.outline
    border.width: Theme.hairline

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 1
        spacing: 6

        Rectangle {
            id: operationsBox
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: Theme.radiusSmall
            color: Theme.surfaceAlt
            border.width: 0
            border.color: Theme.outlineDisabled

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 0

                ProgramHeader {
                    Layout.fillWidth: true
                    Layout.preferredHeight: root.rowH
                    Layout.bottomMargin: 4
                    datum: root.programDatum
                    colDelW: root.colDelW
                    selected: opsList.currentIndex < 0
                    onClicked: {
                        opsList.currentIndex = -1
                        root.programHeaderSelected()
                    }
                }

                OperationsListHeader {
                    Layout.fillWidth: true
                    Layout.preferredHeight: root.rowH
                    Layout.bottomMargin: 4
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
                        currentIndex: -1
                        interactive: root.dragFrom < 0

                        onMovementStarted: root.openSwipeIndex = -1

                        onCurrentIndexChanged: {
                            if (currentIndex >= 0)
                                root.operationSelected(currentIndex)
                        }

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
                                selected: opsList.currentIndex === index
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
                                onRowTapped: function(i) {
                                    opsList.currentIndex = i
                                }
                            }
                        }
                    }

                    ScrollFades {
                        anchors.fill: parent
                        flickable: opsList
                        color: Theme.surfaceAlt
                    }
                }

            }
        }

    }
}
