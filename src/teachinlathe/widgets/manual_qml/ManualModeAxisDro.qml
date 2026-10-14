import QtQuick 2.15
import QtQuick.Controls 2.15
import theme 1.0
import common 1.0

Item {
    id: root

    property string axisLabel: "X"
    property string primaryValue: "+0000.000"
    property string secondaryValue: "+0000.000"
    property bool secondaryVisible: false
    property bool setDatumVisible: false
    property string unit: "mm"
    //: Which of ABS and REL the toggle shows selected.
    property bool isAbs: true

    signal primaryClicked()
    signal zeroClicked()
    signal absRelClicked()
    signal setDatumClicked()
    signal setDatumLongPressed()

    width: 1090
    height: 82

    readonly property int gap: 10
    readonly property int axisWidth: 60
    readonly property int valueLeft: axisWidth + gap
    readonly property int primaryLeft: valueLeft + secondaryWidth + gap
    readonly property int buttonSize: 72
    readonly property int primaryWidth: 316
    readonly property int primaryHeight: 71
    readonly property int secondaryWidth: 132
    readonly property int secondaryHeight: 34
    readonly property int unitWidth: 42
    readonly property int rightButtonSpacing: 18
    readonly property int setDatumButtonSpacing: 26

    Text {
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        width: root.axisWidth
        height: parent.height
        text: root.axisLabel
        font.family: "Liberation Sans Narrow"
        font.pixelSize: 80
        color: "#101010"
        horizontalAlignment: Text.AlignLeft
        verticalAlignment: Text.AlignVCenter
    }

    Rectangle {
        id: secondaryBox
        anchors.left: parent.left
        anchors.leftMargin: root.valueLeft
        anchors.top: parent.top
        anchors.topMargin: 10
        width: root.secondaryWidth
        height: root.secondaryHeight
        visible: root.secondaryVisible
        radius: Theme.radius
        border.color: Theme.outline
        border.width: Theme.hairline
        color: "#56babb"

        Text {
            anchors.fill: parent
            anchors.rightMargin: 7
            text: root.secondaryValue
            color: Theme.surface
            font.family: "Noto Sans Mono"
            font.pixelSize: 21
            horizontalAlignment: Text.AlignRight
            verticalAlignment: Text.AlignVCenter
        }
    }

    Item {
        anchors.left: parent.left
        anchors.leftMargin: root.valueLeft
        anchors.top: parent.top
        anchors.topMargin: 4
        width: root.secondaryWidth
        height: root.secondaryHeight
        visible: !root.secondaryVisible
    }

    Rectangle {
        id: primaryBox
        anchors.left: parent.left
        anchors.leftMargin: root.primaryLeft
        anchors.verticalCenter: parent.verticalCenter
        width: root.primaryWidth
        height: root.primaryHeight
        radius: Theme.radius
        border.color: Theme.outline
        border.width: Theme.hairline
        color: Theme.outlineDisabled

        Text {
            anchors.fill: parent
            anchors.rightMargin: 10
            text: root.primaryValue
            color: "#0a0a0a"
            font.family: "Noto Sans Mono"
            font.pixelSize: 52
            horizontalAlignment: Text.AlignLeft
            verticalAlignment: Text.AlignVCenter
        }

        MouseArea {
            anchors.fill: parent
            onClicked: root.primaryClicked()
        }
    }

    Text {
        anchors.left: primaryBox.right
        anchors.leftMargin: root.gap
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 10
        width: root.unitWidth
        height: 30
        text: root.unit
        font.family: "Liberation Mono"
        font.pixelSize: 24
        color: "#101010"
        horizontalAlignment: Text.AlignLeft
        verticalAlignment: Text.AlignBottom
    }

    Button {
        id: zeroButton
        anchors.right: absRelButton.left
        anchors.rightMargin: root.rightButtonSpacing
        anchors.verticalCenter: parent.verticalCenter
        width: root.buttonSize
        height: root.buttonSize
        // Zero the axis: an icon in place of the "0" it used to read.
        display: AbstractButton.IconOnly
        icon.source: Images.url("zero.svg")
        // As big as the ABS/REL toggle's icon, so their lines match.
        icon.width: Math.round(root.buttonSize * 0.8)
        icon.height: Math.round(root.buttonSize * 0.8)
        icon.color: "transparent"       // the SVG's own colour, not the style's tint
        // Outlined and rounded as the title bar's recent toggle is.
        background: Rectangle {
            radius: Theme.radius
            color: parent.pressed ? Theme.accentSoft : Theme.surface
            border.width: Theme.hairline
            border.color: parent.pressed ? Theme.accentBorder : Theme.outlineStrong
        }
        onClicked: root.zeroClicked()
    }

    Button {
        id: absRelButton
        anchors.right: parent.right
        // The gap the buttons have between them, after the last one too.
        anchors.rightMargin: root.rightButtonSpacing
        anchors.verticalCenter: parent.verticalCenter
        width: root.buttonSize
        height: root.buttonSize
        // ABS over a diagonal, REL under it, the selected one blue.
        display: AbstractButton.IconOnly
        icon.source: Images.url(root.isAbs ? "abs_rel_abs.svg" : "abs_rel_rel.svg")
        icon.width: Math.round(root.buttonSize * 0.8)
        icon.height: Math.round(root.buttonSize * 0.8)
        icon.color: "transparent"       // the SVG's own colours, not the style's tint
        // Outlined and rounded as the title bar's recent toggle is.
        background: Rectangle {
            radius: Theme.radius
            color: parent.pressed ? Theme.accentSoft : Theme.surface
            border.width: Theme.hairline
            border.color: parent.pressed ? Theme.accentBorder : Theme.outlineStrong
        }
        onClicked: root.absRelClicked()
    }

    Button {
        id: datumButton
        visible: root.setDatumVisible
        anchors.right: zeroButton.left
        anchors.rightMargin: root.setDatumButtonSpacing
        anchors.verticalCenter: parent.verticalCenter
        // Square, as the others: the backplot's origin symbol in place of
        // the "Set Datum" it used to read.
        width: root.buttonSize
        height: root.buttonSize
        display: AbstractButton.IconOnly
        icon.source: Images.url("set_datum.svg")
        icon.width: Math.round(root.buttonSize * 0.8)
        icon.height: Math.round(root.buttonSize * 0.8)
        icon.color: "transparent"       // the SVG's own colour, not the style's tint
        // Outlined and rounded as the title bar's recent toggle is. Pressed
        // is the MouseArea's: it takes the taps, for the long press.
        background: Rectangle {
            radius: Theme.radius
            color: datumPressArea.pressed ? Theme.accentSoft : Theme.surface
            border.width: Theme.hairline
            border.color: datumPressArea.pressed ? Theme.accentBorder : Theme.outlineStrong
        }

        property bool longPressTriggered: false
        //: How far the hold has gone toward the long press, 0 to 1.
        property real holdProgress: 0

        // While held, a blue line runs round the symbol's ring from 12
        // o'clock, clockwise; it closes as the long press fires.
        NumberAnimation {
            id: holdAnimation
            target: datumButton
            property: "holdProgress"
            from: 0
            to: 1
            duration: datumPressArea.pressAndHoldInterval
        }

        function endHold() {
            holdAnimation.stop()
            holdProgress = 0
        }

        Canvas {
            id: holdRing
            anchors.centerIn: parent
            width: datumButton.icon.width
            height: datumButton.icon.height
            visible: datumButton.holdProgress > 0
            z: 1
            onVisibleChanged: requestPaint()
            Connections {
                target: datumButton
                function onHoldProgressChanged() { holdRing.requestPaint() }
            }
            onPaint: {
                var ctx = getContext("2d")
                ctx.reset()
                if (datumButton.holdProgress <= 0)
                    return
                // On the symbol's ring: radius 18.5 of set_datum.svg's 48.
                var r = width * 18.5 / 48
                var start = -Math.PI / 2
                ctx.strokeStyle = Theme.accent
                ctx.lineWidth = 2
                ctx.lineCap = "round"
                ctx.beginPath()
                ctx.arc(width / 2, height / 2, r, start,
                        start + 2 * Math.PI * datumButton.holdProgress, false)
                ctx.stroke()
            }
        }

        MouseArea {
            id: datumPressArea
            anchors.fill: parent
            enabled: datumButton.enabled
            pressAndHoldInterval: 1000

            onPressed: {
                datumButton.longPressTriggered = false
                holdAnimation.restart()
            }
            onPressAndHold: {
                datumButton.longPressTriggered = true
                datumButton.endHold()
                root.setDatumLongPressed()
            }
            onReleased: {
                datumButton.endHold()
                if (!datumButton.longPressTriggered && containsMouse) {
                    root.setDatumClicked()
                }
            }
            onCanceled: {
                datumButton.longPressTriggered = false
                datumButton.endHold()
            }
        }
    }
}
