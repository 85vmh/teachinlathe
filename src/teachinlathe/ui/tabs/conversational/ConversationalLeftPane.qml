import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import common

Rectangle {
    id: root

    property var operationsModel: []
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
        : Math.max(0, Math.min(operationsModel.length - 1, dragFrom + Math.round(dragDy / rowH)))
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

    function _operationIndexToListIndex(index) {
        return index >= 0 ? index + 2 : 0
    }

    function _listIndexToOperationIndex(index) {
        return index >= 2 ? index - 2 : -1
    }

    function selectedOperationIndex() {
        return _listIndexToOperationIndex(opsList.currentIndex)
    }

    function setCurrentOperationIndex(index) {
        opsList.currentIndex = _operationIndexToListIndex(index)
    }

    function saveScrollPosition() {
        _savedContentY = opsList.contentY
        _restoreScrollPending = true
    }

    function syncAfterOperationsModelChanged() {
        openSwipeIndex = -1
        var targetY = _restoreScrollPending ? _savedContentY : opsList.contentY
        Qt.callLater(function() {
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
        Qt.callLater(function() { root._dragAnimate = true })
    }

    // The operation row showing its Delete or Duplicate, or null
    readonly property var openSwipeRow: {
        if (openSwipeIndex < 0)
            return null
        var cell = opsList.itemAtIndex(_operationIndexToListIndex(openSwipeIndex))
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
                if (opsList.count <= 0)
                    return
                opsList.positionViewAtEnd()
                // once more, with the last rows now built: the first pass went by
                // contentHeight's estimate, which the shorter header rows throw off
                Qt.callLater(function() { opsList.positionViewAtEnd() })
            })
        })
    }

    onActiveOpIndexChanged: setCurrentOperationIndex(activeOpIndex)
    onOperationsModelChanged: syncAfterOperationsModelChanged()

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
                item.operationsCount = root.operationsModel.length
                item.currentOpIndex = root.selectedOperationIndex()
                if (item.open) item.open()
            }
        }
    }

    Layout.fillWidth: true
    Layout.preferredWidth: 3.5
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
                spacing: 6

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    ListView {
                        id: opsList
                        anchors.fill: parent
                        clip: true
                        model: root.operationsModel.length + 2
                        currentIndex: 0
                        interactive: root.dragFrom < 0

                        onMovementStarted: root.openSwipeIndex = -1

                        onCurrentIndexChanged: {
                            if (currentIndex === 0) {
                                root.programHeaderSelected()
                            } else if (currentIndex >= 2) {
                                root.operationSelected(root._listIndexToOperationIndex(currentIndex))
                            }
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
                            height: index === 1 ? 40 : root.rowH
                            readonly property int operationIndex: index - 2

                            ProgramHeader {
                                anchors.fill: parent
                                visible: index === 0
                                datum: root.programDatum
                                colDelW: root.colDelW
                                selected: opsList.currentIndex === 0
                                onClicked: opsList.currentIndex = 0
                            }

                            OperationsListHeader {
                                anchors.fill: parent
                                visible: index === 1
                                colOpNumW: root.colOpNumW
                                colGenW: root.colGenW
                                colTypeW: root.colTypeW
                                colOptW: root.colOptW
                                headerFontSize: root.opHeaderFontSize
                            }

                            OperationListItem {
                                id: opRow
                                anchors.fill: parent
                                visible: index >= 2
                                operationIndex: parent.operationIndex
                                operationData: index >= 2 ? root.operationsModel[parent.operationIndex] : null
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
                                    root._scrollToLastPending = i === root.operationsModel.length - 1
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
                                                           Math.min((root.operationsModel.length - 1 - i) * root.rowH, dy))
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
                                    opsList.currentIndex = root._operationIndexToListIndex(i)
                                }
                            }
                        }
                    }

                    ScrollFades {
                        anchors.fill: parent
                        flickable: opsList
                        fadeHeight: Theme.buttonHeight
                        color: Theme.surfaceAlt
                    }
                }

                // between the list and the Add New Operation bar
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: Theme.hairline
                    color: Theme.outline
                }

                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 70

                    OperationIconTextButton {
                        anchors.centerIn: parent
                        iconSource: Images.url("add_op_icon.svg")
                        text: "Add New Operation"
                        tint: Theme.success
                        compact: false
                        buttonHeight: Theme.buttonHeightLarge
                        iconSize: 36
                        fontPixelSize: 15
                        onClicked: root.openAddOperationPopup()
                    }
                }
            }
        }
    }
}
