import QtQuick
import theme

/*
 * The fades at a scrolling list's top and bottom: each shown while there is
 * more to scroll to that way. Laid over the list, filling it:
 *
 *     ScrollFades { anchors.fill: list; flickable: list }
 *
 * For a ScrollView, pass its contentItem, the Flickable inside it.
 *
 * By atYBeginning/atYEnd, not by contentY against contentHeight: a list
 * whose rows differ in height only estimates its contentHeight, and moves
 * its origin as it learns better, so the sums are off at the ends.
 */
Item {
    id: root

    property Flickable flickable: null
    readonly property real fadeHeight: Theme.scrollFadeHeight
    //: What the list's rows fade into: the background behind the list.
    property color color: Theme.surfaceSunken

    z: 1

    Rectangle {
        anchors { left: parent.left; right: parent.right; top: parent.top }
        height: root.fadeHeight
        visible: !!root.flickable && !root.flickable.atYBeginning
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0.0; color: root.color }
            GradientStop { position: 1.0; color: "transparent" }
        }
    }

    Rectangle {
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        height: root.fadeHeight
        visible: !!root.flickable && !root.flickable.atYEnd
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0.0; color: "transparent" }
            GradientStop { position: 1.0; color: root.color }
        }
    }
}
