// MachineButton.qml — round machine-style button with concave gradient
import QtQuick 2.15

Item {
    id: root
    width: 80
    height: 80

    property string text: ""
    property bool enabled: true
    // active = program is running (triggers brighter "lit" appearance)
    property bool active: false

    // Normal concave gradient stops (center dark → rim lighter)
    property string centerColor: "#1a5e20"
    property string midColor:    "#2e7d32"
    property string rimColor:    "#66bb6a"

    // Active/lit gradient stops (more uniform, brighter — "solid" look)
    property string activeCenterColor: "#2e7d32"
    property string activeRimColor:    "#81c784"

    // Disabled gradient stops
    property string disabledCenterColor: "#303030"
    property string disabledMidColor:    "#555555"
    property string disabledRimColor:    "#888888"

    signal clicked()

    onEnabledChanged: canvas.requestPaint()
    onActiveChanged:  canvas.requestPaint()
    onTextChanged:    canvas.requestPaint()

    Canvas {
        id: canvas
        anchors.fill: parent

        Component.onCompleted: requestPaint()

        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)

            var cx = width  / 2
            var cy = height / 2
            var borderW = 3
            var outerR = Math.min(width, height) / 2 - 1   // stays inside item bounds
            var innerR = outerR - borderW - 1               // fill surface inset from border

            // ── grey border ring ──────────────────────────────────────
            ctx.beginPath()
            ctx.arc(cx, cy, outerR, 0, Math.PI * 2)
            ctx.strokeStyle = root.enabled ? "#9e9e9e" : "#606060"
            ctx.lineWidth = borderW
            ctx.stroke()

            // ── concave fill with radial gradient ─────────────────────
            // Gradient: origin at center (focal=center), radius = innerR
            // center → darker (shadow at bottom of bowl)
            // rim    → lighter (edge catching light)
            var grd = ctx.createRadialGradient(cx, cy, 0, cx, cy, innerR)

            if (!root.enabled) {
                grd.addColorStop(0.0, root.disabledRimColor)
                grd.addColorStop(0.6, root.disabledMidColor)
                grd.addColorStop(1.0, root.disabledCenterColor)
            } else if (root.active) {
                grd.addColorStop(0.0, root.activeRimColor)
                grd.addColorStop(1.0, root.activeCenterColor)
            } else {
                grd.addColorStop(0.0, root.rimColor)
                grd.addColorStop(0.55, root.midColor)
                grd.addColorStop(1.0, root.centerColor)
            }

            ctx.beginPath()
            ctx.arc(cx, cy, innerR, 0, Math.PI * 2)
            ctx.fillStyle = grd
            ctx.fill()
        }
    }

    // Press darkness overlay
    Rectangle {
        anchors.fill: parent
        radius: width / 2
        color: mouseArea.pressed && root.enabled ? "#50000000" : "transparent"
    }

    Text {
        anchors.centerIn: parent
        text: root.text
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        font.pixelSize: 12
        font.bold: true
        color: root.enabled ? "white" : "#777777"
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
