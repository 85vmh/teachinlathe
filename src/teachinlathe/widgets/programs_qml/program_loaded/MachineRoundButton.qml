// MachineRoundButton.qml — round machine-style button with concave gradient
import QtQuick 2.15

Item {
    id: root
    width: 80
    height: 80

    property string text: ""
    property bool enabled: true
    // active = program is running (triggers brighter "lit" appearance)
    property bool active: false

    // ── Colors ─────────────────────────────────────────────────────────
    // Concave gradient fill — normal state (center dark → rim lighter)
    property string normalFillCenterColor: "#1a5e20"
    property string normalFillMidColor:    "#2e7d32"
    property string normalFillRimColor:    "#66bb6a"

    // Concave gradient fill — active/lit state (brighter, more uniform)
    property string activeFillCenterColor: "#2e7d32"
    property string activeFillRimColor:    "#81c784"

    // Concave gradient fill — disabled state
    property string disabledFillCenterColor: "#303030"
    property string disabledFillMidColor:    "#555555"
    property string disabledFillRimColor:    "#888888"

    // Outer border ring
    property string borderColor:         "#9e9e9e"
    property string disabledBorderColor: "#606060"

    // Label text
    property string textColor:         "white"
    property string disabledTextColor: "#777777"

    // Darkening overlay painted while the button is pressed
    property string pressedOverlayColor: "#50000000"

    signal clicked()

    onEnabledChanged: canvas.requestPaint()
    onActiveChanged:  canvas.requestPaint()
    onTextChanged:    canvas.requestPaint()

    Canvas {
        id: canvas
        anchors.fill: parent

        Component.onCompleted: requestPaint()

        onPaint: {
            var context = getContext("2d")
            context.clearRect(0, 0, width, height)

            var centerX = width  / 2
            var centerY = height / 2
            var borderWidth = 1
            var outerRadius = Math.min(width, height) / 2 - 1     // stays inside item bounds
            var fillRadius = outerRadius - borderWidth - 1        // fill surface inset from border

            // ── grey border ring ──────────────────────────────────────
            context.beginPath()
            context.arc(centerX, centerY, outerRadius, 0, Math.PI * 2)
            context.strokeStyle = root.enabled ? root.borderColor : root.disabledBorderColor
            context.lineWidth = borderWidth
            context.stroke()

            // ── concave fill with radial gradient ─────────────────────
            // Gradient origin at the center (focal = center), radius = fillRadius
            // center → darker (shadow at the bottom of the bowl)
            // rim    → lighter (edge catching the light)
            var fillGradient = context.createRadialGradient(centerX, centerY, 0, centerX, centerY, fillRadius)

            if (!root.enabled) {
                fillGradient.addColorStop(0.0, root.disabledFillRimColor)
                fillGradient.addColorStop(0.6, root.disabledFillMidColor)
                fillGradient.addColorStop(1.0, root.disabledFillCenterColor)
            } else if (root.active) {
                fillGradient.addColorStop(0.0, root.activeFillRimColor)
                fillGradient.addColorStop(1.0, root.activeFillCenterColor)
            } else {
                fillGradient.addColorStop(0.0, root.normalFillRimColor)
                fillGradient.addColorStop(0.55, root.normalFillMidColor)
                fillGradient.addColorStop(1.0, root.normalFillCenterColor)
            }

            context.beginPath()
            context.arc(centerX, centerY, fillRadius, 0, Math.PI * 2)
            context.fillStyle = fillGradient
            context.fill()
        }
    }

    // Press darkness overlay
    Rectangle {
        anchors.fill: parent
        radius: width / 2
        color: mouseArea.pressed && root.enabled ? root.pressedOverlayColor : "transparent"
    }

    Text {
        anchors.centerIn: parent
        text: root.text
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        font.pixelSize: 12
        font.bold: true
        color: root.enabled ? root.textColor : root.disabledTextColor
        style: Text.Outline
        styleColor: "#90000000"
        lineHeightMode: Text.FixedHeight
        lineHeight: 16
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        enabled: root.enabled
        cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: root.clicked()
    }
}
