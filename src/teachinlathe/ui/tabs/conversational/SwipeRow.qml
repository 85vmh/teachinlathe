import QtQuick 2.15
import QtQuick.Controls 2.15
import Qt5Compat.GraphicalEffects
import theme 1.0
import common 1.0

// A list row that swipes, as on a phone: dragged left, its content slides over
// a Delete button behind it at the right; dragged right, over a Duplicate one
// at the left. A drag stays on the side it opened, so going from one to the
// other takes lifting the finger in between.
//
// The list keeps one row open at a time, so it drives swipeSide (1 Delete,
// -1 Duplicate, 0 closed); the row reports back through swipeOpened/Closed.
// The list also closes it on any press elsewhere, asking swipeActionContains
// whether the press is on the open button.
Item {
    id: root

    // What slides: the row's own content goes in here
    default property alias content: rowContent.data
    property color contentColor: "transparent"
    property int contentBorderWidth: 0
    property color contentBorderColor: "transparent"
    property real contentRadius: 0

    property int swipeSide: 0
    property bool swipeEnabled: true
    property bool deleteEnabled: true       // a list may offer only one of them
    property bool duplicateEnabled: true
    property int actionWidth: 100
    property int actionGap: 0             // between the slid content and the button
    property real actionRadius: 0
    // How far the content slides to show a button whole
    readonly property int revealWidth: actionWidth + actionGap
    property real swipeOffset: 0          // > 0 shows Delete, < 0 Duplicate
    // Another SwipeRow this one's drags move in its place - one inside it,
    // say - or null for itself
    property var swipeTarget: null

    // A drag in progress: where it started, and the side it keeps to
    property bool _dragging: false
    property real _dragStart: 0
    property int _dragSide: 0

    signal deleteRequested()
    signal duplicateRequested()
    signal swipeOpened(int side)
    signal swipeClosed()

    // Whether scenePoint falls on the Delete or Duplicate button shown now
    function swipeActionContains(scenePoint) {
        var action = swipeOffset > 0 ? deleteAction : (swipeOffset < 0 ? duplicateAction : null)
        return !!action && action.contains(action.mapFromItem(null, scenePoint.x, scenePoint.y))
    }

    function _settleSwipe() {
        var side = swipeOffset > revealWidth / 2 ? 1
                 : (swipeOffset < -revealWidth / 2 ? -1 : 0)
        swipeOffset = side * revealWidth
        if (side !== 0)
            swipeOpened(side)
        else
            swipeClosed()
    }

    onSwipeSideChanged: swipeOffset = swipeSide * revealWidth

    // Called on whichever row the drag moves: this one, or the one whose
    // swipeTarget it is
    function _beginDrag() {
        _dragging = true
        _dragStart = swipeOffset
        _dragSide = Math.sign(_dragStart)
    }

    function _moveDrag(dx) {
        var offset = Math.max(duplicateEnabled ? -revealWidth : 0,
                              Math.min(deleteEnabled ? revealWidth : 0, _dragStart - dx))
        if (_dragSide === 0)
            _dragSide = Math.sign(offset)
        swipeOffset = _dragSide > 0 ? Math.max(0, offset) : Math.min(0, offset)
    }

    function _endDrag() {
        _dragging = false
        _settleSwipe()
    }

    Behavior on swipeOffset {
        enabled: !root._dragging
        NumberAnimation { duration: 150; easing.type: Easing.OutCubic }
    }

    clip: true

    // A square button behind the row, revealed as the row slides off it
    component SwipeAction: Rectangle {
        id: action
        property url iconSource
        property string text
        property color baseColor
        property color pressedColor
        signal clicked()

        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: root.actionWidth
        radius: root.actionRadius
        color: actionArea.pressed ? pressedColor : baseColor

        Column {
            anchors.centerIn: parent
            spacing: 2

            Item {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 30
                height: 30
                Image {
                    id: actionIcon
                    anchors.fill: parent
                    source: action.iconSource
                    sourceSize.width: 30
                    sourceSize.height: 30
                    visible: false
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                }
                ColorOverlay {
                    anchors.fill: actionIcon
                    source: actionIcon
                    color: "white"
                }
            }
            Label {
                anchors.horizontalCenter: parent.horizontalCenter
                text: action.text
                color: "white"
                font.bold: true
                font.pixelSize: 14
            }
        }

        MouseArea {
            id: actionArea
            anchors.fill: parent
            onClicked: action.clicked()
        }
    }

    // Revealed by a swipe left: deletes without asking
    SwipeAction {
        id: deleteAction
        anchors.right: parent.right
        visible: root.swipeOffset > 0
        iconSource: Images.url("delete_icon.svg")
        text: "Delete"
        baseColor: Theme.danger
        pressedColor: Theme.dangerPressed
        onClicked: root.deleteRequested()
    }

    // Revealed by a swipe right: makes a copy
    SwipeAction {
        id: duplicateAction
        anchors.left: parent.left
        visible: root.swipeOffset < 0
        iconSource: Images.url("duplicate_item.svg")
        text: "Duplicate"
        baseColor: Theme.primary
        pressedColor: Theme.primaryPressed
        onClicked: root.duplicateRequested()
    }

    Rectangle {
        id: rowContent
        width: parent.width
        height: parent.height
        x: -root.swipeOffset
        color: root.contentColor
        border.width: root.contentBorderWidth
        border.color: root.contentBorderColor
        radius: root.contentRadius
    }

    DragHandler {
        id: swipeDrag
        target: null
        // on even with neither button, so a sideways drag is never taken for a tap
        enabled: root.swipeEnabled
        yAxis.enabled: false
        // the row moved, kept for the whole drag
        property var moving: null
        onActiveChanged: {
            if (active) {
                moving = root.swipeTarget || root
                moving._beginDrag()
            } else if (moving) {
                moving._endDrag()
                moving = null
            }
        }
        onTranslationChanged: if (active && moving) moving._moveDrag(translation.x)
    }
}
