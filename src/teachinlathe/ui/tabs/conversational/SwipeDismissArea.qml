import QtQuick

// Laid over a screen whose list has a SwipeRow open: a press anywhere else
// only closes it, and one on the row's Delete or Duplicate goes through.
MouseArea {
    // The SwipeRow showing its button, or null
    property var openRow: null
    signal dismissed()

    anchors.fill: parent
    z: 1000
    visible: !!openRow
    onPressed: function(mouse) {
        if (openRow && openRow.swipeActionContains(mapToItem(null, mouse.x, mouse.y)))
            mouse.accepted = false
        else
            dismissed()
    }
}
