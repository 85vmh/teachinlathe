import QtQuick
import theme
import TeachInLathe

// A button for an action that moves the machine: it acts only once held for
// holdMs. While it is held its background fills from left to right over that
// time; let go before it is full and it empties again, nothing done. Full, it
// sends triggered() - once per press. A tap, let go before its time, shows a
// short toast saying to hold it.
//
//     SafetyButton {
//         text: "Move to G28"
//         onTriggered: viewModel.moveToG28()
//     }
Rectangle {
    id: root

    property string text: ""
    //: how long it has to be held, in ms - the same for every one
    property int holdMs: Theme.safetyHoldMs
    readonly property real holdSeconds: Math.round(holdMs / 100) / 10
    //: the toast a tap shows, and how long it stays
    property string holdHint: "Hold for " + holdSeconds + (holdSeconds === 1 ? " second" : " seconds")
                              + " to trigger the movement"
    property int hintMs: 1500
    property int fontPixelSize: Theme.fontBody
    //: its border, and its fill as it is held (that colour, see-through)
    property color accent: Theme.warning

    //: held for holdMs: do what it is for
    signal triggered()

    //: 0 at rest, 1 when held its whole time
    // view state: how far the hold has got
    property real progress: 0
    readonly property bool pressed: area.pressed
    // already triggered by this press: no second time, no hint on release
    // view state: the hold fired its action, until released
    property bool _fired: false

    implicitWidth: label.implicitWidth + 2 * Theme.spacingLarge
    implicitHeight: Theme.buttonHeightLarge
    radius: Theme.radius
    color: Theme.surface
    border.color: enabled ? accent : Theme.outline
    border.width: 2
    opacity: enabled ? 1.0 : Theme.disabledOpacity

    // the fill, growing from the left while it is held
    Rectangle {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: parent.width * root.progress
        radius: root.radius
        color: Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.35)
        visible: root.progress > 0
    }

    Text {
        id: label
        anchors.centerIn: parent
        text: root.text
        color: Theme.foreground
        font.pixelSize: root.fontPixelSize
        font.bold: true
    }

    NumberAnimation {
        id: fill
        target: root
        property: "progress"
        to: 1
        onFinished: {
            if (!area.pressed || root._fired)
                return
            root._fired = true
            root.triggered()
        }
    }

    NumberAnimation {
        id: empty
        target: root
        property: "progress"
        to: 0
        duration: Theme.animationFast
    }

    MouseArea {
        id: area
        anchors.fill: parent
        onPressed: {
            root._fired = false
            empty.stop()
            // from empty every press, whatever was left of the last one:
            // holdMs of holding, always
            root.progress = 0
            fill.duration = root.holdMs
            fill.start()
        }
        onReleased: root._letGo(true)
        onCanceled: root._letGo(false)
    }

    function _letGo(released) {
        fill.stop()
        if (released && !root._fired)
            AppShellBridge.showToastFor(root.holdHint, root.hintMs)
        empty.start()
    }

    // disabled while held: it lets go
    onEnabledChanged: if (!enabled) _letGo(false)
}
