import QtQuick 2.15

Rectangle {
    id: root

    objectName: "manualJoystickPanel"
    width: 260
    height: 230
    color: "#f5f5f5"

    property var viewModel: null
    property int joystickState: viewModel ? viewModel.joystickState : 0
    property bool rapidMode: viewModel ? viewModel.joystickRapid : false
    property bool allowsTouchInteraction: viewModel ? viewModel.allowsJoystickTouch : true
    property bool angleFeedActive: viewModel ? viewModel.angleFeedActive : false
    property real currentRotation: 0
    property real rotationTarget: angleFeedActive ? 45 : 0
    property bool rotationActive: false

    readonly property real canvasWidth: 250
    readonly property real canvasHeight: 230
    readonly property var ringRadii: [36, 25, 20]
    readonly property real joystickRadius: 15
    readonly property real lineThickness: 1.2
    readonly property real arrowThickness: 4
    readonly property real arrowStartRadius: ringRadii[0] + arrowThickness - lineThickness
    readonly property real arrowTotalLength: 70
    readonly property real arrowHeadSize: 6
    readonly property real labelWidth: 40
    readonly property real labelHeight: 25
    readonly property real labelDistanceFromTip: 23
    readonly property real labelRadius: 5

    readonly property color feedColor: "#009600"
    readonly property color blackColor: "#323232"
    readonly property color dashedColor: "#c8c8c8"

    signal angleFeedClicked()

    onAngleFeedClicked: if (root.viewModel) root.viewModel.toggleAngleFeedFromJoystick()

    function setJoystickState(state) {
        if (root.viewModel)
            return
        root.joystickState = state
        root.allowsTouchInteraction = state === 0
    }

    function setRapid(enabled) {
        if (root.viewModel)
            return
        root.rapidMode = enabled
    }

    function setTouchEnabled(enabled) {
        if (root.viewModel)
            return
        root.allowsTouchInteraction = enabled
    }

    function resetAngle() {
        if (root.viewModel) {
            root.viewModel.resetAngleFeed()
        } else {
            root.angleFeedActive = false
        }
    }

    function isRotated() {
        return root.angleFeedActive
    }

    function colorString(value) {
        return Qt.rgba(value.r, value.g, value.b, value.a).toString()
    }

    function directionAngle(state) {
        if (state === 1)
            return -90
        if (state === 2)
            return 90
        if (state === 3)
            return 180
        if (state === 4)
            return 0
        return null
    }

    function isActiveAngle(angle) {
        return (angle === -90 && root.joystickState === 1)
            || (angle === 90 && root.joystickState === 2)
            || (angle === 180 && root.joystickState === 3)
            || (angle === 0 && root.joystickState === 4)
    }

    function roundedRect(ctx, x, y, width, height, radius) {
        ctx.beginPath()
        ctx.moveTo(x + radius, y)
        ctx.lineTo(x + width - radius, y)
        ctx.quadraticCurveTo(x + width, y, x + width, y + radius)
        ctx.lineTo(x + width, y + height - radius)
        ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height)
        ctx.lineTo(x + radius, y + height)
        ctx.quadraticCurveTo(x, y + height, x, y + height - radius)
        ctx.lineTo(x, y + radius)
        ctx.quadraticCurveTo(x, y, x + radius, y)
        ctx.closePath()
    }

    function drawCircle(ctx, cx, cy, radius, strokeColor, fillColor) {
        ctx.beginPath()
        ctx.arc(cx, cy, radius, 0, Math.PI * 2, false)
        if (fillColor !== null) {
            ctx.fillStyle = fillColor
            ctx.fill()
        }
        if (strokeColor !== null) {
            ctx.strokeStyle = strokeColor
            ctx.lineWidth = root.lineThickness
            ctx.stroke()
        }
    }

    function drawLine(ctx, xStart, yStart, xEnd, yEnd, color, lineWidth) {
        ctx.save()
        ctx.beginPath()
        ctx.strokeStyle = color
        ctx.lineWidth = lineWidth
        ctx.moveTo(xStart, yStart)
        ctx.lineTo(xEnd, yEnd)
        ctx.stroke()
        ctx.restore()
    }

    function drawDashedLine(ctx, xStart, yStart, xEnd, yEnd, color, lineWidth) {
        var dashLength = 3
        var gapLength = 3
        var dx = xEnd - xStart
        var dy = yEnd - yStart
        var length = Math.sqrt(dx * dx + dy * dy)
        var ux = dx / length
        var uy = dy / length
        var distance = 0

        while (distance < length) {
            var segmentEnd = Math.min(distance + dashLength, length)
            drawLine(
                ctx,
                xStart + ux * distance,
                yStart + uy * distance,
                xStart + ux * segmentEnd,
                yStart + uy * segmentEnd,
                color,
                lineWidth
            )
            distance += dashLength + gapLength
        }
    }

    function drawLabel(ctx, cx, cy, angleDeg, text, active, dashed) {
        var angleRad = (angleDeg + (dashed ? 0 : root.currentRotation)) * Math.PI / 180
        var xTip = cx + root.arrowTotalLength * Math.cos(angleRad)
        var yTip = cy + root.arrowTotalLength * Math.sin(angleRad)
        var x = xTip + root.labelDistanceFromTip * Math.cos(angleRad)
        var y = yTip + root.labelDistanceFromTip * Math.sin(angleRad)
        var rectX = x - root.labelWidth / 2
        var rectY = y - root.labelHeight / 2

        ctx.save()
        ctx.fillStyle = dashed ? colorString(root.dashedColor) : active ? colorString(root.feedColor) : colorString(root.blackColor)
        roundedRect(ctx, rectX, rectY, root.labelWidth, root.labelHeight, root.labelRadius)
        ctx.fill()
        ctx.fillStyle = "#ffffff"
        ctx.font = "13px sans-serif"
        ctx.textAlign = "center"
        ctx.textBaseline = "middle"
        ctx.fillText(text, x, y)
        ctx.restore()
    }

    function drawArrow(ctx, cx, cy, angleDeg, active) {
        var angleRad = (angleDeg + root.currentRotation) * Math.PI / 180
        var color = active ? colorString(root.feedColor) : colorString(root.blackColor)
        var positions = active && root.rapidMode ? [root.arrowTotalLength - 8, root.arrowTotalLength] : [root.arrowTotalLength]

        for (var i = 0; i < positions.length; i++) {
            var tipDistance = positions[i]
            var xStart = cx + root.arrowStartRadius * Math.cos(angleRad)
            var yStart = cy + root.arrowStartRadius * Math.sin(angleRad)
            var xLineEnd = cx + (tipDistance - 10) * Math.cos(angleRad)
            var yLineEnd = cy + (tipDistance - 10) * Math.sin(angleRad)
            var xTip = cx + tipDistance * Math.cos(angleRad)
            var yTip = cy + tipDistance * Math.sin(angleRad)
            var backOffset = root.arrowHeadSize * 1.5
            var baseWidth = root.arrowHeadSize * 2.5
            var perpAngle = angleRad + Math.PI / 2
            var baseCenterX = xTip - backOffset * Math.cos(angleRad)
            var baseCenterY = yTip - backOffset * Math.sin(angleRad)
            var leftX = baseCenterX + baseWidth / 2 * Math.cos(perpAngle)
            var leftY = baseCenterY + baseWidth / 2 * Math.sin(perpAngle)
            var rightX = baseCenterX - baseWidth / 2 * Math.cos(perpAngle)
            var rightY = baseCenterY - baseWidth / 2 * Math.sin(perpAngle)

            drawLine(ctx, xStart, yStart, xLineEnd, yLineEnd, color, root.arrowThickness)
            ctx.save()
            ctx.fillStyle = color
            ctx.beginPath()
            ctx.moveTo(xTip, yTip)
            ctx.lineTo(leftX, leftY)
            ctx.lineTo(rightX, rightY)
            ctx.closePath()
            ctx.fill()
            ctx.restore()
        }
    }

    onJoystickStateChanged: joystickCanvas.requestPaint()
    onRapidModeChanged: joystickCanvas.requestPaint()
    onCurrentRotationChanged: joystickCanvas.requestPaint()
    onRotationTargetChanged: {
        if (root.currentRotation !== root.rotationTarget) {
            root.rotationActive = true
            animationTimer.start()
        }
    }

    Timer {
        id: animationTimer
        interval: 16
        repeat: true
        onTriggered: {
            if (root.currentRotation < root.rotationTarget) {
                root.currentRotation = Math.min(root.currentRotation + 3, root.rotationTarget)
            } else if (root.currentRotation > root.rotationTarget) {
                root.currentRotation = Math.max(root.currentRotation - 3, root.rotationTarget)
            }

            if (root.currentRotation === root.rotationTarget) {
                root.rotationActive = false
                stop()
            }
        }
    }

    Canvas {
        id: joystickCanvas
        width: root.canvasWidth
        height: root.canvasHeight
        anchors.left: parent.left
        anchors.top: parent.top
        antialiasing: true
        z: 1

        onPaint: {
            var ctx = getContext("2d")
            var cx = width / 2
            var cy = height / 2
            var black = colorString(root.blackColor)
            var dashed = colorString(root.dashedColor)

            ctx.clearRect(0, 0, width, height)

            if (root.isRotated()) {
                var originalAngles = [-90, 90, 180, 0]
                for (var d = 0; d < originalAngles.length; d++) {
                    var dashedAngle = originalAngles[d]
                    var dashedRad = dashedAngle * Math.PI / 180
                    drawDashedLine(
                        ctx,
                        cx + root.arrowStartRadius * Math.cos(dashedRad),
                        cy + root.arrowStartRadius * Math.sin(dashedRad),
                        cx + root.arrowTotalLength * Math.cos(dashedRad),
                        cy + root.arrowTotalLength * Math.sin(dashedRad),
                        dashed,
                        root.lineThickness
                    )
                    drawLabel(ctx, cx, cy, dashedAngle, {"-90": "X-", "90": "X+", "180": "Z-", "0": "Z+"}[String(dashedAngle)], false, true)
                }
            }

            var activeDirection = root.directionAngle(root.joystickState)
            drawCircle(ctx, cx, cy, root.ringRadii[0], black, null)

            if (activeDirection !== null) {
                var activeRad = activeDirection * Math.PI / 180
                for (var r = 1; r < root.ringRadii.length; r++) {
                    var ringRadius = root.ringRadii[r]
                    var ringOffset = root.ringRadii[0] - ringRadius
                    drawCircle(
                        ctx,
                        cx + ringOffset * Math.cos(activeRad),
                        cy + ringOffset * Math.sin(activeRad),
                        ringRadius,
                        black,
                        null
                    )
                }
                var joystickOffset = root.ringRadii[0] - root.joystickRadius
                drawCircle(
                    ctx,
                    cx + joystickOffset * Math.cos(activeRad),
                    cy + joystickOffset * Math.sin(activeRad),
                    root.joystickRadius,
                    null,
                    black
                )
            } else {
                for (var neutralRing = 1; neutralRing < root.ringRadii.length; neutralRing++)
                    drawCircle(ctx, cx, cy, root.ringRadii[neutralRing], black, null)
                drawCircle(ctx, cx, cy, root.joystickRadius, null, black)
            }

            drawArrow(ctx, cx, cy, -90, root.isActiveAngle(-90))
            drawArrow(ctx, cx, cy, 90, root.isActiveAngle(90))
            drawArrow(ctx, cx, cy, 180, root.isActiveAngle(180))
            drawArrow(ctx, cx, cy, 0, root.isActiveAngle(0))

            drawLabel(ctx, cx, cy, -90, "X-", root.isActiveAngle(-90), false)
            drawLabel(ctx, cx, cy, 90, "X+", root.isActiveAngle(90), false)
            drawLabel(ctx, cx, cy, 180, "Z-", root.isActiveAngle(180), false)
            drawLabel(ctx, cx, cy, 0, "Z+", root.isActiveAngle(0), false)
        }
    }

    MouseArea {
        x: joystickCanvas.x
        y: joystickCanvas.y
        width: joystickCanvas.width
        height: joystickCanvas.height
        z: 2
        onPressed: {
            if (root.allowsTouchInteraction && !root.rotationActive) {
                root.angleFeedClicked()
            }
        }
    }

    Rectangle {
        x: 250
        y: 5
        width: 1
        height: parent.height - 10
        color: "#b7b7b7"
    }
}
